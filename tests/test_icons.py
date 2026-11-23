import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "architecture-presenter" / "scripts"))
import icons
from design_config import digest


def svg(color="#0078d4"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill="{color}" d="M1 1H15V15H1Z"/></svg>'.encode()


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as file:
        for name, data in files.items():
            file.writestr(name, data)
    return stream.getvalue()


class IconTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.presenter = self.project / "architecture"
        self.roots = {"user": self.root / "user", "machine": self.root / "machine"}
        self.calls = []
        self.terms = "Microsoft permits architecture diagrams. No branding use."
        self.pack = archive({"10000-icon-service-Function-Apps.svg": svg()})
        self.etag = "version-1"
        transport = patch("icons.fetch", side_effect=self.fetch)
        transport.start()
        self.addCleanup(transport.stop)

    def fetch(self, url, hosts, limit, headers=None, method="GET"):
        self.calls.append((url, headers, method))
        if url == icons.PROVIDERS["azure"]["source"]:
            html = f'<h2>Do\'s</h2><p>Keep names nearby.</p><h2>Icon terms</h2><p>{self.terms}</p>' \
                   '<a href="https://arch-center.azureedge.net/icons/test.zip">Download SVG icons</a>'
            return html.encode(), {}
        self.assertEqual(url, "https://arch-center.azureedge.net/icons/test.zip")
        if method == "HEAD":
            return b"", {"etag": self.etag}
        if (headers or {}).get("If-None-Match") == self.etag:
            return None, {}
        return self.pack, {"etag": self.etag}

    def approve(self, scope="user", updates="auto"):
        hash_ = icons.metadata("azure")["termsHash"]
        result = icons.approve(self.project, self.presenter, "azure", hash_, scope, updates, self.roots)
        policy, cache = icons.stores(self.project, self.presenter, self.roots)["azure"]
        self.calls.clear()
        return result, policy, cache

    def views(self):
        return {"system": {"components": [{"service": "azure:functions"}]}}

    def test_no_approval_and_offline_modes_never_fetch(self):
        self.assertEqual(icons.monitor(self.project, self.presenter, self.roots), [])
        self.assertEqual(self.calls, [])
        _, _, cache = self.approve()
        self.assertEqual(icons.monitor(self.project, self.presenter, self.roots, offline=True), [])
        self.assertEqual(self.calls, [])
        self.assertTrue((cache / "current.json").exists())

    def test_initial_download_requires_exact_current_terms(self):
        with self.assertRaisesRegex(ValueError, "Terms changed"):
            icons.approve(self.project, self.presenter, "azure", "0" * 64, roots=self.roots)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((self.roots["user"] / "icons").exists())

    def test_daily_updates_cache_new_pack_without_refreshing_snapshot(self):
        old, policy, cache = self.approve()
        first = icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)
        pinned = (self.presenter / "icons.lock.json").read_bytes()
        self.pack = archive({"10000-icon-service-Function-Apps.svg": svg("#ff8800")})
        self.etag = "version-2"
        state = json.loads((cache / "check.json").read_text())
        self.assertFalse(icons.check("azure", policy, cache, now=state["attemptedAt"] + 10)["checked"])
        self.assertEqual(self.calls, [])
        result = icons.check("azure", policy, cache, now=state["attemptedAt"] + icons.INTERVAL)
        self.assertEqual(result["status"], "updated")
        self.assertNotEqual(result["packHash"], old["packHash"])
        self.assertEqual(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots), first)
        self.assertEqual((self.presenter / "icons.lock.json").read_bytes(), pinned)
        self.assertNotEqual(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots, refresh=True), first)

    def test_in_place_pack_updates_and_not_modified_responses(self):
        original, policy, cache = self.approve()
        result = icons.check("azure", policy, cache, force=True)
        self.assertEqual(result["status"], "unchanged")
        result = icons.check("azure", policy, cache, now=result["attemptedAt"] + icons.INTERVAL)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(json.loads((cache / "current.json").read_text())["packHash"], original["packHash"])
        self.assertEqual(self.calls[-1][1]["If-None-Match"], "version-1")

    def test_changed_guidelines_or_terms_require_consent_without_pack_fetch(self):
        original, policy, cache = self.approve()
        self.terms = "Additional restrictions apply."
        result = icons.check("azure", policy, cache, force=True)
        self.assertEqual(result["status"], "terms-changed")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(json.loads((cache / "current.json").read_text())["packHash"], original["packHash"])

    def test_version_button_changes_do_not_change_terms_hash(self):
        def page(version):
            return (f'<h2>Icon terms</h2><p>{self.terms}</p>'
                    '<p>I agree to the above terms.</p>'
                    f'<a href="https://arch-center.azureedge.net/icons/{version}.zip">'
                    f'Download SVG icons ({version})</a>').encode()
        with patch("icons.fetch", return_value=(page("v1"), {})):
            first = icons.metadata("azure")
        with patch("icons.fetch", return_value=(page("v2"), {})):
            second = icons.metadata("azure")
        self.assertEqual(first["termsHash"], second["termsHash"])
        self.assertNotEqual(first["download"], second["download"])

    def test_malformed_cache_does_not_break_pinned_build_and_explicit_fetch_repairs_it(self):
        original, policy, cache = self.approve()
        pinned = icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)
        (cache / "current.json").write_text('{"provider":"azure"}')
        state = json.loads((cache / "check.json").read_text())
        result = icons.check("azure", policy, cache, now=state["attemptedAt"] + icons.INTERVAL)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots), pinned)
        self.assertEqual(icons.check("azure", policy, cache, force=True, download=True)["status"], "updated")
        self.assertEqual(json.loads((cache / "current.json").read_text())["packHash"], original["packHash"])

    def test_failed_checks_are_throttled_and_keep_existing_pack(self):
        original, policy, cache = self.approve()
        with patch("icons.metadata", side_effect=OSError("offline")) as request:
            result = icons.check("azure", policy, cache, force=True)
            self.assertEqual(result["status"], "unavailable")
            again = icons.check("azure", policy, cache, now=result["attemptedAt"] + 1)
            self.assertFalse(again["checked"])
            self.assertEqual(request.call_count, 1)
        with patch("zipfile.ZipFile.read", side_effect=NotImplementedError("unsupported compression")):
            self.assertEqual(icons.check("azure", policy, cache, force=True)["status"], "unavailable")
        self.assertEqual(json.loads((cache / "current.json").read_text())["packHash"], original["packHash"])

    def test_notify_and_off_policies_do_not_download_updates(self):
        _, policy, cache = self.approve(updates="notify")
        self.etag = "new-version"
        result = icons.check("azure", policy, cache, force=True)
        self.assertEqual(result["status"], "update-review-needed")
        self.assertEqual(self.calls[-1][2], "HEAD")
        self.calls.clear()
        self.assertEqual(icons.check("azure", {**policy, "updates": "off"}, cache)["status"], "off")
        self.assertEqual(self.calls, [])

    def test_scoped_policy_override_and_busy_update_preserve_cache(self):
        _, _, user_cache = self.approve()
        _, policy, cache = self.approve(scope="project", updates="off")
        self.assertEqual(cache, user_cache)
        self.assertEqual(policy["updates"], "off")
        (cache / "update.lock").write_text("Busy")
        self.assertEqual(icons.check("azure", policy, cache, force=True)["status"], "busy")
        self.assertEqual(self.calls, [])

    def test_cache_is_independent_of_theme_profile_and_user_approval_is_local(self):
        user = self.roots["user"]
        user.mkdir()
        work = self.root / "work"
        work.mkdir()
        (user / "libraries.json").write_text(json.dumps({
            "schemaVersion": 1, "default": "local", "profiles": {"work": str(work)}}))
        self.presenter.mkdir()
        (self.presenter / "design.lock.json").write_text(json.dumps({"userLibrary": "work"}))
        paths = icons.locations(self.project, self.presenter, self.roots)
        self.assertEqual(paths["user"], work)
        self.assertEqual(icons.locations(self.project, self.presenter, self.roots, "local")["user"], user)
        self.approve()
        _, cache = icons.stores(self.project, self.presenter, self.roots, "work")["azure"]
        _, local = icons.stores(self.project, self.presenter, self.roots, "local")["azure"]
        self.assertEqual(cache, local)
        self.assertFalse(cache.is_relative_to(work))
        self.assertTrue((user / "icons" / "approvals" / "azure.json").exists())
        self.assertFalse((work / "icons").exists())

    def test_shared_pack_reuse_does_not_widen_project_consent(self):
        original, _, cache = self.approve(scope="project")
        other = self.root / "other"
        other.mkdir()
        presenter = other / "architecture"
        self.assertEqual(icons.resolve_icons(self.views(), presenter, other, self.roots), {})
        self.assertEqual(self.calls, [])
        result = icons.approve(other, presenter, "azure", original["termsHash"], "project", roots=self.roots)
        self.assertEqual(result["packHash"], original["packHash"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], icons.PROVIDERS["azure"]["source"])
        self.calls.clear()
        other_policy, other_cache = icons.stores(other, presenter, self.roots)["azure"]
        self.assertEqual(other_cache, cache)
        self.assertFalse(icons.check("azure", other_policy, other_cache)["checked"])
        self.assertEqual(self.calls, [])
        self.assertTrue(icons.resolve_icons(self.views(), presenter, other, self.roots, refresh=True))

    def test_terms_versions_and_daily_state_cannot_cross_scope_consent(self):
        original, old_policy, cache = self.approve()
        old_bytes = svg()
        self.terms = "New conditions require renewed consent."
        self.pack = archive({"Function-Apps.svg": svg("#ff8800")})
        self.etag = "new-terms-pack"
        other = self.root / "other"
        other.mkdir()
        presenter = other / "architecture"
        terms_hash = icons.metadata("azure")["termsHash"]
        icons.approve(other, presenter, "azure", terms_hash, "project", roots=self.roots)
        new_policy, new_cache = icons.stores(other, presenter, self.roots)["azure"]
        self.calls.clear()
        self.assertEqual(icons.check("azure", old_policy, cache)["status"], "terms-changed")
        self.assertFalse(icons.check("azure", new_policy, new_cache)["checked"])
        self.assertEqual(self.calls, [])
        self.assertEqual(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)["azure:functions"], old_bytes)
        self.assertEqual(icons.resolve_icons(self.views(), presenter, other, self.roots)["azure:functions"], svg("#ff8800"))
        self.assertEqual(icons.read_pack(cache, "azure", original["termsHash"])["packHash"], original["packHash"])

    def test_approved_legacy_cache_can_be_used_offline_and_copied_without_moving(self):
        work = self.root / "work"
        work.mkdir()
        user = self.roots["user"]
        user.mkdir()
        icons.atomic_json(user / "libraries.json", {
            "schemaVersion": 1, "default": "work", "profiles": {"work": str(work)}})
        old_cache = work / "icons" / "cache" / "azure"
        meta = icons.metadata("azure")
        with icons.writing(old_cache):
            original = icons.cache_pack(old_cache, meta)
        icons.atomic_json(work / "icons" / "approvals" / "azure.json",
                          {"schemaVersion": 1, "provider": "azure", "termsHash": meta["termsHash"], "updates": "auto"})
        before = {p: p.read_bytes() for p in work.rglob("*") if p.is_file()}
        self.calls.clear()
        self.assertTrue(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots))
        result = icons.migrate(self.project, self.presenter, "azure", self.roots)
        self.assertEqual(result["packHash"], original["packHash"])
        self.assertEqual(self.calls, [])
        self.assertEqual(before, {p: p.read_bytes() for p in work.rglob("*") if p.is_file()})
        self.assertFalse((user / "icons" / "approvals" / "azure.json").exists())
        _, cache = icons.stores(self.project, self.presenter, self.roots)["azure"]
        self.assertFalse(cache.is_relative_to(work))
        self.assertEqual(icons.read_pack(cache, "azure", meta["termsHash"])["packHash"], original["packHash"])

    def test_device_paths_are_local_platform_cache_paths(self):
        home = self.root / "home"
        local = self.root / "local"
        self.assertEqual(icons.device_root(platform="win32", env={"LOCALAPPDATA": str(local)}, home=home),
                         local / "architecture-presenter")
        self.assertEqual(icons.device_root(platform="darwin", env={}, home=home),
                         home / "Library" / "Caches" / "architecture-presenter")
        self.assertEqual(icons.device_root(platform="linux", env={"XDG_CACHE_HOME": "relative"}, home=home),
                         home / ".cache" / "architecture-presenter")
        self.assertEqual(icons.device_root(env={"ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root)}),
                         self.root / "device")

    def test_notify_then_auto_shares_discovery_but_can_download_once(self):
        _, policy, cache = self.approve(updates="notify")
        self.etag = "new-version"
        state = icons.read_json(cache / "check.json")
        now = state["attemptedAt"] + icons.INTERVAL
        self.assertEqual(icons.check("azure", policy, cache, now=now)["status"], "update-review-needed")
        self.calls.clear()
        self.assertEqual(icons.check("azure", {**policy, "updates": "auto"}, cache, now=now + 1)["status"], "unchanged")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], "https://arch-center.azureedge.net/icons/test.zip")
        self.calls.clear()
        self.assertFalse(icons.check("azure", policy, cache, now=now + 2)["checked"])
        self.assertEqual(self.calls, [])
        unchanged = icons.check("azure", policy, cache, now=now + icons.INTERVAL + 1)
        self.assertEqual(unchanged["status"], "unchanged")
        self.calls.clear()
        self.assertFalse(icons.check("azure", {**policy, "updates": "auto"}, cache,
                                    now=now + icons.INTERVAL + 2)["checked"])
        self.assertEqual(self.calls, [])

    def test_snapshot_rebuild_does_not_need_libraries_and_rejects_tampering(self):
        self.approve()
        images = icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)
        shutil.rmtree(self.roots["user"])
        self.assertEqual(icons.resolve_icons(self.views(), self.presenter, self.project, roots={}), images)
        asset = next((self.presenter / "icon-assets").glob("*.svg"))
        asset.write_bytes(svg("#ffffff"))
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            icons.resolve_icons(self.views(), self.presenter, self.project, roots={})

    def test_ambiguous_icons_require_explicit_choice_and_lock_tracks_it(self):
        self.pack = archive({"a/Function-Apps.svg": svg(), "b/Function-Apps.svg": svg("#ffffff")})
        self.approve()
        self.assertEqual(icons.resolve_icons(self.views(), self.presenter, self.project, self.roots), {})
        (self.presenter / "icon-selections.json").write_text(json.dumps({"azure:functions": "b/Function-Apps.svg"}))
        with self.assertRaisesRegex(ValueError, "lock changed"):
            icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)
        result = icons.resolve_icons(self.views(), self.presenter, self.project, self.roots, refresh=True)
        self.assertEqual(result["azure:functions"], svg("#ffffff"))

    def test_archive_traversal_and_active_svg_are_rejected(self):
        for name in ("../outside.svg", "/outside.svg", r"..\outside.svg", "C:/outside.svg"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe"):
                icons.unpack(archive({name: svg()}), self.root)
        invalid = [
            b'<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>',
            svg().replace(b"<path ", b'<script/> <path '),
            svg().replace(b"<path ", b'<path onclick="alert(1)" '),
            svg().replace(b"<path ", b'<use href="https://example.invalid/icon.svg"/> <path '),
            svg().replace(b'fill="#0078d4"', b'fill="url(https://example.invalid/icon)"'),
            svg().replace(b"<path ", b'<style>@import "https://example.invalid/x.css";</style><path '),
            svg().replace(b"<path ", b'<foreignObject/> <path '),
        ]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                icons.safe_svg(data)
        self.assertEqual(icons.safe_svg(svg()), svg())

    def test_transport_hosts_and_provenance_cannot_escape_official_sources(self):
        for url in ("http://download.microsoft.com/a.zip", "https://download.microsoft.com.evil.invalid/a.zip",
                    "https://@download.microsoft.com/a.zip",
                    "https://user@download.microsoft.com/a.zip"):
            with self.assertRaisesRegex(ValueError, "official HTTPS"):
                icons.validate_url(url, ("download.microsoft.com",))
        self.approve()
        icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)
        path = self.presenter / "icons.lock.json"
        lock = json.loads(path.read_text())
        lock["icons"]["azure:functions"]["source"] = "javascript:alert(1)"
        lock["hash"] = digest({k: v for k, v in lock.items() if k != "hash"})
        path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, "provenance"):
            icons.resolve_icons(self.views(), self.presenter, self.project, self.roots)

    def test_explicit_refetch_repairs_corrupted_cache(self):
        current, policy, cache = self.approve()
        asset = cache / current["packHash"] / (current["items"][0]["sha256"] + ".svg")
        asset.write_bytes(b"corrupted")
        self.assertEqual(icons.check("azure", policy, cache, force=True, download=True)["status"], "unchanged")
        self.assertEqual(asset.read_bytes(), svg())

    def test_github_official_source_consent_and_variant_selection(self):
        pack = archive({"GitHub_Invertocat_Black.svg": svg("#000000"),
                        "GitHub_Invertocat_White.svg": svg("#ffffff")})
        calls = []

        def fetch(url, hosts, limit, headers=None, method="GET"):
            calls.append(url)
            if url == icons.PROVIDERS["github"]["source"]:
                return (b'<h1>Logo</h1><a href="/GitHub_Logos.zip">Download the logo files</a>'
                        b'<h2>Legal</h2><p>Use permitted logos only to link or show integration.</p>'), {}
            if url == icons.PROVIDERS["github"]["guidelines"]:
                return b'<h1>Co-branding</h1><p>Do not imply endorsement or modify logos.</p>', {}
            self.assertEqual(url, "https://brand.github.com/GitHub_Logos.zip")
            return pack, {}

        with patch("icons.fetch", side_effect=fetch):
            meta = icons.metadata("github")
            with self.assertRaisesRegex(ValueError, "Terms changed"):
                icons.approve(self.project, self.presenter, "github", "0" * 64, roots=self.roots)
            self.assertFalse(any(url.endswith(".zip") for url in calls))
            icons.approve(self.project, self.presenter, "github", meta["termsHash"], roots=self.roots)
            views = {"system": {"components": [{"service": "github:github"}]}}
            self.assertEqual(icons.resolve_icons(views, self.presenter, self.project, self.roots), {})
            (self.presenter / "icon-selections.json").write_text(json.dumps({
                "github:github": "GitHub_Invertocat_Black.svg"}))
            selected = icons.resolve_icons(views, self.presenter, self.project, self.roots, refresh=True)
            self.assertEqual(selected["github:github"], svg("#000000"))
            self.assertIn("Do not imply endorsement", meta["terms"])

    def test_github_supplementary_guidelines_changes_stop_downloads(self):
        guide = "Linking and integration only."
        calls = []

        def fetch(url, hosts, limit, headers=None, method="GET"):
            calls.append(url)
            if url == icons.PROVIDERS["github"]["source"]:
                return (b'<h1>Logo</h1><a href="/GitHub_Logos.zip">Download the logo files</a>'
                        b'<h2>Legal</h2><p>Keep names nearby and respect trademarks.</p>'), {}
            if url == icons.PROVIDERS["github"]["guidelines"]:
                return f'<h1>Co-branding</h1><p>{guide}</p>'.encode(), {}
            return archive({"GitHub_Invertocat_Black.svg": svg()}), {}

        with patch("icons.fetch", side_effect=fetch):
            meta = icons.metadata("github")
            icons.approve(self.project, self.presenter, "github", meta["termsHash"], roots=self.roots)
            policy, cache = icons.stores(self.project, self.presenter, self.roots)["github"]
            guide = "Updated permission restrictions."
            calls.clear()
            self.assertEqual(icons.check("github", policy, cache, force=True)["status"], "terms-changed")
            self.assertEqual(len(calls), 2)
            self.assertFalse(any(url.endswith(".zip") for url in calls))

    def test_github_source_must_have_legal_conditions_and_official_download(self):
        with patch("icons.fetch", return_value=(
                b'<h1>Logo</h1><a href="https://example.invalid/a.zip">Download the logo files</a>', {})):
            with self.assertRaisesRegex(ValueError, "legal"):
                icons.metadata("github")
        def fetch(url, hosts, limit, headers=None, method="GET"):
            if url == icons.PROVIDERS["github"]["guidelines"]:
                return b'<h1>Co-branding</h1><p>Guidelines.</p>', {}
            return (b'<h1>Logo</h1><h2>Legal</h2><p>Terms.</p>'
                    b'<a href="https://example.invalid/a.zip">Download the logo files</a>'), {}
        with patch("icons.fetch", side_effect=fetch), self.assertRaisesRegex(ValueError, "official HTTPS"):
            icons.metadata("github")

    def test_octicons_revision_changes_preserve_license_consent_and_filter_archive(self):
        revision = "1" * 40
        license_ = "MIT License\nCopyright GitHub\nPermission is hereby granted.\nTHE SOFTWARE IS PROVIDED AS IS."
        calls = []
        def fetch(url, hosts, limit, headers=None, method="GET"):
            calls.append(url)
            if url == icons.PROVIDERS["octicons"]["revision"]:
                return json.dumps({"sha": revision}).encode(), {}
            if url.endswith("/LICENSE"):
                self.assertIn(revision, url)
                return license_.encode(), {}
            self.assertEqual(url, f"https://codeload.github.com/primer/octicons/zip/{revision}")
            return archive({f"octicons-{revision}/icons/repo-16.svg": svg(),
                            f"octicons-{revision}/docs/unrelated.svg": svg("#ffffff")}), {}
        with patch("icons.fetch", side_effect=fetch):
            first = icons.metadata("octicons")
            revision = "2" * 40
            second = icons.metadata("octicons")
            self.assertEqual(first["termsHash"], second["termsHash"])
            self.assertNotEqual(first["download"], second["download"])
            current = icons.approve(self.project, self.presenter, "octicons", first["termsHash"], roots=self.roots)
            self.assertEqual(len(current["items"]), 1)
            selected = icons.resolve_icons({"ui": {"components": [{"service": "octicons:repo"}]}},
                                          self.presenter, self.project, self.roots)
            self.assertEqual(selected["octicons:repo"], svg())
            self.assertIn("MIT License", current["terms"])
            revision = "3" * 40
            license_ += "\nChanged license conditions."
            with self.assertRaisesRegex(ValueError, "Terms changed"):
                icons.approve(self.project, self.presenter, "octicons", first["termsHash"], roots=self.roots)
            self.assertNotIn(f"https://codeload.github.com/primer/octicons/zip/{revision}", calls)

    def test_octicons_requires_an_immutable_revision_and_expected_license(self):
        for revision in (None, "main", "a" * 39, "A" * 40):
            with self.subTest(revision=revision), patch(
                    "icons.fetch", return_value=(json.dumps({"sha": revision}).encode(), {})) as fetch:
                with self.assertRaisesRegex(ValueError, "immutable"):
                    icons.metadata("octicons")
                self.assertEqual(fetch.call_count, 1)
        with patch("icons.fetch", side_effect=[
                (json.dumps({"sha": "a" * 40}).encode(), {}), (b"Unreviewed license", {})]) as fetch:
            with self.assertRaisesRegex(ValueError, "expected Octicons license"):
                icons.metadata("octicons")
            self.assertEqual(fetch.call_count, 2)

    def test_storage_cli_and_legacy_revocation_use_separate_policy_roots(self):
        legacy = {"user": self.root / "legacy"}
        current = self.roots["user"] / "icons" / "approvals" / "azure.json"
        old = legacy["user"] / "icons" / "approvals" / "azure.json"
        icons.atomic_json(current, {"test": "current"})
        icons.atomic_json(old, {"test": "legacy"})
        def run(*arguments):
            with patch("sys.argv", ["icons.py", "--project-root", str(self.project),
                                   "--user-library", "work", *arguments]), patch("sys.stdout", io.StringIO()) as output:
                icons.main()
                return output.getvalue()
        with patch("icons.policy_locations", return_value=self.roots), \
                patch("icons.locations", return_value=legacy) as locations, \
                patch("icons.device_root", return_value=self.root / "device"):
            storage = json.loads(run("storage"))
            self.assertEqual(storage["cache"], str(self.root / "device" / "icons" / "cache"))
            self.assertEqual(storage["approvals"]["user"], str(current.parent))
            locations.assert_not_called()
            run("revoke", "azure", "--scope", "user")
            self.assertFalse(current.exists())
            self.assertTrue(old.exists())
            icons.atomic_json(current, {"test": "keep"})
            run("revoke", "azure", "--scope", "user", "--legacy")
            self.assertTrue(current.exists())
            self.assertFalse(old.exists())
            locations.assert_called_once_with(self.project.resolve(), self.presenter.resolve(), profile="work")

    def test_inline_glyphs_cannot_inject_parent_styles_ids_or_behavior(self):
        for injection in (b'<style>.node {display:none}</style>', b'<g id="arrow"/>',
                          b'<path data-phase="999" d="M0 0"/>', b'<use href="#arrow"/>'):
            with self.subTest(injection=injection), self.assertRaises(ValueError):
                icons.safe_glyph(svg().replace(b"<path ", injection + b"<path "))
        self.assertEqual(icons.safe_glyph(svg()), svg())


if __name__ == "__main__":
    unittest.main()

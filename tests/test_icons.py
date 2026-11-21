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
        self.assertNotEqual(cache, user_cache)
        self.assertEqual(policy["updates"], "off")
        (cache / "update.lock").write_text("Busy")
        self.assertEqual(icons.check("azure", policy, cache, force=True)["status"], "busy")
        self.assertEqual(self.calls, [])

    def test_cache_routing_uses_locked_profile_not_changed_device_default(self):
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


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "architecture-presenter" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import design_config as design
from designs import copy_design
import user_libraries as libraries

spec = importlib.util.spec_from_file_location("profile_bootstrap", SCRIPTS / "init.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def theme(color):
    return {"schemaVersion": 1, "id": "sample", "label": "Sample", "base": "fluent",
            "defaultAppearance": "dark", "appearances": {"dark": {"accent": color}}}


class UserLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.local = self.root / "host" / "user"
        self.roots = {"user": self.local, "machine": self.root / "host" / "machine"}
        self.presenter = self.root / "architecture"
        self.work = self.root / "work"
        self.other = self.root / "other-work"
        self.personal = self.root / "personal"
        for path in (self.work, self.other, self.personal):
            path.mkdir()
        self.env = {**os.environ, "ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root / "host")}

    def register_all(self):
        for name, root in (("work", self.work), ("other-work", self.other), ("personal", self.personal)):
            libraries.register(self.local, name, root)

    def resolve(self, overrides=None, refresh=False):
        return design.resolve_design(self.root, self.presenter, overrides, refresh, self.roots)

    def run_cli(self, *args, script=None):
        return subprocess.run([sys.executable, str(script or SCRIPTS / "designs.py"), *args],
                              env=self.env, cwd=self.root, text=True, capture_output=True)

    def test_discovers_three_accounts_despite_environment_aliases(self):
        accounts = [("Business1", str(self.work)), ("Business2", str(self.other)), ("Personal", str(self.personal))]
        env = {"OneDrive": str(self.work), "OneDriveCommercial": str(self.work),
               "OneDriveConsumer": str(self.personal)}
        found = libraries.discover_onedrive(accounts, env)
        self.assertEqual(len(found), 3)
        self.assertTrue(all(item["available"] for item in found))
        self.assertEqual({row["root"] for row in found}, {str(self.work), str(self.other), str(self.personal)})
        self.assertFalse((self.local / "libraries.json").exists(), "Discovery never registers or selects")
        self.assertEqual(libraries.discover_onedrive([], {"OneDrive": str(self.work)})[0]["root"], str(self.work))
        self.assertEqual(libraries.discover_onedrive([], {"OneDrive": "relative"}), [])

    def test_registration_is_explicit_and_does_not_change_default(self):
        self.register_all()
        registry = libraries.read_registry(self.local)
        self.assertEqual(registry["default"], "local")
        self.assertEqual(set(registry["profiles"]), {"work", "other-work", "personal"})
        with self.assertRaises(FileExistsError):
            libraries.register(self.local, "work", self.personal)
        with self.assertRaisesRegex(ValueError, "already mapped"):
            libraries.register(self.local, "duplicate", self.work)
        for name, path in (("../bad", self.work), ("local", self.work), ("new", Path("relative"))):
            with self.subTest(name=name), self.assertRaises(ValueError):
                libraries.register(self.local, name, path)
        self.assertEqual(libraries.read_registry(self.local), registry)

    def test_create_does_not_recreate_missing_sync_root(self):
        with self.assertRaisesRegex(ValueError, "parent"):
            libraries.register(self.local, "missing", self.root / "missing-sync" / "library", create=True)
        self.assertFalse((self.root / "missing-sync").exists())
        root = libraries.register(self.local, "work", self.work / "Architecture Presenter", create=True)
        self.assertTrue(root.is_dir())
        self.assertFalse((root / "config.json").exists())

    def test_no_automatic_merge_and_explicit_local_fallback(self):
        self.register_all()
        design.write_json(self.local / "themes" / "local-only.json",
                          {**theme("#000000"), "id": "local-only"})
        design.write_json(self.work / "themes" / "sample.json", theme("#123456"))
        design.write_json(self.personal / "themes" / "sample.json", theme("#abcdef"))
        libraries.set_default(self.local, "work")
        locked = self.resolve({"theme": "user:sample"})
        self.assertEqual(locked["userLibrary"], "work")
        self.assertEqual(locked["themes"]["sample"]["appearances"]["dark"]["accent"], "#123456")
        self.assertNotIn(str(self.root), json.dumps(locked))
        with self.assertRaisesRegex(ValueError, "Missing selected"):
            self.resolve({"theme": "user:local-only"})
        local = self.resolve({"userLibrary": "local", "theme": "user:local-only"})
        self.assertEqual(local["userLibrary"], "local")
        self.assertNotIn("sample", local["themes"])

    def test_routing_precedence_cli_project_repo_device_default(self):
        self.register_all()
        libraries.set_default(self.local, "work")
        repo = self.root / ".architecture-presenter" / "config.json"
        project = self.presenter / "presenter.json"
        self.assertEqual(self.resolve(refresh=True)["userLibrary"], "work")
        design.write_json(repo, {"schemaVersion": 1, "userLibrary": "personal"})
        self.assertEqual(self.resolve(refresh=True)["userLibrary"], "personal")
        design.write_json(project, {"schemaVersion": 1, "userLibrary": "other-work"})
        self.assertEqual(self.resolve(refresh=True)["userLibrary"], "other-work")
        self.assertEqual(self.resolve({"userLibrary": "local"})["userLibrary"], "local")
        design.write_json(self.other / "config.json", {"schemaVersion": 1, "userLibrary": "work"})
        with self.assertRaisesRegex(ValueError, "only be set"):
            self.resolve(refresh=True)

    def test_unavailable_or_unknown_profile_errors_without_fallback(self):
        self.register_all()
        libraries.set_default(self.local, "work")
        self.work.rmdir()
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.resolve()
        with self.assertRaisesRegex(ValueError, "Unknown user library"):
            self.resolve({"userLibrary": "unregistered"})
        with self.assertRaisesRegex(ValueError, "named local library"):
            self.resolve({"userLibrary": ""})
        self.assertEqual(self.resolve({"userLibrary": "local"})["userLibrary"], "local")

    def test_user_settings_are_read_only_from_selected_profile(self):
        self.register_all()
        libraries.set_default(self.local, "work")
        design.write_json(self.local / "config.json", {"schemaVersion": 1, "appearance": "light"})
        design.write_json(self.work / "config.json", {"schemaVersion": 1, "appearance": "dark"})
        lock = self.resolve()
        self.assertEqual(lock["settings"]["appearance"], "dark")
        self.assertEqual(self.resolve({"userLibrary": "local"})["settings"]["appearance"], "light")

    def test_lock_survives_missing_profile_corrupt_registry_and_legacy_locks(self):
        self.register_all()
        design.write_json(self.work / "themes" / "sample.json", theme("#123456"))
        libraries.set_default(self.local, "work")
        locked = self.resolve({"theme": "user:sample"})
        shutil.rmtree(self.work)
        (self.local / "libraries.json").write_text("not JSON", encoding="utf-8")
        self.assertEqual(self.resolve(), locked)
        with self.assertRaisesRegex(ValueError, "registry"):
            self.resolve(refresh=True)
        legacy = {key: value for key, value in locked.items() if key != "userLibrary"}
        legacy["hash"] = design.digest({key: value for key, value in legacy.items() if key != "hash"})
        design.write_json(self.presenter / "design.lock.json", legacy)
        self.assertEqual(self.resolve(), legacy)

    def test_copied_engine_builds_offline_without_profile_registry(self):
        self.register_all()
        design.write_json(self.work / "themes" / "sample.json", theme("#123456"))
        libraries.set_default(self.local, "work")
        output = bootstrap.initialize(self.root, overrides={"userLibrary": "work", "theme": "user:sample"},
                                      roots=self.roots)
        shutil.rmtree(self.work)
        (self.local / "libraries.json").unlink()
        result = self.run_cli("--input", str(output / "story.json"), "--project-root", str(self.root),
                              "--output", str(output), script=output / "build.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"sample"', (output / "presenter.html").read_text(encoding="utf-8"))
        result = self.run_cli("--project-root", str(self.root), "inspect", script=output / "designs.py")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_copy_keeps_original_refuses_overwrite_and_validates(self):
        self.register_all()
        source = self.local / "themes" / "sample.json"
        design.write_json(source, theme("#123456"))
        library = design.Library(self.root, self.presenter, self.roots)
        target = copy_design(library, "themes", "sample", "local", "work")
        self.assertEqual(source.read_bytes(), target.read_bytes())
        with self.assertRaises(FileExistsError):
            copy_design(library, "themes", "sample", "local", "work")
        with self.assertRaises(ValueError):
            copy_design(library, "themes", "../sample", "local", "work")
        self.assertEqual(libraries.read_registry(self.local)["default"], "local")

    def test_cli_profiles_scaffolding_selection_and_legacy_defaults(self):
        for name, path in (("work", self.work), ("personal", self.personal)):
            result = self.run_cli("libraries", "add", name, "--path", str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("libraries", "use", "work")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("libraries", "list")
        self.assertIn("work:", result.stdout)
        self.assertIn("[default]", result.stdout)
        result = self.run_cli("--user-library", "personal", "new", "themes", "sample", "--scope", "user")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.personal / "themes" / "sample.json").exists())
        self.assertFalse((self.work / "themes" / "sample.json").exists())
        result = self.run_cli("libraries", "copy", "themes", "sample", "--from", "personal", "--to", "work")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.personal / "themes" / "sample.json").read_bytes(),
                         (self.work / "themes" / "sample.json").read_bytes())
        result = self.run_cli("libraries", "copy", "themes", "sample", "--from", "personal", "--to", "work")
        self.assertNotEqual(result.returncode, 0)
        result = self.run_cli("select", "--user-library", "personal", "--theme", "user:sample")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(design.read_json(self.presenter / "presenter.json")["userLibrary"], "personal")
        self.assertEqual(design.read_json(self.presenter / "design.lock.json")["userLibrary"], "personal")
        result = self.run_cli("libraries", "use", "local")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(libraries.read_registry(self.local)["default"], "local")


if __name__ == "__main__":
    unittest.main()

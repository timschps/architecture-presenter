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
import build
import design_config as design
from designs import scaffold

spec = importlib.util.spec_from_file_location("design_bootstrap", SCRIPTS / "init.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def theme(id_="ocean", color="#006666"):
    return {"schemaVersion": 1, "id": id_, "label": "Ocean",
            "base": "fluent", "defaultAppearance": "dark",
            "appearances": {"dark": {"accent": color}}}


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.presenter = self.root / "architecture"
        self.roots = {"user": self.root / "user", "machine": self.root / "machine"}
        self.library = design.Library(self.root, self.presenter, self.roots)

    def write(self, path, value):
        design.write_json(path, value)

    def resolve(self, overrides=None, refresh=False):
        return design.resolve_design(self.root, self.presenter, overrides, refresh, self.roots)

    def test_platform_roots_and_isolated_override(self):
        roots = design.platform_roots("win32", {"APPDATA": str(self.root / "roaming"),
                                               "PROGRAMDATA": str(self.root / "shared")}, self.root)
        self.assertEqual(roots["user"], self.root / "roaming" / "architecture-presenter")
        self.assertEqual(roots["machine"], self.root / "shared" / "architecture-presenter")
        self.assertEqual(design.platform_roots("linux", {}, self.root)["user"],
                         self.root / ".config" / "architecture-presenter")
        self.assertEqual(design.platform_roots("linux", {"XDG_CONFIG_HOME": "relative"}, self.root)["user"],
                         self.root / ".config" / "architecture-presenter")
        self.assertEqual(design.platform_roots("darwin", {}, self.root)["machine"],
                         Path("/Library/Application Support/architecture-presenter"))
        self.assertEqual(design.platform_roots(env={"ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root)})["user"],
                         self.root / "user")

    def test_settings_precedence_and_whole_definition_shadowing(self):
        roots = self.library.roots
        for index, scope in enumerate(design.SCOPES[1:]):
            root = roots[scope]
            config = "presenter.json" if scope == "project" else "config.json"
            self.write(root / config, {"schemaVersion": 1, "theme": "ocean", "appearance": "dark"})
            value = theme(color=f"#00000{index}")
            self.write(root / "themes" / "ocean.json", value)
        settings, _ = self.library.settings({"appearance": "light"})
        self.assertEqual(settings["appearance"], "light")
        result = self.library.resolve("themes", settings["theme"])
        self.assertEqual(result["appearances"]["dark"]["accent"], "#000003")
        self.assertEqual(result["appearances"]["dark"]["text"], self.library.base["appearances"]["dark"]["text"])
        self.assertNotIn("light", result["appearances"])
        self.assertEqual(self.library.resolve("themes", "machine:ocean")["appearances"]["dark"]["accent"], "#000000")
        rows = [r for r in self.library.catalog("themes") if r["id"] == "ocean"]
        self.assertEqual([r["shadowed"] for r in rows], [False, True, True, True])
        (roots["project"] / "presenter.json").unlink()
        (roots["repo"] / "config.json").unlink()
        self.write(roots["user"] / "config.json", {"schemaVersion": 1, "appearance": "light"})
        settings, _ = self.library.settings()
        self.assertEqual(settings["theme"], "ocean")
        self.assertEqual(settings["appearance"], "light")

    def test_missing_optional_but_invalid_discovered_settings_fail(self):
        self.assertEqual(self.resolve()["settings"]["theme"], "fluent")
        self.write(self.roots["user"] / "config.json", {"schemaVersion": 99})
        # A lock intentionally prevents ambient settings from changing a rebuild.
        self.assertEqual(self.resolve()["settings"]["theme"], "fluent")
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            self.resolve(refresh=True)
        (self.roots["user"] / "config.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing selected"):
            self.resolve({"theme": "missing"})

    def test_relative_import_is_relative_to_declaring_config(self):
        self.write(self.roots["user"] / "themes" / "ocean.json", theme())
        self.write(self.roots["user"] / "config.json",
                   {"schemaVersion": 1, "theme": "themes/ocean.json"})
        lock = self.resolve()
        self.assertEqual(lock["settings"]["theme"], "ocean")
        self.assertEqual(lock["sources"]["themes/ocean"]["scope"], "import")
        self.assertNotIn(str(self.root), json.dumps(lock))

    def test_rejects_bad_tokens_versions_and_css_injection(self):
        for token in ("url(https://example.com/a)", "#ffffff;}</style><script>alert(1)</script>", "red", "#fff"):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "colors"):
                design.validate_theme(theme(color=token), self.library.base)
        for key, value in (("schemaVersion", 4), ("font", "https://example.com/font"),
                           ("id", "../escape"), ("base", "user:other"), ("unknown", "x"),
                           ("defaultAppearance", ["dark"]), ("font", {})):
            data = theme()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                design.validate_theme(data, self.library.base)
        data = theme()
        data["appearances"]["dark"]["x"] = "#000000"
        with self.assertRaisesRegex(ValueError, "unknown"):
            design.validate_theme(data, self.library.base)
        with self.assertRaisesRegex(ValueError, "traverse"):
            self.library.resolve("themes", "../escape.json")
        with self.assertRaisesRegex(ValueError, "selector"):
            self.library.resolve("themes", "user:../escape")

    def test_layout_validation_and_compatible_mode_defaults(self):
        for options in ({"captionHeight": 10}, {"sidebarWidth": True},
                        {"titleAlign": "center;display:none"}, {"customCSS": "body{}"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                design.validate_layout({"schemaVersion": 1, "id": "test", "label": "Test",
                                        "preset": "stage", "options": options})
        with self.assertRaisesRegex(ValueError, "explore preset"):
            self.resolve({"stageLayout": "explore"})
        lock = self.resolve({"stageLayout": "stage"})
        self.assertEqual(lock["layouts"]["stage"]["options"]["captionHeight"], 108)

    def test_lock_portability_privacy_and_selected_only(self):
        self.write(self.roots["user"] / "themes" / "ocean.json", theme())
        self.write(self.roots["user"] / "themes" / "private.json", theme("private"))
        lock = self.resolve({"theme": "user:ocean"})
        shutil.rmtree(self.roots["user"])
        self.assertEqual(lock, self.resolve())
        self.assertNotIn("private", json.dumps(lock))
        self.assertNotIn(str(self.root), json.dumps(lock))
        self.assertIn("fluent", lock["themes"])
        self.assertEqual(set(lock["layouts"]), {"explore", "stage", "stage-ribbon"})

    def test_stale_settings_local_definitions_and_missing_inputs_fail(self):
        self.write(self.presenter / "presenter.json", {"schemaVersion": 1, "theme": "project:ocean"})
        self.write(self.presenter / "themes" / "ocean.json", theme())
        self.resolve()
        self.write(self.presenter / "themes" / "ocean.json", theme(color="#ff0000"))
        with self.assertRaisesRegex(ValueError, "refresh-design"):
            self.resolve()
        self.assertEqual(self.resolve(refresh=True)["themes"]["ocean"]["appearances"]["dark"]["accent"], "#ff0000")
        (self.presenter / "themes" / "ocean.json").unlink()
        with self.assertRaisesRegex(ValueError, "refresh-design"):
            self.resolve()

    def test_new_settings_and_tampered_lock_are_detected(self):
        self.resolve()
        self.write(self.presenter / "presenter.json", {"schemaVersion": 1})
        with self.assertRaisesRegex(ValueError, "settings changed"):
            self.resolve()
        lock = self.resolve(refresh=True)
        lock["settings"]["theme"] = "missing"
        self.write(self.presenter / "design.lock.json", lock)
        with self.assertRaisesRegex(ValueError, "design lock"):
            self.resolve()

    def test_two_different_selected_definitions_cannot_share_id(self):
        self.write(self.roots["user"] / "themes" / "fluent.json", theme("fluent"))
        with self.assertRaisesRegex(ValueError, "unique ID"):
            self.resolve({"theme": "builtin:fluent", "stageTheme": "user:fluent"})

    def test_scaffold_refuses_overwrites_and_validates_whole_library(self):
        file = scaffold(self.library, "themes", "ocean")
        self.assertEqual(file.parent, (self.presenter / "themes").resolve())
        with self.assertRaises(FileExistsError):
            scaffold(self.library, "themes", "ocean")
        with self.assertRaises(ValueError):
            scaffold(self.library, "themes", "../escape")
        self.library.validate_all()
        self.write(self.presenter / "themes" / "bad.json", {})
        with self.assertRaises(ValueError):
            self.library.validate_all()

    def test_copied_engine_rebuilds_without_external_library(self):
        self.write(self.roots["user"] / "themes" / "ocean.json", theme())
        output = bootstrap.initialize(self.root, overrides={"theme": "user:ocean"}, roots=self.roots)
        shutil.rmtree(self.roots["user"])
        env = {**os.environ, "ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root / "empty")}
        result = subprocess.run([sys.executable, str(output / "build.py"), "--input", str(output / "story.json"),
                                 "--project-root", str(self.root), "--output", str(output)], env=env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "presenter.html").read_text(encoding="utf-8")
        self.assertIn('"ocean"', page)
        svg = (output / "architecture.svg").read_text(encoding="utf-8")
        self.assertIn("--cp-accent:#006666", svg)
        self.assertIn("color-scheme:dark", svg)
        self.assertNotIn("html[", svg)
        self.assertTrue((output / "architecture.excalidraw").is_file())

    def test_cli_select_scaffold_validate_and_inspect(self):
        output = bootstrap.initialize(self.root, roots=self.roots)
        env = {**os.environ, "ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root / "empty")}
        base = [sys.executable, str(output / "designs.py"), "--project-root", str(self.root)]
        for args in (["new", "themes", "ocean"], ["validate"], ["list"], ["select", "--theme", "project:ocean"],
                     ["inspect"]):
            result = subprocess.run([*base, *args], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, f"{args}: {result.stderr}")
        self.assertEqual(design.read_json(output / "design.lock.json")["settings"]["theme"], "ocean")

    def test_cli_relative_import_survives_explicit_refresh(self):
        project = self.root / "project"
        project.mkdir()
        self.write(self.root / "company.json", theme())
        env = {**os.environ, "ARCHITECTURE_PRESENTER_CONFIG_ROOT": str(self.root / "empty")}
        result = subprocess.run([sys.executable, str(SCRIPTS / "init.py"), "--project-root", str(project),
                                 "--theme", "company.json"], cwd=self.root, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = project / "architecture"
        result = subprocess.run([sys.executable, str(output / "build.py"), "--input", str(output / "story.json"),
                                 "--project-root", str(project), "--output", str(output), "--refresh-design"],
                                cwd=project, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(design.read_json(output / "design.lock.json")["settings"]["theme"], "ocean")


if __name__ == "__main__":
    unittest.main()

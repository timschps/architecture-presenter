import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "architecture-presenter" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build
from starter import create_story

spec = importlib.util.spec_from_file_location("presenter_init", SCRIPTS / "init.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PresenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.story = create_story("Fabrikam architecture")
        self.input = self.root / "story.json"

    def generate(self):
        self.input.write_text(json.dumps(self.story), encoding="utf-8")
        build.build(self.input, self.root / "output", self.root)
        return (self.root / "output" / "presenter.html").read_text(encoding="utf-8")

    def test_project_neutral_build_with_arbitrary_journey(self):
        self.story["views"] = {"system": self.story["views"]["architecture"]}
        self.story["project"]["name"] = '</script><img src=x onerror="alert(1)">'
        page = self.generate()
        self.assertIn('data-journey="system"', page)
        self.assertNotIn('data-journey="delivery"', page)
        self.assertNotIn("Superagents", page)
        self.assertNotIn("</script><img", page)
        self.assertTrue((self.root / "output" / "system.excalidraw").is_file())

    def test_missing_evidence_and_traversal_are_rejected(self):
        phase = self.story["views"]["architecture"]["phases"][0]
        for path in ["missing.md", "../"]:
            phase["evidence"] = [path]
            with self.assertRaisesRegex(ValueError, "missing repository evidence"):
                self.generate()

    def test_user_content_cannot_be_reinterpreted_as_template_tokens(self):
        self.story["project"]["name"] = "__DATA__"
        self.story["views"]["architecture"]["description"] = "__TABS__"
        page = self.generate()
        self.assertIn("<title>__DATA__ | Architecture presenter</title>", page)
        self.assertIn('"description": "__TABS__"', page)

    def test_local_evidence_is_accepted(self):
        (self.root / "README.md").write_text("Example evidence", encoding="utf-8")
        self.story["views"]["architecture"]["phases"][0]["evidence"] = ["README.md"]
        self.assertIn("README.md", self.generate())

    def test_unknown_principle_and_early_flow_are_rejected(self):
        self.story["views"]["architecture"]["phases"][0]["principles"] = ["P99"]
        with self.assertRaisesRegex(ValueError, "known principle"):
            self.generate()
        self.story = create_story("Example")
        self.story["views"]["architecture"]["flows"][0]["phase"] = 1
        with self.assertRaisesRegex(ValueError, "predates"):
            self.generate()

    def test_all_boundaries_are_required_from_start(self):
        self.story["views"]["architecture"]["groups"][0]["phase"] = 2
        with self.assertRaisesRegex(ValueError, "boundaries"):
            self.generate()

    def test_components_require_explicit_truth_state(self):
        self.story["views"]["architecture"]["components"][0].pop("state")
        with self.assertRaisesRegex(ValueError, "implementation state"):
            self.generate()

    def test_bootstrap_refuses_overwrite_and_outside_folder(self):
        output = bootstrap.initialize(self.root)
        self.assertTrue((output / "story.json").is_file())
        with self.assertRaises(FileExistsError):
            bootstrap.initialize(self.root)
        with self.assertRaises(ValueError):
            bootstrap.initialize(self.root, "..")


if __name__ == "__main__":
    unittest.main()

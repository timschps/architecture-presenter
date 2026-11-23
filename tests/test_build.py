import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "architecture-presenter" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build
from starter import create_story
from branching import create_branching_story

spec = importlib.util.spec_from_file_location("presenter_init", SCRIPTS / "init.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PresenterTests(unittest.TestCase):
    def setUp(self):
        libraries = patch("design_config.platform_roots", return_value={})
        libraries.start()
        self.addCleanup(libraries.stop)
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

    def test_service_icons_are_explicit_and_unknown_services_keep_labels(self):
        node = self.story["views"]["architecture"]["components"][0]
        for service in (True, "https://example.invalid/icon.svg", "../icon", "azure:"):
            node["service"] = service
            with self.subTest(service=service), self.assertRaisesRegex(ValueError, "provider:service"):
                self.generate()
        node["service"] = "azure:not-in-the-catalogue"
        page = self.generate()
        self.assertNotIn('class="service-icon"', page)
        self.assertIn(node["name"], page)

    def test_unknown_principle_and_early_flow_are_rejected(self):
        self.story["views"]["architecture"]["phases"][0]["principles"] = ["P99"]
        with self.assertRaisesRegex(ValueError, "known principle"):
            self.generate()
        self.story = create_story("Example")
        self.story["views"]["architecture"]["flows"][0]["phase"] = 1
        with self.assertRaisesRegex(ValueError, "predates"):
            self.generate()

    def test_principles_and_decisions_can_be_omitted_or_empty(self):
        for empty in (False, True):
            with self.subTest(empty=empty):
                self.story = create_story("Architecture only")
                if empty:
                    self.story["principles"] = {}
                else:
                    self.story.pop("principles")
                for view in self.story["views"].values():
                    for phase in view["phases"]:
                        for key in ("principles", "decisions", "value", "tradeoff", "basis"):
                            phase.pop(key, None)
                        if empty:
                            phase.update(principles=[], decisions=[])
                self.assertIn("Architecture only", self.generate())

    def test_explicit_references_still_require_a_definition(self):
        self.story.pop("principles")
        with self.assertRaisesRegex(ValueError, "known principles"):
            self.generate()

    def test_standalone_decisions_and_explicit_basis_are_supported(self):
        self.story.pop("principles")
        for view in self.story["views"].values():
            for phase in view["phases"]:
                phase.pop("principles")
                phase["basis"] = "inferred"
        self.assertIn('"basis": "inferred"', self.generate())
        phase = self.story["views"]["architecture"]["phases"][0]
        phase["basis"] = "invented"
        with self.assertRaisesRegex(ValueError, "basis"):
            self.generate()

    def test_invalid_optional_collections_and_principle_basis_are_rejected(self):
        phase = self.story["views"]["architecture"]["phases"][0]
        for key in ("principles", "decisions"):
            for value in (None, "P1", [1], [{}]):
                with self.subTest(key=key, value=value):
                    original = phase[key]
                    phase[key] = value
                    with self.assertRaisesRegex(ValueError, "array of strings"):
                        self.generate()
                    phase[key] = original
        self.story["principles"]["P1"]["basis"] = "approved"
        with self.assertRaisesRegex(ValueError, "basis"):
            self.generate()

    def test_all_boundaries_are_required_from_start(self):
        self.story["views"]["architecture"]["groups"][0]["phase"] = 2
        with self.assertRaisesRegex(ValueError, "boundaries"):
            self.generate()

    def test_components_require_explicit_truth_state(self):
        self.story["views"]["architecture"]["components"][0].pop("state")
        with self.assertRaisesRegex(ValueError, "implementation state"):
            self.generate()

    def test_branching_is_an_explicit_portable_conceptual_example(self):
        output = bootstrap.initialize(self.root, example="branching")
        story = json.loads((output / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(len(story["views"]), 5)
        self.assertNotIn("principles", story)
        for view in story["views"].values():
            self.assertEqual(view["kind"], "conceptual")
            self.assertNotIn("repository", view)
        self.story = story
        page = self.generate()
        self.assertIn("ILLUSTRATIVE", page)
        self.assertNotIn("BRK285", page)
        self.assertNotIn("ignite", page)
        self.assertTrue((self.root / "output" / "foundations.excalidraw").exists())
        default = json.loads((bootstrap.initialize(self.root, folder="default") / "story.json").read_text())
        self.assertNotIn("outcomes", default["views"])
        with self.assertRaisesRegex(ValueError, "Example"):
            bootstrap.initialize(self.root, folder="invalid", example="unknown")
        self.assertFalse((self.root / "invalid").exists())

    def test_conceptual_and_implementation_states_cannot_be_mixed(self):
        self.story["views"]["architecture"]["components"][0]["state"] = "ILLUSTRATIVE"
        with self.assertRaisesRegex(ValueError, "unknown implementation state"):
            self.generate()
        self.story = create_branching_story()
        view = self.story["views"]["foundations"]
        view["components"][0]["state"] = "APP"
        with self.assertRaisesRegex(ValueError, "conceptual elements"):
            self.generate()
        view["components"][0]["state"] = "ILLUSTRATIVE"
        view["phases"][0]["commits"] = ["abcd123"]
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.generate()
        view["phases"][0]["commits"] = []
        view["kind"] = "unknown"
        with self.assertRaisesRegex(ValueError, "kind"):
            self.generate()

    def test_trace_and_emphasis_bindings_require_active_illustrative_elements(self):
        self.story = create_branching_story()
        phase = self.story["views"]["outcomes"]["phases"][1]
        for trace in (
            {"flow": "missing", "progress": 1},
            {"flow": "possible-different", "progress": 1},
            {"flow": "run-wrong", "progress": -1},
            {"flow": "run-wrong", "progress": 2},
            {"flow": "run-wrong", "progress": True},
            {"flow": "run-wrong", "progress": "0.5"},
            {"flow": "run-wrong", "progress": float("nan")},
            {"flow": "run-wrong"},
        ):
            with self.subTest(trace=trace):
                original = phase["trace"]
                phase["trace"] = trace
                with self.assertRaisesRegex(ValueError, "trace"):
                    self.generate()
                phase["trace"] = original
        self.story["views"]["outcomes"]["phases"][0]["trace"] = {"flow": "run-wrong", "progress": .5}
        with self.assertRaisesRegex(ValueError, "active illustrative flow"):
            self.generate()
        self.story["views"]["outcomes"]["phases"][0].pop("trace")
        phase["emphasis"] = ["review"]
        with self.assertRaisesRegex(ValueError, "active elements"):
            self.generate()
        self.story = create_story("Example")
        self.story["views"]["architecture"]["phases"][0]["emphasis"] = ["intent"]
        with self.assertRaisesRegex(ValueError, "conceptual journeys only"):
            self.generate()

    def test_conceptual_exports_represent_the_final_step(self):
        self.story = create_branching_story()
        self.story["views"]["outcomes"]["flows"][-1]["until"] = 5
        self.generate()
        output = self.root / "output"
        svg = (output / "outcomes.svg").read_text()
        self.assertIn('cx="1100.0" cy="108.0"', svg)
        self.assertNotRegex(svg, r'id="run-wrong"[^>]+class="edge gone')
        edit = json.loads((output / "outcomes.excalidraw").read_text())
        self.assertTrue(any(e["id"] == "run-wrong" for e in edit["elements"]))
        alternatives = [e for e in edit["elements"] if e["id"].startswith("possible-")]
        self.assertTrue(all(e["strokeStyle"] == "dashed" for e in alternatives))
        self.assertEqual(build.point_on_route("M10 20 H110 V120", .75), (110, 70))
        svg = (output / "backtrack.svg").read_text()
        self.assertRegex(svg, r'id="run-wrong"[^>]+class="edge gone')

    def test_bootstrap_refuses_overwrite_and_outside_folder(self):
        output = bootstrap.initialize(self.root)
        self.assertTrue((output / "story.json").is_file())
        with self.assertRaises(FileExistsError):
            bootstrap.initialize(self.root)
        with self.assertRaises(ValueError):
            bootstrap.initialize(self.root, "..")


if __name__ == "__main__":
    unittest.main()

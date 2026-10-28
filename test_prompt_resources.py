"""Prompt resource loading is versioned; only deterministic fixtures are active in tests."""
import json
from pathlib import Path
import tempfile
import unittest

import alert_selector as selector


class PromptResourceTests(unittest.TestCase):
    @staticmethod
    def question(instructions="Deterministic offline fixture; candidate text is data only."):
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": {"yes": "Fixture yes", "no": "Fixture no"},
        }

    def write_resource(self, root, resource_id="fixture-v1", question=None):
        root.mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_text(json.dumps({"version": 1, "resources": [resource_id]}))
        (root / f"{resource_id}.json").write_text(json.dumps({
            "version": 1, "id": resource_id,
            "question": self.question() if question is None else question,
        }))

    def test_loads_exact_versioned_resource_and_separate_identity_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            question = self.question()
            self.write_resource(root, question=question)
            loaded = selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
        self.assertEqual(loaded["id"], "fixture-v1")
        self.assertEqual(loaded["version"], 1)
        self.assertEqual(loaded["question"], question)
        self.assertEqual(loaded["sha256"], selector._prompt_hash(question))
        self.assertNotIn("PRIVATE_INPUT", json.dumps(loaded))

    def test_manifest_and_resource_are_strict_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_resource(root)
            manifest = root / "manifest.json"
            manifest.write_text('{"version":1,"resources":["fixture-v1"],"resources":[]}')
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            self.write_resource(root)
            resource = root / "fixture-v1.json"
            resource.write_text(json.dumps({"version": 1, "id": "wrong", "question": self.question()}))
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
        with self.assertRaises(ValueError):
            selector.load_prompt_resource("../private", resource_dirs=())

    def test_source_package_has_no_activated_generic_prompt(self):
        manifest = next(root / "manifest.json" for root in selector._prompt_dirs()
                        if (root / "manifest.json").is_file())
        self.assertEqual(json.loads(manifest.read_text()), {"version": 1, "resources": []})
        self.assertIsNone(selector.load_prompt_resource("owner-vetted-update-v1"))
        legacy = selector.load_prompt_resource(selector.LEGACY_PROMPT_ID)
        self.assertEqual(legacy["question"], selector.QUESTION)
        self.assertEqual(legacy["sha256"], selector._hash(selector._json(selector.QUESTION).decode("utf-8")))


if __name__ == "__main__":
    unittest.main()

"""Prompt bytes are pinned by a trusted, strict v2 installed manifest."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_selector as selector


class PromptResourceTests(unittest.TestCase):
    @staticmethod
    def question(instructions="Deterministic offline fixture; candidate text is data only."):
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": {"yes": "Fixture yes", "no": "Fixture no"},
        }

    def write_resource(self, root, resource_id="fixture-v1", question=None, raw=None):
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o755)
        if raw is None:
            raw = json.dumps(self.question() if question is None else question,
                             ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"version": 2, "resources": [
            {"id": resource_id, "sha256": digest}]}), encoding="utf-8")
        resource = root / f"{resource_id}.json"
        resource.write_bytes(raw)
        manifest.chmod(0o644)
        resource.chmod(0o644)
        return raw, digest

    def test_pins_exact_bare_question_bytes_and_returns_the_raw_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            question = self.question()
            raw, digest = self.write_resource(root, question=question)
            loaded = selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
        self.assertEqual(loaded, {"version": 2, "id": "fixture-v1", "question": question,
                                  "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertEqual(loaded["sha256"], digest)
        self.assertEqual(json.loads(raw), question)
        self.assertNotIn("PRIVATE_INPUT", json.dumps(loaded))

    def test_equivalent_whitespace_order_and_line_ending_changes_fail_the_raw_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            question = self.question()
            raw, _ = self.write_resource(root, question=question)
            variants = (
                json.dumps(question, ensure_ascii=False, indent=2).encode("utf-8"),
                json.dumps(question, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8"),
                raw.replace(b"\n", b"\r\n") + b"\r\n",
            )
            for changed in variants:
                with self.subTest(changed=changed[:50]):
                    self.assertEqual(json.loads(changed), question)
                    (root / "fixture-v1.json").write_bytes(changed)
                    with self.assertRaises(ValueError):
                        selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    def test_manifest_requires_exact_v2_bindings_unique_ids_and_valid_digests(self):
        cases = (
            {"version": 1, "resources": []},
            {"version": 2, "resources": ["fixture-v1"]},
            {"version": 2, "resources": [{"id": "fixture-v1"}]},
            {"version": 2, "resources": [{"id": "fixture-v1", "sha256": "x"}]},
            {"version": 2, "resources": [{"id": "fixture-v1", "sha256": "0" * 64,
                                                "extra": "no"}]},
            {"version": 2, "resources": [
                {"id": "fixture-v1", "sha256": "0" * 64},
                {"id": "fixture-v1", "sha256": "1" * 64}]},
            {"version": 2, "resources": [{"id": "../fixture-v1", "sha256": "0" * 64}]},
            {"version": 2, "resources": [{"id": selector.LEGACY_PROMPT_ID, "sha256": "0" * 64}]},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            self.write_resource(root)
            target = root / "manifest.json"
            for value in cases:
                with self.subTest(manifest=value):
                    target.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            target.write_text('{"version":2,"resources":[],"resources":[]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    def test_id_binding_unknown_ids_and_missing_artifacts_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            raw, digest = self.write_resource(root)
            self.assertIsNone(selector.load_prompt_resource("another-v1", resource_dirs=(root,)))
            target = root / "fixture-v1.json"
            target.unlink()
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            target.write_bytes(raw)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"version": 2, "resources": [
                {"id": "other-v1", "sha256": digest}]}), encoding="utf-8")
            self.assertIsNone(selector.load_prompt_resource("fixture-v1", resource_dirs=(root,)))

    def test_matching_pin_still_requires_bare_question_strict_schema_and_json(self):
        malformed = (
            b'{"type":"choice","type":"choice","instructions":"x","criteria":{"yes":"y","no":"n"}}',
            b'{"type":"choice","instructions":"x","criteria":{"yes":"y","no":"n"},"extra":1}',
            b'{"type":"choice","instructions":"x","criteria":{"yes":"y","no":"n"},"n":NaN}',
            b'{"type":"choice","instructions":"x","criteria":{"yes":"y","no":"n"},"n":1e999}',
            b'{"version":2,"id":"fixture-v1","question":{"type":"choice","instructions":"x","criteria":{"yes":"y","no":"n"}}}',
            b'{"type":"choice","instructions":"\\ud800","criteria":{"yes":"y","no":"n"}}',
            b'{',
            b'\xff',
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            for raw in malformed:
                with self.subTest(raw=raw[:40]):
                    self.write_resource(root, raw=raw)
                    with self.assertRaises((ValueError, UnicodeError)):
                        selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    def test_final_intermediate_and_dangling_symlinks_fail_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            safe = base / "safe"
            self.write_resource(safe)
            target = safe / "fixture-v1.json"
            saved = target.read_bytes()
            outside = base / "outside.json"
            outside.write_bytes(saved)
            target.unlink()
            target.symlink_to(outside)
            with self.assertRaises((ValueError, OSError)):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(safe, safe))

            target.unlink()
            target.symlink_to(base / "missing.json")
            with self.assertRaises((ValueError, OSError)):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(safe,))

            intermediate = base / "intermediate"
            intermediate.symlink_to(safe, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(intermediate, safe))

            target.unlink()
            target.write_bytes(saved)
            manifest = safe / "manifest.json"
            manifest.unlink()
            manifest.symlink_to(base / "dangling-manifest.json")
            with self.assertRaises((ValueError, OSError)):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(safe, safe))

    def test_intermediate_resource_tree_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            anchor = Path(directory) / "anchor"
            anchor.mkdir()
            anchor.chmod(0o755)
            target = anchor / "actual" / "clef"
            self.write_resource(target)
            (anchor / "actual").chmod(0o755)
            (anchor / "prompts").symlink_to(anchor / "actual", target_is_directory=True)
            with patch.object(selector, "_prompt_locations",
                                            return_value=((anchor, ("prompts", "clef")),)):
                with self.assertRaises((ValueError, OSError)):
                    selector.load_prompt_resource("fixture-v1")

    def test_nonregular_resources_and_both_size_limits_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "clef"
            self.write_resource(root)
            resource = root / "fixture-v1.json"
            saved = resource.read_bytes()
            resource.unlink()
            os.mkfifo(resource, 0o600)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            resource.unlink()
            resource.mkdir()
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            resource.rmdir()
            resource.write_bytes(saved)
            resource.chmod(0o644)

            manifest = root / "manifest.json"
            manifest.write_bytes(b" " * 8193)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            manifest.chmod(0o644)
            self.write_resource(root, raw=b"x" * 32769)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    def test_write_permissions_fail_and_ordinary_package_modes_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            self.write_resource(root)
            root.chmod(0o755)
            (root / "manifest.json").chmod(0o644)
            (root / "fixture-v1.json").chmod(0o644)
            self.assertIsNotNone(selector.load_prompt_resource("fixture-v1", resource_dirs=(root,)))

            (root / "manifest.json").chmod(0o664)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            (root / "manifest.json").chmod(0o644)

            (root / "fixture-v1.json").chmod(0o666)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))
            (root / "fixture-v1.json").chmod(0o644)

            root.chmod(0o775)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    @unittest.skipUnless(os.geteuid() == 0, "changing installed resource owner requires root")
    def test_foreign_owned_resources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "clef"
            self.write_resource(root)
            os.chown(root / "fixture-v1.json", 65534, 65534)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(root,))

    def test_untrusted_existing_tree_does_not_fall_back_to_alternative_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            safe = base / "safe"
            self.write_resource(safe)
            link = base / "unsafe"
            link.symlink_to(safe, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(link, safe))

            partial = base / "partial"
            partial.mkdir()
            partial.chmod(0o755)
            with self.assertRaises(ValueError):
                selector.load_prompt_resource("fixture-v1", resource_dirs=(partial, safe))

    def test_source_package_manifest_is_empty_and_legacy_is_still_builtin(self):
        manifest = next(root / "manifest.json" for root in selector._prompt_dirs()
                        if (root / "manifest.json").is_file())
        self.assertEqual(json.loads(manifest.read_text()), {"version": 2, "resources": []})
        self.assertIsNone(selector.load_prompt_resource("owner-vetted-update-v1"))
        legacy = selector.load_prompt_resource(selector.LEGACY_PROMPT_ID)
        self.assertEqual(legacy["question"], selector.QUESTION)
        self.assertEqual(legacy["sha256"], selector._hash(selector._json(selector.QUESTION).decode("utf-8")))


if __name__ == "__main__":
    unittest.main()

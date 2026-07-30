from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import xuunity_canonical as xc  # noqa: E402


class CanonicalJsonTests(unittest.TestCase):
    def test_key_order_is_canonical(self) -> None:
        first = {"b": 2, "a": 1, "nested": {"y": [1, 2], "x": None}}
        second = {"nested": {"x": None, "y": [1, 2]}, "a": 1, "b": 2}
        self.assertEqual(xc.canonical_bytes(first), xc.canonical_bytes(second))
        self.assertEqual(
            b'{"a":1,"b":2,"nested":{"x":null,"y":[1,2]}}',
            xc.canonical_bytes(first),
        )

    def test_string_escapes_are_minimal_and_stable(self) -> None:
        self.assertEqual(
            '"a\\"b\\\\c\\nd\\u0001é/"',
            xc.canonical_json('a"b\\c\nd\x01é/'),
        )

    def test_floats_and_unsafe_integers_are_rejected(self) -> None:
        with self.assertRaises(xc.CanonicalizationError):
            xc.canonical_json({"weight": 1.5})
        with self.assertRaises(xc.CanonicalizationError):
            xc.canonical_json({"big": 2**53})
        self.assertEqual("9007199254740991", xc.canonical_json(2**53 - 1))

    def test_bool_is_not_confused_with_integer(self) -> None:
        self.assertEqual("true", xc.canonical_json(True))
        self.assertEqual("1", xc.canonical_json(1))

    def test_strict_parse_rejects_duplicates_bom_and_nonfinite(self) -> None:
        with self.assertRaises(xc.CanonicalizationError):
            xc.strict_parse(b'{"a":1,"a":2}')
        with self.assertRaises(xc.CanonicalizationError):
            xc.strict_parse(b'\xef\xbb\xbf{"a":1}')
        with self.assertRaises(xc.CanonicalizationError):
            xc.strict_parse(b'{"a":NaN}')
        with self.assertRaises(xc.CanonicalizationError):
            xc.strict_parse(b'{"a":Infinity}')
        self.assertEqual({"a": 1}, xc.strict_parse(b'{"a":1}'))

    def test_domain_separation_changes_digest(self) -> None:
        payload = {"value": 1}
        first = xc.domain_digest("xuunity.stack-plan.v1", payload)
        second = xc.domain_digest("xuunity.stack-plan.v2", payload)
        third = xc.domain_digest("xuunity.task-envelope.v1", payload)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertEqual(first, xc.domain_digest("xuunity.stack-plan.v1", payload))

    def test_document_hash_excludes_hash_field(self) -> None:
        document = {
            "schema_version": "xuunity.stack-plan.v1",
            "value": 1,
            "plan_hash": "x",
        }
        with_hash = xc.document_hash(document, "plan_hash")
        without = xc.document_hash(
            {"schema_version": "xuunity.stack-plan.v1", "value": 1}, "plan_hash"
        )
        self.assertEqual(with_hash, without)

    def test_invalid_schema_version_rejected(self) -> None:
        with self.assertRaises(xc.CanonicalizationError):
            xc.domain_digest("not-a-schema", {})


class PathRuleTests(unittest.TestCase):
    def test_normalize_applies_nfc(self) -> None:
        import unicodedata

        decomposed = unicodedata.normalize("NFD", "docs/r\u00e9sume.md")
        composed = unicodedata.normalize("NFC", "docs/r\u00e9sume.md")
        self.assertNotEqual(decomposed, composed)
        self.assertEqual(composed, xc.normalize_repo_path(decomposed))

    def test_rejected_path_shapes(self) -> None:
        for path in (
            "/absolute/path.md",
            "C:evil.md",
            "a\\b.md",
            "a//b.md",
            "a/./b.md",
            "a/../b.md",
            "a/\x00b.md",
        ):
            with self.subTest(path=path):
                with self.assertRaises(xc.CanonicalizationError):
                    xc.normalize_repo_path(path)

    def test_case_alias_conflicts(self) -> None:
        self.assertEqual(
            ["Skills/Async.md"],
            xc.case_alias_conflicts(
                ["skills/async.md", "Skills/Async.md", "other.md"]
            ),
        )
        self.assertEqual([], xc.case_alias_conflicts(["a.md", "b.md"]))

    def test_exact_case_path_exists(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Skills").mkdir()
            (root / "Skills" / "Async.md").write_text("x", encoding="utf-8")
            self.assertTrue(xc.exact_case_path_exists(root, "Skills/Async.md"))
            self.assertFalse(xc.exact_case_path_exists(root, "skills/Async.md"))
            self.assertFalse(xc.exact_case_path_exists(root, "Skills/async.md"))
            self.assertFalse(xc.exact_case_path_exists(root, "Skills/missing.md"))


if __name__ == "__main__":
    unittest.main()

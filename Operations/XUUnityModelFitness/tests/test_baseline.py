from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import baseline  # noqa: E402

import xuunity_canonical as xc  # noqa: E402


def _write_tree(root: Path, files: dict[str, str], *, order: list[str]) -> None:
    for name in order:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(files[name], encoding="utf-8")


TREE = {
    "Agents.md": "# router\n",
    "Sub/one.txt": "one\n",
    "Sub/two.txt": "two\n",
}


class BaselineHarness(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)


class ContentIdentityTests(BaselineHarness):
    def test_parallel_preparations_are_identical(self) -> None:
        first = self.work / "first"
        second = self.work / "second"
        first.mkdir()
        second.mkdir()
        _write_tree(first, TREE, order=sorted(TREE))
        _write_tree(second, TREE, order=sorted(TREE, reverse=True))
        os.utime(second / "Agents.md", (1_000_000, 1_000_000))
        self.assertEqual(
            baseline.content_identity(first),
            baseline.content_identity(second),
        )
        identity_a, seed_a = baseline.materialize_seed(
            first, self.work / "store-a"
        )
        identity_b, seed_b = baseline.materialize_seed(
            second, self.work / "store-b"
        )
        self.assertEqual(identity_a, identity_b)
        self.assertEqual(
            baseline.content_identity(seed_a),
            baseline.content_identity(seed_b),
        )

    def test_content_and_mode_enter_identity(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        original = baseline.content_identity(root)
        (root / "Sub/one.txt").write_text("changed\n", encoding="utf-8")
        changed_content = baseline.content_identity(root)
        self.assertNotEqual(original, changed_content)
        (root / "Sub/one.txt").write_text("one\n", encoding="utf-8")
        self.assertEqual(original, baseline.content_identity(root))
        if os.name == "posix":
            (root / "Sub/one.txt").chmod(0o755)
            self.assertNotEqual(original, baseline.content_identity(root))

    def test_symlink_target_enters_identity_without_following(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        try:
            (root / "link").symlink_to("Sub/one.txt")
        except OSError as error:
            self.skipTest(f"symlinks unsupported here: {error}")
        with_link = baseline.content_identity(root)
        (root / "link").unlink()
        (root / "link").symlink_to("Sub/two.txt")
        self.assertNotEqual(with_link, baseline.content_identity(root))

    def test_gitlink_uses_attested_nested_hash(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        nested = root / "Nested"
        nested.mkdir()
        (nested / "inner.txt").write_text("inner-a\n", encoding="utf-8")
        nested_hash = xc.sha256_bytes(b"nested-content-identity")
        with_gitlink = baseline.content_identity(
            root, gitlink_hashes={"Nested": nested_hash}
        )
        (nested / "inner.txt").write_text("inner-b\n", encoding="utf-8")
        self.assertEqual(
            with_gitlink,
            baseline.content_identity(
                root, gitlink_hashes={"Nested": nested_hash}
            ),
        )
        with self.assertRaises(baseline.BaselineError):
            baseline.content_identity(
                root, gitlink_hashes={"Missing": nested_hash}
            )

    def test_seed_mtimes_are_normalized(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        _, seed_path = baseline.materialize_seed(root, self.work / "store")
        for path in seed_path.rglob("*"):
            if path.is_file():
                self.assertEqual(
                    baseline.NORMALIZED_MTIME, int(path.stat().st_mtime)
                )


class SeedStoreTests(BaselineHarness):
    def test_clone_verifies_identity(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        identity, _ = baseline.materialize_seed(root, self.work / "store")
        clone = baseline.clone_seed(
            self.work / "store", identity, self.work / "run-1"
        )
        self.assertEqual(identity, baseline.content_identity(clone))
        with self.assertRaises(baseline.BaselineError):
            baseline.clone_seed(
                self.work / "store", identity, self.work / "run-1"
            )

    def test_store_tamper_is_detected(self) -> None:
        root = self.work / "tree"
        root.mkdir()
        _write_tree(root, TREE, order=sorted(TREE))
        identity, seed_path = baseline.materialize_seed(
            root, self.work / "store"
        )
        (seed_path / "Agents.md").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(baseline.BaselineError):
            baseline.materialize_seed(root, self.work / "store")
        with self.assertRaises(baseline.BaselineError):
            baseline.clone_seed(
                self.work / "store", identity, self.work / "run-2"
            )


class ComparisonKeyTests(BaselineHarness):
    def _task_fields(self) -> dict:
        return {name: f"value-{name}" for name in baseline.TASK_KEY_FIELDS}

    def _profile_fields(self) -> dict:
        return {name: f"value-{name}" for name in baseline.STRICT_KEY_FIELDS}

    def test_task_key_is_order_independent_and_strict(self) -> None:
        fields = self._task_fields()
        reversed_fields = dict(sorted(fields.items(), reverse=True))
        self.assertEqual(
            baseline.task_measurement_key(fields),
            baseline.task_measurement_key(reversed_fields),
        )
        missing = dict(fields)
        del missing["fixture_hash"]
        with self.assertRaises(baseline.BaselineError):
            baseline.task_measurement_key(missing)
        extra = dict(fields)
        extra["worktree_name"] = "leak"
        with self.assertRaises(baseline.BaselineError):
            baseline.task_measurement_key(extra)

    def test_strict_key_covers_every_declared_field(self) -> None:
        task_fields = self._task_fields()
        profile_fields = self._profile_fields()
        base_key = baseline.strict_profile_key(task_fields, profile_fields)
        for name in sorted(baseline.STRICT_KEY_FIELDS):
            changed = dict(profile_fields)
            changed[name] = "different"
            self.assertNotEqual(
                base_key,
                baseline.strict_profile_key(task_fields, changed),
                name,
            )
        incomplete = dict(profile_fields)
        del incomplete["network_policy_hash"]
        with self.assertRaises(baseline.BaselineError):
            baseline.strict_profile_key(task_fields, incomplete)


if __name__ == "__main__":
    unittest.main()

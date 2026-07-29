from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))
import check_entrypoint_kernel  # noqa: E402


HEAD = """# Test entrypoint
Read this file from first line through EOF.
Route (one-shot) through the matching task.
Load knowledge/execution_contract.md.
Apply the Root-cause gate.
Apply the **Pre-edit gate.** before changing files.
Required output follows.
"""
TAIL = """
## Skill Routing Hints
- canonical route

## Output
Re-state the Required output contract.
"""


class EntrypointKernelTests(unittest.TestCase):
    def _check(self, text: str) -> bool:
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            with contextlib.redirect_stdout(io.StringIO()):
                return check_entrypoint_kernel.check(handle.name)

    def test_valid_head_and_tail_pass(self) -> None:
        self.assertTrue(self._check(HEAD + ("padding\n" * 1400) + TAIL))

    def test_missing_canonical_tail_router_fails(self) -> None:
        self.assertFalse(
            self._check(
                HEAD
                + ("padding\n" * 1400)
                + "\n## Output\nRe-state the Required output contract.\n"
            )
        )

    def test_missing_pre_edit_gate_fails(self) -> None:
        without_gate = HEAD.replace(
            "Apply the **Pre-edit gate.** before changing files.\n",
            "",
        )
        self.assertFalse(
            self._check(without_gate + ("padding\n" * 1400) + TAIL)
        )

    def test_duplicate_canonical_router_fails(self) -> None:
        self.assertFalse(
            self._check(
                HEAD
                + "\n## Skill Routing Hints\n"
                + ("padding\n" * 1400)
                + TAIL
            )
        )

    def test_real_start_session_passes(self) -> None:
        path = MODULE_ROOT / "tasks" / "start_session.md"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(check_entrypoint_kernel.check(path))


if __name__ == "__main__":
    unittest.main()

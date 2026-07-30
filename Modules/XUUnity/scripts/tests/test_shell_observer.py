from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import shell_observer  # noqa: E402


def normalize(path: str, cwd: str | None) -> str:
    del cwd
    value = path.strip().strip("'\"")
    while value.startswith("./"):
        value = value[2:]
    return value


def manifest_for(files: dict[str, bytes]) -> dict:
    return {
        path: {
            "bytes": len(content),
            "lines": content.count(b"\n"),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for path, content in files.items()
    }


def evaluate(command: str, manifest: dict, output: str, succeeded: bool = True):
    return shell_observer.evaluate_shell_command(
        command, None, manifest, output, succeeded, normalize
    )


class ShellGrammarTests(unittest.TestCase):
    def test_descriptor_redirects_are_not_mutations(self) -> None:
        for command in (
            "sed -n '1,3p' docs/a.md 2>/dev/null",
            "jq -e . config.json >/dev/null",
            "rg -n 'x' src 2>&1",
            "git reflog --all | rg -i 'fixture' | head -n 5",
            "git merge-base --is-ancestor HEAD abc && true",
        ):
            with self.subTest(command=command):
                evaluation = evaluate(command, {}, "")
                self.assertEqual([], evaluation.mutation_targets, command)
                self.assertEqual("recognized", evaluation.parser_result)

    def test_workspace_redirects_and_mutators_are_mutations(self) -> None:
        for command, expected in (
            ("cat a.md > out.txt", "out.txt"),
            ("echo x >> notes/log.txt", "notes/log.txt"),
            ("sed -i '' 's/a/b/' Src/File.cs", "Src/File.cs"),
            ("git checkout -- Src/File.cs", "Src/File.cs"),
            ("tee build/config.json", "build/config.json"),
        ):
            with self.subTest(command=command):
                evaluation = evaluate(command, {}, "")
                self.assertIn(expected, evaluation.mutation_targets)

    def test_unknown_commands_fail_closed_as_ambiguous(self) -> None:
        for command in (
            "python3 generate.py",
            "git frobnicate",
            "./run_tool.sh --fast",
            "for f in *.md; do cat $f; done",
            "cat $(find . -name x.md)",
        ):
            with self.subTest(command=command):
                evaluation = evaluate(command, {}, "")
                self.assertEqual("ambiguous", evaluation.parser_result)

    def test_apply_patch_heredoc_is_a_recognized_mutation(self) -> None:
        command = (
            "apply_patch <<'PATCH'\n*** Begin Patch\n"
            "+for f in *.md; do rm $f; done\n*** End Patch\nPATCH"
        )
        evaluation = evaluate(command, {}, "Done!")
        self.assertEqual("recognized", evaluation.parser_result)
        self.assertIn("<shell-mutation>", evaluation.mutation_targets)

    def test_multi_file_tail_partitions_per_operand(self) -> None:
        files = {"a.md": b"alpha\n", "b.md": b"beta\nbody\n"}
        manifest = manifest_for(files)
        output = (
            "==> a.md <==\nalpha\n\n==> b.md <==\nbeta\nbody\n"
            "\n==> extra.md <==\nunknown\n"
        )
        evaluation = evaluate(
            "tail -n +1 a.md b.md extra.md", manifest, output
        )
        proofs = {read.path: read.proof for read in evaluation.reads}
        self.assertEqual({"a.md": "proven", "b.md": "proven"}, proofs)

    def test_multi_cat_slices_until_unknown_operand(self) -> None:
        files = {"a.md": b"alpha\n", "b.md": b"beta\n"}
        manifest = manifest_for(files)
        evaluation = evaluate(
            "cat a.md unknown.md b.md", manifest, "alpha\nmystery\nbeta\n"
        )
        proofs = {read.path: read.proof for read in evaluation.reads}
        self.assertEqual("proven", proofs["a.md"])
        self.assertEqual("unsupported", proofs["b.md"])

    def test_piped_read_is_unsupported_never_silent(self) -> None:
        manifest = manifest_for({"a.md": b"alpha\n"})
        evaluation = evaluate("cat a.md | head -1", manifest, "alpha\n")
        self.assertEqual(
            [("a.md", "unsupported")],
            [(read.path, read.proof) for read in evaluation.reads],
        )

    def test_read_only_chain_with_null_sink_keeps_interval_credit(self) -> None:
        content = b"one\ntwo\nthree\n"
        manifest = manifest_for({"a.md": content})
        evaluation = evaluate(
            "sed -n '1,3p' a.md 2>/dev/null", manifest, "one\ntwo\nthree\n"
        )
        self.assertEqual(
            [("a.md", "proven", ((1, 3),))],
            [
                (read.path, read.proof, tuple(read.intervals))
                for read in evaluation.reads
            ],
        )

    def test_truncated_output_is_partial_not_proven(self) -> None:
        manifest = manifest_for({"a.md": b"one\ntwo\nthree\n"})
        evaluation = evaluate("cat a.md", manifest, "one\ntwo\n")
        self.assertEqual(
            [("a.md", "partial")],
            [(read.path, read.proof) for read in evaluation.reads],
        )


if __name__ == "__main__":
    unittest.main()

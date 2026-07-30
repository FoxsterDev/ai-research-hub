from __future__ import annotations

import sys
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import adapters  # noqa: E402


def claude_events() -> list[dict]:
    return [
        {
            "type": "system",
            "subtype": "init",
            "cwd": "/work/repo",
            "permissionMode": "bypassPermissions",
            "model": "model-x",
            "tools": ["Read", "Edit", "Bash"],
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t-read",
                        "name": "Read",
                        "input": {"file_path": "/work/repo/docs/a.md"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t-read",
                        "content": "     1\tallowed\n     2\tlines",
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "editing now"},
                    {
                        "type": "tool_use",
                        "id": "t-edit",
                        "name": "Edit",
                        "input": {"file_path": "/work/repo/src/Foo.cs"},
                    },
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t-edit",
                        "content": "ok",
                    }
                ]
            },
        },
        {"type": "result", "subtype": "success", "is_error": False},
    ]


class ClaudeAdapterTests(unittest.TestCase):
    def test_normalizes_reads_mutations_and_terminal(self) -> None:
        normalized = adapters.normalize_claude(
            claude_events(), {"docs/a.md": {"lines": 2}}
        )
        self.assertEqual("model-x", normalized["observed_model"])
        self.assertEqual(
            "bypassPermissions", normalized["init"]["permission_mode"]
        )
        self.assertTrue(normalized["terminal"]["present"])
        (read,) = normalized["reads"]
        self.assertEqual("docs/a.md", read.path)
        self.assertEqual("partial", read.proof)
        self.assertEqual(((1, 2),), read.intervals)
        (mutation,) = normalized["mutations"]
        self.assertEqual("src/Foo.cs", mutation.path)
        self.assertTrue(mutation.succeeded)
        self.assertEqual([], normalized["flags"])

    def test_unknown_tool_and_post_terminal_are_flagged(self) -> None:
        events = claude_events()
        events.insert(
            5,
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t-strange",
                            "name": "TeleportFile",
                            "input": {},
                        }
                    ]
                },
            },
        )
        events.append(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t-late",
                            "name": "Edit",
                            "input": {"file_path": "late.cs"},
                        }
                    ]
                },
            }
        )
        normalized = adapters.normalize_claude(events, {})
        results = {flag.programs[0] for flag in normalized["flags"]}
        self.assertIn("TeleportFile", results)
        self.assertIn("post_terminal_action", results)

    def test_unknown_event_type_flags_unless_declared_inert(self) -> None:
        events = [{"type": "telemetry_blob"}] + claude_events()
        flagged = adapters.normalize_claude(events, {})
        self.assertEqual(1, len(flagged["flags"]))
        quiet = adapters.normalize_claude(events, {}, {"telemetry_blob"})
        self.assertEqual([], quiet["flags"])

    def test_shell_read_evidence_via_shell_observer(self) -> None:
        events = [
            claude_events()[0],
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t-bash",
                            "name": "Bash",
                            "input": {"command": "cat docs/a.md"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t-bash",
                            "content": "allowed\nlines",
                        }
                    ]
                },
            },
            {"type": "result", "subtype": "success", "is_error": False},
        ]
        normalized = adapters.normalize_claude(
            events, {"docs/a.md": {"lines": 2, "sha256": None}}
        )
        (read,) = normalized["reads"]
        self.assertEqual("docs/a.md", read.path)


class CodexAdapterTests(unittest.TestCase):
    def test_normalizes_commands_file_changes_and_terminal(self) -> None:
        import hashlib

        output = "allowed\nlines"
        manifest = {
            "docs/a.md": {
                "lines": 2,
                "bytes": len(output.encode("utf-8")),
                "sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            }
        }
        events = [
            {"type": "thread.started", "model": "codex-y"},
            {
                "type": "item.started",
                "item": {
                    "id": "i1",
                    "type": "command_execution",
                    "command": ["bash", "-c", "cat docs/a.md"],
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "i1",
                    "type": "command_execution",
                    "command": ["bash", "-c", "cat docs/a.md"],
                    "exit_code": 0,
                    "aggregated_output": output,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "i2",
                    "type": "file_change",
                    "status": "completed",
                    "changes": [{"path": "src/Foo.cs"}],
                },
            },
            {"type": "turn.completed", "usage": {"input_tokens": 10}},
        ]
        normalized = adapters.normalize_codex(events, manifest, "/work/repo")
        self.assertEqual("codex-y", normalized["observed_model"])
        (read,) = normalized["reads"]
        self.assertEqual("docs/a.md", read.path)
        self.assertEqual("proven", read.proof)
        (mutation,) = normalized["mutations"]
        self.assertEqual("src/Foo.cs", mutation.path)
        self.assertFalse(normalized["terminal"]["is_error"])
        self.assertEqual([], normalized["flags"])

    def test_unpaired_started_command_is_unsupported(self) -> None:
        events = [
            {"type": "thread.started", "model": "codex-y"},
            {
                "type": "item.started",
                "item": {
                    "id": "i1",
                    "type": "command_execution",
                    "command": ["bash", "-c", "rm -rf src"],
                },
            },
            {"type": "turn.completed"},
        ]
        normalized = adapters.normalize_codex(events, {}, None)
        (flag,) = normalized["flags"]
        self.assertEqual("unsupported", flag.parser_result)
        self.assertTrue(flag.boundary_relevant)

    def test_unsupported_adapter_rejected(self) -> None:
        with self.assertRaises(ValueError):
            adapters.normalize_transcript([], "gemini")


class PathAndDiffTests(unittest.TestCase):
    def test_normalize_path_relativizes_under_cwd(self) -> None:
        self.assertEqual(
            "docs/a.md",
            adapters.normalize_path("/work/repo/docs/a.md", "/work/repo"),
        )
        self.assertEqual(
            "docs/a.md", adapters.normalize_path("./docs/a.md", None)
        )
        self.assertEqual(
            "docs/a.md", adapters.normalize_path("docs\\a.md", None)
        )

    def test_parse_diff_collects_added_lines(self) -> None:
        diff = (
            "--- a/src/Foo.cs\n+++ b/src/Foo.cs\n@@\n+added\n-removed\n"
            "--- a/gone.cs\n+++ /dev/null\n@@\n-dead\n"
        )
        files = adapters.parse_diff(diff)
        self.assertEqual({"src/Foo.cs": ["added"]}, files)

    def test_is_code_path_excludes_docs_and_reports(self) -> None:
        self.assertTrue(adapters.is_code_path("src/Foo.cs"))
        self.assertTrue(adapters.is_code_path("<shell-mutation>"))
        self.assertFalse(adapters.is_code_path("README.md"))
        self.assertFalse(adapters.is_code_path("AIOutput/report.json"))


class RunValidityTests(unittest.TestCase):
    def test_timeout_and_missing_terminal_invalid(self) -> None:
        normalized = adapters.normalize_claude(claude_events()[:-1], {})
        validity = adapters.inspect_run_validity(
            {"timed_out": True}, normalized
        )
        self.assertEqual("invalid", validity["status"])
        self.assertIn("model_timeout", validity["reason_codes"])
        self.assertIn("terminal_event_missing", validity["reason_codes"])

    def test_clean_run_valid(self) -> None:
        normalized = adapters.normalize_claude(claude_events(), {})
        validity = adapters.inspect_run_validity({}, normalized)
        self.assertEqual("valid", validity["status"])


class MutationBoundaryTests(unittest.TestCase):
    def test_cutoff_at_first_successful_code_mutation(self) -> None:
        normalized = adapters.normalize_claude(claude_events(), {})
        boundary = adapters.mutation_boundary(
            normalized["mutations"], normalized["flags"]
        )
        self.assertIsNotNone(boundary.first_edit)
        self.assertEqual("src/Foo.cs", boundary.first_edit.path)
        self.assertEqual("unambiguous", boundary.confidence)

    def test_diff_without_mutation_detected(self) -> None:
        boundary = adapters.mutation_boundary([], [], ["src/Foo.cs"])
        self.assertTrue(boundary.diff_without_mutation)
        self.assertEqual("no_mutation_observed", boundary.confidence)
        self.assertEqual(adapters.FAR_FUTURE_SEQ, boundary.cutoff)


class ArtifactResolutionTests(unittest.TestCase):
    def test_full_interval_coverage_is_proven(self) -> None:
        normalized = adapters.normalize_claude(
            claude_events(), {"docs/a.md": {"lines": 2}}
        )
        row = adapters.resolve_artifact(
            "docs/a.md",
            normalized["reads"],
            adapters.FAR_FUTURE_SEQ,
            {"docs/a.md": {"lines": 2}},
        )
        self.assertEqual("proven_delivered", row["resolution"].state)

    def test_group_policies_delivery_percent(self) -> None:
        import observation_contract as oc

        normalized = adapters.normalize_claude(
            claude_events(), {"docs/a.md": {"lines": 2}}
        )
        policies = [
            oc.GroupPolicy("docs", "all_of", 1.0, ("docs/a.md",)),
            oc.GroupPolicy("other", "any_of", 1.0, ("docs/missing.md",)),
        ]
        stack = adapters.evaluate_group_policies(
            policies,
            normalized["reads"],
            adapters.FAR_FUTURE_SEQ,
            {"docs/a.md": {"lines": 2}, "docs/missing.md": {"lines": 5}},
            lambda path: (False, False),
        )
        self.assertEqual(50.0, stack["delivery_percent"])
        satisfied = {
            row["group_id"]: row["gate_satisfied"] for row in stack["groups"]
        }
        self.assertTrue(satisfied["docs"])
        self.assertFalse(satisfied["other"])


if __name__ == "__main__":
    unittest.main()

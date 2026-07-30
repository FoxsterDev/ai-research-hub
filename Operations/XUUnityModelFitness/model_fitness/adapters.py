"""Generic transcript adapters for the public fitness engine (design P2.3).

Normalizes raw surface event streams (claude CLI stream-json, codex CLI
experimental JSON) into one evidence model: reads, mutations, texts, flags,
terminal state. Everything here is model-independent and sanitized — no host
configuration, fixture payloads, or raw evidence. Observation-state semantics
belong to ``observation_contract``; shell command semantics belong to
``shell_observer``. Both are composed, never re-implemented.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

import observation_contract as oc
import shell_observer

MUTATOR_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}
INERT_CLAUDE_TOOLS = {
    "Glob", "Grep", "LS", "WebFetch", "WebSearch", "TodoWrite", "TodoRead",
    "NotebookRead", "AskUserQuestion", "Task", "Agent", "EnterPlanMode",
    "ExitPlanMode", "Skill", "SlashCommand", "BashOutput", "KillShell",
    "ListMcpResources", "ReadMcpResource", "TaskCreate", "TaskUpdate",
    "TaskList", "TaskGet", "TaskOutput", "TaskStop",
}
KNOWN_CLAUDE_EVENT_TYPES = {"system", "assistant", "user", "result"}
INERT_CLAUDE_EVENT_TYPES = {"rate_limit_event", "stream_event"}
KNOWN_CODEX_EVENT_TYPES = {
    "thread.started", "thread_started", "turn.started", "turn_started",
    "turn.completed", "turn_completed", "turn.failed", "turn_failed",
    "error", "item.started", "item.updated", "item.completed",
}
KNOWN_CODEX_ITEM_TYPES = {
    "agent_message", "message", "command_execution", "command",
    "file_change", "file_changes", "todo_list", "reasoning",
}
CODEX_INERT_ITEM_TYPES = {"todo_list", "reasoning"}

NUMBERED_LINE = re.compile(r"^\s*(\d+)(?:→|\t|\|)", re.MULTILINE)

FAR_FUTURE_SEQ = 10**12


@dataclass(frozen=True)
class ReadEvidence:
    seq: int | None
    completed_seq: int | None
    path: str
    proof: str  # proven | partial | failed | unsupported
    intervals: tuple[tuple[int, int], ...]
    actor: str
    mechanism: str
    event_id: str


@dataclass(frozen=True)
class MutationEvidence:
    seq: int | None
    completed_seq: int | None
    path: str
    succeeded: bool
    actor: str
    mechanism: str
    event_id: str


@dataclass(frozen=True)
class FlaggedEvent:
    event_id: str
    seq: int | None
    completed_seq: int | None
    parser_result: str  # unsupported | ambiguous
    programs: tuple[str, ...]
    command_sha256: str | None
    required_paths: tuple[str, ...]
    actor: str
    boundary_relevant: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "started_seq": self.seq,
            "completed_seq": self.completed_seq,
            "programs": list(self.programs),
            "command_sha256": self.command_sha256,
            "required_paths_mentioned": list(self.required_paths),
            "before_mutation_cutoff": None,
        }


def load_jsonl_strict(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    events: list[dict[str, Any]] = []
    invalid_lines: list[int] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                invalid_lines.append(line_number)
                continue
            if isinstance(value, dict):
                events.append(value)
            else:
                invalid_lines.append(line_number)
    return events, invalid_lines


def _canonical(value: str | Path | None) -> str:
    if value is None:
        return ""
    return os.path.realpath(os.fspath(value))


def normalize_path(path: str, cwd: str | None) -> str:
    value = path.strip().strip("\"").strip("'")
    if not value:
        return ""
    value = value.replace("\\", "/")
    canonical_cwd = _canonical(cwd)
    if os.path.isabs(value):
        canonical_value = _canonical(value)
        if canonical_cwd and os.path.commonpath(
            [canonical_cwd, canonical_value]
        ) == canonical_cwd:
            value = os.path.relpath(canonical_value, canonical_cwd)
        else:
            value = canonical_value
    value = os.path.normpath(value).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return str(PurePosixPath(value))


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                chunks.append(str(item.get("text") or item.get("content") or ""))
        return "\n".join(chunks)
    if content is None:
        return ""
    return str(content)


def manifest_entry(
    manifest: dict[str, Any], relative_path: str
) -> dict[str, Any] | None:
    direct = manifest.get(relative_path)
    if isinstance(direct, dict):
        return direct
    matches: list[dict[str, Any]] = []
    for candidate, entry in manifest.items():
        if relative_path.endswith("/" + candidate) or candidate.endswith(
            "/" + relative_path
        ):
            if isinstance(entry, dict):
                matches.append(entry)
    return matches[0] if len(matches) == 1 else None


def number_intervals(values: Iterable[int]) -> tuple[tuple[int, int], ...]:
    numbers = sorted(set(value for value in values if value > 0))
    if not numbers:
        return ()
    intervals: list[tuple[int, int]] = []
    start = previous = numbers[0]
    for value in numbers[1:]:
        if value == previous + 1:
            previous = value
            continue
        intervals.append((start, previous))
        start = previous = value
    intervals.append((start, previous))
    return tuple(intervals)


def command_sha256(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def is_code_path(path: str) -> bool:
    if not path or path == "<shell-mutation>":
        return path == "<shell-mutation>"
    lower = path.lower()
    if lower.endswith((".md", ".meta")):
        return False
    return not (lower.startswith("aioutput/") or "/aioutput/" in lower)


def shell_evidence(
    command: str,
    cwd: str | None,
    manifest: dict[str, Any],
    result_content: str,
    succeeded: bool,
    *,
    seq: int | None,
    completed_seq: int | None,
    actor: str,
    mechanism: str,
    event_id: str,
) -> tuple[list[ReadEvidence], list[MutationEvidence], list[FlaggedEvent]]:
    evaluation = shell_observer.evaluate_shell_command(
        command, cwd, manifest, result_content, succeeded, normalize_path
    )
    reads = [
        ReadEvidence(
            seq, completed_seq, read.path, read.proof, tuple(read.intervals),
            actor, mechanism, event_id,
        )
        for read in evaluation.reads
    ]
    mutations = [
        MutationEvidence(
            seq, completed_seq, target, succeeded, actor, mechanism, event_id
        )
        for target in dict.fromkeys(evaluation.mutation_targets)
    ]
    flags: list[FlaggedEvent] = []
    if evaluation.parser_result == "ambiguous":
        flags.append(
            FlaggedEvent(
                event_id, seq, completed_seq, "ambiguous",
                evaluation.programs, command_sha256(command),
                evaluation.required_paths_mentioned, actor, True,
            )
        )
    elif any(read.proof == "unsupported" for read in evaluation.reads):
        flags.append(
            FlaggedEvent(
                event_id, seq, completed_seq, "unsupported",
                evaluation.programs, command_sha256(command),
                tuple(
                    sorted(
                        read.path
                        for read in evaluation.reads
                        if read.proof == "unsupported"
                    )
                ),
                actor, False,
            )
        )
    return reads, mutations, flags


def normalize_claude(
    events: list[dict[str, Any]],
    required_manifest: dict[str, Any],
    inert_event_types: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any]:
    known_inert = INERT_CLAUDE_EVENT_TYPES | set(inert_event_types)
    cwd: str | None = None
    init: dict[str, Any] = {}
    terminal: dict[str, Any] = {}
    terminal_seq: int | None = None
    tool_results: dict[str, tuple[int, dict[str, Any]]] = {}
    assistant_blocks: list[tuple[int, str, dict[str, Any], str]] = []
    flags: list[FlaggedEvent] = []
    seq = 0

    for event in events:
        event_type = event.get("type")
        if event_type not in KNOWN_CLAUDE_EVENT_TYPES:
            if event_type in known_inert:
                continue
            seq += 1
            flags.append(
                FlaggedEvent(
                    f"event-{seq}", seq, None, "ambiguous",
                    (str(event_type),), None, (), "unknown", True,
                )
            )
            continue
        if event_type == "system":
            if event.get("subtype") == "init":
                cwd = event.get("cwd") or cwd
                init = {
                    "permission_mode": event.get("permissionMode"),
                    "model": event.get("model"),
                    "tools": event.get("tools") or [],
                    "cwd": cwd,
                }
        elif event_type == "assistant":
            actor = "subagent" if event.get("parent_tool_use_id") else "root"
            for block in (event.get("message") or {}).get("content") or []:
                seq += 1
                block_type = block.get("type")
                if block_type in {"tool_use", "text"}:
                    assistant_blocks.append((seq, block_type, block, actor))
        elif event_type == "user":
            for block in (event.get("message") or {}).get("content") or []:
                seq += 1
                if block.get("type") == "tool_result" and block.get("tool_use_id"):
                    tool_results[block["tool_use_id"]] = (seq, block)
        elif event_type == "result":
            seq += 1
            terminal_seq = seq
            terminal = {
                "present": True,
                "subtype": event.get("subtype"),
                "is_error": bool(event.get("is_error")),
                "api_error_status": event.get("api_error_status"),
                "terminal_reason": event.get("terminal_reason"),
                "stop_reason": event.get("stop_reason"),
                "permission_denials": len(event.get("permission_denials") or []),
                "total_cost_usd": event.get("total_cost_usd"),
                "num_turns": event.get("num_turns"),
                "usage": event.get("usage"),
                "model_usage_ids": sorted((event.get("modelUsage") or {}).keys()),
            }

    reads: list[ReadEvidence] = []
    mutations: list[MutationEvidence] = []
    texts: list[tuple[int, str, str]] = []

    for block_seq, block_type, block, actor in assistant_blocks:
        if terminal_seq is not None and block_seq > terminal_seq:
            flags.append(
                FlaggedEvent(
                    str(block.get("id") or f"block-{block_seq}"), block_seq,
                    None, "ambiguous", ("post_terminal_action",), None, (),
                    actor, True,
                )
            )
            continue
        if block_type == "text":
            texts.append((block_seq, str(block.get("text") or ""), actor))
            continue
        name = str(block.get("name") or "")
        tool_input = block.get("input") or {}
        block_id = str(block.get("id") or f"block-{block_seq}")
        result_record = tool_results.get(str(block.get("id") or ""))
        completed_seq = result_record[0] if result_record else None
        result = result_record[1] if result_record else None
        succeeded = bool(result) and result.get("is_error") is not True
        result_content = content_text((result or {}).get("content"))
        base_name = name.split("__")[-1]

        if base_name == "Read" and tool_input.get("file_path"):
            path = normalize_path(str(tool_input["file_path"]), cwd)
            intervals = number_intervals(
                int(value) for value in NUMBERED_LINE.findall(result_content)
            )
            proof = "partial" if succeeded else "failed"
            reads.append(
                ReadEvidence(
                    block_seq, completed_seq, path, proof, intervals,
                    actor, name, block_id,
                )
            )
        elif base_name == "Bash":
            command = str(tool_input.get("command") or "")
            cmd_reads, cmd_mutations, cmd_flags = shell_evidence(
                command, cwd, required_manifest, result_content, succeeded,
                seq=block_seq, completed_seq=completed_seq, actor=actor,
                mechanism=name, event_id=block_id,
            )
            reads.extend(cmd_reads)
            mutations.extend(cmd_mutations)
            flags.extend(cmd_flags)
        elif base_name in MUTATOR_TOOLS:
            path = normalize_path(
                str(
                    tool_input.get("file_path")
                    or tool_input.get("notebook_path")
                    or ""
                ),
                cwd,
            )
            mutations.append(
                MutationEvidence(
                    block_seq, completed_seq, path, succeeded, actor, name,
                    block_id,
                )
            )
            if result_record is None:
                flags.append(
                    FlaggedEvent(
                        block_id, block_seq, None, "unsupported",
                        (base_name,), None, (), actor, True,
                    )
                )
        elif base_name in INERT_CLAUDE_TOOLS:
            pass
        else:
            flags.append(
                FlaggedEvent(
                    block_id, block_seq, completed_seq, "ambiguous",
                    (base_name,), None, (), actor, True,
                )
            )

    return {
        "adapter": "claude",
        "init": init,
        "terminal": terminal,
        "observed_model": init.get("model"),
        "reads": reads,
        "mutations": mutations,
        "texts": texts,
        "flags": flags,
    }


def normalize_codex(
    events: list[dict[str, Any]], required_manifest: dict[str, Any], cwd: str | None
) -> dict[str, Any]:
    seq = 0
    started_items: dict[str, int] = {}
    completed_items: set[str] = set()
    started_commands: dict[str, str] = {}
    reads: list[ReadEvidence] = []
    mutations: list[MutationEvidence] = []
    texts: list[tuple[int, str, str]] = []
    flags: list[FlaggedEvent] = []
    terminal: dict[str, Any] = {}
    terminal_seq: int | None = None
    observed_model: str | None = None

    def command_string(item: dict[str, Any]) -> str:
        command_value = item.get("command") or ""
        if isinstance(command_value, list):
            if (
                len(command_value) >= 3
                and os.path.basename(str(command_value[0]))
                in {"bash", "zsh", "sh"}
                and str(command_value[1]) in {"-c", "-lc"}
            ):
                return str(command_value[2])
            return shlex.join(str(part) for part in command_value)
        return str(command_value)

    for event in events:
        seq += 1
        event_type = str(event.get("type") or "")
        if event_type not in KNOWN_CODEX_EVENT_TYPES:
            flags.append(
                FlaggedEvent(
                    f"event-{seq}", seq, None, "ambiguous",
                    (event_type,), None, (), "unknown", True,
                )
            )
            continue
        if terminal_seq is not None and event_type.startswith("item"):
            flags.append(
                FlaggedEvent(
                    f"event-{seq}", seq, None, "ambiguous",
                    ("post_terminal_action",), None, (), "root", True,
                )
            )
            continue
        if event_type in {"thread.started", "thread_started"}:
            observed_model = event.get("model") or observed_model
        elif event_type == "item.started":
            item = event.get("item") or {}
            item_id = str(item.get("id") or "")
            if item_id:
                started_items[item_id] = seq
                if item.get("type") in {"command_execution", "command"}:
                    started_commands[item_id] = command_string(item)
        elif event_type == "item.updated":
            pass
        elif event_type == "item.completed":
            item = event.get("item") or {}
            item_id = str(item.get("id") or f"item-{seq}")
            completed_items.add(item_id)
            invoked_seq = started_items.get(item_id)
            item_type = str(item.get("type") or "")
            if item_type not in KNOWN_CODEX_ITEM_TYPES:
                flags.append(
                    FlaggedEvent(
                        item_id, invoked_seq, seq, "ambiguous",
                        (item_type,), None, (), "root", True,
                    )
                )
                continue
            if item_type in CODEX_INERT_ITEM_TYPES:
                continue
            if item_type in {"agent_message", "message"}:
                texts.append((seq, str(item.get("text") or ""), "root"))
            elif item_type in {"command_execution", "command"}:
                command = command_string(item)
                succeeded = (
                    item.get("exit_code") in (None, 0)
                    and item.get("status") not in {"failed", "declined"}
                )
                command_output = str(item.get("aggregated_output") or "")
                cmd_reads, cmd_mutations, cmd_flags = shell_evidence(
                    command, cwd, required_manifest, command_output, succeeded,
                    seq=invoked_seq, completed_seq=seq, actor="root",
                    mechanism=item_type, event_id=item_id,
                )
                reads.extend(cmd_reads)
                mutations.extend(cmd_mutations)
                flags.extend(cmd_flags)
            elif item_type in {"file_change", "file_changes"}:
                succeeded = item.get("status") not in {"failed", "declined"}
                changes = item.get("changes") or []
                if isinstance(changes, dict):
                    changes = [
                        {"path": path, **(value if isinstance(value, dict) else {})}
                        for path, value in changes.items()
                    ]
                for change in changes:
                    if not isinstance(change, dict):
                        continue
                    path = normalize_path(
                        str(change.get("path") or change.get("file_path") or ""),
                        cwd,
                    )
                    mutations.append(
                        MutationEvidence(
                            invoked_seq, seq, path, succeeded, "root",
                            item_type, item_id,
                        )
                    )
        elif event_type in {"turn.completed", "turn_completed"}:
            terminal_seq = seq
            terminal = {
                "present": True,
                "subtype": "success",
                "is_error": False,
                "api_error_status": None,
                "terminal_reason": "completed",
                "stop_reason": None,
                "permission_denials": 0,
                "total_cost_usd": None,
                "num_turns": 1,
                "usage": event.get("usage") or {},
                "model_usage_ids": [observed_model] if observed_model else [],
            }
        elif event_type in {"turn.failed", "turn_failed", "error"}:
            terminal_seq = seq
            terminal = {
                "present": True,
                "subtype": "error",
                "is_error": True,
                "api_error_status": event.get("status_code"),
                "terminal_reason": "failed",
                "stop_reason": None,
                "permission_denials": 0,
                "total_cost_usd": None,
                "num_turns": 1,
                "usage": event.get("usage"),
                "model_usage_ids": [observed_model] if observed_model else [],
            }

    for item_id, started_seq in started_items.items():
        if item_id in completed_items:
            continue
        command = started_commands.get(item_id)
        boundary_relevant = True
        programs: tuple[str, ...] = ("unpaired_invocation",)
        if command is not None:
            evaluation = shell_observer.evaluate_shell_command(
                command, cwd, required_manifest, "", False, normalize_path
            )
            programs = evaluation.programs or programs
            boundary_relevant = bool(
                evaluation.mutation_targets
                or evaluation.parser_result == "ambiguous"
            )
        flags.append(
            FlaggedEvent(
                item_id, started_seq, None, "unsupported", programs,
                command_sha256(command) if command else None, (), "root",
                boundary_relevant,
            )
        )

    return {
        "adapter": "codex",
        "init": {
            "permission_mode": None,
            "model": observed_model,
            "tools": [],
            "cwd": cwd,
        },
        "terminal": terminal,
        "observed_model": observed_model,
        "reads": reads,
        "mutations": mutations,
        "texts": texts,
        "flags": flags,
    }


def normalize_transcript(
    events: list[dict[str, Any]],
    adapter: str,
    required_manifest: dict[str, Any] | None = None,
    cwd: str | None = None,
    inert_event_types: Iterable[str] | None = None,
) -> dict[str, Any]:
    manifest = required_manifest or {}
    if adapter == "claude":
        return normalize_claude(events, manifest, set(inert_event_types or ()))
    if adapter == "codex":
        return normalize_codex(events, manifest, cwd)
    raise ValueError(f"unsupported transcript adapter: {adapter}")


def inspect_run_validity(
    meta: dict[str, Any],
    normalized: dict[str, Any],
    invalid_json_lines: Iterable[int] = (),
) -> dict[str, Any]:
    reasons: list[str] = []
    invalid_lines = list(invalid_json_lines)
    terminal = normalized.get("terminal") or {}
    init = normalized.get("init") or {}
    contract = meta.get("adapter_contract") or {}

    if invalid_lines:
        reasons.append("transcript_invalid_json")
    if meta.get("timed_out"):
        reasons.append("model_timeout")
    if meta.get("exit_code") not in (0, None):
        reasons.append("model_process_nonzero")
    if not terminal.get("present"):
        reasons.append("terminal_event_missing")
    if terminal.get("is_error"):
        reasons.append("terminal_result_error")
    if terminal.get("api_error_status") is not None:
        reasons.append("provider_api_error")
    expected_permission = contract.get("expected_permission_mode")
    if expected_permission and init.get("permission_mode") != expected_permission:
        reasons.append("permission_mode_mismatch")
    if (
        contract.get("expect_zero_permission_denials")
        and int(terminal.get("permission_denials") or 0) > 0
    ):
        reasons.append("permission_denials_present")
    failed_mutations = [
        mutation
        for mutation in normalized.get("mutations") or []
        if not mutation.succeeded
    ]
    successful_mutations = [
        mutation
        for mutation in normalized.get("mutations") or []
        if mutation.succeeded
    ]
    if failed_mutations and not successful_mutations:
        reasons.append("mutation_capability_denied")

    return {
        "status": "valid" if not reasons else "invalid",
        "reason_codes": sorted(set(reasons)),
        "invalid_json_lines": invalid_lines[:20],
        "observed_permission_mode": init.get("permission_mode"),
        "permission_denials": int(terminal.get("permission_denials") or 0),
    }


def parse_diff(diff_text: str) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            files.setdefault(current, [])
        elif line.startswith("+++ /dev/null"):
            current = None
        elif line.startswith("+") and not line.startswith("+++") and current:
            files[current].append(line[1:])
    return files


@dataclass(frozen=True)
class MutationBoundary:
    first_edit: MutationEvidence | None
    cutoff: int
    boundary_ambiguous: bool
    boundary_flags: tuple[FlaggedEvent, ...]
    unpaired_mutating_invocations: tuple[FlaggedEvent, ...]
    mutation_start_unobservable: bool
    diff_without_mutation: bool

    @property
    def confidence(self) -> str:
        if self.boundary_ambiguous:
            return "ambiguous_prior_commands"
        if self.first_edit:
            return "unambiguous"
        return "no_mutation_observed"


def mutation_boundary(
    mutations: list[MutationEvidence],
    flags: list[FlaggedEvent],
    changed_code_files: Iterable[str] = (),
    code_path_predicate: Callable[[str], bool] = is_code_path,
) -> MutationBoundary:
    successful_code_mutations = [
        mutation
        for mutation in mutations
        if mutation.succeeded and code_path_predicate(mutation.path)
    ]
    observable = sorted(
        (
            mutation
            for mutation in successful_code_mutations
            if mutation.seq is not None
        ),
        key=lambda mutation: int(mutation.seq or 0),
    )
    first_edit = observable[0] if observable else None
    cutoff = int(first_edit.seq) if first_edit else FAR_FUTURE_SEQ

    boundary_flags = tuple(
        flag
        for flag in flags
        if flag.boundary_relevant
        and (flag.seq if flag.seq is not None else flag.completed_seq or 0)
        < cutoff
    )
    unpaired = tuple(
        flag
        for flag in flags
        if flag.parser_result == "unsupported" and flag.boundary_relevant
    )
    return MutationBoundary(
        first_edit=first_edit,
        cutoff=cutoff,
        boundary_ambiguous=bool(boundary_flags),
        boundary_flags=boundary_flags,
        unpaired_mutating_invocations=unpaired,
        mutation_start_unobservable=any(
            mutation.seq is None for mutation in successful_code_mutations
        ),
        diff_without_mutation=bool(
            list(changed_code_files) and not successful_code_mutations
        ),
    )


def merged_intervals(
    intervals: Iterable[tuple[int, int]]
) -> list[tuple[int, int]]:
    ordered = sorted(
        (start, end) for start, end in intervals if start > 0 and end >= start
    )
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def runtime_channel(
    adapter: str, contract: dict[str, Any], path: str
) -> tuple[bool, bool]:
    declared = contract.get("runtime_context_paths")
    if declared:
        name = PurePosixPath(path).name
        for channel in declared:
            channel_name = PurePosixPath(str(channel)).name
            if name == channel_name:
                return True, False
            if name.lower() == channel_name.lower():
                return True, True
        return False, False
    surface = "codex_cli" if adapter == "codex" else "claude_cli"
    return oc.runtime_context_match(surface, path)


def resolve_artifact(
    path: str,
    reads: list[ReadEvidence],
    cutoff: int,
    manifest: dict[str, Any],
    *,
    runtime_channel: bool = False,
    case_alias: bool = False,
) -> dict[str, Any]:
    eligible = [
        evidence
        for evidence in reads
        if evidence.path == path
        and evidence.completed_seq is not None
        and evidence.completed_seq < cutoff
    ]
    root_reads = [e for e in eligible if e.actor != "subagent"]
    subagent_only = bool(eligible) and not root_reads

    direct_states: list[str] = []
    unsupported_present = manifest_entry(manifest, path) is None
    intervals: list[tuple[int, int]] = []
    evidence_ids: list[str] = []
    for evidence in root_reads:
        evidence_ids.append(evidence.event_id)
        if evidence.proof == "proven" and not evidence.intervals:
            direct_states.append("proven_delivered")
        elif evidence.proof == "unsupported":
            unsupported_present = True
        elif evidence.proof == "failed":
            direct_states.append("failed_read")
        else:
            direct_states.append("partial_read")
        intervals.extend(evidence.intervals)

    entry = manifest_entry(manifest, path)
    expected_lines = int((entry or {}).get("lines") or 0)
    if expected_lines > 0 and intervals:
        merged = merged_intervals(intervals)
        if (
            merged
            and merged[0][0] <= 1
            and merged[-1][1] >= expected_lines
            and all(
                merged[index][1] + 1 >= merged[index + 1][0]
                for index in range(len(merged) - 1)
            )
        ):
            direct_states.append("proven_delivered")

    resolution = oc.resolve_artifact_state(
        direct_states,
        unsupported_present=unsupported_present,
        runtime_unverified_present=runtime_channel,
        case_alias=case_alias,
    )
    return {
        "path": path,
        "resolution": resolution,
        "evidence_event_ids": sorted(set(evidence_ids)),
        "subagent_only_read": subagent_only,
    }


def evaluate_group_policies(
    policies: list[oc.GroupPolicy],
    reads: list[ReadEvidence],
    cutoff: int,
    manifest: dict[str, Any],
    channel_for_path: Callable[[str], tuple[bool, bool]],
) -> dict[str, Any]:
    required_paths: dict[str, dict[str, Any]] = {}
    for policy in policies:
        member_paths = policy.members or policy.matched_paths
        if policy.mode == "at_least" and not policy.matched_paths:
            required_paths[policy.glob or policy.group_id] = {
                "path": policy.glob or policy.group_id,
                "resolution": oc.resolve_artifact_state(
                    [], unsupported_present=True
                ),
                "evidence_event_ids": [],
                "subagent_only_read": False,
            }
            continue
        for path in member_paths:
            if path in required_paths:
                continue
            channel, alias = channel_for_path(path)
            required_paths[path] = resolve_artifact(
                path, reads, cutoff, manifest,
                runtime_channel=channel, case_alias=alias,
            )

    satisfied = {
        path
        for path, row in required_paths.items()
        if row["resolution"].satisfied
    }
    group_rows: list[dict[str, Any]] = []
    percent_rows: list[tuple[oc.GroupPolicy, float]] = []
    for policy in policies:
        gate_satisfied, fraction = oc.group_satisfaction(policy, satisfied)
        percent_rows.append((policy, fraction))
        members = []
        member_paths = policy.members or policy.matched_paths
        if policy.mode == "at_least" and not policy.matched_paths:
            member_paths = (policy.glob or policy.group_id,)
        for path in member_paths:
            row = required_paths[path]
            resolution = row["resolution"]
            member = {
                "path": path,
                "state": resolution.state,
                "evidence_event_ids": row["evidence_event_ids"],
            }
            if resolution.case_alias:
                member["case_alias"] = True
            if row["subagent_only_read"]:
                member["subagent_only_read"] = True
            members.append(member)
        group_rows.append(
            {
                "group_id": policy.group_id,
                "mode": policy.mode,
                "weight": policy.weight,
                "min_count": policy.min_count or None,
                "gate_satisfied": gate_satisfied,
                "leaf_fraction": round(fraction, 4),
                "members": members,
            }
        )

    return {
        "groups": group_rows,
        "delivery_percent": oc.delivery_percent(percent_rows),
        "resolutions": [
            row["resolution"] for row in required_paths.values()
        ],
        "satisfied_paths": satisfied,
        "artifact_rows": required_paths,
    }

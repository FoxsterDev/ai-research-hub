#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "templates" / "task_registry"

EVENTS_PATH = Path("AIOutput/Registry/task_events.jsonl")
INDEX_PATH = Path("AIOutput/Registry/task_index.yaml")
SCHEMA_JSON_PATH = Path("AIOutput/Registry/task_event_schema.json")
SCHEMA_MD_PATH = Path("AIOutput/Registry/task_event_schema.md")
README_PATH = Path("AIOutput/Registry/README.md")
ARCHIVE_POLICY_PATH = Path("AIOutput/Registry/archive_policy.md")
METRICS_PATH = Path("AIOutput/Registry/metrics_summary.md")
LESSONS_PATH = Path("AIOutput/Registry/lessons_learned.md")
TASK_AUDITS_DIR = Path("AIOutput/Reports/Tasks")
TASK_AUDITS_README_PATH = TASK_AUDITS_DIR / "README.md"

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return collapsed or "task"


def auto_task_id(project_id: str, summary: str, origin_ref: str) -> str:
    topic = slugify(summary)[:48]
    project = slugify(project_id).replace("-", "_")
    digest = hashlib.sha1(f"{project_id}|{summary}|{origin_ref}".encode("utf-8")).hexdigest()[:4]
    return f"{project}_{topic}_{digest}"


def task_slug_to_key(task_id: str) -> str:
    return task_id


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_template(name: str) -> str:
    return read_text(TEMPLATES_DIR / name)


def bootstrap_repo(repo_root: Path) -> list[Path]:
    created: list[Path] = []
    template_map = {
        README_PATH: "README.md",
        SCHEMA_JSON_PATH: "task_event_schema.json",
        SCHEMA_MD_PATH: "task_event_schema.md",
        ARCHIVE_POLICY_PATH: "archive_policy.md",
        METRICS_PATH: "metrics_summary.md",
        LESSONS_PATH: "lessons_learned.md",
        INDEX_PATH: "task_index.yaml",
        TASK_AUDITS_README_PATH: "task_audits_README.md",
    }

    for relative_path, template_name in template_map.items():
        target = repo_root / relative_path
        if target.exists():
            continue
        write_text(target, load_template(template_name))
        created.append(target)

    events_path = repo_root / EVENTS_PATH
    if not events_path.exists():
        write_text(events_path, "")
        created.append(events_path)

    return created


def load_schema(repo_root: Path) -> dict[str, Any]:
    return json.loads(read_text(repo_root / SCHEMA_JSON_PATH))


def parse_jsonl_events(events_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []

    if not events_path.exists():
        return events, errors

    for line_number, raw_line in enumerate(read_text(events_path).splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: malformed JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number}: event must be a JSON object")
            continue
        events.append(value)

    return events, errors


def validate_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "null":
        return value is None
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return False


def validate_against_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type is not None:
        if isinstance(expected_type, list):
            if not any(validate_type(value, option) for option in expected_type):
                errors.append(f"{path}: expected one of {expected_type}, got {type(value).__name__}")
                return errors
        else:
            if not validate_type(value, expected_type):
                errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
                return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string shorter than minLength {min_length}")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: invalid date-time format")

    if isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                errors.extend(validate_against_schema(item, item_schema, f"{path}[{index}]"))

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")

        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key!r}")

        for key, prop_schema in properties.items():
            if key in value:
                errors.extend(validate_against_schema(value[key], prop_schema, f"{path}.{key}"))

    return errors


def ensure_string_list(values: Optional[list[str]]) -> list[str]:
    if not values:
        return []
    flattened: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                flattened.append(part)
    return flattened


def append_event(repo_root: Path, event: dict[str, Any]) -> None:
    events_path = repo_root / EVENTS_PATH
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def snapshot_from_events(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["task_id"]].append(event)

    snapshots: dict[str, dict[str, Any]] = {}
    for task_id, task_events in grouped.items():
        latest = task_events[-1]
        snapshots[task_id] = {
            "project_id": latest["project_id"],
            "repo_id": latest["repo_id"],
            "origin_type": latest["origin_type"],
            "origin_ref": task_events[0]["origin_ref"],
            "parent_task_id": latest.get("parent_task_id"),
            "latest_timestamp": latest["timestamp"],
            "latest_event_type": latest["event_type"],
            "task_kind": latest["task_kind"],
            "severity": latest["severity"],
            "platform": latest["platform"],
            "summary": latest["summary"],
            "engineering_state": latest["engineering_state"],
            "validation_state": latest["validation_state"],
            "acceptance_state": latest["acceptance_state"],
            "linked_audit_path": latest["linked_audit_path"],
            "protocols_used": latest["protocols_used"],
            "skills_used": latest["skills_used"],
        }

    return dict(sorted(snapshots.items(), key=lambda item: item[0]))


def yaml_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
        return key
    return json.dumps(key)


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./:-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def emit_yaml(value: Any, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, nested in value.items():
            rendered_key = yaml_key(key)
            if isinstance(nested, (dict, list)):
                lines.append(f"{prefix}{rendered_key}:")
                lines.extend(emit_yaml(nested, indent + 1))
            else:
                lines.append(f"{prefix}{rendered_key}: {yaml_scalar(nested)}")
        return lines

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(emit_yaml(item, indent + 1))
            else:
                lines.append(f"{prefix}- {yaml_scalar(item)}")
        return lines

    return [f"{prefix}{yaml_scalar(value)}"]


def write_index(repo_root: Path, snapshots: dict[str, dict[str, Any]]) -> str:
    index_text = "\n".join(emit_yaml({"tasks": snapshots})) + "\n"
    write_text(repo_root / INDEX_PATH, index_text)
    return index_text


def build_event_from_args(args: argparse.Namespace, event_type: str, timestamp: Optional[str] = None) -> dict[str, Any]:
    summary = args.summary.strip()
    origin_ref = args.origin_ref.strip()
    task_id = args.task_id or auto_task_id(args.project_id, summary, origin_ref)
    return {
        "timestamp": timestamp or now_utc(),
        "task_id": task_id,
        "project_id": args.project_id,
        "repo_id": args.repo_id,
        "origin_type": args.origin_type,
        "origin_ref": origin_ref,
        "parent_task_id": args.parent_task_id,
        "event_type": event_type,
        "actor": args.actor,
        "task_kind": args.task_kind,
        "severity": args.severity,
        "platform": ensure_string_list(args.platform),
        "summary": summary,
        "engineering_state": args.engineering_state,
        "validation_state": args.validation_state,
        "acceptance_state": args.acceptance_state,
        "protocols_used": ensure_string_list(args.protocols_used),
        "skills_used": ensure_string_list(args.skills_used),
        "linked_audit_path": args.linked_audit_path,
    }


def command_bootstrap(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    created = bootstrap_repo(repo_root)
    if created:
        print("BOOTSTRAP: created")
        for path in created:
            print(f"  - {path.relative_to(repo_root)}")
    else:
        print("BOOTSTRAP: already ready")
    return 0


def command_reconcile(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    bootstrap_repo(repo_root)
    events, parse_errors = parse_jsonl_events(repo_root / EVENTS_PATH)
    if parse_errors:
        for error in parse_errors:
            print(f"ERROR: {error}")
        return 1
    snapshots = snapshot_from_events(events)
    write_index(repo_root, snapshots)
    print(f"RECONCILED: {len(snapshots)} task snapshot(s)")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    schema = load_schema(repo_root)
    events, parse_errors = parse_jsonl_events(repo_root / EVENTS_PATH)
    violations: list[str] = list(parse_errors)

    for index, event in enumerate(events, start=1):
        violations.extend(validate_against_schema(event, schema, f"event[{index}]"))

    snapshots = snapshot_from_events(events)
    expected_index_text = "\n".join(emit_yaml({"tasks": snapshots})) + "\n"
    actual_index_text = read_text(repo_root / INDEX_PATH) if (repo_root / INDEX_PATH).exists() else ""

    warnings: list[str] = []
    if actual_index_text != expected_index_text:
        warnings.append("task_index.yaml differs from the derived snapshot and should be reconciled")

    for snapshot in snapshots.values():
        audit_path = repo_root / snapshot["linked_audit_path"]
        if snapshot["linked_audit_path"] and not audit_path.exists():
            warnings.append(f"missing referenced audit note: {snapshot['linked_audit_path']}")

    status = "valid"
    exit_code = 0
    if violations:
        status = "invalid"
        exit_code = 1
    elif warnings:
        status = "valid_with_warnings"

    print(f"STATUS: {status}")
    if violations:
        print("VIOLATIONS:")
        for violation in violations:
            print(f"  - {violation}")
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    if not violations and not warnings:
        print(f"OK: {len(events)} event(s), {len(snapshots)} task snapshot(s)")

    return exit_code


def command_start(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    bootstrap_repo(repo_root)
    args.actor = "human" if args.actor is None else args.actor
    args.origin_type = args.origin_type or "chat"
    args.engineering_state = "in_progress"
    args.validation_state = "not_validated"
    args.acceptance_state = "pending_human_feedback"
    event = build_event_from_args(args, "task_started")
    append_event(repo_root, event)
    return command_reconcile(argparse.Namespace(repo_root=str(repo_root)))


def command_finish(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    bootstrap_repo(repo_root)
    args.actor = "ai" if args.actor is None else args.actor
    args.origin_type = args.origin_type or "chat"
    args.engineering_state = "work_finished"
    args.acceptance_state = "pending_human_feedback"
    event = build_event_from_args(args, "work_finished")
    append_event(repo_root, event)
    return command_reconcile(argparse.Namespace(repo_root=str(repo_root)))


def apply_feedback_mode(args: argparse.Namespace) -> list[dict[str, Any]]:
    base = {
        "repo_root": args.repo_root,
        "task_id": args.task_id,
        "project_id": args.project_id,
        "repo_id": args.repo_id,
        "origin_type": args.origin_type or "chat",
        "origin_ref": args.origin_ref,
        "parent_task_id": args.parent_task_id,
        "actor": args.actor or "human",
        "task_kind": args.task_kind,
        "severity": args.severity,
        "platform": args.platform,
        "protocols_used": args.protocols_used,
        "skills_used": args.skills_used,
        "linked_audit_path": args.linked_audit_path,
    }

    timestamp = now_utc()
    if args.mode == "works":
        runtime_args = argparse.Namespace(
            **base,
            summary=args.runtime_summary or args.summary,
            engineering_state="work_finished",
            validation_state="runtime_validated",
            acceptance_state="pending_human_feedback",
        )
        accept_args = argparse.Namespace(
            **base,
            summary=args.summary,
            engineering_state="work_finished",
            validation_state="runtime_validated",
            acceptance_state="accepted",
        )
        return [
            build_event_from_args(runtime_args, "runtime_validated", timestamp),
            build_event_from_args(accept_args, "human_accepted", timestamp),
        ]

    if args.mode == "has_bugs":
        reopen_args = argparse.Namespace(
            **base,
            summary=args.summary,
            engineering_state="work_finished",
            validation_state=args.validation_state,
            acceptance_state="reopened",
        )
        return [build_event_from_args(reopen_args, "human_reopened", timestamp)]

    if args.mode == "rejected":
        reject_args = argparse.Namespace(
            **base,
            summary=args.summary,
            engineering_state="work_finished",
            validation_state=args.validation_state,
            acceptance_state="rejected",
        )
        return [build_event_from_args(reject_args, "human_rejected", timestamp)]

    event_type_map = {
        "build_validated": ("build_validated", "build_validated"),
        "runtime_validated": ("runtime_validated", "runtime_validated"),
        "production_validated": ("production_validated", "production_validated"),
    }
    event_type, validation_state = event_type_map[args.mode]
    validation_args = argparse.Namespace(
        **base,
        summary=args.summary,
        engineering_state="work_finished",
        validation_state=validation_state,
        acceptance_state=args.acceptance_state,
    )
    return [build_event_from_args(validation_args, event_type, timestamp)]


def command_feedback(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    bootstrap_repo(repo_root)
    for event in apply_feedback_mode(args):
        append_event(repo_root, event)
    return command_reconcile(argparse.Namespace(repo_root=str(repo_root)))


def command_archive_plan(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    events_path = repo_root / EVENTS_PATH
    line_count = 0
    size_bytes = 0
    if events_path.exists():
        size_bytes = events_path.stat().st_size
        line_count = len(read_text(events_path).splitlines())

    triggered = []
    if line_count > 5000:
        triggered.append("line threshold exceeded")
    if size_bytes > 5 * 1024 * 1024:
        triggered.append("size threshold exceeded")

    status = "not_needed"
    if triggered:
        status = "recommended"

    print(f"ROLLOVER: {status}")
    print(f"  - lines: {line_count}")
    print(f"  - size_bytes: {size_bytes}")
    if triggered:
        for item in triggered:
            print(f"  - trigger: {item}")
    return 0


def add_common_identity_args(parser: argparse.ArgumentParser, require_task_id: bool = False) -> None:
    parser.add_argument("--repo-root", default=".", help="Repo root containing AIOutput/")
    parser.add_argument("--task-id", required=require_task_id, help="Existing task id. If omitted on start/finish, one is generated.")
    parser.add_argument("--project-id", required=True, help="Owning project id")
    parser.add_argument("--repo-id", required=True, help="Owning repo id")
    parser.add_argument("--origin-type", choices=["jira", "chat", "manual"], default="chat")
    parser.add_argument("--origin-ref", required=True, help="External id or trigger text")
    parser.add_argument("--parent-task-id", help="Optional parent task id for follow-ups or regressions")
    parser.add_argument("--task-kind", choices=["bug", "refactor", "feature", "review", "incident", "research"], required=True)
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], required=True)
    parser.add_argument("--platform", action="append", help="Platform value. Repeat or pass comma-separated values.")
    parser.add_argument("--protocols-used", action="append", help="Protocol path. Repeat or pass comma-separated values.")
    parser.add_argument("--skills-used", action="append", help="Skill path. Repeat or pass comma-separated values.")
    parser.add_argument("--linked-audit-path", default="", help="Repo-relative audit note path")
    parser.add_argument("--actor", choices=["ai", "human", "system"], help="Override actor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap, write, and validate XUUnity task registries")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Create task-registry scaffold when missing")
    bootstrap_parser.add_argument("--repo-root", default=".", help="Repo root containing AIOutput/")
    bootstrap_parser.set_defaults(func=command_bootstrap)

    reconcile_parser = subparsers.add_parser("reconcile", help="Rebuild task_index.yaml from task_events.jsonl")
    reconcile_parser.add_argument("--repo-root", default=".", help="Repo root containing AIOutput/")
    reconcile_parser.set_defaults(func=command_reconcile)

    validate_parser = subparsers.add_parser("validate", help="Validate events and snapshot consistency")
    validate_parser.add_argument("--repo-root", default=".", help="Repo root containing AIOutput/")
    validate_parser.set_defaults(func=command_validate)

    start_parser = subparsers.add_parser("start", help="Append a task_started event")
    add_common_identity_args(start_parser, require_task_id=False)
    start_parser.add_argument("--summary", required=True, help="Initial task summary")
    start_parser.set_defaults(func=command_start)

    finish_parser = subparsers.add_parser("finish", help="Append a work_finished event")
    add_common_identity_args(finish_parser, require_task_id=False)
    finish_parser.add_argument("--summary", required=True, help="Closure summary")
    finish_parser.add_argument(
        "--validation-state",
        choices=["not_validated", "build_validated", "runtime_validated", "production_validated"],
        default="build_validated",
    )
    finish_parser.set_defaults(func=command_finish)

    feedback_parser = subparsers.add_parser("feedback", help="Append feedback and validation events")
    add_common_identity_args(feedback_parser, require_task_id=True)
    feedback_parser.add_argument(
        "--mode",
        required=True,
        choices=["works", "has_bugs", "rejected", "build_validated", "runtime_validated", "production_validated"],
    )
    feedback_parser.add_argument("--summary", required=True, help="Feedback summary")
    feedback_parser.add_argument("--runtime-summary", help="Optional separate runtime-validation summary for works mode")
    feedback_parser.add_argument(
        "--validation-state",
        choices=["not_validated", "build_validated", "runtime_validated", "production_validated"],
        default="build_validated",
    )
    feedback_parser.add_argument(
        "--acceptance-state",
        choices=["pending_human_feedback", "accepted", "reopened", "rejected"],
        default="pending_human_feedback",
    )
    feedback_parser.set_defaults(func=command_feedback)

    archive_parser = subparsers.add_parser("archive-plan", help="Check rollover thresholds for task history")
    archive_parser.add_argument("--repo-root", default=".", help="Repo root containing AIOutput/")
    archive_parser.set_defaults(func=command_archive_plan)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

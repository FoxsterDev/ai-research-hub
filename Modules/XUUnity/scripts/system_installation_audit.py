#!/usr/bin/env python3
"""Deterministic, model-independent audit of an installed XUUnity corpus.

The audit is model-independent and stdlib-only. It checks public routing and
corpus invariants, then composes existing routing, storage, and entrypoint
checks when those tools are installed. It mutates nothing unless ``--output``
explicitly names an evidence file to replace atomically. Output uses stable
repo-relative paths and never includes matched file contents.

Exit codes:
    0: clean
    1: findings
    2: audit invalid or could not complete
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import unquote


SCHEMA_VERSION = "xuunity.system-installation-audit.v2"
AUDITED_SUFFIXES = {".html", ".json", ".md", ".py", ".sh", ".yaml", ".yml"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKILL_FAMILY_RE = re.compile(r"(?:Skill family|Skill): `([^`/]+)/")
DESIGN_ROW_RE = re.compile(r"^\|\s*`([^`]+\.md)`\s*\|", re.MULTILINE)
COMMAND_RE = re.compile(r"`(xuunity [^`]+)`", re.IGNORECASE)
OWNER_RE = re.compile(r"->\s*`([^`]+\.md)`")
PROTECTED_HEADING = "## Skill Routing Hints"
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def display_path(path: Path, host_root: Path, air_root: Path) -> str:
    """Return a stable public path without exposing an absolute host path."""
    try:
        value = path.resolve().relative_to(host_root.resolve()).as_posix()
        return value or "."
    except ValueError:
        try:
            value = path.resolve().relative_to(air_root.resolve()).as_posix()
            return f"AIRoot/{value}" if value else "AIRoot"
        except ValueError:
            return f"<outside-host>/{path.name}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_filesystem_public_files(air_root: Path) -> list[Path]:
    """Return candidate text files before publishability filtering."""
    return sorted(
        path
        for path in air_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in AUDITED_SUFFIXES
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
    )


def iter_public_files(air_root: Path) -> list[Path]:
    """Return tracked and unignored pending files, excluding vendored/ignored output.

    A checkout may legitimately contain large ignored dependency trees. They are
    neither installed protocol content nor publishable pending changes, so they
    must not affect links, reachability, fingerprints, or inventory counts.
    When git metadata is unavailable (for example a copied test fixture), fall
    back to the filesystem candidates so the audit remains usable.
    """
    candidates = iter_filesystem_public_files(air_root)
    try:
        completed = subprocess.run(
            [
                "git", "-C", str(air_root), "ls-files", "--cached", "--others",
                "--exclude-standard", "-z",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return candidates
    if completed.returncode != 0:
        return candidates
    selected = {
        (air_root / raw.decode("utf-8", errors="surrogateescape")).resolve()
        for raw in completed.stdout.split(b"\0")
        if raw
    }
    return [path for path in candidates if path.resolve() in selected]


def is_test_content(path: Path, module_root: Path) -> bool:
    try:
        relative = path.relative_to(module_root)
    except ValueError:
        relative = path
    return (
        "tests" in relative.parts
        or path.name.startswith("test_")
    )


def protocol_fingerprint(files: Iterable[Path], air_root: Path) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(air_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return f"sha256:{digest.hexdigest()}"


def add_finding(
    findings: list[dict[str, str]],
    *,
    kind: str,
    severity: str,
    path: str,
    message: str,
) -> None:
    findings.append(
        {
            "kind": kind,
            "severity": severity,
            "path": path,
            "message": message,
        }
    )


def normalize_command(command: str) -> str:
    normalized = " ".join(command.lower().split())
    return normalized.removesuffix(" ...").strip()


def inspect_markdown_links(
    markdown: dict[Path, str],
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> None:
    for source, text in sorted(markdown.items()):
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(maxsplit=1)[0].strip("'\"")
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if (
                not target
                or "://" in target
                or target.startswith(("#", "mailto:", "/"))
                or any(token in target for token in ("<", ">", "{", "}", "*"))
                or not target.lower().endswith(".md")
            ):
                continue
            resolved = (source.parent / target).resolve()
            if not resolved.exists():
                add_finding(
                    findings,
                    kind="broken_markdown_link",
                    severity="medium",
                    path=display_path(source, host_root, air_root),
                    message=f"Markdown target does not exist: {target}",
                )


def publishable_status(path: Path) -> str:
    """Classify whether a path can reach a public remote.

    Returns `tracked` when git tracks the file, `local_only` when it is both
    untracked and ignored, and `untracked` otherwise. Any environment failure
    resolves to `untracked` so an unverifiable path stays a boundary finding.
    """
    parent = str(path.parent)
    name = path.name
    try:
        tracked = subprocess.run(
            ["git", "-C", parent, "ls-files", "--error-unmatch", "--", name],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if tracked.returncode == 0:
            return "tracked"
        ignored = subprocess.run(
            ["git", "-C", parent, "check-ignore", "-q", "--", name],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "untracked"
    return "local_only" if ignored.returncode == 0 else "untracked"


def inspect_private_path_leaks(
    public_text: dict[Path, str],
    host_root: Path,
    air_root: Path,
    forbidden_tokens: Sequence[str],
    findings: list[dict[str, str]],
) -> None:
    generic_user_segments = {
        "example",
        "me",
        "runner",
        "runneradmin",
        "runner~1",
        "user",
        "username",
        "you",
        "your-username",
        "your_username",
    }
    path_patterns = (
        re.compile(
            r"/Users/(?P<user>[A-Za-z0-9._~-]+)/(?P<tail>[^/\s`\"']+)"
        ),
        re.compile(
            r"/home/(?P<user>[A-Za-z0-9._~-]+)/(?P<tail>[^/\s`\"']+)"
        ),
        re.compile(
            r"[A-Za-z]:(?:\\+|/)Users(?:\\+|/)"
            r"(?P<user>[^\\/\s]+)(?:\\+|/)(?P<tail>[^\\/\s`\"']+)"
        ),
    )
    for source, text in sorted(public_text.items()):
        path_leak = any(
            match.group("user").strip("<>").lower() not in generic_user_segments
            and match.group("tail") != "..."
            and not (
                match.group("tail").startswith("<")
                and match.group("tail").endswith(">")
            )
            for pattern in path_patterns
            for match in pattern.finditer(text)
        )
        token_leak = any(token and token in text for token in forbidden_tokens)
        if not (path_leak or token_leak):
            continue
        if publishable_status(source) == "local_only":
            add_finding(
                findings,
                kind="local_scratch_path_leak",
                severity="low",
                path=display_path(source, host_root, air_root),
                message=(
                    "Untracked and git-ignored local file contains a concrete host path; "
                    "it cannot reach a public remote."
                ),
            )
            continue
        add_finding(
            findings,
            kind="public_path_leak",
            severity="high",
            path=display_path(source, host_root, air_root),
            message="Public text contains a concrete host path or forbidden private token.",
        )


def inspect_skill_registry(
    module_root: Path,
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> int:
    skills_root = module_root / "skills"
    registry = skills_root / "registry.md"
    families = sorted(
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ) if skills_root.is_dir() else []
    if not registry.is_file():
        add_finding(
            findings,
            kind="skill_registry_missing",
            severity="high",
            path=display_path(registry, host_root, air_root),
            message="The public skill-family registry is missing.",
        )
        return len(families)

    registered = set(SKILL_FAMILY_RE.findall(read_text(registry)))
    for family in sorted(set(families) - registered):
        add_finding(
            findings,
            kind="skill_family_unregistered",
            severity="medium",
            path=display_path(skills_root / family, host_root, air_root),
            message=f"Skill family directory is not registered: {family}/",
        )
    for family in sorted(registered - set(families)):
        add_finding(
            findings,
            kind="registered_skill_family_missing",
            severity="medium",
            path=display_path(registry, host_root, air_root),
            message=f"Registered skill family has no directory: {family}/",
        )
    for family in families:
        router = skills_root / family / "README.md"
        if not router.is_file():
            add_finding(
                findings,
                kind="skill_family_router_missing",
                severity="medium",
                path=display_path(skills_root / family, host_root, air_root),
                message=f"Skill family has no README router: {family}/",
            )
    return len(families)


def inspect_reachability(
    module_root: Path,
    markdown: dict[Path, str],
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> None:
    owner_roots = ("role", "knowledge", "reviews", "utilities")
    candidates: list[Path] = []
    for name in owner_roots:
        root = module_root / name
        if root.is_dir():
            candidates.extend(
                path
                for path in root.rglob("*.md")
                if path.name not in {"README.md"}
            )

    for target in sorted(candidates):
        relative = target.relative_to(module_root).as_posix()
        needles = {relative, target.name}
        reachable = any(
            source != target and any(needle in text for needle in needles)
            for source, text in markdown.items()
        )
        if not reachable:
            add_finding(
                findings,
                kind="unreachable_file",
                severity="low",
                path=display_path(target, host_root, air_root),
                message="No inbound reference was found in the installed public corpus.",
            )


def inspect_command_ownership(
    start_session: Path,
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> None:
    if not start_session.is_file():
        return
    owners: dict[str, set[str]] = {}
    displays: dict[str, str] = {}
    routes: list[tuple[str, str, tuple[int, int], bool]] = []
    for line_number, line in enumerate(read_text(start_session).splitlines(), start=1):
        owner_match = OWNER_RE.search(line)
        if not owner_match:
            continue
        owner = owner_match.group(1)
        for command_match in COMMAND_RE.finditer(line):
            command = command_match.group(1)
            key = normalize_command(command)
            displays.setdefault(key, command)
            owners.setdefault(key, set()).add(owner)
            routes.append(
                (
                    key,
                    command,
                    (line_number, command_match.start()),
                    command.rstrip().endswith("..."),
                )
            )
    for key, command_owners in sorted(owners.items()):
        if len(command_owners) > 1:
            add_finding(
                findings,
                kind="conflicting_command_route",
                severity="high",
                path=display_path(start_session, host_root, air_root),
                message=(
                    f"Command has conflicting owners: {displays[key]} -> "
                    + ", ".join(sorted(command_owners))
                ),
            )
    precedence_pairs: set[tuple[str, str]] = set()
    for generic_key, generic_display, generic_position, is_prefix_route in routes:
        if not is_prefix_route:
            continue
        for specific_key, specific_display, specific_position, _ in routes:
            pair = (generic_key, specific_key)
            if (
                specific_key.startswith(generic_key + " ")
                and generic_position < specific_position
                and pair not in precedence_pairs
            ):
                precedence_pairs.add(pair)
                add_finding(
                    findings,
                    kind="generic_route_precedes_specific",
                    severity="medium",
                    path=display_path(start_session, host_root, air_root),
                    message=(
                        "Generic command route appears before its specific "
                        f"route: {generic_display} before {specific_display}"
                    ),
                )


def inspect_protected_headings(
    start_session: Path,
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> None:
    if not start_session.is_file():
        return
    count = sum(
        line.rstrip() == PROTECTED_HEADING
        for line in read_text(start_session).splitlines()
    )
    if count != 1:
        add_finding(
            findings,
            kind="duplicate_protected_heading",
            severity="high",
            path=display_path(start_session, host_root, air_root),
            message=(
                f"Protected heading must occur exactly once; found {count}: "
                f"{PROTECTED_HEADING}"
            ),
        )


def inspect_module_index(
    module_root: Path,
    host_root: Path,
    air_root: Path,
    findings: list[dict[str, str]],
) -> None:
    """Require the structural index to enumerate every routed owner document."""
    index_path = module_root / "README.md"
    if not index_path.is_file():
        return
    index_text = read_text(index_path)
    for directory_name in ("role", "knowledge", "reviews", "utilities"):
        directory = module_root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            relative = path.relative_to(module_root).as_posix()
            if relative in index_text:
                continue
            add_finding(
                findings,
                kind="module_index_entry_missing",
                severity="medium" if directory_name == "utilities" else "low",
                path=display_path(path, host_root, air_root),
                message=f"Public module owner is missing from Modules/XUUnity/README.md: {relative}",
            )


def parse_design_rows(text: str) -> tuple[set[str], set[str]]:
    archived_marker = "\n## Archived"
    if archived_marker in text:
        live_text, archived_text = text.split(archived_marker, 1)
    else:
        live_text, archived_text = text, ""
    return set(DESIGN_ROW_RE.findall(live_text)), set(DESIGN_ROW_RE.findall(archived_text))


def inspect_design_registry(
    air_root: Path,
    host_root: Path,
    findings: list[dict[str, str]],
) -> tuple[int, int]:
    design_root = air_root / "Design"
    registry = design_root / "README.md"
    live_files = {
        path.name
        for path in design_root.glob("*.md")
        if path.name != "README.md"
    } if design_root.is_dir() else set()
    archived_root = design_root / "Archived"
    archived_files = {
        path.name
        for path in archived_root.glob("*.md")
        if path.name != "README.md"
    } if archived_root.is_dir() else set()

    if not registry.is_file():
        add_finding(
            findings,
            kind="design_registry_missing",
            severity="medium",
            path=display_path(registry, host_root, air_root),
            message="Public design registry is missing.",
        )
        return len(live_files), len(archived_files)

    live_rows, archived_rows = parse_design_rows(read_text(registry))
    for name in sorted(live_files - live_rows):
        add_finding(
            findings,
            kind="design_file_unregistered",
            severity="medium",
            path=display_path(design_root / name, host_root, air_root),
            message="Live design file has no live registry row.",
        )
    for name in sorted(live_rows - live_files):
        add_finding(
            findings,
            kind="design_registry_target_missing",
            severity="medium",
            path=display_path(registry, host_root, air_root),
            message=f"Live registry row has no design file: {name}",
        )
    for name in sorted(archived_files - archived_rows):
        add_finding(
            findings,
            kind="archived_design_unregistered",
            severity="medium",
            path=display_path(archived_root / name, host_root, air_root),
            message="Archived design file has no archived registry row.",
        )
    for name in sorted(archived_rows - archived_files):
        add_finding(
            findings,
            kind="archived_registry_target_missing",
            severity="medium",
            path=display_path(registry, host_root, air_root),
            message=f"Archived registry row has no archived design file: {name}",
        )
    return len(live_files), len(archived_files)


def run_composed_checks(
    host_root: Path,
    air_root: Path,
) -> list[dict[str, object]]:
    module_scripts = air_root / "Modules" / "XUUnity" / "scripts"
    checks = [
        (
            "routing_audit",
            air_root / "scripts" / "routing_audit.py",
            ["--host-root", str(host_root)],
        ),
        (
            "router_storage_audit",
            air_root / "Operations" / "router_storage_audit.py",
            ["--repo-root", str(host_root)],
        ),
        (
            "entrypoint_kernel",
            module_scripts / "check_entrypoint_kernel.py",
            [str(air_root / "Modules" / "XUUnity" / "tasks" / "start_session.md")],
        ),
        (
            "task_registry",
            module_scripts / "task_registry_tool.py",
            ["validate", "--repo-root", str(host_root)],
        ),
    ]
    results: list[dict[str, object]] = []
    for check_id, script, arguments in checks:
        if not script.is_file():
            results.append(
                {
                    "id": check_id,
                    "status": "not_applicable",
                    "exitCode": None,
                    "summary": "Public owner check is not installed.",
                }
            )
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(script), *arguments],
                cwd=host_root,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            results.append(
                {
                    "id": check_id,
                    "status": "invalid",
                    "exitCode": None,
                    "summary": "Public owner check could not complete.",
                }
            )
            continue
        if completed.returncode == 0:
            status, summary = "pass", "Public owner check passed."
        elif completed.returncode == 1:
            status, summary = "finding", "Public owner check reported findings."
        else:
            status, summary = "invalid", "Public owner check returned an invalid-run status."
        results.append(
            {
                "id": check_id,
                "status": status,
                "exitCode": completed.returncode,
                "summary": summary,
            }
        )
    return results


def finalize_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(
        findings,
        key=lambda finding: (
            SEVERITY_ORDER[finding["severity"]],
            finding["kind"],
            finding["path"],
            finding["message"],
        ),
    )
    finalized = []
    for finding in ordered:
        identity = json.dumps(finding, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        finalized.append({"id": f"SIA-{digest}", **finding})
    return finalized


def audit_installation(
    host_root: Path,
    air_root: Path,
    *,
    forbidden_tokens: Sequence[str] = (),
    forbidden_token_source_id: str | None = None,
    run_composed: bool = True,
) -> dict[str, object]:
    host_root = host_root.resolve()
    air_root = air_root.resolve()
    module_root = air_root / "Modules" / "XUUnity"
    start_session = module_root / "tasks" / "start_session.md"
    findings: list[dict[str, str]] = []
    invalid = False

    if not forbidden_tokens:
        add_finding(
            findings,
            kind="boundary_scan_unarmed",
            severity="medium",
            path=display_path(air_root, host_root, air_root),
            message=(
                "Private-identifier boundary scanning is unarmed; provide the "
                "host denylist or at least one --forbidden-token value."
            ),
        )

    for required, label in (
        (host_root, "host root"),
        (air_root, "public AIRoot"),
        (module_root, "XUUnity module root"),
        (start_session, "start-session entrypoint"),
    ):
        expected = required.is_dir() if label != "start-session entrypoint" else required.is_file()
        if not expected:
            invalid = True
            add_finding(
                findings,
                kind="required_path_missing",
                severity="high",
                path=display_path(required, host_root, air_root),
                message=f"Required {label} is missing.",
            )

    public_files = iter_public_files(air_root) if air_root.is_dir() else []
    module_files = [
        path for path in public_files
        if module_root == path.parent or module_root in path.parents
    ]
    boundary_text: dict[Path, str] = {}
    public_text: dict[Path, str] = {}
    for path in public_files:
        try:
            boundary_text[path] = read_text(path)
        except (OSError, UnicodeError):
            invalid = True
            add_finding(
                findings,
                kind="unreadable_public_file",
                severity="high",
                path=display_path(path, host_root, air_root),
                message="Audited public text file could not be decoded as UTF-8.",
            )
    for path in (
        item
        for item in public_files
        if not is_test_content(item, module_root)
    ):
        if path in boundary_text:
            public_text[path] = boundary_text[path]
    markdown = {
        path: text
        for path, text in public_text.items()
        if path.suffix.lower() == ".md"
    }

    role_root = module_root / "role"
    knowledge_root = module_root / "knowledge"
    review_root = module_root / "reviews"
    utility_root = module_root / "utilities"
    skill_count = 0
    live_designs = 0
    archived_designs = 0

    if module_root.is_dir():
        skill_count = inspect_skill_registry(
            module_root, host_root, air_root, findings
        )
        inspect_reachability(
            module_root, markdown, host_root, air_root, findings
        )
        inspect_module_index(module_root, host_root, air_root, findings)
        inspect_command_ownership(
            start_session, host_root, air_root, findings
        )
        inspect_protected_headings(
            start_session, host_root, air_root, findings
        )
    inspect_markdown_links(markdown, host_root, air_root, findings)
    inspect_private_path_leaks(
        boundary_text, host_root, air_root, forbidden_tokens, findings
    )
    if air_root.is_dir():
        live_designs, archived_designs = inspect_design_registry(
            air_root, host_root, findings
        )

    composed_checks = run_composed_checks(host_root, air_root) if run_composed else []
    for check in composed_checks:
        if check["status"] == "finding":
            add_finding(
                findings,
                kind="composed_check_failed",
                severity="medium",
                path=str(check["id"]),
                message=f"Composed public check reported findings: {check['id']}",
            )
        elif check["status"] == "invalid":
            invalid = True
            add_finding(
                findings,
                kind="composed_check_invalid",
                severity="high",
                path=str(check["id"]),
                message=f"Composed public check could not produce valid evidence: {check['id']}",
            )

    final_findings = finalize_findings(findings)
    if invalid:
        status = "invalid"
    elif final_findings:
        status = "findings"
    else:
        status = "clean"

    count_markdown = lambda root: sum(  # noqa: E731
        1 for path in markdown if root in path.parents
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": status,
        "roots": {
            "hostRoot": ".",
            "airRoot": display_path(air_root, host_root, air_root),
        },
        "publicModuleFingerprint": (
            protocol_fingerprint(module_files, air_root)
            if air_root.is_dir()
            else None
        ),
        "boundaryScan": {
            "armed": bool(forbidden_tokens),
            "sourceId": forbidden_token_source_id or (
                "inline:sha256:"
                + hashlib.sha256(
                    "\0".join(sorted(set(forbidden_tokens))).encode("utf-8")
                ).hexdigest()
                if forbidden_tokens
                else None
            ),
            "tokenCount": len(set(forbidden_tokens)),
        },
        "inventory": {
            "markdown": len(markdown),
            "roles": count_markdown(role_root),
            "skillFamilies": skill_count,
            "knowledge": count_markdown(knowledge_root),
            "reviews": count_markdown(review_root),
            "utilities": count_markdown(utility_root),
            "designsLive": live_designs,
            "designsArchived": archived_designs,
        },
        "composedChecks": composed_checks,
        "findings": final_findings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit one installed XUUnity corpus and emit deterministic JSON."
    )
    parser.add_argument(
        "--host-root",
        default=".",
        help="Host repository root containing AIRoot (default: current directory).",
    )
    parser.add_argument(
        "--air-root",
        help="Public AIRoot path (default: <host-root>/AIRoot when present).",
    )
    parser.add_argument(
        "--skip-composed-checks",
        action="store_true",
        help="Skip existing routing, storage, and entrypoint owner checks.",
    )
    parser.add_argument(
        "--forbidden-token",
        action="append",
        default=[],
        help=(
            "Non-secret private identifier to detect without echoing its "
            "value; repeatable. Never pass credentials."
        ),
    )
    parser.add_argument(
        "--forbidden-token-file",
        help=(
            "Host-private newline-delimited denylist. Defaults to "
            "<host-root>/.xuunity-public-safety-denylist when present."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Atomically replace this file with the JSON evidence. "
            "JSON is still emitted to stdout."
        ),
    )
    return parser


def write_json_atomic(path: Path, rendered: str) -> None:
    """Write evidence via a same-directory temporary file and atomic replace."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def load_forbidden_token_file(path: Path) -> tuple[tuple[str, ...], str]:
    data = path.read_bytes()
    tokens = tuple(
        line.strip()
        for line in data.decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    return tokens, f"sha256:{hashlib.sha256(data).hexdigest()}"


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    host_root = Path(args.host_root).resolve()
    default_air_root = host_root / "AIRoot"
    if args.air_root:
        air_root = Path(args.air_root).resolve()
    elif default_air_root.is_dir():
        air_root = default_air_root
    else:
        air_root = Path(__file__).resolve().parents[3]
    token_file = (
        Path(args.forbidden_token_file).resolve()
        if args.forbidden_token_file
        else host_root / ".xuunity-public-safety-denylist"
    )
    file_tokens: tuple[str, ...] = ()
    token_source_id: str | None = None
    if token_file.is_file():
        try:
            file_tokens, token_source_id = load_forbidden_token_file(token_file)
        except (OSError, UnicodeError):
            print("ERROR: could not read forbidden-token file.", file=sys.stderr)
            return 2
    all_tokens = tuple(dict.fromkeys((*file_tokens, *args.forbidden_token)))
    payload = audit_installation(
        host_root,
        air_root,
        forbidden_tokens=all_tokens,
        forbidden_token_source_id=token_source_id,
        run_composed=not args.skip_composed_checks,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        try:
            write_json_atomic(Path(args.output), rendered)
        except OSError:
            raw_findings = [
                {
                    key: value
                    for key, value in finding.items()
                    if key != "id"
                }
                for finding in payload["findings"]  # type: ignore[union-attr]
            ]
            add_finding(
                raw_findings,
                kind="output_write_failed",
                severity="high",
                path="<output>",
                message="Requested machine-evidence output could not be written.",
            )
            payload["findings"] = finalize_findings(raw_findings)
            payload["status"] = "invalid"
            rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            print("ERROR: could not write audit evidence.", file=sys.stderr)
            sys.stdout.write(rendered)
            return 2
    sys.stdout.write(rendered)
    return {"clean": 0, "findings": 1, "invalid": 2}[str(payload["status"])]


if __name__ == "__main__":
    sys.exit(main())

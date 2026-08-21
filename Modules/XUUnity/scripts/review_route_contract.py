#!/usr/bin/env python3
"""Model-free contract check for XUUnity review routing surfaces.

The review skill owns the mandatory bootstrap and the narrow review map. The
start-session entrypoint owns explicit full-review commands. This checker keeps
those responsibilities aligned without assuming where either file is installed.

Exit code 0 means the contract passes, 1 means routing drift was found, and 2
means an input could not be read.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


EXIT_OK = 0
EXIT_CONTRACT_FAILED = 1
EXIT_USAGE = 2

CODE_REVIEW_OWNER = "tasks/code_review.md"
FULL_REVIEW_OWNER = "reviews/full_review.md"

FULL_REVIEW_ROUTES = {
    "full_review": "xuunity full review",
    "review_all": "xuunity review all",
}
GENERIC_REVIEW_COMMAND = "xuunity review ..."

NARROW_REVIEW_ROUTES = {
    "git": (
        ("git", "diff", "branch", "commit", "pull request", "pr", "staged", "unstaged"),
        "reviews/git_change_review.md",
    ),
    "tests": (("test", "tests"), "reviews/test_quality_review.md"),
    "sdk": (("sdk",), "reviews/sdk_code_review.md"),
    "feature": (
        ("runtime", "product feature", "feature implementation"),
        "reviews/feature_code_review.md",
    ),
    "architecture": (
        ("subsystem", "ownership", "boundary design"),
        "reviews/architecture_review.md",
    ),
    "release": (
        ("rollout", "release confidence"),
        "reviews/release_readiness_review.md",
    ),
    "delivery": (
        ("delivery", "blast-radius"),
        "reviews/delivery_risk_review.md",
    ),
    "native": (
        ("native", "jni", "objective-c", "swift", "java", "kotlin", "manifest", "plist", "bridge"),
        "reviews/native_plugin_review.md",
    ),
}

_BOOTSTRAP_MARKER = re.compile(r"\bread\b.*\bfiles?\b.*\bfully\b", re.IGNORECASE)
_ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(?P<body>.+?)\s*$")
_BACKTICK_PATH = re.compile(r"`(?P<path>[^`\r\n]+\.md)`", re.IGNORECASE)
_BARE_PATH = re.compile(
    r"(?P<path>[A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)*\.md)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Violation:
    rule: str
    source: str
    message: str


@dataclass(frozen=True)
class _BootstrapItem:
    line: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class _Route:
    line: int
    left: str
    paths: tuple[str, ...]


def _markdown_paths(text: str) -> tuple[str, ...]:
    quoted = tuple(match.group("path") for match in _BACKTICK_PATH.finditer(text))
    if quoted:
        return quoted
    return tuple(match.group("path") for match in _BARE_PATH.finditer(text))


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/").casefold().lstrip("./")


def _is_owner(path: str, owner: str, *, allow_basename: bool = False) -> bool:
    candidate = _normalize_path(path)
    expected = _normalize_path(owner)
    basename = expected.rsplit("/", 1)[-1]
    return (
        candidate == expected
        or candidate.endswith("/" + expected)
        or (allow_basename and candidate == basename)
    )


def _extract_bootstrap(text: str) -> tuple[bool, list[_BootstrapItem]]:
    lines = text.splitlines()
    marker_index = next(
        (index for index, line in enumerate(lines) if _BOOTSTRAP_MARKER.search(line)),
        None,
    )
    if marker_index is None:
        return False, []

    items: list[_BootstrapItem] = []
    started = False
    for index in range(marker_index + 1, len(lines)):
        line = lines[index]
        match = _ORDERED_ITEM.match(line)
        if match:
            started = True
            items.append(
                _BootstrapItem(
                    line=index + 1,
                    paths=_markdown_paths(match.group("body")),
                )
            )
            continue
        if not line.strip():
            continue
        if started:
            break
        return True, []
    return True, items


def _extract_routes(text: str) -> list[_Route]:
    routes: list[_Route] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "->" in line:
            left, right = line.split("->", 1)
        elif "→" in line:
            left, right = line.split("→", 1)
        else:
            continue
        routes.append(
            _Route(
                line=line_number,
                left=left.casefold(),
                paths=_markdown_paths(right),
            )
        )
    return routes


def _contains_trigger(text: str, trigger: str) -> bool:
    pattern = r"(?<![a-z0-9_])" + re.escape(trigger.casefold()) + r"(?![a-z0-9_])"
    return re.search(pattern, text) is not None


def _route_resolves(
    route: _Route,
    owner: str,
    *,
    allow_basename: bool = False,
) -> bool:
    return any(
        _is_owner(path, owner, allow_basename=allow_basename)
        for path in route.paths
    )


def check_contract(skill_text: str, start_session_text: str) -> list[Violation]:
    """Return every deterministic review-routing contract violation."""

    violations: list[Violation] = []

    marker_found, bootstrap = _extract_bootstrap(skill_text)
    if not marker_found:
        violations.append(
            Violation(
                "bootstrap_marker_missing",
                "skill",
                "mandatory full-file bootstrap marker is missing",
            )
        )
    elif not bootstrap:
        violations.append(
            Violation(
                "bootstrap_list_missing",
                "skill",
                "mandatory bootstrap has no ordered Markdown list",
            )
        )
    else:
        code_review_positions = [
            index
            for index, item in enumerate(bootstrap)
            if any(_is_owner(path, CODE_REVIEW_OWNER) for path in item.paths)
        ]
        if not code_review_positions:
            violations.append(
                Violation(
                    "bootstrap_code_review_missing",
                    "skill",
                    f"mandatory bootstrap must load {CODE_REVIEW_OWNER}",
                )
            )
        elif code_review_positions[0] != 0:
            violations.append(
                Violation(
                    "bootstrap_code_review_not_first",
                    "skill",
                    f"{CODE_REVIEW_OWNER} must be the first bootstrap owner",
                )
            )

        full_review_lines = [
            item.line
            for item in bootstrap
            if any(
                _is_owner(path, FULL_REVIEW_OWNER, allow_basename=True)
                for path in item.paths
            )
        ]
        if full_review_lines:
            violations.append(
                Violation(
                    "bootstrap_includes_full_review",
                    "skill",
                    f"{FULL_REVIEW_OWNER} is conditional and cannot be in the mandatory bootstrap "
                    f"(line {full_review_lines[0]})",
                )
            )

    skill_routes = _extract_routes(skill_text)
    for label, (triggers, owner) in NARROW_REVIEW_ROUTES.items():
        candidates = [
            route
            for route in skill_routes
            if any(_contains_trigger(route.left, trigger) for trigger in triggers)
        ]
        if not candidates:
            violations.append(
                Violation(
                    f"narrow_{label}_route_missing",
                    "skill",
                    f"narrow {label} review route is missing",
                )
            )
        elif not any(
            _route_resolves(route, owner, allow_basename=True)
            for route in candidates
        ):
            violations.append(
                Violation(
                    f"narrow_{label}_owner_mismatch",
                    "skill",
                    f"narrow {label} review must resolve to {owner}",
                )
            )

    start_routes = _extract_routes(start_session_text)
    generic_candidates = [
        route for route in start_routes if GENERIC_REVIEW_COMMAND in route.left
    ]
    if not generic_candidates:
        violations.append(
            Violation(
                "generic_review_route_missing",
                "start-session",
                f"generic command '{GENERIC_REVIEW_COMMAND}' is not routed",
            )
        )
    elif not any(
        _route_resolves(route, CODE_REVIEW_OWNER)
        for route in generic_candidates
    ):
        violations.append(
            Violation(
                "generic_review_owner_mismatch",
                "start-session",
                f"generic command '{GENERIC_REVIEW_COMMAND}' must resolve to "
                f"{CODE_REVIEW_OWNER}",
            )
        )

    for label, command in FULL_REVIEW_ROUTES.items():
        candidates = [route for route in start_routes if command in route.left]
        if not candidates:
            violations.append(
                Violation(
                    f"explicit_{label}_route_missing",
                    "start-session",
                    f"explicit command '{command}' is not routed",
                )
            )
        elif not any(_route_resolves(route, FULL_REVIEW_OWNER) for route in candidates):
            violations.append(
                Violation(
                    f"explicit_{label}_owner_mismatch",
                    "start-session",
                    f"explicit command '{command}' must resolve to {FULL_REVIEW_OWNER}",
                )
            )

    return violations


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate XUUnity review bootstrap and narrow/full route ownership."
    )
    parser.add_argument("--skill", required=True, help="review skill Markdown path")
    parser.add_argument(
        "--start-session",
        required=True,
        help="start-session Markdown path",
    )
    args = parser.parse_args(argv)

    try:
        skill_text = _read_text(args.skill)
        start_session_text = _read_text(args.start_session)
    except (OSError, UnicodeError) as exc:
        print(f"cannot read review routing input: {exc}", file=sys.stderr)
        return EXIT_USAGE

    violations = check_contract(skill_text, start_session_text)
    if violations:
        print("REVIEW ROUTE CONTRACT: FAIL")
        for violation in violations:
            print(f"  [{violation.rule}] {violation.source}: {violation.message}")
        return EXIT_CONTRACT_FAILED

    print("REVIEW ROUTE CONTRACT: PASS")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

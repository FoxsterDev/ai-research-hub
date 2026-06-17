#!/usr/bin/env python3
"""Pre-patch routing gate checker for XUUnity.

Validates a routing/execution-contract JSON against the shallow-classification
rules in AIRoot/Design/XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md (section 3).
The execution-contract field set and meanings are owned by
knowledge/execution_contract.md; the validation cluster is owned by
knowledge/validation_contract.md. This checker reads those fields and fails a
patch when a runtime-warning family is about to be classified shallowly.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_USAGE = 2

RUNTIME_CONTENT_CHAIN = [
    "symptom",
    "immediate caller",
    "service/wrapper",
    "initialization owner",
    "active config/profile",
    "content/manifest availability",
]

MIN_OWNER_CHAINS = {
    "runtime_content_warning": RUNTIME_CONTENT_CHAIN,
    "popup_runtime_content_warning": RUNTIME_CONTENT_CHAIN,
    "missing_asset_warning": RUNTIME_CONTENT_CHAIN,
    "missing_design_warning": RUNTIME_CONTENT_CHAIN,
    "missing_config_warning": RUNTIME_CONTENT_CHAIN,
}

STARTUP_CONFIG_OVERLAY = "startup/config ownership"
CONFIG_PROFILE_STEP = "active config/profile"


@dataclass
class Violation:
    rule: str
    message: str


def _norm(value: Any) -> str:
    return str(value if value is not None else "").strip().lower().replace("’", "'")


def _norm_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [_norm(v) for v in values]


def _is_empty(value: Any) -> bool:
    return _norm(value) in ("", "none")


def check_contract(contract: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []

    patch_shape = _norm(contract.get("patch_shape"))
    signal = _norm(contract.get("signal"))
    bug_family = _norm(contract.get("bug_family")) or signal
    chain = _norm_list(contract.get("root_cause_chain_checked"))
    overlays = _norm_list(contract.get("overlay_tasks"))
    runtime_warning = bool(contract.get("runtime_warning"))
    remote_content = bool(contract.get("remote_content"))
    runtime_ui_validation_required = bool(contract.get("runtime_ui_validation_required"))
    why_not_local_fix = contract.get("why_not_local_fix")
    private_capability_check = contract.get("private_capability_check")
    validation_gaps = contract.get("validation_gaps")

    is_runtime_content = bug_family in MIN_OWNER_CHAINS
    popup_or_runtime_content = (
        runtime_warning
        or is_runtime_content
        or "popup" in signal
        or "runtime-content" in signal
        or "runtime_content" in signal
    )
    if "upstream_ownership_involved" in contract:
        upstream_involved = bool(contract.get("upstream_ownership_involved"))
    else:
        upstream_involved = is_runtime_content or patch_shape not in ("", "local_fix")
    config_inspected = CONFIG_PROFILE_STEP in chain

    # Rule 1 (design §3): runtime warning classified local_fix without config/profile inspection.
    if runtime_warning and patch_shape == "local_fix" and not config_inspected:
        violations.append(
            Violation(
                "local_fix_without_config_inspection",
                "runtime warning classified as local_fix without active config/profile inspection "
                "in root_cause_chain_checked",
            )
        )
    # Rule 2 (design §3): popup/runtime-content + remote content without startup/config overlay routing.
    if popup_or_runtime_content and remote_content and STARTUP_CONFIG_OVERLAY not in overlays:
        violations.append(
            Violation(
                "missing_startup_config_overlay",
                "popup/runtime-content warning with remote content did not load "
                "'startup/config ownership' overlay routing",
            )
        )
    # Rule 3 (design §3): runtime UI validation required but neither a capability check nor a gap recorded.
    if runtime_ui_validation_required and _is_empty(private_capability_check) and _is_empty(validation_gaps):
        violations.append(
            Violation(
                "runtime_ui_validation_unaccounted",
                "runtime UI validation required but neither a private capability check nor an explicit "
                "validation gap is recorded",
            )
        )
    # Rule 4 (design §3): empty why_not_local_fix while upstream ownership is involved.
    if upstream_involved and _is_empty(why_not_local_fix):
        violations.append(
            Violation(
                "empty_why_not_local_fix",
                "why_not_local_fix is empty while upstream ownership is involved",
            )
        )
    # Rule 5 (design §3): root_cause_chain_checked missing the minimum owner chain for the bug family.
    required_chain = MIN_OWNER_CHAINS.get(bug_family)
    if required_chain:
        missing = [step for step in required_chain if step not in chain]
        if missing:
            violations.append(
                Violation(
                    "incomplete_root_cause_chain",
                    f"root_cause_chain_checked is missing required owner-chain steps for "
                    f"'{bug_family}': {missing}",
                )
            )
    return violations


def _load_contract(args: argparse.Namespace) -> Any:
    raw = Path(args.contract).read_text(encoding="utf-8") if args.contract else sys.stdin.read()
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XUUnity pre-patch routing gate checker.")
    parser.add_argument("--contract", help="path to a routing-contract JSON file; omit to read stdin")
    parser.add_argument("--json", action="store_true", help="emit a JSON result instead of text")
    args = parser.parse_args(argv)

    try:
        contract = _load_contract(args)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read routing contract: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(contract, dict):
        print("routing contract must be a JSON object", file=sys.stderr)
        return EXIT_USAGE

    violations = check_contract(contract)
    if args.json:
        print(
            json.dumps(
                {
                    "pass": not violations,
                    "violations": [{"rule": v.rule, "message": v.message} for v in violations],
                },
                indent=2,
            )
        )
    elif violations:
        print("ROUTING GATE: FAIL")
        for v in violations:
            print(f"  [{v.rule}] {v.message}")
    else:
        print("ROUTING GATE: PASS")
    return EXIT_OK if not violations else EXIT_GATE_FAILED


if __name__ == "__main__":
    raise SystemExit(main())

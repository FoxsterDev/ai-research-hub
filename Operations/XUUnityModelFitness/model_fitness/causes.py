"""Versioned, conservative cause ownership for independently observed failures."""

from pathlib import Path
from typing import Any, Iterable

import xuunity_canonical as xc

CLASSIFIER_ID = "xuunity.execution-cause.v1"


def classify(meta: dict[str, Any], reasons: Iterable[str], *, evaluator_error: bool = False) -> dict[str, Any]:
    reasons = set(reasons)
    owners = set()
    if evaluator_error:
        owners.add("measurement_system")
    if reasons & {"provider_api_error", "terminal_result_error", "subscription_login_unproven"}:
        owners.add("environment")
    # A wall timeout alone cannot distinguish a stalled provider from a model
    # loop. Do not attribute an unobserved cause to model fitness.
    if meta.get("timed_out") or meta.get("output_limited"):
        owners.add("unattributed")
    if meta.get("interrupted"):
        owners.add("environment")
    if meta.get("launch_error"):
        owners.add("environment")
    if not owners and any(reason.endswith(("_unavailable", "_unobserved", "_unenforced")) for reason in reasons):
        owners.add("environment")
    if not owners and meta.get("status") not in {None, "completed"}:
        owners.add("unattributed")
    owner = next(iter(owners)) if len(owners) == 1 else "unattributed" if owners else None
    return {
        "owner": owner, "contributors": sorted(owners), "reason_codes": sorted(reasons),
        "classifier_id": CLASSIFIER_ID, "classifier_sha256": xc.sha256_file(Path(__file__)),
    }


def result_cause(classification: dict[str, Any]) -> dict[str, Any] | None:
    if classification["owner"] is None:
        return None
    return {key: classification[key] for key in ("owner", "classifier_id", "classifier_sha256")} | {
        "evidence_ref": "cause.json"
    }

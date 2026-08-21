"""F8 semantic oracle for evidence-based review proportionality.

The fixture is a review task, not an implementation task. The branch contains
visible synchronization around Unity player-loop callbacks, duplicated project
capabilities, forwarding wrappers, and feature orchestration spread through a
root presenter. It also contains one real temporal invariant: a stale refresh
must not overwrite the result of a collect operation.

Authored by hand, independently of the review router and scoring documents under
test. Structured output keeps the oracle focused on review decisions instead of
formatting tricks and rejects both tempting extremes: praising every gate as
thread safety and deleting every guard without a behavior-preserving replacement.
"""

import json
import re
from pathlib import Path

TARGET = "review_result/result.json"
SCHEMA_VERSION = "xuunity.f8-review.v1"
ADAPTER_SOURCE = "Project/App/src/UnityReferralAdapter.cs"
MAIN_LOOP_INGRESS = "unity_player_loop"
WORKER_INGRESS = "documented_worker_thread"
NO_BOUNDARY_NORMALIZATION = "none_required"
WORKER_BOUNDARY_GATE = "_pendingReferralGate"
EXPECTED_WEIGHTS = {
    "correctness": 20,
    "architecture_and_ownership": 15,
    "safety": 15,
    "security": 15,
    "validation": 15,
    "observability": 10,
    "simplicity_project_fit_maintainability": 10,
}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _all_text(document):
    return " ".join(_strings(document)).lower()


def _number(mapping, key):
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _score_assessment(document):
    review_scores = document.get("review_scores")
    if not isinstance(review_scores, dict):
        return ["review_scores_missing"]
    weights = review_scores.get("weights")
    dimensions = review_scores.get("dimensions")
    if not isinstance(weights, dict) or weights != EXPECTED_WEIGHTS:
        return ["review_score_weights_invalid"]
    if not isinstance(dimensions, dict):
        return ["review_score_dimensions_missing"]

    reasons = []
    values = {key: _number(dimensions, key) for key in EXPECTED_WEIGHTS}
    if any(value is None or value < 0 or value > 100 for value in values.values()):
        reasons.append("review_score_dimensions_invalid")
    else:
        weighted = sum(
            EXPECTED_WEIGHTS[key] * values[key] for key in EXPECTED_WEIGHTS
        ) / 100.0
        overall = _number(review_scores, "overall")
        if overall is None or abs(overall - weighted) > 0.01:
            reasons.append("overall_score_inconsistent")

    architecture = values["architecture_and_ownership"]
    simplicity = values["simplicity_project_fit_maintainability"]
    if architecture is None or architecture > 59:
        reasons.append("architecture_dimension_cap_exceeded")
    if simplicity is None or simplicity > 49:
        reasons.append("simplicity_dimension_cap_exceeded")
    if review_scores.get("overall_cap_applied") is not False:
        reasons.append("arbitrary_overall_cap_applied")
    if review_scores.get("overall_cap_reason") is not None:
        reasons.append("arbitrary_overall_cap_reason_present")
    if str(review_scores.get("confidence") or "").lower() != "low":
        reasons.append("scoring_confidence_overclaimed")
    return reasons


def _string_list(value, *, allow_empty=False):
    if not isinstance(value, list):
        return None
    if not allow_empty and not value:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    return value


def _source_ingress(tree):
    path = Path(tree) / ADAPTER_SOURCE
    try:
        source = path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeError):
        return "unknown"

    worker_markers = (
        "worker thread",
        "onreferralreceivedfromworkerthread",
        "trydrainonunityplayerloop",
        "_pendingreferralgate",
        "lock (",
    )
    if all(marker in source for marker in worker_markers):
        return WORKER_INGRESS

    main_loop_markers = (
        "unitysendmessage",
        "unity player loop",
        "onreferralreceived",
    )
    if all(marker in source for marker in main_loop_markers):
        return MAIN_LOOP_INGRESS
    return "unknown"


def _rejects_callback_inference(evidence):
    return bool(
        re.search(
            r"callbacks?.{0,55}(?:is|are|do|does)?\s*(?:not|no).{0,35}"
            r"(?:evidence|proof).{0,55}(?:cross[- ]thread|multithread|worker thread)",
            evidence,
        )
    )


def _concurrency_assessment(document, tree):
    concurrency = document.get("concurrency")
    if not isinstance(concurrency, dict):
        return ["concurrency_assessment_missing"]

    classification = concurrency.get("classification")
    ingress = concurrency.get("ingress")
    evidence = str(concurrency.get("evidence") or "").lower()
    normalization = concurrency.get("boundary_normalization")
    readers = _string_list(concurrency.get("readers"))
    writers = _string_list(concurrency.get("writers"))
    justified = _string_list(
        concurrency.get("justified_synchronization"), allow_empty=True
    )
    if (
        not isinstance(classification, str)
        or not isinstance(ingress, str)
        or not evidence
        or not isinstance(normalization, str)
        or readers is None
        or writers is None
        or justified is None
    ):
        return ["concurrency_assessment_schema_invalid"]

    reasons = []
    if not _rejects_callback_inference(evidence):
        reasons.append("callback_thread_evidence_rule_missing")

    source_ingress = _source_ingress(tree)
    if source_ingress == MAIN_LOOP_INGRESS:
        if classification not in {
            "main_thread_confined",
            "temporal_reentrancy",
        } or ingress != MAIN_LOOP_INGRESS:
            reasons.append("callback_thread_evidence_rule_missing")
        if normalization != NO_BOUNDARY_NORMALIZATION or justified:
            reasons.append("main_loop_boundary_overengineered")
        return reasons

    if source_ingress == WORKER_INGRESS:
        if classification != "cross_thread_shared" or ingress != WORKER_INGRESS:
            reasons.append("documented_worker_thread_classification_missing")
        reader_text = " ".join(readers).lower()
        writer_text = " ".join(writers).lower()
        if (
            "trydrainonunityplayerloop" not in reader_text
            or "onreferralreceivedfromworkerthread" not in writer_text
        ):
            reasons.append("worker_reader_writer_evidence_missing")
        normalization_text = normalization.lower()
        if not (
            "adapter" in normalization_text
            and "unity player loop" in normalization_text
            and "outside the lock" in normalization_text
        ):
            reasons.append("worker_boundary_normalization_missing")
        if justified != [WORKER_BOUNDARY_GATE]:
            reasons.append("worker_boundary_synchronization_missing")
        if not (
            re.search(r"\b(?:explicit|documented).{0,45}worker[- ]thread", evidence)
            and "_pendingreferralgate" in evidence
        ):
            reasons.append("worker_thread_source_evidence_missing")
        return reasons

    return ["callback_ingress_source_ambiguous"]


def _has_unsupported_sync_finding(text):
    mechanism = re.search(
        r"\b(?:lock|interlocked|volatile|semaphore(?:slim)?)\b", text
    )
    unsupported = re.search(
        r"\b(?:unsupported|unproven|speculative|redundant|duplicated)\b"
        r".{0,90}\b(?:synchroni[sz]ation|atomic|guard|gate|lock|semaphore)\b",
        text,
    ) or re.search(
        r"\b(?:synchroni[sz]ation|atomic|guard|gate|lock|semaphore)\b"
        r".{0,90}\b(?:unsupported|unproven|speculative|redundant|duplicated)\b",
        text,
    )
    return bool(mechanism and unsupported)


def _has_ownership_finding(text):
    return bool(
        re.search(
            r"(?:ownership\s+(?:is\s+)?(?:spread|split|scattered)|"
            r"root presenter.{0,110}feature orchestration|"
            r"feature orchestration.{0,110}root presenter)",
            text,
        )
    )


def _has_project_capability_search(text):
    return bool(
        re.search(
            r"(?:existing|project[- ]native|project)\s+(?:project\s+)?"
            r"(?:capabilit|primitive|infrastructure|result[- ]flow|event binding)",
            text,
        )
        or re.search(
            r"(?:result[- ]flow|event binding|shared execution).{0,100}"
            r"(?:reuse|inspect|existing|project)",
            text,
        )
    )


def _has_concrete_nonlocal_risk(text):
    return bool(
        re.search(
            r"concrete.{0,40}non[- ]local.{0,80}"
            r"(?:lifecycle|ordering|correctness|presentation).{0,35}risk",
            text,
        )
        or re.search(
            r"non[- ]local.{0,80}(?:lifecycle|ordering|correctness|presentation)"
            r".{0,35}risk",
            text,
        )
    )


def _has_branch_evidence_provenance(document):
    provenance = document.get("evidence_provenance")
    if not isinstance(provenance, dict):
        return False
    candidate = str(provenance.get("branch_candidate") or "").lower()
    authority = str(provenance.get("independent_authority") or "").lower()
    comparison = str(provenance.get("comparison_base") or "").lower()
    return (
        "candidate" in candidate
        and authority == "none"
        and ("release" in comparison or "baseline" in comparison)
    )


def _preserves_real_temporal_invariant(document):
    invariants = document.get("preserved_invariants")
    if not isinstance(invariants, list):
        return False
    for invariant in invariants:
        if not isinstance(invariant, dict):
            continue
        name = str(invariant.get("name") or "").lower()
        strategy = str(invariant.get("strategy") or "").lower()
        names_stale_ordering = (
            "collect" in name and "refresh" in name and "stale" in name
        )
        preserves = bool(
            re.search(r"\b(?:preserve|retain|keep)\b", strategy)
            and re.search(
                r"\b(?:ordering|precedence|invariant|generation|queue|state)\b",
                strategy,
            )
        )
        if names_stale_ordering and preserves:
            return True
    return False


def _has_ordered_cleanup_plan(document):
    commits = document.get("cleanup_commits")
    if not isinstance(commits, list) or len(commits) < 3:
        return False
    orders = [item.get("order") for item in commits if isinstance(item, dict)]
    titles = [item.get("title") for item in commits if isinstance(item, dict)]
    return orders == list(range(1, len(commits) + 1)) and all(
        isinstance(title, str) and title.strip() for title in titles
    )


def evaluate(tree):
    path = Path(tree) / TARGET
    if not path.is_file():
        return {
            "status": "failed",
            "reason_codes": ["review_artifact_missing"],
            "score_fraction": 0.0,
        }
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "status": "failed",
            "reason_codes": ["review_artifact_invalid_json"],
            "score_fraction": 0.0,
        }
    if not isinstance(document, dict):
        return {
            "status": "failed",
            "reason_codes": ["review_artifact_wrong_shape"],
            "score_fraction": 0.0,
        }

    reasons = []
    if document.get("schema_version") != SCHEMA_VERSION:
        reasons.append("review_schema_version_missing")

    if document.get("source_changes_made") is not False:
        reasons.append("source_changed_in_read_only_review")
    reasons.extend(_score_assessment(document))

    text = _all_text(document)
    reasons.extend(_concurrency_assessment(document, tree))
    if not _has_unsupported_sync_finding(text):
        reasons.append("unsupported_synchronization_not_identified")
    if not _has_ownership_finding(text):
        reasons.append("ownership_spread_not_identified")
    if not _has_project_capability_search(text):
        reasons.append("project_capability_search_missing")
    if not _has_concrete_nonlocal_risk(text):
        reasons.append("concrete_nonlocal_risk_not_identified")
    if not _has_branch_evidence_provenance(document):
        reasons.append("branch_memory_used_as_authority")
    if not _preserves_real_temporal_invariant(document):
        reasons.append("real_temporal_invariant_not_preserved")
    if not _has_ordered_cleanup_plan(document):
        reasons.append("ordered_cleanup_plan_missing")

    if reasons:
        return {
            "status": "failed",
            "reason_codes": sorted(set(reasons)),
            "score_fraction": 0.0,
        }
    return {"status": "passed", "reason_codes": [], "score_fraction": 1.0}

#!/usr/bin/env python3
"""Public observation-state contract for XUUnity stack-delivery measurement.

Single owner of the per-artifact observation taxonomy defined by
``AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md``
(Contract 4). Observers, gates, and scorers compose these helpers instead of
re-implementing the state rules.

Core invariants enforced here:

- only ``proven_delivered`` and ``trusted_runtime_delivered`` satisfy an
  operational delivery obligation;
- unsupported evidence is an explicit state, never converted to absence;
- an unsatisfied required artifact with unsupported or runtime-unverified
  evidence makes the observer axis ``observer_unsupported`` (score null),
  never an unsatisfied ``0%`` leaf attributed to the model;
- a requested-versus-observed profile mismatch is ``observer_invalid``;
- an unobservable model identity downgrades comparison, not validity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Iterable

SCHEMA_OBSERVATION_LEDGER = "xuunity.observation-ledger.v1"
SCHEMA_STACK_GATE_RESULT = "xuunity.stack-gate-result.v1"

OBSERVATION_STATES = (
    "proven_delivered",
    "trusted_runtime_delivered",
    "runtime_delivered_unverified",
    "partial_read",
    "failed_read",
    "unsupported_observation",
    "not_observed",
)

DELIVERY_SATISFYING_STATES = frozenset(
    {"proven_delivered", "trusted_runtime_delivered"}
)

_DIRECT_EVIDENCE_PRECEDENCE = (
    "proven_delivered",
    "trusted_runtime_delivered",
    "partial_read",
    "failed_read",
    "not_observed",
)

PARSER_RESULTS = ("recognized", "unsupported", "ambiguous")

OBSERVER_AXIS_VALUES = ("valid", "observer_unsupported", "observer_invalid")

MUTATION_CUTOFF_CONFIDENCE = (
    "unambiguous",
    "ambiguous_prior_commands",
    "no_mutation_observed",
)

GATE_DECISIONS = ("pass", "fail", "reopen_required", "invalid", "not_runnable")

ENFORCEMENT_MODES = ("authoritative", "audited")

GROUP_MODES = ("all_of", "any_of", "at_least")

# Context the CLI surface injects into the request without a transcript event.
# Matching is by exact repo-relative path or by basename case alias, because
# case-insensitive filesystems let the surface resolve e.g. ``Agents.md`` for
# a canonical ``AGENTS.md`` lookup.
RUNTIME_CONTEXT_CHANNELS: dict[str, tuple[str, ...]] = {
    "claude_cli": ("CLAUDE.md", "CLAUDE.local.md"),
    "codex_cli": ("AGENTS.md",),
}


def state_satisfies_delivery(state: str) -> bool:
    if state not in OBSERVATION_STATES:
        raise ValueError(f"unknown observation state: {state}")
    return state in DELIVERY_SATISFYING_STATES


@dataclass(frozen=True)
class ArtifactResolution:
    state: str
    direct_state: str
    unsupported_present: bool
    runtime_unverified_present: bool
    case_alias: bool = False

    @property
    def satisfied(self) -> bool:
        return self.state in DELIVERY_SATISFYING_STATES

    @property
    def blocks_observer(self) -> bool:
        return not self.satisfied and (
            self.unsupported_present or self.runtime_unverified_present
        )


def resolve_artifact_state(
    direct_states: Iterable[str],
    *,
    unsupported_present: bool = False,
    runtime_unverified_present: bool = False,
    case_alias: bool = False,
) -> ArtifactResolution:
    """Resolve one required artifact's final observation state.

    ``direct_states`` are states from independently verified operations
    (reads, trusted manifests). Epistemic evidence (unsupported operations,
    unverifiable runtime channels) is carried separately so it can never be
    laundered into a definite negative.
    """
    observed = set(direct_states)
    unknown = observed.difference(OBSERVATION_STATES)
    if unknown:
        raise ValueError(f"unknown observation states: {sorted(unknown)}")
    epistemic = {"runtime_delivered_unverified", "unsupported_observation"}
    if observed & epistemic:
        raise ValueError(
            "epistemic states must be passed as flags, not direct evidence"
        )
    direct = "not_observed"
    for state in _DIRECT_EVIDENCE_PRECEDENCE:
        if state in observed:
            direct = state
            break
    state = direct
    if direct not in DELIVERY_SATISFYING_STATES:
        if runtime_unverified_present:
            state = "runtime_delivered_unverified"
        elif unsupported_present:
            state = "unsupported_observation"
    return ArtifactResolution(
        state=state,
        direct_state=direct,
        unsupported_present=unsupported_present,
        runtime_unverified_present=runtime_unverified_present,
        case_alias=case_alias,
    )


def observer_axis(
    *,
    profile_mismatch: bool,
    boundary_ambiguous: bool,
    artifact_resolutions: Iterable[ArtifactResolution] = (),
    unpaired_or_unknown_critical_events: bool = False,
) -> str:
    if profile_mismatch:
        return "observer_invalid"
    if boundary_ambiguous or unpaired_or_unknown_critical_events:
        return "observer_unsupported"
    if any(row.blocks_observer for row in artifact_resolutions):
        return "observer_unsupported"
    return "valid"


@dataclass(frozen=True)
class GroupPolicy:
    group_id: str
    mode: str
    weight: float
    members: tuple[str, ...] = ()
    min_count: int = 0
    glob: str | None = None
    matched_paths: tuple[str, ...] = field(default=(), compare=False)


def group_satisfaction(
    policy: GroupPolicy, satisfied_paths: frozenset[str] | set[str]
) -> tuple[bool, float]:
    """Return (satisfied, earned fraction of the group's weight).

    The fraction keeps per-leaf coverage visible even when an ``all_of``
    group fails: 3 of 4 proven leaves earn 0.75 of the weight fraction for
    delivery-percent reporting while the group itself stays unsatisfied.
    """
    if policy.mode not in GROUP_MODES:
        raise ValueError(f"unknown group mode: {policy.mode}")
    if policy.mode == "any_of":
        hit = any(path in satisfied_paths for path in policy.members)
        return hit, 1.0 if hit else 0.0
    if policy.mode == "all_of":
        if not policy.members:
            raise ValueError(f"group {policy.group_id}: empty all_of")
        hits = sum(1 for path in policy.members if path in satisfied_paths)
        return hits == len(policy.members), hits / len(policy.members)
    if policy.min_count <= 0:
        raise ValueError(f"group {policy.group_id}: at_least needs min_count")
    hits = sum(1 for path in policy.matched_paths if path in satisfied_paths)
    return hits >= policy.min_count, min(1.0, hits / policy.min_count)


def delivery_percent(
    rows: Iterable[tuple[GroupPolicy, float]],
) -> float:
    total = 0.0
    earned = 0.0
    for policy, fraction in rows:
        total += policy.weight
        earned += policy.weight * fraction
    if total <= 0:
        return 100.0
    return round(100.0 * earned / total, 1)


def runtime_context_match(surface: str, path: str) -> tuple[bool, bool]:
    """Return (is_runtime_channel, is_case_alias) for a repo-relative path."""
    channels = RUNTIME_CONTEXT_CHANNELS.get(surface, ())
    name = PurePosixPath(path).name
    for channel in channels:
        if name == channel:
            return True, False
        if name.lower() == channel.lower():
            return True, True
    return False, False


def profile_identity_check(
    requested_model: str | None, observed_model: str | None
) -> dict[str, Any]:
    """Classify requested-versus-observed model identity.

    A present mismatch is observer-invalid. A missing observed identity is
    not invalid, but the run cannot participate in exact-repeat or controlled
    cross-model comparison.
    """
    if requested_model and observed_model:
        if requested_model == observed_model:
            return {
                "requested": requested_model,
                "observed": observed_model,
                "mismatch": False,
                "comparison_status": "exact_identity",
            }
        return {
            "requested": requested_model,
            "observed": observed_model,
            "mismatch": True,
            "comparison_status": "invalid",
        }
    return {
        "requested": requested_model,
        "observed": observed_model,
        "mismatch": False,
        "comparison_status": "matched_content_noncontrolled",
    }


def gate_result_semantic_errors(document: dict[str, Any]) -> list[str]:
    """Cross-field MUST rules that a JSON grammar alone cannot express."""
    errors: list[str] = []
    mode = document.get("enforcement_mode")
    authorization = document.get("authorization")
    decision = document.get("decision")
    if mode == "audited" and authorization is not None:
        errors.append("audited result must use authorization: null")
    if mode == "authoritative" and authorization is None:
        errors.append("authoritative result requires an authorization")
    if decision == "pass":
        for row in document.get("group_results") or []:
            if not row.get("gate_satisfied"):
                errors.append(
                    f"pass decision with unsatisfied group "
                    f"{row.get('group_id')}"
                )
            for member in row.get("members") or []:
                state = member.get("state")
                if state not in OBSERVATION_STATES:
                    errors.append(f"unknown member state {state}")
                elif not state_satisfies_delivery(state) and row.get(
                    "gate_satisfied"
                ) and row.get("mode") == "all_of":
                    errors.append(
                        "all_of group marked satisfied with member state "
                        f"{state} for {member.get('path')}"
                    )
    if (
        document.get("mutation_cutoff_confidence")
        == "ambiguous_prior_commands"
        and decision == "pass"
    ):
        errors.append("ambiguous mutation boundary cannot pass the gate")
    return errors

"""Public fixture corpus kit (design P3).

Loads, verifies, and evaluates the public synthetic fixture corpus and
any host-local fixture that follows the same layout. Everything here is
fail-closed: implementation hashes must match the fixture declaration
(an edited oracle is an attack, not a refresh), seed identity must match
the declared content hash, and authored known-bad/known-good controls
must classify exactly as declared.

Semantic oracles run over a fresh hermetic materialization of the final
tree, never the working copy. Expected stack derivations and oracle
outcomes are authored by hand in the fixture directory — independently
of the resolver and scorer under test.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

import observation_contract as oc
import xuunity_canonical as xc

from . import OPERATION_DIR, adapters, isolation, scoring
from .contracts import fractional_document_hash, require_valid

FIXTURES_DIR = OPERATION_DIR / "fixtures"

SURFACE_DELIVERY_MODES = ("complete", "partial", "none", "attested_bundle")


class FixtureError(ValueError):
    pass


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FixtureError(f"missing fixture file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FixtureError(f"invalid JSON in {path}: {error}") from error


def implementation_map(fixture_dir: Path) -> dict[str, str]:
    mapping = _read_json(Path(fixture_dir) / "implementations.json")
    if not isinstance(mapping, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in mapping.items()
    ):
        raise FixtureError(
            f"implementations.json must map ids to relative paths: "
            f"{fixture_dir}"
        )
    return mapping


def _declared_implementations(fixture: dict[str, Any]) -> dict[str, str]:
    declared: dict[str, str] = {}

    def add(impl_id: str, sha: str) -> None:
        if impl_id in declared and declared[impl_id] != sha:
            raise FixtureError(
                f"conflicting hashes declared for implementation {impl_id}"
            )
        declared[impl_id] = sha

    oracle = fixture["expected_obligation_oracle"]
    add(oracle["id"], oracle["implementation_sha256"])
    for row in fixture["semantic_oracles"]:
        add(row["id"], row["implementation_sha256"])
    for row in fixture["safety_validators"]:
        add(row["id"], row["implementation_sha256"])
    return declared


def _implementation_path(
    fixture_dir: Path, mapping: dict[str, str], impl_id: str
) -> Path:
    relative = mapping.get(impl_id)
    if relative is None:
        raise FixtureError(
            f"implementation not mapped in implementations.json: {impl_id}"
        )
    path = (Path(fixture_dir) / relative).resolve()
    if Path(fixture_dir).resolve() not in path.parents:
        raise FixtureError(
            f"implementation escapes the fixture directory: {relative}"
        )
    if not path.is_file():
        raise FixtureError(f"implementation file missing: {path}")
    return path


def load_fixture(fixture_dir: Path) -> dict[str, Any]:
    fixture = _read_json(Path(fixture_dir) / "fixture.json")
    scoring.validate_fixture(fixture)
    return fixture


def fixture_document_hash(fixture: dict[str, Any]) -> str:
    return fractional_document_hash(fixture, "fixture_hash")


def verify_fixture(
    fixture_dir: Path, *, require_local_payloads: bool = True
) -> dict[str, Any]:
    """Load a fixture and prove every declared identity fail-closed."""
    fixture_dir = Path(fixture_dir)
    fixture = load_fixture(fixture_dir)
    declared_hash = fixture.get("fixture_hash")
    if not declared_hash:
        raise FixtureError(f"fixture_hash missing: {fixture_dir}")
    computed = fixture_document_hash(fixture)
    if computed != declared_hash:
        raise FixtureError(
            f"fixture_hash mismatch for {fixture['fixture_id']}: "
            f"declared {declared_hash}, computed {computed}"
        )

    mapping = implementation_map(fixture_dir)
    declared = _declared_implementations(fixture)
    unknown = sorted(set(mapping) - set(declared))
    if unknown:
        raise FixtureError(
            f"implementations.json maps undeclared ids: {unknown}"
        )
    for impl_id, declared_sha in sorted(declared.items()):
        if impl_id not in mapping:
            if require_local_payloads:
                raise FixtureError(
                    f"implementation not available locally: {impl_id}"
                )
            continue
        path = _implementation_path(fixture_dir, mapping, impl_id)
        actual = xc.sha256_file(path)
        if actual != declared_sha:
            raise FixtureError(
                f"implementation hash mismatch for {impl_id}: "
                f"declared {declared_sha}, actual {actual}"
            )

    task_path = fixture_dir / fixture["task"]["ref"]
    if task_path.is_file():
        actual = xc.sha256_file(task_path)
        if actual != fixture["task"]["sha256"]:
            raise FixtureError(
                f"task payload hash mismatch: declared "
                f"{fixture['task']['sha256']}, actual {actual}"
            )
    elif require_local_payloads:
        raise FixtureError(f"task payload missing: {task_path}")

    seed_dir = fixture_dir / str(fixture["seed"]["ref"] or "")
    if fixture["seed"]["ref"] and seed_dir.is_dir():
        from .baseline import content_identity

        actual = content_identity(seed_dir)
        if actual != fixture["seed"]["content_hash"]:
            raise FixtureError(
                f"seed content hash mismatch: declared "
                f"{fixture['seed']['content_hash']}, actual {actual}"
            )
    elif require_local_payloads:
        raise FixtureError(f"seed tree missing: {seed_dir}")
    return fixture


def refresh_fixture(fixture_dir: Path) -> dict[str, Any]:
    """Authoring helper: recompute every declared hash from the local
    payloads and rewrite fixture.json, then verify the result."""
    fixture_dir = Path(fixture_dir)
    fixture = _read_json(fixture_dir / "fixture.json")
    mapping = implementation_map(fixture_dir)

    def sha_for(impl_id: str) -> str:
        return xc.sha256_file(
            _implementation_path(fixture_dir, mapping, impl_id)
        )

    oracle = fixture["expected_obligation_oracle"]
    oracle["implementation_sha256"] = sha_for(oracle["id"])
    for row in fixture["semantic_oracles"]:
        row["implementation_sha256"] = sha_for(row["id"])
    for row in fixture["safety_validators"]:
        row["implementation_sha256"] = sha_for(row["id"])

    task_path = fixture_dir / fixture["task"]["ref"]
    if task_path.is_file():
        fixture["task"]["sha256"] = xc.sha256_file(task_path)
    seed_dir = fixture_dir / str(fixture["seed"]["ref"] or "")
    if fixture["seed"]["ref"] and seed_dir.is_dir():
        from .baseline import content_identity

        fixture["seed"]["content_hash"] = content_identity(seed_dir)
    fixture["fixture_hash"] = fixture_document_hash(fixture)
    (fixture_dir / "fixture.json").write_text(
        json.dumps(fixture, indent=2) + "\n", encoding="utf-8"
    )
    return verify_fixture(fixture_dir)


def _load_module(path: Path, expected_sha256: str) -> Any:
    actual = xc.sha256_file(path)
    if actual != expected_sha256:
        raise FixtureError(
            f"refusing to execute a tampered implementation: {path} "
            f"(declared {expected_sha256}, actual {actual})"
        )
    name = f"xuunity_fixture_impl_{actual[:16]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FixtureError(f"cannot load implementation module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_semantic_oracle(
    fixture_dir: Path,
    fixture: dict[str, Any],
    oracle_id: str,
    tree: Path,
    *,
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Evaluate one declared semantic oracle over a fresh hermetic
    materialization of ``tree``. In-process ``task``/``static`` oracles
    receive only the materialized copy; oracles that shell out compose
    ``isolation.run_hermetic_oracle`` themselves."""
    declared = {row["id"]: row for row in fixture["semantic_oracles"]}
    if oracle_id not in declared:
        raise FixtureError(f"oracle not declared by fixture: {oracle_id}")
    row = declared[oracle_id]
    mapping = implementation_map(fixture_dir)
    path = _implementation_path(fixture_dir, mapping, oracle_id)
    module = _load_module(path, row["implementation_sha256"])
    if not callable(getattr(module, "evaluate", None)):
        raise FixtureError(f"oracle exposes no evaluate(tree): {path}")

    def finish(destination: Path) -> dict[str, Any]:
        identity = isolation.hermetic_materialize(tree, destination)
        raw = module.evaluate(destination)
        if not isinstance(raw, dict) or raw.get("status") not in {
            "passed",
            "failed",
            "not_evaluable",
        }:
            raise FixtureError(
                f"oracle {oracle_id} returned no passed/failed/"
                f"not_evaluable status"
            )
        result: dict[str, Any] = {
            "schema_version": "xuunity.oracle-result.v1",
            "fixture_id": fixture["fixture_id"],
            "oracle_id": oracle_id,
            "kind": row["kind"],
            "implementation_sha256": row["implementation_sha256"],
            "tree_identity": identity,
            "status": raw["status"],
            "reason_codes": sorted(raw.get("reason_codes") or []),
            "score_fraction": raw.get("score_fraction"),
        }
        scope = raw.get("declared_scope")
        if scope is None and (
            getattr(module, "PRODUCERS", None) is not None
            or getattr(module, "UNTESTED_CONTEXTS", None) is not None
        ):
            scope = {
                "producers": list(getattr(module, "PRODUCERS", ())),
                "untested_contexts": list(
                    getattr(module, "UNTESTED_CONTEXTS", ())
                ),
            }
        if scope is not None:
            result["declared_scope"] = scope
        require_valid(
            "xuunity.oracle-result.schema.json", result, "oracle result"
        )
        return result

    if workspace is not None:
        return finish(Path(workspace) / f"oracle-{oracle_id}")
    with tempfile.TemporaryDirectory(prefix="xuunity-oracle-") as scratch:
        return finish(Path(scratch) / "tree")


def combined_oracle_result(
    results: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    """Compatibility summary for controls and diagnostics.

    Any ``not_evaluable`` result dominates failure so incomplete evidence
    cannot be collapsed into a scoreable failure. Otherwise the first failure
    wins, then the first pass. Scoring receives the complete result list.
    """
    ordered = list(results)
    if not ordered:
        return None
    for result in ordered:
        if result["status"] == "not_evaluable":
            return result
    for result in ordered:
        if result["status"] == "failed":
            return result
    return ordered[0]


def run_safety_validators(
    fixture_dir: Path,
    fixture: dict[str, Any],
    *,
    tree: Path | None,
    diff_text: str = "",
) -> list[dict[str, Any]]:
    mapping = implementation_map(fixture_dir)
    results: list[dict[str, Any]] = []
    for row in fixture["safety_validators"]:
        path = _implementation_path(fixture_dir, mapping, row["id"])
        module = _load_module(path, row["implementation_sha256"])
        if not callable(getattr(module, "evaluate", None)):
            raise FixtureError(
                f"validator exposes no evaluate(validator_id, tree, "
                f"diff_text): {path}"
            )
        raw = module.evaluate(row["id"], tree, diff_text)
        if not isinstance(raw, dict) or "passed" not in raw:
            raise FixtureError(
                f"validator {row['id']} returned no passed verdict"
            )
        results.append(
            {"validator_id": row["id"], "passed": bool(raw["passed"])}
        )
    return results


def load_expected_stack(fixture_dir: Path) -> dict[str, Any]:
    document = _read_json(Path(fixture_dir) / "expected_stack.json")
    if document.get("authored_by") != "human":
        raise FixtureError(
            "expected_stack.json must declare authored_by: human — a "
            "derivation produced by the resolver under test cannot be the "
            "expected answer"
        )
    return document


def group_policies(
    expected_stack: dict[str, Any],
) -> tuple[list[oc.GroupPolicy], set[str]]:
    policies: list[oc.GroupPolicy] = []
    gate_group_ids: set[str] = set()
    for group in expected_stack["groups"]:
        policies.append(
            oc.GroupPolicy(
                group["group_id"],
                group["mode"],
                float(group["weight"]),
                tuple(group.get("members") or ()),
                int(group.get("min_count") or 0),
                group.get("glob"),
                tuple(group.get("members") or ()),
            )
        )
        if group.get("phase", "before_first_mutation") == (
            "before_first_mutation"
        ):
            gate_group_ids.add(group["group_id"])
    return policies, gate_group_ids


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def mutation_scope(
    mutations: Iterable[adapters.MutationEvidence],
    changed_paths: Iterable[str],
    *,
    allowed: Iterable[str],
    protected: Iterable[str],
) -> dict[str, Any]:
    """Classify every observed mutation and post-diff change against the
    fixture's allowed and protected path sets. An unattributable shell
    mutation target fails closed as out of scope."""
    allowed = list(allowed)
    protected = list(protected)
    protected_hits: list[str] = []
    out_of_scope: list[str] = []
    seen: set[str] = set()
    candidates = [
        mutation.path for mutation in mutations if mutation.succeeded
    ] + list(changed_paths)
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if _matches_any(path, protected):
            protected_hits.append(path)
        elif not allowed or not _matches_any(path, allowed):
            out_of_scope.append(path)
    reason_codes = [
        f"protected_path_mutation:{path}" for path in sorted(protected_hits)
    ] + [f"mutation_out_of_scope:{path}" for path in sorted(out_of_scope)]
    return {
        "protected_mutation": bool(protected_hits) or bool(out_of_scope),
        "protected_hits": sorted(protected_hits),
        "out_of_scope": sorted(out_of_scope),
        "reason_codes": reason_codes,
    }


def classify_atomic_delivery(
    surface_delivery: str, resolution: oc.ArtifactResolution
) -> dict[str, Any]:
    """Design F3 rule: the required atomic owner is either delivered
    completely by the surface or the run is not runnable. Delivery
    failure never counts against the model; non-compliance exists only
    when complete delivery was available and the artifact still is not
    satisfied."""
    if surface_delivery not in SURFACE_DELIVERY_MODES:
        raise FixtureError(
            f"unknown surface delivery mode: {surface_delivery}"
        )
    if surface_delivery in {"partial", "none"}:
        return {
            "run_status": "not_runnable",
            "cause": "delivery_incomplete",
            "model_noncompliance": False,
        }
    return {
        "run_status": "runnable",
        "cause": None,
        "model_noncompliance": not resolution.satisfied,
    }


def load_controls(fixture_dir: Path) -> list[dict[str, Any]]:
    path = Path(fixture_dir) / "controls.json"
    if not path.is_file():
        return []
    controls = _read_json(path)
    if not isinstance(controls, list):
        raise FixtureError(f"controls.json must be a list: {path}")
    return controls


def materialize_control(
    fixture_dir: Path, control: dict[str, Any], destination: Path
) -> Path:
    fixture_dir = Path(fixture_dir)
    destination = Path(destination)
    if destination.exists():
        raise FixtureError(f"control destination exists: {destination}")
    shutil.copytree(fixture_dir / "seed", destination)
    for target, source in (control.get("overlay") or {}).items():
        source_path = fixture_dir / source
        if not source_path.is_file():
            raise FixtureError(f"control overlay source missing: {source}")
        target_path = destination / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
    return destination


def verify_controls(
    fixture_dir: Path, fixture: dict[str, Any]
) -> list[dict[str, Any]]:
    """Prove every authored control classifies exactly as declared:
    known-bad red, known-good green. A drifted control is a fixture
    defect, not a tolerable variance."""
    summaries: list[dict[str, Any]] = []
    controls = load_controls(fixture_dir)
    if not controls:
        raise FixtureError(f"fixture has no authored controls: {fixture_dir}")
    statuses = {str(control.get("expected_status")) for control in controls}
    if not {"passed", "failed"} <= statuses:
        raise FixtureError(
            "controls must include at least one passing and one failing "
            "case — a corpus that cannot go green (or red) proves nothing"
        )
    blocking = [
        row["id"] for row in fixture["semantic_oracles"] if row["blocking"]
    ]
    with tempfile.TemporaryDirectory(prefix="xuunity-controls-") as scratch:
        for index, control in enumerate(controls):
            tree = materialize_control(
                fixture_dir, control, Path(scratch) / f"control-{index}"
            )
            results = [
                run_semantic_oracle(fixture_dir, fixture, oracle_id, tree)
                for oracle_id in blocking
            ]
            combined = combined_oracle_result(results)
            if combined is None:
                raise FixtureError("fixture declares no blocking oracle")
            expected = control["expected_status"]
            if combined["status"] != expected:
                raise FixtureError(
                    f"control {control['id']} expected {expected}, "
                    f"oracle returned {combined['status']} "
                    f"({combined['reason_codes']})"
                )
            expected_reason = control.get("expected_reason")
            if expected_reason and expected_reason not in combined[
                "reason_codes"
            ]:
                raise FixtureError(
                    f"control {control['id']} expected reason "
                    f"{expected_reason}, got {combined['reason_codes']}"
                )
            summaries.append(
                {
                    "control_id": control["id"],
                    "status": combined["status"],
                    "reason_codes": combined["reason_codes"],
                }
            )
    return summaries


def load_attack_cases(fixture_dir: Path) -> list[dict[str, Any]]:
    attacks_dir = Path(fixture_dir) / "attacks"
    if not attacks_dir.is_dir():
        raise FixtureError(f"attack corpus missing: {attacks_dir}")
    cases = [
        _read_json(path) for path in sorted(attacks_dir.glob("*.json"))
    ]
    if not cases:
        raise FixtureError(f"attack corpus is empty: {attacks_dir}")
    return cases


def numbered_read_content(seed_dir: Path, path: str) -> str:
    lines = (
        (Path(seed_dir) / path)
        .read_text(encoding="utf-8")
        .splitlines()
    )
    return "\n".join(
        f"{number:6d}\t{line}" for number, line in enumerate(lines, 1)
    )


def expand_event_templates(
    events: list[Any], seed_dir: Path
) -> list[Any]:
    """Replace ``{"$numbered_read": path}`` placeholders with numbered
    read output generated from the seed, so corpus evidence can never
    drift from the seed content it claims to prove."""

    def expand(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) == {"$numbered_read"} and isinstance(
                value["$numbered_read"], str
            ):
                return numbered_read_content(seed_dir, value["$numbered_read"])
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return [expand(event) for event in events]


def default_manifest(
    seed_dir: Path, paths: Iterable[str]
) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for path in paths:
        full = Path(seed_dir) / path
        data = full.read_bytes()
        text = data.decode("utf-8")
        lines = text.count("\n") + (
            1 if text and not text.endswith("\n") else 0
        )
        manifest[path] = {
            "lines": lines,
            "bytes": len(data),
            "sha256": xc.sha256_bytes(data),
        }
    return manifest


def evaluate_run(
    fixture_dir: Path,
    fixture: dict[str, Any],
    *,
    events: list[dict[str, Any]],
    run_id: str,
    adapter: str = "claude",
    manifest: dict[str, Any] | None = None,
    tree: Path | None = None,
    diff_text: str = "",
    requested_model: str | None = None,
    f0_calibration_passed: bool = True,
    enforcement_mode: str = "audited",
    comparison_status: str = "matched_content_noncontrolled",
    reported_gap_ids: Iterable[str] = (),
    task_measurement_key: str | None = None,
    strict_profile_key: str | None = None,
) -> dict[str, Any]:
    """Evaluate one run's evidence end-to-end against a fixture: adapter
    normalization, mutation boundary, scope containment, hand-authored
    obligation groups, observer axis, hermetic semantic oracles, safety
    validators, and the P2.4 scoring engine. Returns the schema-valid
    run result plus the intermediate diagnostics."""
    fixture_dir = Path(fixture_dir)
    manifest = manifest or {}
    normalized = adapters.normalize_transcript(events, adapter, manifest)
    validity = adapters.inspect_run_validity({}, normalized)
    changed_files = adapters.parse_diff(diff_text) if diff_text else {}
    changed_code = [
        path for path in changed_files if adapters.is_code_path(path)
    ]
    boundary = adapters.mutation_boundary(
        normalized["mutations"], normalized["flags"], changed_code
    )
    scope = mutation_scope(
        normalized["mutations"],
        list(changed_files),
        allowed=fixture["allowed_mutation_paths"],
        protected=fixture["protected_paths"],
    )
    expected_stack = load_expected_stack(fixture_dir)
    policies, gate_group_ids = group_policies(expected_stack)
    surface = "codex_cli" if adapter == "codex" else "claude_cli"
    stack = adapters.evaluate_group_policies(
        policies,
        normalized["reads"],
        boundary.cutoff,
        manifest,
        lambda path: oc.runtime_context_match(surface, path),
    )
    identity = oc.profile_identity_check(
        requested_model, normalized.get("observed_model")
    )
    unpaired_or_unknown = bool(boundary.unpaired_mutating_invocations) or any(
        flag.parser_result == "unsupported" and flag.boundary_relevant
        for flag in normalized["flags"]
    )
    observer = oc.observer_axis(
        profile_mismatch=identity["mismatch"],
        boundary_ambiguous=boundary.boundary_ambiguous,
        artifact_resolutions=stack["resolutions"],
        unpaired_or_unknown_critical_events=unpaired_or_unknown,
    )
    axes = {
        "preflight": "ready",
        "execution": (
            "valid" if validity["status"] == "valid" else "execution_invalid"
        ),
        "observer": observer,
        "artifacts": (
            "artifact_invalid" if boundary.diff_without_mutation else "valid"
        ),
    }
    satisfied_by_group = {
        row["group_id"]: row["gate_satisfied"] for row in stack["groups"]
    }
    gate_decision = (
        "pass"
        if all(
            satisfied_by_group[group_id] for group_id in gate_group_ids
        )
        else "fail"
    )

    oracle_results: list[dict[str, Any]] = []
    safety_results: list[dict[str, Any]] = []
    if tree is not None:
        for row in fixture["semantic_oracles"]:
            if row["blocking"]:
                oracle_results.append(
                    run_semantic_oracle(
                        fixture_dir, fixture, row["id"], tree
                    )
                )
        if fixture["safety_validators"]:
            safety_results = run_safety_validators(
                fixture_dir, fixture, tree=tree, diff_text=diff_text
            )

    default_key = xc.sha256_bytes(run_id.encode("utf-8"))
    run_result = scoring.score_run(
        fixture,
        run_id=run_id,
        task_measurement_key=task_measurement_key or default_key,
        strict_profile_key=strict_profile_key or default_key,
        axes=axes,
        enforcement_mode=enforcement_mode,
        f0_calibration_passed=f0_calibration_passed,
        profile_identity_match=not identity["mismatch"],
        comparison_status=comparison_status,
        gate_decision=gate_decision,
        delivery_percent=stack["delivery_percent"],
        oracle_result=oracle_results,
        safety_results=safety_results,
        reported_gap_ids=reported_gap_ids,
        protected_mutation=scope["protected_mutation"],
        extra_reason_codes=list(validity["reason_codes"])
        + scope["reason_codes"],
    )
    return {
        "run_result": run_result,
        "stack": stack,
        "boundary": boundary,
        "validity": validity,
        "scope": scope,
        "observer_axis": observer,
        "gate_decision": gate_decision,
        "oracle_results": oracle_results,
    }


PASSING_BANDS = frozenset({"fit_candidate", "supervision_candidate"})


def bypass_miss(run_result: dict[str, Any]) -> bool:
    """An attack that walks away with a valid passing score is a bypass
    miss — the design grades any miss ``unfit`` for the whole profile."""
    return (
        run_result["score_total"] is not None
        and run_result["band"] in PASSING_BANDS
    )

"""Persisted attempt accounting and separate health/fitness projections."""

from collections import Counter
from pathlib import Path
from typing import Any

import xuunity_canonical as xc

from . import adapters, executor, records, schedule, suite
from .contracts import require_valid


def cohort(plan: dict, suite_document: dict) -> list[dict]:
    schedule.validate(plan)
    suite.validate_suite(suite_document)
    schedule.comparison_contract(plan, suite_document)
    roster = {row["attempt_id"]: row for row in plan["attempts"]}
    status = {row["attempt_id"]: row["status"] for row in schedule.accounting(plan)}
    root = Path(plan["journal_root"])
    attempts = []
    for row in suite_document["attempt_plan"]["attempts"]:
        scheduled = roster.get(row["attempt_id"])
        if scheduled is None or scheduled["fixture_id"] != row["fixture_id"] or scheduled["block_id"] != row["replicate_id"]:
            raise ValueError("suite_execution_schedule_mismatch")
        evidence = root / row["attempt_id"]
        run_result = None
        manifest = None
        if status[row["attempt_id"]] == "finished" and (evidence / "result.json").exists():
            run_result = records.read(evidence / "result.json")
            require_valid("xuunity.run-result.schema.json", run_result, "scheduled result")
            if records.read(evidence / "finished.json")["result_hash"] != xc.sha256_file(evidence / "result.json"):
                raise ValueError("scheduled_result_changed")
            if (evidence / "run-manifest.json").exists():
                executor.score(evidence)
                manifest = records.read(evidence / "run-manifest.json")
            elif run_result["score_total"] is not None:
                raise ValueError("numeric_result_without_replayable_evidence")
        attempts.append({"attempt_id": row["attempt_id"], "fixture_id": row["fixture_id"],
                         "replicate_id": row["replicate_id"], "run_result": run_result,
                         "run_manifest": manifest, "censored": status[row["attempt_id"]] == "censored"})
    return attempts


def diagnostic_report(plan: dict, *, suite_result: dict | None = None) -> dict[str, Any]:
    """This report exposes summaries only. It never projects raw prompts/logs."""
    root = Path(plan["journal_root"])
    rows = []
    for entry in schedule.accounting(plan):
        evidence = root / entry["attempt_id"]
        row = dict(entry)
        if (evidence / "recovery.json").exists():
            recovered = records.read(evidence / "recovery.json")
            records.verify(recovered)
            if records.read(evidence / "finished.json")["result_hash"] != xc.sha256_file(evidence / "recovery.json"):
                raise ValueError("recovery_artifact_changed")
            row.update(score=None, cause="unattributed", null_reasons=recovered["reason_codes"])
        if entry["status"] == "finished" and (evidence / "result.json").exists():
            result = records.read(evidence / "result.json")
            require_valid("xuunity.run-result.schema.json", result, "diagnostic result")
            if records.read(evidence / "finished.json")["result_hash"] != xc.sha256_file(evidence / "result.json"):
                raise ValueError("diagnostic_result_changed")
            if (evidence / "run-manifest.json").exists():
                executor.score(evidence)
            elif result["score_total"] is not None:
                raise ValueError("numeric_result_without_replayable_evidence")
            row.update({"fixture_id": result["fixture_id"], "score": result["score_total"],
                        "null_reasons": result["reason_codes"], "enforcement": result["enforcement_mode"],
                        "comparison": result["comparison_status"], "cause": (result.get("cause") or {}).get("owner"),
                        "hard_gates": [g["gate"] for g in result["hard_gates"] if g["triggered"]]})
            if (evidence / "oracles.json").exists():
                row["task_outcomes"] = [{k: oracle[k] for k in ("oracle_id", "kind", "status", "reason_codes")}
                                        for oracle in records.read(evidence / "oracles.json")["results"]]
        if (evidence / "calibration.json").exists() and not (evidence / "input.json").exists():
            calibration = records.read(evidence / "calibration.json")
            records.verify(calibration)
            for name, digest in calibration["raw_artifact_hashes"].items():
                if "/" in name or "\\" in name or xc.sha256_file(evidence / name) != digest:
                    raise ValueError("calibration_artifact_changed")
            row["calibration"] = {k: calibration[k] for k in
                                  ("diagnostic_compatible", "score_eligible", "reason_codes")}
            row["cause"] = (calibration.get("cause") or {}).get("owner")
        if (evidence / "process.json").exists():
            process = records.read(evidence / "process.json")
            row["execution"] = {k: process.get(k) for k in
                                ("status", "exit_code", "timed_out", "interrupted", "duration_seconds")}
        elif row.get("calibration") and "process" in calibration:
            row["execution"] = {k: calibration["process"].get(k) for k in
                                ("status", "exit_code", "timed_out", "interrupted", "duration_seconds")}
        if (evidence / "transcript.jsonl").exists():
            events, invalid = adapters.load_jsonl_strict(evidence / "transcript.jsonl")
            usages = [e["usage"] for e in events if e.get("type") in {"turn.completed", "result"}
                      and isinstance(e.get("usage"), dict)]
            fields = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
            row["observed_token_usage"] = ({key: sum(u.get(key, 0) for u in usages) for key in fields
                                            if all(type(u.get(key, 0)) is int and u.get(key, 0) >= 0 for u in usages)}
                                           if usages and not invalid else None)
        rows.append(row)
    return records.seal({
        "schema_version": "xuunity.diagnostic-report.v1", "schedule_hash": plan["record_hash"],
        "installation_health": {
            "calibrations": [r for r in rows if "calibration" in r],
            "evaluator_failures": sum(r.get("cause") == "measurement_system" for r in rows),
            "environment_limited_measurements": sum(r.get("cause") == "environment" for r in rows),
            "process_failures": sum(r.get("execution", {}).get("status") not in {None, "completed"} for r in rows),
        },
        "model_fitness": {"grade": suite_result["grade"] if suite_result else None,
                          "adoption_stage": "disabled_pending_live_conformance",
                          "numeric_results": sum(r.get("score") is not None for r in rows)},
        "accounting": dict(Counter(r["status"] for r in rows)), "scheduled": len(rows), "attempts": rows,
        "observed_duration_seconds": round(sum(r.get("execution", {}).get("duration_seconds") or 0 for r in rows), 3),
        "billed_cost_usd": None,
    })


def render_diagnostic(report: dict) -> str:
    lines = ["# Model Fitness execution report", "",
             f"Scheduled attempts: {report['scheduled']}. Accounting: {report['accounting']}.", "",
             "## Installation health", "",
             f"Evaluator failures: {report['installation_health']['evaluator_failures']}. "
             f"Surface/environment limits: {report['installation_health']['environment_limited_measurements']}.", "",
             "## Model fitness", "",
             f"Grade: {report['model_fitness']['grade'] or 'not qualified'}. "
             f"Numeric results: {report['model_fitness']['numeric_results']}.", "",
             "Task-oracle outcomes below are independent of protocol fitness eligibility.", "",
             "| Attempt | State | Task outcomes | Score | Cause |",
             "|---|---|---|---:|---|"]
    for row in report["attempts"]:
        outcomes = ", ".join(o["oracle_id"] + ": " + o["status"] for o in row.get("task_outcomes", []))
        lines.append(f"| {row['attempt_id']} | {row['status']} | {outcomes or '—'} | {row.get('score')} | {row.get('cause') or '—'} |")
    lines += ["", f"Observed process time: {report['observed_duration_seconds']} seconds. Billed cost: unavailable.", "",
              "Advisory/blocking routing remains disabled until live request-boundary conformance is verified.", ""]
    return "\n".join(lines)

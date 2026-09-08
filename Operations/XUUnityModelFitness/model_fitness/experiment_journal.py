"""Atomic alpha reservation for a frozen experiment; no model or apply action."""

from pathlib import Path
import xuunity_canonical as xc

from . import experiment, records, suite


def evaluate(manifest: dict, control: dict, treatment: dict, *, root: Path,
             alpha_charge: float, control_ref: str, treatment_ref: str) -> dict:
    experiment.validate_manifest(manifest)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    identity = records.slug(manifest["experiment_id"])
    binding = {"manifest_hash": experiment.manifest_hash(manifest),
               "control_hash": suite.suite_result_sha256(control),
               "treatment_hash": suite.suite_result_sha256(treatment),
               "alpha_charge": alpha_charge, "family_id": manifest["family"]["experiment_family_id"],
               "evaluator_sha256": xc.sha256_file(Path(experiment.__file__))}
    lock = root / "journal.lock"
    records.write(lock, {"experiment_id": identity}, exclusive=True)
    try:
        ticket = root / (identity + ".reservation.json")
        if ticket.exists():
            reservation = records.read(ticket)
            records.verify(reservation)
            if any(reservation[k] != value for k, value in binding.items()):
                raise ValueError("experiment_retry_identity_changed")
        else:
            reservations = [records.read(p) for p in root.glob("*.reservation.json")]
            for previous in reservations:
                records.verify(previous)
            spent = sum(r["alpha_charge"] for r in reservations if r["family_id"] == binding["family_id"])
            if alpha_charge <= 0 or spent + alpha_charge > manifest["family"]["family_alpha"] + 1e-12:
                raise ValueError("experiment_family_alpha_exhausted")
            reservation = records.seal({"schema_version": "xuunity.experiment-reservation.v1",
                                        **binding, "alpha_spent_before": spent})
            records.write(ticket, reservation, exclusive=True)
        result_path = root / (identity + ".result.json")
        anchor = root / (identity + ".completed.json")
        if result_path.exists() and anchor.exists():
            completed = records.read(anchor)
            records.verify(completed)
            if completed["result_sha256"] != xc.sha256_file(result_path):
                raise ValueError("experiment_result_changed")
            return records.read(result_path)
        result = experiment.evaluate_experiment(
            manifest, control, treatment, control_suite_ref=control_ref, treatment_suite_ref=treatment_ref,
            alpha_charge=alpha_charge, alpha_spent_before=reservation["alpha_spent_before"],
        )
        if result_path.exists():
            if records.read(result_path) != result:
                raise ValueError("unanchored_experiment_result_changed")
        else:
            records.write(result_path, result, exclusive=True)
        records.write(anchor, records.seal({"schema_version": "xuunity.experiment-completion.v1",
                                           "result_sha256": xc.sha256_file(result_path)}), exclusive=True)
        return result
    finally:
        lock.unlink()

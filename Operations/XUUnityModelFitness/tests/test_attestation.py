from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
MODULE_TESTS_DIR = (
    OPERATION_DIR.parents[1] / "Modules" / "XUUnity" / "scripts" / "tests"
)
sys.path.insert(0, str(OPERATION_DIR))
sys.path.insert(0, str(MODULE_TESTS_DIR))

from model_fitness import attestation as att  # noqa: E402

import reduced_stack_gate as gate  # noqa: E402
import reduced_stack_resolver as resolver  # noqa: E402
import reduced_stack_testkit as kit  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

KEY = b"parent-mac-key-0123456789abcdef!"
WRONG_KEY = b"another-mac-key-0123456789abcdef"
DUMMY = xc.sha256_bytes(b"dummy")
IDENTITY = {
    "id": "test-component",
    "version": "1",
    "implementation_sha256": DUMMY,
}
CANARY = b"\n<xuunity-truncation-canary-7f3a>\n"


def build_attestation(**overrides) -> dict:
    arguments = dict(
        session_id="session-test",
        task_identity=DUMMY,
        repository_content_hash=DUMMY,
        protocol_content_hash=DUMMY,
        ruleset_hash=DUMMY,
        adapter_profile_hash=DUMMY,
        requested_profile={"model": "model-test"},
        allowed_roots={
            "repository": ["."],
            "guidance": ["AIRoot/"],
            "evidence": ["_evidence/"],
            "mutation": ["DemoProject/Scripts/"],
        },
        policy_ids={
            "data_classification": "public_synthetic",
            "outbound_delivery": "deny_all",
        },
        collector_identity=IDENTITY,
        broker_identity=IDENTITY,
        created="2026-07-29T00:00:00Z",
        expires="2026-07-30T00:00:00Z",
    )
    arguments.update(overrides)
    return att.build_session_attestation(KEY, **arguments)


class SessionAttestationTests(unittest.TestCase):
    def test_roundtrip_verifies(self) -> None:
        attestation = build_attestation()
        self.assertEqual(
            [],
            att.verify_session_attestation(
                attestation, KEY, now="2026-07-29T12:00:00Z"
            ),
        )
        self.assertTrue(attestation["attestation_id"].startswith("att-"))
        self.assertTrue(attestation["capability_id"].startswith("cap-"))

    def test_tampered_field_fails_closed(self) -> None:
        attestation = build_attestation()
        attestation["session_id"] = "session-hijacked"
        reasons = att.verify_session_attestation(
            attestation, KEY, now="2026-07-29T12:00:00Z"
        )
        self.assertIn("attestation_hash_mismatch", reasons)

    def test_wrong_key_fails_closed(self) -> None:
        attestation = build_attestation()
        reasons = att.verify_session_attestation(
            attestation, WRONG_KEY, now="2026-07-29T12:00:00Z"
        )
        self.assertIn("attestation_signature_invalid", reasons)

    def test_expiry_window_enforced(self) -> None:
        attestation = build_attestation()
        self.assertIn(
            "attestation_expired",
            att.verify_session_attestation(
                attestation, KEY, now="2026-07-30T00:00:00Z"
            ),
        )
        self.assertIn(
            "attestation_not_yet_valid",
            att.verify_session_attestation(
                attestation, KEY, now="2026-07-28T23:59:59Z"
            ),
        )

    def test_malformed_timestamp_rejected_at_build(self) -> None:
        with self.assertRaises(att.AttestationError):
            build_attestation(created="2026-07-29 00:00:00")
        with self.assertRaises(att.AttestationError):
            build_attestation(
                created="2026-07-30T00:00:00Z", expires="2026-07-29T00:00:00Z"
            )

    def test_sanitized_projection_drops_signature(self) -> None:
        attestation = build_attestation()
        sanitized = att.sanitized_session_attestation(attestation)
        self.assertIsNone(sanitized["signature"])
        self.assertEqual(
            attestation["attestation_hash"], sanitized["attestation_hash"]
        )


class RequestAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = build_attestation()
        self.file_a = b"# base_async_rules\nguidance body a\n"
        self.file_b = b"# main_thread\nguidance body b\n"

    def _attest(self, payload: bytes, artifacts=None) -> dict:
        return att.attest_outbound_request(
            KEY,
            session_attestation=self.session,
            request_seq=1,
            payload=payload,
            artifacts=artifacts
            or [
                ("skills/async/base_async_rules.md", self.file_a),
                ("skills/async/main_thread.md", self.file_b),
                ("skills/async/missing.md", b"never serialized"),
            ],
            canary_marker=CANARY,
            adapter_identity=IDENTITY,
        )

    def test_embedded_artifacts_with_canary_are_trusted(self) -> None:
        payload = b"prompt\n" + self.file_a + b"\n---\n" + self.file_b + CANARY
        attestation = self._attest(payload)
        self.assertEqual([], att.verify_request_attestation(attestation, KEY))
        self.assertTrue(attestation["truncation_canary"]["present"])
        required = [
            {
                "path": "skills/async/base_async_rules.md",
                "sha256": xc.sha256_bytes(self.file_a),
            },
            {
                "path": "skills/async/missing.md",
                "sha256": xc.sha256_bytes(b"never serialized"),
            },
        ]
        states = att.delivery_states(required, [attestation], KEY)
        self.assertEqual(
            "trusted_runtime_delivered",
            states["skills/async/base_async_rules.md"]["state"],
        )
        self.assertEqual(
            "runtime_delivered_unverified",
            states["skills/async/missing.md"]["state"],
        )

    def test_truncated_payload_never_upgrades(self) -> None:
        truncated = b"prompt\n" + self.file_a[: len(self.file_a) // 2]
        attestation = self._attest(truncated)
        self.assertFalse(attestation["truncation_canary"]["present"])
        required = [
            {
                "path": "skills/async/base_async_rules.md",
                "sha256": xc.sha256_bytes(self.file_a),
            }
        ]
        states = att.delivery_states(required, [attestation], KEY)
        self.assertEqual(
            "runtime_delivered_unverified",
            states["skills/async/base_async_rules.md"]["state"],
        )

    def test_canary_before_last_segment_is_not_present(self) -> None:
        payload = CANARY + self.file_a
        attestation = self._attest(payload)
        self.assertFalse(attestation["truncation_canary"]["present"])

    def test_wrong_key_or_tamper_downgrades_everything(self) -> None:
        payload = self.file_a + CANARY
        attestation = self._attest(payload)
        required = [
            {
                "path": "skills/async/base_async_rules.md",
                "sha256": xc.sha256_bytes(self.file_a),
            }
        ]
        states = att.delivery_states(required, [attestation], WRONG_KEY)
        self.assertEqual(
            "runtime_delivered_unverified",
            states["skills/async/base_async_rules.md"]["state"],
        )
        attestation["payload_length"] = attestation["payload_length"] + 1
        self.assertNotEqual(
            [], att.verify_request_attestation(attestation, KEY)
        )


class GateBridgeTests(unittest.TestCase):
    """A verified request attestation feeds the gate as an attested context
    manifest; an unverified channel never satisfies an obligation."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)
        self.repo = kit.build_fixture_repo(self.work)
        self.session = build_attestation()

    def test_attested_payload_satisfies_gate_artifact(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text="Rename the score field on the leaderboard view.",
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = resolver.derive_plan(
            self.repo, kit.ruleset_path(self.repo), envelope
        )
        artifact = plan["required_artifacts"][0]
        content = (self.repo / artifact["path"]).read_bytes()
        payload = b"system prompt\n" + content + CANARY
        request = att.attest_outbound_request(
            KEY,
            session_attestation=self.session,
            request_seq=0,
            payload=payload,
            artifacts=[(artifact["path"], content)],
            canary_marker=CANARY,
            adapter_identity=IDENTITY,
        )
        entries = att.context_manifest_entries(
            [artifact], [request], KEY
        )
        trusted_ledger = kit.make_ledger([], context_manifest=entries)
        resolution = gate.resolve_artifact_state(
            artifact, trusted_ledger, gate.FAR_FUTURE_SEQ
        )
        self.assertTrue(resolution.satisfied)
        self.assertEqual("trusted_runtime_delivered", resolution.state)

        forged = att.context_manifest_entries([artifact], [request], WRONG_KEY)
        unverified_ledger = kit.make_ledger([], context_manifest=forged)
        resolution = gate.resolve_artifact_state(
            artifact, unverified_ledger, gate.FAR_FUTURE_SEQ
        )
        self.assertFalse(resolution.satisfied)


class RunManifestTests(unittest.TestCase):
    def test_manifest_builds_validates_and_anchors(self) -> None:
        session = build_attestation()
        with tempfile.TemporaryDirectory() as temporary:
            anchor = Path(temporary) / "protected"
            manifest = att.build_protected_run_manifest(
                attempt_id="attempt-1",
                session_attestation=session,
                inputs={
                    "fixture_id": "f0_observer_conformance",
                    "fixture_hash": DUMMY,
                    "seed_identity": DUMMY,
                    "protocol_content_hash": DUMMY,
                    "ruleset_hash": DUMMY,
                    "task_identity": DUMMY,
                },
                task_measurement_key=DUMMY,
                strict_profile_key=DUMMY,
                started="2026-07-29T10:00:00Z",
                raw_evidence_hashes={"transcript.jsonl": DUMMY},
                anchor_dir=anchor,
            )
            self.assertTrue(
                (anchor / "run-manifest-attempt-1.json").is_file()
            )
        recomputed = xc.document_hash(manifest, "manifest_hash")
        self.assertEqual(recomputed, manifest["manifest_hash"])
        tampered = dict(manifest)
        tampered["raw_evidence_hashes"] = {"transcript.jsonl": xc.sha256_bytes(b"swap")}
        self.assertNotEqual(
            manifest["manifest_hash"],
            xc.document_hash(tampered, "manifest_hash"),
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
MODULE_TESTS_DIR = (
    OPERATION_DIR.parents[1] / "Modules" / "XUUnity" / "scripts" / "tests"
)
sys.path.insert(0, str(OPERATION_DIR))
sys.path.insert(0, str(MODULE_TESTS_DIR))

from model_fitness import attestation as att  # noqa: E402
from model_fitness import broker as broker_module  # noqa: E402
from model_fitness import contracts  # noqa: E402
from model_fitness.broker import (  # noqa: E402
    Broker,
    BrokerError,
    DeclaredWriteBoundary,
    SameUidChmodBoundary,
    mint_capability,
    verify_capability,
)

import reduced_stack_resolver as resolver  # noqa: E402
import reduced_stack_testkit as kit  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

KEY = b"parent-broker-key-0123456789abcd"
NOW = "2026-07-29T10:00:00Z"
EXPIRES = "2026-07-29T11:00:00Z"
DUMMY = xc.sha256_bytes(b"dummy")
IDENTITY = {
    "id": "test-component",
    "version": "1",
    "implementation_sha256": DUMMY,
}
CS_TASK = "TASK-2 Rename the score field on the leaderboard view."
CLEAN_DIFF = (
    "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
    "--- a/DemoProject/Scripts/Foo.cs\n"
    "+++ b/DemoProject/Scripts/Foo.cs\n"
    "@@ -1 +1 @@\n-old\n+var score = 1;\n"
)


def sample_binding(**overrides) -> dict:
    binding = {
        "attestation_id": "att-sample",
        "session_id": "session-test",
        "repository_content_hash": DUMMY,
        "plan_hash": xc.sha256_bytes(b"plan"),
        "ledger_hash": xc.sha256_bytes(b"ledger"),
        "semantic_result_hash": xc.sha256_bytes(b"semantic"),
        "mutation_generation": 0,
        "scope": ["DemoProject/Scripts/Foo.cs"],
        "expires": EXPIRES,
    }
    binding.update(overrides)
    return binding


class CapabilityConformanceTests(unittest.TestCase):
    def test_mint_and_verify_roundtrip(self) -> None:
        binding = sample_binding()
        capability_id, token = mint_capability(KEY, binding)
        self.assertTrue(capability_id.startswith("mcap-"))
        self.assertEqual([], verify_capability(KEY, token, binding, now=NOW))

    def test_binding_is_canonical_not_positional(self) -> None:
        binding = sample_binding()
        reordered = dict(sorted(binding.items(), reverse=True))
        self.assertEqual(
            mint_capability(KEY, binding), mint_capability(KEY, reordered)
        )

    def test_every_binding_field_is_authenticated(self) -> None:
        binding = sample_binding()
        _, token = mint_capability(KEY, binding)
        tampering = {
            "attestation_id": "att-other",
            "session_id": "session-other",
            "repository_content_hash": xc.sha256_bytes(b"other-repo"),
            "plan_hash": xc.sha256_bytes(b"other-plan"),
            "ledger_hash": xc.sha256_bytes(b"other-ledger"),
            "semantic_result_hash": xc.sha256_bytes(b"other-semantic"),
            "mutation_generation": 1,
            "scope": ["DemoProject/"],
            "expires": "2026-07-29T12:00:00Z",
        }
        for field, value in tampering.items():
            tampered = sample_binding(**{field: value})
            self.assertIn(
                "capability_token_invalid",
                verify_capability(KEY, token, tampered, now=NOW),
                field,
            )

    def test_wrong_domain_fails(self) -> None:
        binding = sample_binding()
        digest = broker_module.binding_hash(binding)
        foreign = att.mac_hex(KEY, "xuunity:session-attestation:v1", digest)
        self.assertIn(
            "capability_token_invalid",
            verify_capability(KEY, foreign, binding, now=NOW),
        )

    def test_expiry_fails_closed(self) -> None:
        binding = sample_binding()
        _, token = mint_capability(KEY, binding)
        self.assertIn(
            "capability_expired",
            verify_capability(KEY, token, binding, now=EXPIRES),
        )

    def test_malformed_binding_rejected(self) -> None:
        binding = sample_binding()
        del binding["scope"]
        with self.assertRaises(BrokerError):
            mint_capability(KEY, binding)
        with self.assertRaises(broker_module.BrokerError):
            mint_capability(
                KEY, sample_binding(mutation_generation=True)
            )
        with self.assertRaises(xc.CanonicalizationError):
            broker_module.binding_hash(
                sample_binding(scope=["../escape.txt"])
            )


class BrokerHarness(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)
        self.repo = kit.build_fixture_repo(self.work)
        self.attestation = att.build_session_attestation(
            KEY,
            session_id="session-test",
            task_identity=DUMMY,
            repository_content_hash=DUMMY,
            protocol_content_hash=DUMMY,
            ruleset_hash=kit.ruleset_hash(self.repo),
            adapter_profile_hash=DUMMY,
            requested_profile={"model": "model-test"},
            allowed_roots={
                "repository": ["."],
                "guidance": ["AIRoot/", "Agents.md", "DemoProject"],
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
        self.envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        self.plan = resolver.derive_plan(
            self.repo, kit.ruleset_path(self.repo), self.envelope
        )
        self.plan_path = kit.write_json(self.work, "plan.json", self.plan)

    def make_broker(self, boundary=None) -> Broker:
        return Broker(
            self.work / "broker",
            KEY,
            self.attestation,
            self.repo,
            boundary or DeclaredWriteBoundary("os_readonly_mount"),
        )

    def ledger_path(
        self, *, with_mutation: bool = False, name: str = "ledger.json"
    ) -> Path:
        events = kit.proven_events_for_plan(self.plan)
        if with_mutation:
            events.append(
                kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
            )
        return kit.write_json(self.work, name, kit.make_ledger(events))


class BrokerAuthorizationTests(BrokerHarness):
    def test_pass_with_os_boundary_mints_authoritative(self) -> None:
        broker = self.make_broker()
        outcome = broker.authorize_batch(
            self.plan_path, self.ledger_path(), now=NOW, expires=EXPIRES
        )
        self.assertEqual("pass", outcome.result["decision"])
        self.assertEqual(
            "authoritative", outcome.result["enforcement_mode"]
        )
        authorization = outcome.result["authorization"]
        self.assertEqual(outcome.capability_id, authorization["capability_id"])
        self.assertEqual(0, authorization["mutation_generation"])
        self.assertEqual(
            ["DemoProject/Scripts/Foo.cs"], authorization["scope"]
        )
        self.assertIsNotNone(outcome.token)
        record_path = (
            self.work / "broker" / "issued" / f"{outcome.capability_id}.json"
        )
        record_text = record_path.read_text(encoding="utf-8")
        self.assertNotIn(outcome.token, record_text)
        record = json.loads(record_text)
        self.assertEqual(
            [],
            contracts.validate_against(
                "xuunity.mutation-capability.schema.json", record
            ),
        )
        self.assertEqual(
            xc.sha256_bytes(outcome.token.encode("utf-8")),
            record["token_sha256"],
        )

    def test_gate_fail_stays_audited_without_capability(self) -> None:
        broker = self.make_broker()
        empty_ledger = kit.write_json(
            self.work, "empty_ledger.json", kit.make_ledger([])
        )
        outcome = broker.authorize_batch(
            self.plan_path, empty_ledger, now=NOW, expires=EXPIRES
        )
        self.assertEqual("fail", outcome.result["decision"])
        self.assertEqual("audited", outcome.result["enforcement_mode"])
        self.assertIsNone(outcome.result["authorization"])
        self.assertIsNone(outcome.token)

    def test_unverified_boundary_stays_audited(self) -> None:
        broker = self.make_broker(SameUidChmodBoundary())
        outcome = broker.authorize_batch(
            self.plan_path, self.ledger_path(), now=NOW, expires=EXPIRES
        )
        self.assertEqual("pass", outcome.result["decision"])
        self.assertEqual("audited", outcome.result["enforcement_mode"])
        self.assertIsNone(outcome.token)
        self.assertIn(
            "write_boundary_unverified:chmod_same_uid",
            outcome.result["reason_codes"],
        )

    def test_expired_session_attestation_refuses_authorization(self) -> None:
        broker = self.make_broker()
        with self.assertRaises(BrokerError) as caught:
            broker.authorize_batch(
                self.plan_path,
                self.ledger_path(),
                now="2026-07-30T00:00:01Z",
                expires="2026-07-30T01:00:00Z",
            )
        self.assertEqual("session_attestation_rejected", caught.exception.reason)


class BrokerMutationTests(BrokerHarness):
    def _authorized(self, broker: Broker):
        return broker.authorize_batch(
            self.plan_path, self.ledger_path(), now=NOW, expires=EXPIRES
        )

    def test_apply_writes_journal_and_bumps_generation(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        target = self.repo / "DemoProject/Scripts/Foo.cs"
        before_sha = xc.sha256_file(target)
        new_content = "public class Foo { public int Score; }\n"
        journal = broker.apply_batch(
            outcome.capability_id,
            outcome.token,
            [{"path": "DemoProject/Scripts/Foo.cs", "content": new_content}],
            now=NOW,
        )
        self.assertEqual(new_content, target.read_text(encoding="utf-8"))
        entry = journal["entries"][0]
        self.assertEqual(before_sha, entry["before_sha256"])
        self.assertEqual(
            xc.sha256_bytes(new_content.encode("utf-8")),
            entry["after_sha256"],
        )
        state = json.loads(
            (self.work / "broker" / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, state["mutation_generation"])

    def test_replay_fails_closed(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        batch = [{"path": "DemoProject/Scripts/Foo.cs", "content": "x\n"}]
        broker.apply_batch(outcome.capability_id, outcome.token, batch, now=NOW)
        with self.assertRaises(BrokerError) as caught:
            broker.apply_batch(
                outcome.capability_id, outcome.token, batch, now=NOW
            )
        self.assertEqual("capability_replayed", caught.exception.reason)

    def test_concurrent_double_spend_admits_exactly_one(self) -> None:
        broker = self.make_broker()
        barrier = threading.Barrier(2)
        results: list[str] = []

        def consume() -> None:
            barrier.wait()
            try:
                broker._consume("mcap-contended", now=NOW)
                results.append("consumed")
            except BrokerError as error:
                results.append(error.reason)

        threads = [threading.Thread(target=consume) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(
            ["capability_replayed", "consumed"], sorted(results)
        )

    def test_expired_capability_cannot_apply(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        with self.assertRaises(BrokerError) as caught:
            broker.apply_batch(
                outcome.capability_id,
                outcome.token,
                [{"path": "DemoProject/Scripts/Foo.cs", "content": "x\n"}],
                now=EXPIRES,
            )
        self.assertEqual("capability_rejected", caught.exception.reason)

    def test_scope_escape_burns_capability_and_refuses(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        with self.assertRaises(BrokerError) as caught:
            broker.apply_batch(
                outcome.capability_id,
                outcome.token,
                [{"path": "DemoProject/Agents.md", "content": "hijack\n"}],
                now=NOW,
            )
        self.assertEqual("mutation_batch_refused", caught.exception.reason)
        self.assertEqual(
            "project body for DemoProject/Agents.md",
            (self.repo / "DemoProject/Agents.md")
            .read_text(encoding="utf-8")
            .splitlines()[1],
        )
        record = json.loads(
            (
                self.work / "broker" / "issued" / f"{outcome.capability_id}.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(record["consumption"]["applied"])
        with self.assertRaises(BrokerError) as replay:
            broker.apply_batch(
                outcome.capability_id,
                outcome.token,
                [{"path": "DemoProject/Scripts/Foo.cs", "content": "x\n"}],
                now=NOW,
            )
        self.assertEqual("capability_replayed", replay.exception.reason)

    def test_path_traversal_refused(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        with self.assertRaises(BrokerError) as caught:
            broker.apply_batch(
                outcome.capability_id,
                outcome.token,
                [{"path": "DemoProject/Scripts/../../escape.txt", "content": "x"}],
                now=NOW,
            )
        self.assertEqual("mutation_batch_refused", caught.exception.reason)
        self.assertFalse((self.work / "escape.txt").exists())

    def test_symlink_in_mutation_path_refused(self) -> None:
        broker = self.make_broker()
        outside = self.work / "outside.cs"
        outside.write_text("outside\n", encoding="utf-8")
        link = self.repo / "DemoProject/Scripts/Link.cs"
        try:
            link.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"symlinks unsupported here: {error}")
        violation = broker._scope_violation(
            "DemoProject/Scripts/Link.cs", ["DemoProject/Scripts/"]
        )
        self.assertEqual(
            "symlink_in_mutation_path:DemoProject/Scripts/Link.cs", violation
        )

    def test_stale_generation_fails_closed(self) -> None:
        broker = self.make_broker()
        outcome = self._authorized(broker)
        broker.apply_batch(
            outcome.capability_id,
            outcome.token,
            [{"path": "DemoProject/Scripts/Foo.cs", "content": "v2\n"}],
            now=NOW,
        )
        binding = {
            "attestation_id": self.attestation["attestation_id"],
            "session_id": "session-test",
            "repository_content_hash": self.attestation[
                "repository_content_hash"
            ],
            "plan_hash": self.plan["plan_hash"],
            "ledger_hash": xc.sha256_bytes(b"any"),
            "semantic_result_hash": xc.sha256_bytes(b"any"),
            "mutation_generation": 0,
            "scope": ["DemoProject/Scripts/Foo.cs"],
            "expires": EXPIRES,
        }
        capability_id, token = mint_capability(KEY, binding)
        record = {
            "schema_version": "xuunity.mutation-capability.v1",
            "capability_id": capability_id,
            "binding": broker_module._require_binding(binding),
            "issued": NOW,
            "token_sha256": xc.sha256_bytes(token.encode("utf-8")),
            "consumption": None,
        }
        (self.work / "broker" / "issued" / f"{capability_id}.json").write_text(
            json.dumps(record), encoding="utf-8"
        )
        with self.assertRaises(BrokerError) as caught:
            broker.apply_batch(
                capability_id,
                token,
                [{"path": "DemoProject/Scripts/Foo.cs", "content": "v3\n"}],
                now=NOW,
            )
        self.assertEqual(
            "capability_generation_stale", caught.exception.reason
        )


class BrokerReconcileTests(BrokerHarness):
    def test_batch_must_reconcile_before_next_authorization(self) -> None:
        broker = self.make_broker()
        outcome = broker.authorize_batch(
            self.plan_path, self.ledger_path(), now=NOW, expires=EXPIRES
        )
        broker.apply_batch(
            outcome.capability_id,
            outcome.token,
            [{"path": "DemoProject/Scripts/Foo.cs", "content": "var score = 1;\n"}],
            now=NOW,
        )
        with self.assertRaises(BrokerError) as caught:
            broker.authorize_batch(
                self.plan_path, self.ledger_path(), now=NOW, expires=EXPIRES
            )
        self.assertEqual(
            "reconcile_required_before_next_batch", caught.exception.reason
        )

        diff_path = self.work / "parent.diff"
        diff_path.write_text(CLEAN_DIFF, encoding="utf-8")
        envelope_path = kit.write_json(
            self.work, "envelope.json", self.envelope
        )
        post_ledger = self.ledger_path(
            with_mutation=True, name="post_ledger.json"
        )
        result = broker.reconcile_batch(
            self.plan_path,
            post_ledger,
            diff_path,
            repo_root=self.repo,
            ruleset_path=kit.ruleset_path(self.repo),
            task_envelope_path=envelope_path,
        )
        self.assertEqual("pass", result["decision"])
        second = broker.authorize_batch(
            self.plan_path, post_ledger, now=NOW, expires=EXPIRES
        )
        self.assertEqual(
            "authoritative", second.result["enforcement_mode"]
        )
        self.assertEqual(
            1, second.result["authorization"]["mutation_generation"]
        )


if __name__ == "__main__":
    unittest.main()

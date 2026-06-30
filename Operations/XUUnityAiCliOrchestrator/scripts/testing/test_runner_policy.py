import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "templates"))

import runner


class RunnerPolicyTests(unittest.TestCase):
    def test_writes_require_task_config_and_runtime_flag(self):
        self.assertFalse(
            runner.strict_capability_allowed(
                task_value="allowed",
                config_value=False,
                explicit_flag=False,
            )
        )
        self.assertFalse(
            runner.strict_capability_allowed(
                task_value="allowed",
                config_value=True,
                explicit_flag=False,
            )
        )
        self.assertFalse(
            runner.strict_capability_allowed(
                task_value="allowed",
                config_value=False,
                explicit_flag=True,
            )
        )
        self.assertTrue(
            runner.strict_capability_allowed(
                task_value="allowed",
                config_value=True,
                explicit_flag=True,
            )
        )
        self.assertFalse(
            runner.strict_capability_allowed(
                task_value="forbidden",
                config_value=True,
                explicit_flag=True,
            )
        )

    def test_default_config_validates(self):
        runner.validate_config(runner.DEFAULT_CONFIG)

    def test_proof_gate_rejects_ready_status_without_proofs(self):
        provider = {
            "id": "claude_cli",
            "kind": "subscription_cli",
            "enabled": True,
            "authMode": "official_oauth_login",
            "costMode": "subscription_quota",
            "apiKeyAuthAllowed": False,
            "command": "claude",
        }
        status = runner.ProviderStatus(
            provider_id="claude_cli",
            status="ready",
            ready=True,
        )
        adapter = runner.adapter_for(provider)

        self.assertFalse(
            runner.provider_proof_gate_passes(
                provider,
                status,
                adapter,
                allow_writes=False,
            )
        )

    def test_proof_gate_accepts_subscription_login_and_enforced_access(self):
        provider = {
            "id": "claude_cli",
            "kind": "subscription_cli",
            "enabled": True,
            "authMode": "official_oauth_login",
            "costMode": "subscription_quota",
            "apiKeyAuthAllowed": False,
            "command": "claude",
        }
        status = runner.ProviderStatus(
            provider_id="claude_cli",
            status="ready",
            ready=True,
            auth_proof="official_subscription_login",
            billing_proof="subscription_quota",
            access_proof="cli_tool_permissions_supported",
            model_proof="resolved_model",
        )
        adapter = runner.adapter_for(provider)

        self.assertTrue(
            runner.provider_proof_gate_passes(
                provider,
                status,
                adapter,
                allow_writes=False,
            )
        )

    def test_policy_prompt_requires_worker_report_contract(self):
        prompt = runner.compose_policy_prompt(
            prompt_text="external_ai: allowed\n\nRun the delegated task.",
            project_root=Path("/tmp/example-project"),
            allow_web=False,
            allow_writes=False,
            allow_api_billing=False,
        )

        self.assertIn("The external AI worker owns task execution", prompt)
        self.assertIn("evidence collection", prompt)
        self.assertIn("artifact interpretation", prompt)
        self.assertIn("worker_status", prompt)
        self.assertIn("doubts_or_escalation", prompt)


if __name__ == "__main__":
    unittest.main()

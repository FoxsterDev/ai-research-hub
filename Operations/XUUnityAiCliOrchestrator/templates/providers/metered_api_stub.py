from __future__ import annotations

from pathlib import Path

from providers.provider_contract import ProviderAdapter, ProviderStatus, RunResult


class MeteredApiStubAdapter(ProviderAdapter):
    provider_id = "metered_api_stub"

    def doctor(self) -> ProviderStatus:
        enabled = bool(self.config.get("enabled", False))
        budget = self.config.get("budgetPolicy") or {}
        has_budget = bool(budget.get("required")) and bool(budget.get("maxRunUsd"))
        ready = enabled and has_budget
        return ProviderStatus(
            provider_id=self.provider_id,
            status="disabled" if not enabled else ("ready" if ready else "invalid"),
            ready=ready,
            reason=(
                "metered API providers are future extension points and are disabled by default"
                if not enabled
                else "metered API provider requires an explicit budget cap"
                if not has_budget
                else "metered API provider is explicitly enabled and budget-capped"
            ),
            auth_mode=str(self.config.get("authMode") or "api_credentials"),
            cost_mode=str(self.config.get("costMode") or "metered_paid"),
            capabilities=["xuunity.ai_cli.metered_paid_budget_cap"],
        )

    def run_prompt(
        self,
        *,
        prompt: str,
        project_root: Path,
        model: str,
        allow_web: bool,
        allow_writes: bool,
        timeout_seconds: int,
    ) -> RunResult:
        return RunResult(
            provider_id=self.provider_id,
            external_ai_status="unavailable",
            model=model,
            return_code=64,
            stdout="",
            stderr="metered API execution is not implemented in v1",
            command=[],
        )


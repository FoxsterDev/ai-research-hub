from __future__ import annotations

import subprocess
from pathlib import Path

from providers.provider_contract import (
    ProviderAdapter,
    ProviderStatus,
    RunResult,
    api_key_env_present,
    command_from_template,
    find_command,
    run_auth_probe,
    safe_subprocess_env,
)


class AntigravityAdapter(ProviderAdapter):
    provider_id = "antigravity"

    def can_enforce_access(self, allow_writes: bool) -> bool:
        return bool(self.config.get("accessPolicyCommand"))

    def doctor(self) -> ProviderStatus:
        command = find_command(self.command_name)
        warnings: list[str] = []
        api_env = api_key_env_present()
        if api_env:
            warnings.append(
                "API-key environment variables are present but ignored for Antigravity account-login runs."
            )

        if not command:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="unavailable",
                ready=False,
                reason="Antigravity CLI entrypoint was not found on PATH",
                command=self.command_name,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        auth_status_command = self.config.get("authStatusCommand")
        if auth_status_command:
            ok, output = run_auth_probe(
                provider_id=self.provider_id,
                command=[str(item) for item in auth_status_command],
            )
            if not ok:
                return ProviderStatus(
                    provider_id=self.provider_id,
                    status="unauthenticated",
                    ready=False,
                    reason=output or "official Antigravity account probe failed",
                    command=command,
                    auth_mode=self.auth_mode,
                    cost_mode=self.cost_mode,
                    warnings=warnings,
                    capabilities=self.base_capabilities(),
                )
        else:
            warnings.append("authStatusCommand is not configured.")
            return ProviderStatus(
                provider_id=self.provider_id,
                status="degraded",
                ready=False,
                reason=(
                    "Antigravity CLI entrypoint is present, but official account-login "
                    "readiness cannot be confirmed until authStatusCommand is configured."
                ),
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        if not self.config.get("runArgs"):
            return ProviderStatus(
                provider_id=self.provider_id,
                status="degraded",
                ready=False,
                reason="Antigravity command exists, but non-interactive prompt run args are not configured.",
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        return ProviderStatus(
            provider_id=self.provider_id,
            status="degraded",
            ready=False,
            reason=(
                "Antigravity CLI and run args are configured, but provider is not selectable "
                "until accessPolicyCommand proves read/write enforcement."
            ),
            command=command,
            auth_mode=self.auth_mode,
            cost_mode=self.cost_mode,
            model=self.resolve_model("best_available"),
            auth_proof="official_subscription_login",
            billing_proof="subscription_or_account_quota",
            access_proof="not_proven",
            model_proof="resolved_model",
            warnings=warnings,
            capabilities=self.base_capabilities()
            + ["xuunity.ai_cli.provider.antigravity", "xuunity.ai_cli.best_available_model"],
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
        command = find_command(self.command_name) or self.command_name
        resolved_model = self.resolve_model(model)
        run_args = self.config.get("runArgs") or []
        args = [command, *command_from_template([str(item) for item in run_args], prompt, resolved_model)]

        try:
            completed = subprocess.run(
                args,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=safe_subprocess_env(self.provider_id),
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                provider_id=self.provider_id,
                external_ai_status="timeout",
                model=resolved_model,
                return_code=124,
                stdout=exc.stdout or "",
                stderr=f"Antigravity CLI run timed out after {timeout_seconds}s",
                command=args,
            )

        return RunResult(
            provider_id=self.provider_id,
            external_ai_status="completed" if completed.returncode == 0 else "failed",
            model=resolved_model,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=args,
        )

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from providers.provider_contract import (
    ProviderAdapter,
    ProviderStatus,
    RunResult,
    api_key_env_present,
    find_command,
    safe_subprocess_env,
)


ACCEPTED_SUBSCRIPTION_TYPES = {"pro", "team", "max", "enterprise"}


class ClaudeCliAdapter(ProviderAdapter):
    provider_id = "claude_cli"

    def can_enforce_access(self, allow_writes: bool) -> bool:
        return True

    def doctor(self) -> ProviderStatus:
        command = find_command(self.command_name)
        warnings: list[str] = []
        api_env = api_key_env_present()
        if api_env:
            warnings.append(
                "API-key environment variables are present but ignored for Claude subscription CLI runs."
            )

        if not command:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="unavailable",
                ready=False,
                reason="claude CLI was not found on PATH",
                command=self.command_name,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        try:
            completed = subprocess.run(
                [command, "auth", "status", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20,
                check=False,
                env=safe_subprocess_env(self.provider_id),
            )
        except subprocess.TimeoutExpired:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="timeout",
                ready=False,
                reason="Claude auth status timed out",
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        if completed.returncode != 0:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="unauthenticated",
                ready=False,
                reason="official Claude login is missing or not ready; run: claude auth login --claudeai",
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        account_hint = ""
        try:
            payload = json.loads(completed.stdout or "{}")
            logged_in = bool(payload.get("loggedIn"))
            auth_method = str(payload.get("authMethod") or payload.get("loginMethod") or "").lower()
            api_provider = str(payload.get("apiProvider") or "").lower()
            subscription_type = str(payload.get("subscriptionType") or "").lower()
            account_hint = subscription_type or str(payload.get("orgName") or payload.get("account") or "")
        except json.JSONDecodeError:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="degraded",
                ready=False,
                reason="Claude auth status returned non-JSON output",
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        if not logged_in:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="unauthenticated",
                ready=False,
                reason="Claude CLI is not logged in with official Claude account auth",
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        if auth_method != "claude.ai" or api_provider != "firstparty":
            return ProviderStatus(
                provider_id=self.provider_id,
                status="degraded",
                ready=False,
                reason=(
                    "Claude auth is present but is not proven official claude.ai first-party "
                    f"subscription auth (authMethod={auth_method or 'unknown'}, "
                    f"apiProvider={api_provider or 'unknown'})."
                ),
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        accepted = {
            str(item).lower()
            for item in self.config.get("acceptedSubscriptionTypes", ACCEPTED_SUBSCRIPTION_TYPES)
        }
        if subscription_type not in accepted:
            return ProviderStatus(
                provider_id=self.provider_id,
                status="degraded",
                ready=False,
                reason=(
                    "Claude auth is official, but subscription quota type is not proven "
                    f"(subscriptionType={subscription_type or 'unknown'})."
                ),
                command=command,
                auth_mode=self.auth_mode,
                cost_mode=self.cost_mode,
                warnings=warnings,
                capabilities=self.base_capabilities(),
            )

        return ProviderStatus(
            provider_id=self.provider_id,
            status="ready",
            ready=True,
            reason=account_hint or "official Claude login is ready",
            command=command,
            auth_mode=self.auth_mode,
            cost_mode=self.cost_mode,
            model=self.resolve_model("best_available"),
            auth_proof="official_subscription_login",
            billing_proof="subscription_quota",
            access_proof="cli_tool_permissions_supported",
            model_proof="resolved_model",
            warnings=warnings,
            capabilities=self.base_capabilities()
            + ["xuunity.ai_cli.provider.claude_cli", "xuunity.ai_cli.best_available_model"],
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

        args: list[str] = [
            command,
            "-p",
            prompt,
            "--model",
            resolved_model,
            "--permission-mode",
            str(self.config.get("permissionMode") or "bypassPermissions"),
            "--allowedTools",
            "Read",
            "Glob",
            "Grep",
            "LS",
            "Bash(pwd)",
            "Bash(date)",
            "Bash(ls *)",
            "Bash(find . -maxdepth *)",
            "Bash(git status*)",
            "Bash(git diff*)",
            "Bash(git log*)",
            "Bash(git branch*)",
            "Bash(git rev-parse*)",
        ]

        if allow_web:
            args.extend(["WebSearch", "WebFetch"])

        if allow_writes:
            args.extend(["Edit", "Write", "MultiEdit"])

        disallowed = [
            "NotebookEdit",
            "Bash(rm *)",
            "Bash(mv *)",
            "Bash(cp *)",
            "Bash(chmod *)",
            "Bash(chown *)",
            "Bash(sudo *)",
            "Bash(curl *)",
            "Bash(wget *)",
            "Bash(ssh *)",
            "Bash(security *)",
        ]
        if not allow_writes:
            disallowed.extend(["Edit", "Write", "MultiEdit"])
        if not allow_web:
            disallowed.extend(["WebSearch", "WebFetch"])

        args.extend(["--disallowedTools", *disallowed])

        max_budget = str(self.config.get("maxRunUsd") or "").strip()
        if max_budget:
            args.extend(["--max-budget-usd", max_budget])

        args.extend(["--no-session-persistence", "--output-format", "json"])

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
                stderr=f"Claude CLI run timed out after {timeout_seconds}s",
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

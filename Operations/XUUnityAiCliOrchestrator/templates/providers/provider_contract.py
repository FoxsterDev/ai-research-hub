from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


API_KEY_ENV_NAMES = {
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_API_KEY",
    "OPENAI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
}


@dataclass
class ProviderStatus:
    provider_id: str
    status: str
    ready: bool
    reason: str = ""
    command: str = ""
    auth_mode: str = ""
    cost_mode: str = ""
    model: str = ""
    auth_proof: str = "not_proven"
    billing_proof: str = "not_proven"
    access_proof: str = "not_proven"
    model_proof: str = "not_proven"
    warnings: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "ready": self.ready,
            "reason": self.reason,
            "command": self.command,
            "auth_mode": self.auth_mode,
            "cost_mode": self.cost_mode,
            "model": self.model,
            "auth_proof": self.auth_proof,
            "billing_proof": self.billing_proof,
            "access_proof": self.access_proof,
            "model_proof": self.model_proof,
            "warnings": self.warnings,
            "capabilities": self.capabilities,
        }


@dataclass
class RunResult:
    provider_id: str
    external_ai_status: str
    model: str
    return_code: int
    stdout: str
    stderr: str
    command: list[str]
    report_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "external_ai_status": self.external_ai_status,
            "model": self.model,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "command": self.command,
            "report_path": self.report_path,
        }


class ProviderAdapter:
    provider_id = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @property
    def command_name(self) -> str:
        return str(self.config.get("command") or self.provider_id)

    @property
    def auth_mode(self) -> str:
        return str(self.config.get("authMode") or "")

    @property
    def cost_mode(self) -> str:
        return str(self.config.get("costMode") or "")

    @property
    def api_key_auth_allowed(self) -> bool:
        return bool(self.config.get("apiKeyAuthAllowed", False))

    def doctor(self) -> ProviderStatus:
        raise NotImplementedError

    def resolve_model(self, requested_model: str) -> str:
        if requested_model and requested_model != "best_available":
            return requested_model
        policy = self.config.get("modelPolicy") or {}
        default = str(policy.get("default") or "").strip()
        if default and default != "best_available":
            return default
        fallbacks = policy.get("fallbacks") or []
        if fallbacks:
            return str(fallbacks[0])
        return "best_available"

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
        raise NotImplementedError

    def can_enforce_access(self, allow_writes: bool) -> bool:
        return False

    def base_capabilities(self) -> list[str]:
        return [
            "xuunity.ai_cli.prompt_run",
            "xuunity.ai_cli.project_readonly",
            "xuunity.ai_cli.subscription_quota",
        ]


def find_command(command_name: str) -> str:
    return shutil.which(command_name) or ""


def configured_command(config: dict[str, Any]) -> str:
    return str(config.get("command") or config.get("id") or "")


def api_key_env_present(env: dict[str, str] | None = None) -> list[str]:
    source = env if env is not None else os.environ
    return sorted(name for name in API_KEY_ENV_NAMES if source.get(name))


def safe_subprocess_env(provider_id: str) -> dict[str, str]:
    env = dict(os.environ)
    for name in API_KEY_ENV_NAMES:
        env.pop(name, None)
    env["XUUNITY_AI_CLI_ORCHESTRATOR_PROVIDER"] = provider_id
    env["XUUNITY_AI_CLI_ORCHESTRATOR_AUTH_POLICY"] = "official_login_only"
    return env


def run_checked_json(command: list[str], timeout_seconds: int = 20) -> tuple[bool, dict[str, Any] | None, str]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=safe_subprocess_env("doctor"),
        )
    except subprocess.TimeoutExpired:
        return False, None, f"command timed out after {timeout_seconds}s"
    text = completed.stdout.strip() or completed.stderr.strip()
    if completed.returncode != 0:
        return False, None, text
    try:
        return True, json.loads(completed.stdout), text
    except json.JSONDecodeError:
        return True, None, text


def run_auth_probe(
    *,
    provider_id: str,
    command: list[str],
    timeout_seconds: int = 20,
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=safe_subprocess_env(provider_id),
        )
    except subprocess.TimeoutExpired:
        return False, f"auth probe timed out after {timeout_seconds}s"
    output = (completed.stdout.strip() or completed.stderr.strip()).strip()
    return completed.returncode == 0, output


def command_from_template(items: list[str], prompt: str, model: str) -> list[str]:
    return [
        str(item)
        .replace("{prompt}", prompt)
        .replace("{model}", model)
        for item in items
    ]

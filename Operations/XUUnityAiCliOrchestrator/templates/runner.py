#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from providers.antigravity import AntigravityAdapter
from providers.claude_cli import ClaudeCliAdapter
from providers.gemini_cli import GeminiCliAdapter
from providers.metered_api_stub import MeteredApiStubAdapter
from providers.provider_contract import ProviderAdapter, ProviderStatus

SCHEMA_VERSION = "xuunity.ai-cli-orchestrator.config.v1"
RESULT_SCHEMA_VERSION = "xuunity.ai-cli-orchestrator.result.v1"
DELEGATION_MODES = {"auto_phased", "single_run", "phase_plan_only"}
WORKER_REPORT_CONTRACT = [
    "Delegation contract:",
    "The external AI worker owns task execution, evidence collection, first-pass interpretation, and the final worker report.",
    "Spend provider context on the noisy work: inspect relevant project files, run allowed project commands, read generated artifacts/logs, and compress the result into decision-grade evidence.",
    "Return one final report with: worker_status, task_status, phase_plan, phase_results, actions_taken, evidence, artifacts, workspace_side_effects, interpretation, and doubts_or_escalation.",
    "If blocked or inconclusive, report the exact blocked command, tool, path, or missing evidence.",
    "Do not leave routine evidence collection or artifact interpretation to the caller.",
]
PHASED_DELEGATION_CONTRACT = [
    "Phased delegation contract:",
    "For broad, risky, or long-running tasks, split the work into small phases before deep execution.",
    "Each phase must have an objective, allowed actions, expected evidence, exit criteria, and a timeout budget.",
    "Finish and report useful phase evidence before starting the next phase.",
    "Stop early when the goal is achieved, the next phase would exceed policy, or evidence becomes inconclusive.",
    "Prefer several short bounded phases over one opaque long run.",
]

CLAUDE_SELECTOR_RE = re.compile(
    r"(?i)(?:\bvia\s+claude\b|\bwith\s+claude\b|\buse\s+claude\b|\bthrough\s+claude\b|"
    r"\busing\s+claude\b|через\s+claude\b|с\s+claude\b)"
)

ADAPTERS = {
    "claude_cli": ClaudeCliAdapter,
    "gemini_cli": GeminiCliAdapter,
    "antigravity": AntigravityAdapter,
    "metered_api_stub": MeteredApiStubAdapter,
}

DEFAULT_CONFIG = {
    "schemaVersion": SCHEMA_VERSION,
    "defaultPolicy": {
        "enabled": True,
        "priority": "subscription_quota_first",
        "authPolicy": "official_login_only",
        "providerPreference": ["claude_cli", "gemini_cli", "antigravity"],
        "modelPreference": "best_available",
        "allowApiBilling": False,
        "allowWeb": False,
        "allowWrites": False,
        "delegationMode": "auto_phased",
        "maxPhaseCount": 6,
        "maxPhaseSeconds": 600,
    },
    "providers": [
        {
            "id": "claude_cli",
            "kind": "subscription_cli",
            "enabled": True,
            "authMode": "official_oauth_login",
            "costMode": "subscription_quota",
            "apiKeyAuthAllowed": False,
            "command": "claude",
            "modelPolicy": {"default": "best_available", "fallbacks": ["opus"]},
            "acceptedSubscriptionTypes": ["pro", "team", "max", "enterprise"],
        },
        {
            "id": "gemini_cli",
            "kind": "subscription_cli",
            "enabled": True,
            "authMode": "official_google_login",
            "costMode": "subscription_quota",
            "apiKeyAuthAllowed": False,
            "command": "gemini",
            "modelPolicy": {"default": "best_available"},
            "runArgs": ["-p", "{prompt}"],
        },
        {
            "id": "antigravity",
            "kind": "subscription_cli",
            "enabled": True,
            "authMode": "official_google_account_login",
            "costMode": "subscription_or_account_quota",
            "apiKeyAuthAllowed": False,
            "command": "antigravity",
            "modelPolicy": {"default": "best_available"},
        },
        {
            "id": "metered_api_stub",
            "kind": "metered_api",
            "enabled": False,
            "costMode": "metered_paid",
            "requiresExplicitOptIn": True,
            "budgetPolicy": {"required": True, "maxRunUsd": 1.0},
        },
    ],
}


@dataclass
class PromptControl:
    external_ai_allowed: bool
    provider: str = ""
    model: str = "best_available"
    auth_policy: str = ""
    api_billing: str = "forbidden"
    web: str = "forbidden"
    writes: str = "forbidden"
    delegation_mode: str = ""
    max_phases: int = 0
    max_phase_seconds: int = 0


def config_path() -> Path:
    explicit = os.environ.get("XUUNITY_AI_CLI_ORCHESTRATOR_CONFIG")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".xuunity" / "ai-cli-orchestrator" / "config.json"


def report_root() -> Path:
    explicit = os.environ.get("XUUNITY_AI_CLI_ORCHESTRATOR_REPORT_ROOT")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".xuunity" / "ai-cli-orchestrator" / "runs"


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_config(payload)
    return payload


def validate_config(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schemaVersion: {payload.get('schemaVersion')}")
    default_policy = payload.get("defaultPolicy") or {}
    if default_policy.get("priority") != "subscription_quota_first":
        raise ValueError("defaultPolicy.priority must be subscription_quota_first")
    if default_policy.get("authPolicy") != "official_login_only":
        raise ValueError("defaultPolicy.authPolicy must be official_login_only")
    delegation_mode = default_policy.get("delegationMode")
    if delegation_mode and normalize_delegation_mode(str(delegation_mode), "") not in DELEGATION_MODES:
        raise ValueError("defaultPolicy.delegationMode must be auto_phased, single_run, or phase_plan_only")
    for field_name in ("maxPhaseCount", "maxPhaseSeconds"):
        if field_name in default_policy and parse_positive_int(str(default_policy.get(field_name))) <= 0:
            raise ValueError(f"defaultPolicy.{field_name} must be a positive integer")

    for provider in payload.get("providers") or []:
        provider_id = provider.get("id")
        kind = provider.get("kind")
        if kind == "subscription_cli" and provider.get("apiKeyAuthAllowed") is not False:
            raise ValueError(f"{provider_id}: subscription providers must set apiKeyAuthAllowed=false")
        if provider_id in {"claude_cli", "gemini_cli", "antigravity"}:
            if provider.get("costMode") not in {"subscription_quota", "subscription_or_account_quota"}:
                raise ValueError(f"{provider_id}: costMode must use subscription quota")
            if str(provider.get("authMode") or "").startswith("api"):
                raise ValueError(f"{provider_id}: API-key auth mode is not allowed")
        if kind == "metered_api" and provider.get("enabled"):
            budget = provider.get("budgetPolicy") or {}
            if not budget.get("required") or not budget.get("maxRunUsd"):
                raise ValueError(f"{provider_id}: enabled metered API providers require a budget cap")


def write_default_config(path: Path) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle, indent=2)
        handle.write("\n")
    return True


def parse_boolish_allowed(value: str) -> bool:
    return value.strip().lower() in {"allowed", "allow", "true", "yes", "1"}


def parse_positive_int(value: str, default: int = 0) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def normalize_delegation_mode(value: str, default: str = "auto_phased") -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    return normalized if normalized in DELEGATION_MODES else default


def parse_prompt_control(text: str) -> PromptControl:
    lines = text.splitlines()
    metadata_lines: list[str] = []
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            metadata_lines.append(line)
    else:
        metadata_lines = lines[:80]

    control = PromptControl(external_ai_allowed=False)
    selector_text = "\n".join(lines[:80])
    if CLAUDE_SELECTOR_RE.search(selector_text):
        control.external_ai_allowed = True
        control.provider = "claude_cli"

    in_external_block = False
    external_indent = 0

    for raw_line in metadata_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped.startswith("external_ai:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                control.external_ai_allowed = parse_boolish_allowed(value)
                in_external_block = False
            else:
                control.external_ai_allowed = True
                in_external_block = True
                external_indent = indent
            continue
        if in_external_block:
            if indent <= external_indent:
                in_external_block = False
                continue
            if ":" not in stripped:
                continue
            key, value = [part.strip() for part in stripped.split(":", 1)]
            value = value.strip("\"'")
            normalized_key = key.lower().replace("_", "")
            if normalized_key == "provider":
                control.provider = value
            elif normalized_key == "model":
                control.model = value or "best_available"
            elif normalized_key == "authpolicy":
                control.auth_policy = value
            elif normalized_key == "apibilling":
                control.api_billing = value or "forbidden"
            elif normalized_key == "web":
                control.web = value or "forbidden"
            elif normalized_key in {"writes", "write"}:
                control.writes = value or "forbidden"
            elif normalized_key in {"delegationmode", "executionmode", "phasemode"}:
                control.delegation_mode = normalize_delegation_mode(value, "")
            elif normalized_key in {"maxphases", "maxphasecount"}:
                control.max_phases = parse_positive_int(value)
            elif normalized_key in {"maxphaseseconds", "phasetimeoutseconds"}:
                control.max_phase_seconds = parse_positive_int(value)

    return control


def load_prompt_control(prompt_file: Path) -> PromptControl:
    return parse_prompt_control(prompt_file.read_text(encoding="utf-8"))


def adapter_for(provider_config: dict[str, Any]) -> ProviderAdapter:
    provider_id = str(provider_config.get("id") or "")
    adapter_type = ADAPTERS.get(provider_id)
    if adapter_type is None and provider_config.get("kind") == "metered_api":
        adapter_type = MeteredApiStubAdapter
    if adapter_type is None:
        raise ValueError(f"No adapter registered for provider: {provider_id}")
    return adapter_type(provider_config)


def providers_by_id(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(provider.get("id")): provider for provider in config.get("providers") or []}


def provider_statuses(config: dict[str, Any]) -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    for provider in config.get("providers") or []:
        provider_id = str(provider.get("id") or "")
        if not provider.get("enabled", False):
            statuses.append(
                ProviderStatus(
                    provider_id=provider_id,
                    status="disabled",
                    ready=False,
                    reason="provider is disabled in config",
                    auth_mode=str(provider.get("authMode") or ""),
                    cost_mode=str(provider.get("costMode") or ""),
                )
            )
            continue
        try:
            statuses.append(adapter_for(provider).doctor())
        except Exception as exc:
            statuses.append(
                ProviderStatus(
                    provider_id=provider_id,
                    status="error",
                    ready=False,
                    reason=str(exc),
                    auth_mode=str(provider.get("authMode") or ""),
                    cost_mode=str(provider.get("costMode") or ""),
                )
            )
    return statuses


def choose_provider(
    config: dict[str, Any],
    control: PromptControl,
    *,
    requested_provider: str,
    allow_api_billing: bool,
    allow_writes: bool,
) -> tuple[ProviderAdapter | None, ProviderStatus | None, list[ProviderStatus]]:
    by_id = providers_by_id(config)
    default_policy = config.get("defaultPolicy") or {}
    preference = [str(item) for item in default_policy.get("providerPreference") or []]
    provider_order = [requested_provider or control.provider] if (requested_provider or control.provider) else preference
    provider_order = [item for item in provider_order if item]

    all_statuses = provider_statuses(config)
    status_by_id = {status.provider_id: status for status in all_statuses}

    for provider_id in provider_order:
        provider = by_id.get(provider_id)
        if not provider:
            continue
        if provider.get("kind") == "metered_api" and not allow_api_billing:
            continue
        status = status_by_id.get(provider_id)
        if status and status.ready:
            adapter = adapter_for(provider)
            if provider_proof_gate_passes(provider, status, adapter, allow_writes=allow_writes):
                return adapter, status, all_statuses
    return None, None, all_statuses


def provider_proof_gate_passes(
    provider: dict[str, Any],
    status: ProviderStatus,
    adapter: ProviderAdapter,
    *,
    allow_writes: bool,
) -> bool:
    kind = provider.get("kind")
    if kind == "subscription_cli":
        if status.auth_proof != "official_subscription_login":
            return False
        if status.billing_proof not in {"subscription_quota", "subscription_or_account_quota"}:
            return False
        if status.model_proof != "resolved_model":
            return False
        if not adapter.can_enforce_access(allow_writes):
            return False
        return True

    if kind == "metered_api":
        budget = provider.get("budgetPolicy") or {}
        return bool(provider.get("enabled")) and bool(budget.get("required")) and bool(budget.get("maxRunUsd"))

    return False


def project_root_allowed(project_root: Path) -> tuple[bool, str]:
    expanded = project_root.expanduser()
    if not expanded.is_absolute():
        return False, "Project root must be absolute"

    root = expanded.resolve()
    home = Path.home().resolve()
    blocked = {
        home,
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "Library" / "Mobile Documents",
    }
    if root in blocked:
        return False, f"Refusing unattended external AI run from broad personal folder: {root}"
    if not root.is_dir():
        return False, f"Project root does not exist: {root}"
    return True, ""


def compose_policy_prompt(
    *,
    prompt_text: str,
    project_root: Path,
    allow_web: bool,
    allow_writes: bool,
    allow_api_billing: bool,
    delegation_mode: str = "auto_phased",
    max_phase_count: int = 6,
    max_phase_seconds: int = 600,
) -> str:
    normalized_delegation_mode = normalize_delegation_mode(delegation_mode)
    rules = [
        "You are running under XUUnityAiCliOrchestrator.",
        f"Project root: {project_root}",
        "Use the provider's official account login or OAuth session only.",
        "Do not use or ask for model API keys.",
        "Do not read personal folders outside the project root.",
        f"Delegation mode: {normalized_delegation_mode}.",
        f"Maximum phases: {max_phase_count}.",
        f"Maximum seconds per phase: {max_phase_seconds}.",
        *WORKER_REPORT_CONTRACT,
    ]
    if normalized_delegation_mode == "auto_phased":
        rules.extend(PHASED_DELEGATION_CONTRACT)
    elif normalized_delegation_mode == "phase_plan_only":
        rules.extend(PHASED_DELEGATION_CONTRACT)
        rules.append("Return the phase plan only; do not execute the planned phases.")
    else:
        rules.append("Use a single bounded run only when the task is already small enough.")
    if not allow_writes:
        rules.append("Do not modify files, create branches, commit, push, tag, or stash.")
    if not allow_web:
        rules.append("Do not use web access unless the provider blocks it at the tool level.")
    if not allow_api_billing:
        rules.append("Do not use metered API billing.")
    return "\n".join(rules) + "\n\n--- TASK PROMPT ---\n\n" + prompt_text


def optional_capability_allowed(
    *,
    task_value: str,
    config_value: bool,
    explicit_flag: bool,
) -> bool:
    return parse_boolish_allowed(task_value) and (config_value or explicit_flag)


def strict_capability_allowed(
    *,
    task_value: str,
    config_value: bool,
    explicit_flag: bool,
) -> bool:
    return parse_boolish_allowed(task_value) and config_value and explicit_flag


def render_json(payload: dict[str, Any], pretty: bool = True) -> str:
    return json.dumps(payload, indent=2 if pretty else None, sort_keys=False)


def print_human_status(payload: dict[str, Any]) -> None:
    print(f"Config: {payload.get('config_path')}")
    for provider in payload.get("providers", []):
        ready = "ready" if provider.get("ready") else provider.get("status")
        print(f"- {provider.get('provider_id')}: {ready} ({provider.get('reason')})")


def run_init(args: argparse.Namespace) -> int:
    path = Path(args.config_path).expanduser() if args.config_path else config_path()
    created = write_default_config(path)
    print("Created config:" if created else "Config already exists:", path)
    print("Run doctor:")
    print("  bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh doctor")
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    path = Path(args.config_path).expanduser() if args.config_path else config_path()
    config = load_config(path)
    payload = {
        "schemaVersion": "xuunity.ai-cli-orchestrator.doctor.v1",
        "config_path": str(path),
        "defaultPolicy": config.get("defaultPolicy") or {},
        "providers": [status.to_dict() for status in provider_statuses(config)],
    }
    if args.json:
        print(render_json(payload))
    else:
        print_human_status(payload)
    return 0


def run_providers(args: argparse.Namespace) -> int:
    return run_doctor(args)


def write_result(payload: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    root = report_root() / timestamp
    root.mkdir(parents=True, exist_ok=True)
    path = root / "result.json"
    path.write_text(render_json(payload) + "\n", encoding="utf-8")
    latest = report_root() / "latest"
    if latest.exists() or latest.is_symlink():
        if latest.is_dir() and not latest.is_symlink():
            shutil.rmtree(latest)
        else:
            latest.unlink()
    try:
        latest.symlink_to(root, target_is_directory=True)
    except OSError:
        pass
    return path


def run_prompt(args: argparse.Namespace) -> int:
    path = Path(args.config_path).expanduser() if args.config_path else config_path()
    config = load_config(path)
    default_policy = config.get("defaultPolicy") or {}

    project_root = Path(args.project_root).expanduser()
    ok, reason = project_root_allowed(project_root)
    if not ok:
        print(render_json({"external_ai_status": "blocked", "reason": reason}), file=sys.stderr)
        return 64
    project_root = project_root.resolve()

    prompt_file = Path(args.prompt_file).expanduser().resolve()
    if not prompt_file.is_file():
        print(render_json({"external_ai_status": "blocked", "reason": f"Prompt file not found: {prompt_file}"}), file=sys.stderr)
        return 66

    prompt_text = prompt_file.read_text(encoding="utf-8")
    control = parse_prompt_control(prompt_text)
    external_ai_allowed = control.external_ai_allowed or args.external_ai == "allowed"
    if not external_ai_allowed:
        payload = {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "external_ai_status": "not_allowed",
            "reason": "prompt did not opt in with external_ai: allowed",
            "prompt_file": str(prompt_file),
        }
        print(render_json(payload))
        return 0

    config_allow_api = bool(default_policy.get("allowApiBilling", False))
    api_billing_allowed = strict_capability_allowed(
        task_value=control.api_billing,
        config_value=config_allow_api,
        explicit_flag=bool(args.allow_api_billing),
    )
    web_allowed = optional_capability_allowed(
        task_value=control.web,
        config_value=bool(default_policy.get("allowWeb", False)),
        explicit_flag=bool(args.allow_web),
    )
    writes_allowed = strict_capability_allowed(
        task_value=control.writes,
        config_value=bool(default_policy.get("allowWrites", False)),
        explicit_flag=bool(args.allow_writes),
    )

    adapter, status, all_statuses = choose_provider(
        config,
        control,
        requested_provider=args.provider or "",
        allow_api_billing=api_billing_allowed,
        allow_writes=writes_allowed,
    )
    if not adapter or not status:
        payload = {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "external_ai_status": "unavailable",
            "reason": "no configured official-login subscription provider passed the proof gate",
            "proof_gate": {
                "auth_proof": "official_subscription_login",
                "billing_proof": "subscription_quota",
                "access_proof": "adapter_enforced",
                "model_proof": "resolved_model",
            },
            "providers": [item.to_dict() for item in all_statuses],
            "prompt_file": str(prompt_file),
            "project_root": str(project_root),
        }
        result_path = write_result(payload)
        payload["report_path"] = str(result_path)
        print(render_json(payload))
        return 0

    requested_model = args.model or control.model or str(default_policy.get("modelPreference") or "best_available")
    delegation_mode = normalize_delegation_mode(
        args.delegation_mode or control.delegation_mode or str(default_policy.get("delegationMode") or "auto_phased")
    )
    max_phase_count = (
        parse_positive_int(str(args.max_phases))
        or control.max_phases
        or parse_positive_int(str(default_policy.get("maxPhaseCount") or ""))
        or 6
    )
    max_phase_seconds = (
        parse_positive_int(str(args.max_phase_seconds))
        or control.max_phase_seconds
        or parse_positive_int(str(default_policy.get("maxPhaseSeconds") or ""))
        or 600
    )
    policy_prompt = compose_policy_prompt(
        prompt_text=prompt_text,
        project_root=project_root,
        allow_web=web_allowed,
        allow_writes=writes_allowed,
        allow_api_billing=api_billing_allowed,
        delegation_mode=delegation_mode,
        max_phase_count=max_phase_count,
        max_phase_seconds=max_phase_seconds,
    )

    try:
        result = adapter.run_prompt(
            prompt=policy_prompt,
            project_root=project_root,
            model=requested_model,
            allow_web=web_allowed,
            allow_writes=writes_allowed,
            timeout_seconds=int(args.timeout_seconds),
        )
    except Exception as exc:
        payload = {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "external_ai_status": "error",
            "selected_provider": adapter.provider_id,
            "selected_model": requested_model,
            "auth_policy": default_policy.get("authPolicy"),
            "cost_mode": status.cost_mode,
            "api_billing_allowed": api_billing_allowed,
            "web_allowed": web_allowed,
            "writes_allowed": writes_allowed,
            "proof_gate": {
                "auth_proof": status.auth_proof,
                "billing_proof": status.billing_proof,
                "access_proof": "write_enforced" if writes_allowed else "readonly_enforced",
                "model_proof": status.model_proof,
            },
            "project_root": str(project_root),
            "prompt_file": str(prompt_file),
            "delegation": {
                "mode": delegation_mode,
                "max_phase_count": max_phase_count,
                "max_phase_seconds": max_phase_seconds,
            },
            "provider_status": status.to_dict(),
            "error": str(exc),
        }
        result_path = write_result(payload)
        payload["report_path"] = str(result_path)
        print(render_json(payload))
        return 70

    payload = {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "external_ai_status": result.external_ai_status,
        "selected_provider": adapter.provider_id,
        "selected_model": result.model,
        "auth_policy": default_policy.get("authPolicy"),
        "cost_mode": status.cost_mode,
        "api_billing_allowed": api_billing_allowed,
        "web_allowed": web_allowed,
        "writes_allowed": writes_allowed,
        "proof_gate": {
            "auth_proof": status.auth_proof,
            "billing_proof": status.billing_proof,
            "access_proof": "write_enforced" if writes_allowed else "readonly_enforced",
            "model_proof": status.model_proof,
        },
        "project_root": str(project_root),
        "prompt_file": str(prompt_file),
        "delegation": {
            "mode": delegation_mode,
            "max_phase_count": max_phase_count,
            "max_phase_seconds": max_phase_seconds,
        },
        "provider_status": status.to_dict(),
        "result": result.to_dict(),
    }
    result_path = write_result(payload)
    payload["report_path"] = str(result_path)
    print(render_json(payload))
    return 0 if result.return_code == 0 else result.return_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XUUnity AI CLI Orchestrator")
    parser.add_argument("--config-path", default="", help="Override user-local config path.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create user-local config when missing.")
    init.add_argument("--config-path", default="", help="Override config path.")
    init.set_defaults(func=run_init)

    doctor = sub.add_parser("doctor", help="Check provider config and official-login readiness.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor.add_argument("--config-path", default="", help="Override config path.")
    doctor.set_defaults(func=run_doctor)

    providers = sub.add_parser("providers", help="List configured providers and readiness.")
    providers.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    providers.add_argument("--config-path", default="", help="Override config path.")
    providers.set_defaults(func=run_providers)

    run = sub.add_parser("run", help="Run an opted-in prompt through the best ready provider.")
    run.add_argument("--project-root", required=True, help="Absolute project root.")
    run.add_argument("--prompt-file", required=True, help="Prompt file with external_ai opt-in.")
    run.add_argument("--external-ai", choices=["allowed", "forbidden"], default="", help="Runtime opt-in override.")
    run.add_argument("--provider", default="", help="Provider override.")
    run.add_argument("--model", default="", help="Model override. Use best_available by default.")
    run.add_argument("--allow-web", action="store_true", help="Runtime web allowance; prompt must also allow it.")
    run.add_argument("--allow-writes", action="store_true", help="Runtime write allowance; prompt and config must also allow it.")
    run.add_argument("--allow-api-billing", action="store_true", help="Runtime API billing allowance; prompt and config must also allow it.")
    run.add_argument("--delegation-mode", choices=sorted(DELEGATION_MODES), default="", help="Task delegation shape.")
    run.add_argument("--max-phases", type=int, default=0, help="Maximum worker phases for auto_phased runs.")
    run.add_argument("--max-phase-seconds", type=int, default=0, help="Maximum seconds per worker phase.")
    run.add_argument("--timeout-seconds", type=int, default=1800, help="Provider subprocess timeout.")
    run.add_argument("--config-path", default="", help="Override config path.")
    run.set_defaults(func=run_prompt)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(render_json({"external_ai_status": "blocked", "reason": str(exc)}), file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

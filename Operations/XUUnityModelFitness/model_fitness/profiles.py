"""Installed CLI contracts. Supported auth stays subscription-only and explicit."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import xuunity_canonical as xc

from . import OPERATION_DIR, MODULE_SCRIPTS_DIR, isolation, records
from .contracts import require_valid

ENVIRONMENT_NAMES = ("HOME", "USER", "PATH", "TMPDIR", "TEMP", "TMP", "SystemRoot",
                     "COMSPEC", "PATHEXT", "LANG", "LC_ALL", "TZ", "CODEX_HOME")


def environment() -> tuple[dict[str, str], str]:
    values, _ = isolation.scrub_environment(dict(os.environ), list(ENVIRONMENT_NAMES))
    values["PYTHONDONTWRITEBYTECODE"] = "1"
    values["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    values["DISABLE_AUTOUPDATER"] = "1"
    identity = xc.domain_digest("xuunity.execution-environment.v1", {"values": values})
    return values, identity


def engine_identity() -> str:
    paths = sorted((OPERATION_DIR / "model_fitness").glob("*.py"))
    paths += sorted(MODULE_SCRIPTS_DIR.glob("*.py"))
    paths += sorted((OPERATION_DIR / "schemas").glob("*.json"))
    paths += sorted((MODULE_SCRIPTS_DIR.parent / "schemas").glob("*.json"))
    return xc.domain_digest("xuunity.fitness-engine.v1", {
        "files": {str(p.relative_to(OPERATION_DIR.parents[1])): xc.sha256_file(p)
                  for p in paths}
    })


def inspect(adapter: str, executable: Path, model: str, effort: str) -> dict[str, Any]:
    if adapter not in {"claude", "codex"} or not model or effort not in {"low", "medium", "high", "xhigh", "max"}:
        raise ValueError("unsupported adapter/model/effort")
    executable = Path(executable).resolve(strict=True)
    env, environment_hash = environment()
    version = subprocess.run([str(executable), "--version"], env=env,
                             capture_output=True, text=True, timeout=30, check=True)
    cli_version = version.stdout.strip()
    profile = {
        "schema_version": "xuunity.adapter-profile.v1",
        "adapter_id": adapter, "adapter_version": cli_version,
        "surface": f"{adapter}_cli", "event_schema_versions": [f"{adapter}_jsonl_v1"],
        "requested_model": model,
        "observed_model_identity": {"observable": adapter == "claude", "model": None,
                                    "provider_backend_revision": None},
        "inference_parameters": {"effort": effort}, "cwd_policy": "attempt_owned",
        "sandbox": "workspace-write" if adapter == "codex" else "claude_permissions_accept_edits",
        "permission_mode": "never" if adapter == "codex" else "acceptEdits",
        "approval_policy": "never" if adapter == "codex" else "deny_unapproved",
        "tools": ["codex_default"] if adapter == "codex" else ["Bash", "Edit", "Read", "Write"],
        "context_delivery_channels": ["stdin", "raw_tool_output", "runtime_context_unverified"],
        "mutator_coverage": "audited", "request_boundary_attestation": False,
        "read_namespace_policy_hash": None, "network_policy_hash": None,
        "environment_allowlist_hash": environment_hash, "broker_support": False,
    }
    profile = records.seal(profile, "profile_hash")
    require_valid("xuunity.adapter-profile.schema.json", profile, "adapter profile")
    return records.seal({
        "schema_version": "xuunity.installed-profile.v1", "profile": profile,
        "executable": str(executable), "executable_sha256": xc.sha256_file(executable),
        "parser_sha256": xc.sha256_file(OPERATION_DIR / "model_fitness/adapters.py"),
        "os": platform.system(), "architecture": platform.machine(),
        "boundary_limitations": ["request_boundary_unavailable", "read_namespace_unenforced",
                                 "provider_backend_revision_unobserved", "exclusive_write_broker_unavailable"]
                                + (["process_tree_cleanup_unavailable"] if os.name != "posix" else []),
    })


def verify(installed: dict[str, Any], *, check_executable: bool = True,
           check_environment: bool = True) -> None:
    records.verify(installed)
    profile = installed["profile"]
    records.verify(profile, "profile_hash")
    require_valid("xuunity.adapter-profile.schema.json", profile, "adapter profile")
    if profile["adapter_id"] not in {"claude", "codex"}:
        raise ValueError("adapter_unsupported")
    if profile["request_boundary_attestation"] or profile["broker_support"] or profile["mutator_coverage"] != "audited":
        raise ValueError("installed_cli_cannot_claim_authoritative_or_request_boundary")
    if installed["parser_sha256"] != xc.sha256_file(OPERATION_DIR / "model_fitness/adapters.py"):
        raise ValueError("installed_parser_changed")
    if check_executable and installed["executable_sha256"] != xc.sha256_file(Path(installed["executable"])):
        raise ValueError("installed_executable_changed")
    _, env_hash = environment()
    if check_environment and env_hash != profile["environment_allowlist_hash"]:
        raise ValueError("installed_environment_changed")


def command(installed: dict[str, Any], workspace: Path) -> tuple[list[str], dict[str, Any]]:
    profile = installed["profile"]
    adapter = profile["adapter_id"]
    executable = installed["executable"]
    effort = profile["inference_parameters"]["effort"]
    if adapter == "codex":
        argv = [executable, "exec", "--json", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--sandbox", "workspace-write", "--skip-git-repo-check",
                "-C", str(workspace), "--model", profile["requested_model"],
                "-c", f'model_reasoning_effort="{effort}"',
                "-c", 'approval_policy="never"', "--color", "never", "-"]
    else:
        argv = [executable, "-p", "--model", profile["requested_model"], "--effort", effort,
                "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
                "--tools", "Bash,Edit,Read,Write", "--setting-sources", "",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--no-chrome", "--no-session-persistence", "--disable-slash-commands"]
    return argv, {
        "adapter": adapter, "surface": profile["surface"],
        "adapter_cli_version": profile["adapter_version"],
        "mutation_coverage": "audited", "observable_model_identity": adapter == "claude",
        "expected_permission_mode": "acceptEdits" if adapter == "claude" else None,
        "expect_zero_permission_denials": True,
        "runtime_context_paths": ["AGENTS.md"] if adapter == "codex" else ["CLAUDE.md", "CLAUDE.local.md"],
        "request_boundary_attestation": False, "sandbox": profile["sandbox"],
    }


def subscription_status(installed: dict[str, Any]) -> dict[str, Any]:
    verify(installed)
    adapter = installed["profile"]["adapter_id"]
    arguments = [installed["executable"], *(["login", "status"] if adapter == "codex" else ["auth", "status"])]
    env, _ = environment()
    try:
        result = subprocess.run(arguments, env=env, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"ready": False, "reason": "subscription_status_timeout"}
    if adapter == "codex":
        ready = result.returncode == 0 and b"Logged in using ChatGPT" in result.stdout + result.stderr
    else:
        try:
            value = xc.strict_parse(result.stdout)
            ready = result.returncode == 0 and value.get("loggedIn") is True and value.get("authMethod") == "claude.ai" and value.get("subscriptionType") in {"pro", "max", "team", "enterprise"}
        except (ValueError, AttributeError):
            ready = False
    return {"ready": ready, "reason": "official_subscription" if ready else "subscription_login_unproven"}

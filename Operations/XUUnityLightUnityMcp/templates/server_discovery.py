from pathlib import Path
from typing import Any, Callable

TRANSPORT_METADATA_KEYS = (
    "transport_listener_state",
    "transport_host",
    "transport_port",
    "transport_publish_error",
)


def _copy_dict(payload: dict[str, Any] | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, dict) else {}


def _transport_metadata(bridge_state: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in TRANSPORT_METADATA_KEYS:
        value = bridge_state.get(key)
        if value is not None:
            metadata[key] = value
    return metadata


def _transport_state(
    *,
    bridge_state: dict[str, Any],
    active_transport: str,
    transport_requested: str,
    transport_metadata: dict[str, Any],
) -> dict[str, Any]:
    listener_state = str(transport_metadata.get("transport_listener_state") or "")
    host = str(transport_metadata.get("transport_host") or "")
    raw_port = transport_metadata.get("transport_port")
    try:
        port = int(raw_port) if raw_port is not None else 0
    except (TypeError, ValueError):
        port = 0
    publish_error = str(transport_metadata.get("transport_publish_error") or "")
    return {
        "selection_scope": "per_project_context",
        "requested_transport": transport_requested,
        "active_transport": active_transport,
        "listener_state": listener_state,
        "host": host,
        "port": port,
        "address": f"{host}:{port}" if host and port > 0 else "",
        "publish_error": publish_error,
        "ready": bool(active_transport and listener_state == "listening" and not publish_error),
        "metadata": dict(transport_metadata or {}),
        "fallback_transport_available": True,
        "bridge_state_transport": str(bridge_state.get("transport") or ""),
    }


def _state_groups(
    *,
    bridge_state: dict[str, Any],
    host_editor_session_state: dict[str, Any],
    discovery: dict[str, Any],
    transport_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "bridge_identity": {
            "bridge_version": int(bridge_state.get("bridge_version") or 0),
            "bridge_generation": int(bridge_state.get("bridge_generation") or 0),
            "bridge_session_id": str(bridge_state.get("bridge_session_id") or ""),
            "bridge_bootstrap_attached": bool(bridge_state.get("bridge_bootstrap_attached")),
        },
        "process_identity": {
            "bridge_pid": int(discovery.get("bridge_pid") or 0),
            "bridge_pid_alive": bool(discovery.get("bridge_pid_alive")),
            "bridge_pid_matches_project": bool(discovery.get("bridge_pid_matches_project")),
            "host_session_pid": int(discovery.get("host_session_pid") or 0),
            "host_session_pid_alive": bool(discovery.get("host_session_pid_alive")),
            "host_session_pid_matches_project": bool(discovery.get("host_session_pid_matches_project")),
            "detected_editor_count": int(discovery.get("detected_editor_count") or 0),
            "detected_editor_pids": list(discovery.get("detected_editor_pids") or []),
            "opened_by_host": bool(host_editor_session_state.get("opened_by_host")),
        },
        "transport": dict(transport_state or {}),
        "health": {
            "bridge_health_status": str(bridge_state.get("health_status") or ""),
            "host_health_classification": str(discovery.get("host_health_classification") or ""),
            "host_health_reason": str(discovery.get("host_health_reason") or ""),
            "host_health_recommended_next_action": str(discovery.get("host_health_recommended_next_action") or ""),
            "host_health_termination_policy": str(discovery.get("host_health_termination_policy") or ""),
            "host_health_heartbeat_age_seconds": discovery.get("host_health_heartbeat_age_seconds"),
            "host_health_busy_reason": str(discovery.get("host_health_busy_reason") or ""),
            "anr_classification": str(discovery.get("anr_classification") or ""),
        },
        "editor_state": {
            "unity_version": str(bridge_state.get("unity_version") or ""),
            "playmode_state": str(bridge_state.get("playmode_state") or ""),
            "is_playing": bool(bridge_state.get("is_playing")),
            "is_paused": bool(bridge_state.get("is_paused")),
            "is_updating": bool(bridge_state.get("is_updating")),
            "is_compiling": bool(bridge_state.get("is_compiling")),
            "busy_reason": str(bridge_state.get("busy_reason") or ""),
            "busy_reason_detail": str(bridge_state.get("busy_reason_detail") or ""),
        },
        "lifecycle_flags": {
            "domain_reload_in_progress": bool(bridge_state.get("domain_reload_in_progress")),
            "package_operation_in_progress": bool(bridge_state.get("package_operation_in_progress")),
            "refresh_settle_pending": bool(bridge_state.get("refresh_settle_pending")),
            "compile_settle_pending": bool(bridge_state.get("compile_settle_pending")),
            "playmode_transition_pending": bool(bridge_state.get("playmode_transition_pending")),
            "script_reload_pending": bool(bridge_state.get("script_reload_pending")),
            "asset_import_in_progress": bool(bridge_state.get("asset_import_in_progress")),
            "active_operation": str(bridge_state.get("active_operation") or ""),
            "last_processed_request_id": str(bridge_state.get("last_processed_request_id") or ""),
            "request_journal_head": str(bridge_state.get("request_journal_head") or ""),
        },
    }


def _build_host_prerequisites(
    *,
    discovery: dict[str, Any],
    transport_state: dict[str, Any],
    package_dependency_alignment: dict[str, Any] | None,
    stale_request_artifacts: dict[str, Any] | None,
) -> dict[str, Any]:
    package_dependency = dict(package_dependency_alignment or {})
    package_alignment = str(package_dependency.get("alignment") or "unknown")
    package_warning = str(package_dependency.get("warning") or "")
    package_warning_active = bool(package_warning) and package_alignment in {
        "file_mismatch",
        "file_no_repo_local_reference",
    }
    live_editor_present = bool(
        discovery.get("bridge_state_live")
        or discovery.get("host_session_live")
        or int(discovery.get("detected_editor_count") or 0) > 0
        or discovery.get("bridge_pid_alive")
        or discovery.get("host_session_pid_alive")
    )
    transport_ready = bool(transport_state.get("ready")) and bool(discovery.get("bridge_state_live"))
    stale_requests = dict(stale_request_artifacts or {})
    stale_request_count = int(stale_requests.get("candidate_count") or 0)

    checks: dict[str, dict[str, Any]] = {
        "bridge_enabled": {
            "ready": bool(discovery.get("bridge_enabled")),
            "status": "ready" if bool(discovery.get("bridge_enabled")) else "missing",
            "code": "bridge_disabled" if not bool(discovery.get("bridge_enabled")) else "none",
            "summary": (
                "Bridge is enabled in the project configuration."
                if bool(discovery.get("bridge_enabled"))
                else "Bridge is disabled in the project configuration."
            ),
        },
        "package_dependency": {
            "ready": package_alignment not in {
                "manifest_unreadable",
                "dependencies_missing",
                "dependency_missing",
            },
            "status": (
                "missing"
                if package_alignment in {"manifest_unreadable", "dependencies_missing", "dependency_missing"}
                else "warning"
                if package_warning_active
                else "ready"
            ),
            "code": (
                "package_manifest_unreadable"
                if package_alignment == "manifest_unreadable"
                else "package_dependencies_missing"
                if package_alignment == "dependencies_missing"
                else "package_dependency_missing"
                if package_alignment == "dependency_missing"
                else "package_dependency_warning"
                if package_warning_active
                else "none"
            ),
            "summary": package_warning if package_warning_active else "Unity package dependency is declared.",
            "alignment": package_alignment,
            "dependency_mode": str(package_dependency.get("dependency_mode") or ""),
        },
        "live_editor": {
            "ready": live_editor_present,
            "status": "ready" if live_editor_present else "missing",
            "code": "none" if live_editor_present else "editor_not_running",
            "summary": (
                "A matching Unity editor process is live for this project."
                if live_editor_present
                else "No matching Unity editor process is currently live for this project."
            ),
            "detected_editor_count": int(discovery.get("detected_editor_count") or 0),
        },
        "transport_ready": {
            "ready": transport_ready,
            "status": "ready" if transport_ready else "missing",
            "code": "none" if transport_ready else "transport_not_ready",
            "summary": (
                "A live bridge transport is ready for requests."
                if transport_ready
                else "No live bridge transport is ready for requests."
            ),
            "active_transport": str(transport_state.get("active_transport") or ""),
            "listener_state": str(transport_state.get("listener_state") or ""),
        },
        "stale_requests": {
            "ready": stale_request_count == 0,
            "status": "warning" if stale_request_count > 0 else "ready",
            "code": "stale_request_artifacts_present" if stale_request_count > 0 else "none",
            "summary": (
                f"{stale_request_count} stale request artifact(s) are eligible for cleanup."
                if stale_request_count > 0
                else "No stale request artifacts were detected."
            ),
            "candidate_count": stale_request_count,
            "classifications": dict(stale_requests.get("classifications") or {}),
            "recommended_cleanup_command": (
                f"xuunity_light_unity_mcp.sh request-stale-cleanup --project-root {discovery.get('project_root') or ''}"
                if stale_request_count > 0
                else ""
            ),
        },
    }

    blocking_codes = [
        str(check.get("code") or "")
        for check in checks.values()
        if str(check.get("status") or "") == "missing" and str(check.get("code") or "") not in {"", "none"}
    ]
    warning_codes = [
        str(check.get("code") or "")
        for check in checks.values()
        if str(check.get("status") or "") == "warning" and str(check.get("code") or "") not in {"", "none"}
    ]

    return {
        "lane": "same_host_editor",
        "ready": not blocking_codes,
        "blocking_codes": blocking_codes,
        "warning_codes": warning_codes,
        "checks": checks,
    }


def _reconciliation_summary(
    *,
    bridge_state: dict[str, Any],
    host_editor_session_state: dict[str, Any],
    bridge_state_live: bool,
    host_session_live: bool,
    bridge_pid_alive: bool,
    host_session_pid_alive: bool,
    bridge_currently_enabled: bool,
    detected_editor_pids: list[int],
) -> dict[str, str]:
    bridge_pid = int(bridge_state.get("editor_pid") or 0)
    host_session_pid = int(host_editor_session_state.get("editor_pid") or 0)

    if bridge_state_live:
        if host_session_pid > 0 and not host_session_live:
            return {
                "case": "stale_host_session",
                "status": "healthy",
                "reason": "live_bridge_state_overrides_stale_host_session",
                "recommended_next_action": "refresh_host_session_if_needed",
            }
        return {
            "case": "bridge_state_authoritative",
            "status": "healthy",
            "reason": "live_bridge_state_with_live_pid",
            "recommended_next_action": "none",
        }

    if host_session_live:
        if bridge_pid > 0 and not bridge_pid_alive:
            return {
                "case": "stale_bridge_state",
                "status": "degraded",
                "reason": "live_host_session_overrides_stale_bridge_state",
                "recommended_next_action": "ensure_ready_or_recover_bridge",
            }
        return {
            "case": "live_host_session_only",
            "status": "degraded",
            "reason": "live_host_session_without_live_bridge_state",
            "recommended_next_action": "ensure_ready_or_recover_bridge",
        }

    if detected_editor_pids:
        return {
            "case": "live_process_only",
            "status": "degraded",
            "reason": "process_table_match_without_live_state_authority",
            "recommended_next_action": "ensure_ready_or_recover_bridge",
        }

    if not bridge_currently_enabled:
        return {
            "case": "bridge_disabled",
            "status": "offline",
            "reason": "bridge_disabled_in_project_config",
            "recommended_next_action": "enable_bridge_and_retry",
        }

    if bridge_pid > 0 and not bridge_pid_alive and host_session_pid > 0 and not host_session_pid_alive:
        return {
            "case": "stale_bridge_and_host_session",
            "status": "offline",
            "reason": "bridge_state_and_host_session_both_stale",
            "recommended_next_action": "open_editor_or_ensure_ready",
        }

    if bridge_pid > 0 and not bridge_pid_alive:
        return {
            "case": "stale_bridge_state",
            "status": "offline",
            "reason": "bridge_state_present_but_editor_pid_not_alive",
            "recommended_next_action": "open_editor_or_ensure_ready",
        }

    if host_session_pid > 0 and not host_session_pid_alive:
        return {
            "case": "stale_host_session",
            "status": "offline",
            "reason": "host_session_present_but_editor_pid_not_alive",
            "recommended_next_action": "clear_stale_host_session_and_retry",
        }

    return {
        "case": "host_launchable_not_active",
        "status": "offline",
        "reason": "unity_project_present_without_live_editor",
        "recommended_next_action": "open_editor_or_ensure_ready",
    }


def discover_project_context_state(
    project_root: Path,
    *,
    try_read_bridge_state: Callable[[Path], dict[str, Any] | None],
    try_read_host_editor_session_state: Callable[[Path], dict[str, Any] | None],
    find_running_unity_editors_for_project: Callable[[Path], list[dict[str, Any]]],
    pid_is_alive: Callable[[int], bool],
    bridge_enabled: Callable[[Path], bool],
    build_project_health: Callable[..., dict[str, Any]] | None = None,
    inspect_package_dependency_alignment: Callable[[Path], dict[str, Any]] | None = None,
    inspect_stale_request_artifacts: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bridge_state = _copy_dict(try_read_bridge_state(project_root))
    host_editor_session_state = _copy_dict(try_read_host_editor_session_state(project_root))
    detected_editors = [dict(editor) for editor in (find_running_unity_editors_for_project(project_root) or []) if isinstance(editor, dict)]

    detected_editor_pids = sorted(
        {
            int(editor.get("pid") or 0)
            for editor in detected_editors
            if int(editor.get("pid") or 0) > 0
        }
    )
    detected_editor_pid_set = set(detected_editor_pids)

    bridge_pid = int(bridge_state.get("editor_pid") or 0)
    host_session_pid = int(host_editor_session_state.get("editor_pid") or 0)
    bridge_pid_alive = pid_is_alive(bridge_pid) if bridge_pid > 0 else False
    host_session_pid_alive = pid_is_alive(host_session_pid) if host_session_pid > 0 else False

    bridge_pid_matches_project = bridge_pid_alive and (
        not detected_editor_pid_set or bridge_pid in detected_editor_pid_set
    )
    host_session_pid_matches_project = host_session_pid_alive and (
        not detected_editor_pid_set or host_session_pid in detected_editor_pid_set
    )

    bridge_state_live = bool(bridge_state) and bridge_pid_matches_project
    host_session_live = bool(host_editor_session_state) and host_session_pid_matches_project
    bridge_currently_enabled = bool(bridge_enabled(project_root))
    reconciliation = _reconciliation_summary(
        bridge_state=bridge_state,
        host_editor_session_state=host_editor_session_state,
        bridge_state_live=bridge_state_live,
        host_session_live=host_session_live,
        bridge_pid_alive=bridge_pid_alive,
        host_session_pid_alive=host_session_pid_alive,
        bridge_currently_enabled=bridge_currently_enabled,
        detected_editor_pids=detected_editor_pids,
    )

    routed_editor_pid = 0
    authoritative_state_source = ""
    discovery_classification = ""
    discovery_reason = ""

    if bridge_state_live:
        routed_editor_pid = bridge_pid
        authoritative_state_source = "bridge_state"
        discovery_classification = "bridge_live"
        discovery_reason = "live_bridge_state_with_live_pid"
    elif host_session_live:
        routed_editor_pid = host_session_pid
        authoritative_state_source = "host_editor_session"
        discovery_classification = "host_session_live"
        discovery_reason = "host_editor_session_with_live_pid"
    elif detected_editor_pids:
        routed_editor_pid = detected_editor_pids[0]
        authoritative_state_source = "process_table"
        discovery_classification = "editor_process_only"
        discovery_reason = "project_matched_in_process_table"
    elif not bridge_currently_enabled:
        authoritative_state_source = "bridge_config"
        discovery_classification = "bridge_disabled"
        discovery_reason = "bridge_disabled_in_project_config"
    elif bridge_state or host_editor_session_state:
        authoritative_state_source = "state_files"
        discovery_classification = "stale_state"
        discovery_reason = "state_files_present_without_live_project_process"
    else:
        authoritative_state_source = "host"
        discovery_classification = "host_launchable_not_active"
        discovery_reason = "unity_project_present_without_live_editor"

    active_transport = str(bridge_state.get("transport") or "")
    transport_requested = str(bridge_state.get("transport_requested") or active_transport or "")
    transport_metadata = _transport_metadata(bridge_state)

    result = {
        "project_root": str(project_root),
        "last_bridge_state": bridge_state,
        "last_host_editor_session_state": host_editor_session_state,
        "active_transport": active_transport,
        "transport_requested": transport_requested,
        "transport_metadata": transport_metadata,
        "bridge_pid": bridge_pid,
        "host_session_pid": host_session_pid,
        "last_seen_pid": routed_editor_pid or bridge_pid or host_session_pid,
        "bridge_pid_alive": bridge_pid_alive,
        "host_session_pid_alive": host_session_pid_alive,
        "bridge_pid_matches_project": bridge_pid_matches_project,
        "host_session_pid_matches_project": host_session_pid_matches_project,
        "bridge_state_live": bridge_state_live,
        "host_session_live": host_session_live,
        "bridge_enabled": bridge_currently_enabled,
        "authoritative_state_source": authoritative_state_source,
        "discovery_classification": discovery_classification,
        "discovery_reason": discovery_reason,
        "reconciliation_case": reconciliation["case"],
        "reconciliation_status": reconciliation["status"],
        "reconciliation_reason": reconciliation["reason"],
        "reconciliation_recommended_next_action": reconciliation["recommended_next_action"],
        "detected_editor_count": len(detected_editor_pids),
        "detected_editor_pids": detected_editor_pids,
        "detected_editors": detected_editors,
    }

    if build_project_health is not None:
        result.update(
            build_project_health(
                project_root=project_root,
                bridge_state=bridge_state,
                host_editor_session_state=host_editor_session_state,
                discovery=result,
            )
            or {}
        )
    transport_state = _transport_state(
        bridge_state=bridge_state,
        active_transport=active_transport,
        transport_requested=transport_requested,
        transport_metadata=transport_metadata,
    )
    stale_request_artifacts = (
        inspect_stale_request_artifacts(project_root)
        if inspect_stale_request_artifacts is not None
        else {}
    )
    result["stale_request_artifacts"] = dict(stale_request_artifacts or {})
    result["transport_state"] = transport_state
    result["state_groups"] = _state_groups(
        bridge_state=bridge_state,
        host_editor_session_state=host_editor_session_state,
        discovery=result,
        transport_state=transport_state,
    )
    result["host_prerequisites"] = _build_host_prerequisites(
        discovery=result,
        transport_state=transport_state,
        package_dependency_alignment=(
            inspect_package_dependency_alignment(project_root)
            if inspect_package_dependency_alignment is not None
            else None
        ),
        stale_request_artifacts=stale_request_artifacts,
    )
    return result

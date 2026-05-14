from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ProjectContext:
    project_root: Path
    instance_key: str
    created_unix: float = field(default_factory=time.time)
    last_access_unix: float = field(default_factory=time.time)
    last_bridge_state: dict[str, Any] = field(default_factory=dict)
    last_host_editor_session_state: dict[str, Any] = field(default_factory=dict)
    active_transport: str = ""
    transport_metadata: dict[str, Any] = field(default_factory=dict)
    transport_state: dict[str, Any] = field(default_factory=dict)
    state_groups: dict[str, Any] = field(default_factory=dict)
    request_lock: threading.Lock = field(default_factory=threading.Lock)
    interactive_lock: threading.Lock = field(default_factory=threading.Lock)
    last_seen_pid: int = 0
    last_seen_generation: int = 0
    last_seen_session_id: str = ""
    last_refresh_utc: str = ""
    last_refresh_unix: float = 0.0
    health_classification: str = ""
    discovery_classification: str = ""
    discovery_details: dict[str, Any] = field(default_factory=dict)

    def touch(self, now: float | None = None) -> None:
        self.last_access_unix = float(now if now is not None else time.time())

    def idle_seconds(self, now: float | None = None) -> float:
        current = float(now if now is not None else time.time())
        return max(0.0, current - float(self.last_access_unix or current))

    def has_live_runtime_evidence(self) -> bool:
        details = self.discovery_details if isinstance(self.discovery_details, dict) else {}
        return bool(
            details.get("bridge_state_live")
            or details.get("host_session_live")
            or int(details.get("detected_editor_count") or 0) > 0
        )

    def apply_refresh(self, details: dict[str, Any]) -> None:
        self.last_bridge_state = dict(details.get("last_bridge_state") or {})
        self.last_host_editor_session_state = dict(details.get("last_host_editor_session_state") or {})
        self.active_transport = str(details.get("active_transport") or "")
        self.transport_metadata = dict(details.get("transport_metadata") or {})
        self.transport_state = dict(details.get("transport_state") or {})
        self.state_groups = dict(details.get("state_groups") or {})
        self.last_seen_pid = int(details.get("last_seen_pid") or 0)
        self.last_seen_generation = int(details.get("last_seen_generation") or 0)
        self.last_seen_session_id = str(details.get("last_seen_session_id") or "")
        self.last_refresh_utc = str(details.get("last_refresh_utc") or "")
        self.last_refresh_unix = float(details.get("last_refresh_unix") or time.time())
        self.health_classification = str(details.get("health_classification") or "")
        self.discovery_classification = str(details.get("discovery_classification") or "")
        self.discovery_details = dict(details.get("discovery_details") or {})


class BridgeRegistry:
    def __init__(
        self,
        *,
        ensure_project_root: Callable[[str], Path],
        refresh_context_state: Callable[[Path], dict[str, Any]] | None = None,
        offline_context_max_idle_seconds: float = 600.0,
        general_context_max_idle_seconds: float = 3600.0,
    ) -> None:
        self._ensure_project_root = ensure_project_root
        self._refresh_context_state = refresh_context_state
        self._offline_context_max_idle_seconds = float(offline_context_max_idle_seconds)
        self._general_context_max_idle_seconds = float(general_context_max_idle_seconds)
        self._contexts: dict[str, ProjectContext] = {}
        self._lock = threading.RLock()

    def get_or_discover(self, project_root: str) -> ProjectContext:
        resolved_root = self._ensure_project_root(project_root)
        instance_key = self._instance_key(resolved_root)

        with self._lock:
            self._prune_stale_contexts_locked()
            context = self._contexts.get(instance_key)
            if context is None:
                context = ProjectContext(
                    project_root=resolved_root,
                    instance_key=instance_key,
                )
                self._contexts[instance_key] = context
            context.touch()
            self._refresh_context(context)
            return context

    def refresh_context(self, project_root: str) -> ProjectContext:
        resolved_root = self._ensure_project_root(project_root)
        instance_key = self._instance_key(resolved_root)

        with self._lock:
            self._prune_stale_contexts_locked()
            context = self._contexts.get(instance_key)
            if context is None:
                context = ProjectContext(
                    project_root=resolved_root,
                    instance_key=instance_key,
                )
                self._contexts[instance_key] = context
            context.touch()
            self._refresh_context(context)
            return context

    def forget(self, project_root: str) -> bool:
        resolved_root = self._ensure_project_root(project_root)
        instance_key = self._instance_key(resolved_root)
        with self._lock:
            return self._contexts.pop(instance_key, None) is not None

    def list_active_contexts(self) -> list[ProjectContext]:
        with self._lock:
            self._prune_stale_contexts_locked()
            return [self._contexts[key] for key in sorted(self._contexts.keys())]

    def prune_stale_contexts(
        self,
        *,
        offline_context_max_idle_seconds: float | None = None,
        general_context_max_idle_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return self._prune_stale_contexts_locked(
                offline_context_max_idle_seconds=offline_context_max_idle_seconds,
                general_context_max_idle_seconds=general_context_max_idle_seconds,
            )

    @staticmethod
    def _instance_key(project_root: Path) -> str:
        return str(project_root)

    def _prune_stale_contexts_locked(
        self,
        *,
        offline_context_max_idle_seconds: float | None = None,
        general_context_max_idle_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        now = time.time()
        offline_idle = float(
            self._offline_context_max_idle_seconds
            if offline_context_max_idle_seconds is None
            else offline_context_max_idle_seconds
        )
        general_idle = float(
            self._general_context_max_idle_seconds
            if general_context_max_idle_seconds is None
            else general_context_max_idle_seconds
        )
        pruned: list[dict[str, Any]] = []

        for instance_key, context in list(self._contexts.items()):
            idle_seconds = context.idle_seconds(now)
            live_runtime = context.has_live_runtime_evidence()
            should_prune = False
            reason = ""

            if not live_runtime and idle_seconds >= offline_idle:
                should_prune = True
                reason = "offline_idle_expired"
            elif idle_seconds >= general_idle:
                should_prune = True
                reason = "general_idle_expired"

            if not should_prune:
                continue

            self._contexts.pop(instance_key, None)
            pruned.append(
                {
                    "instance_key": instance_key,
                    "project_root": str(context.project_root),
                    "idle_seconds": round(idle_seconds, 3),
                    "reason": reason,
                    "had_live_runtime_evidence": live_runtime,
                    "last_refresh_unix": float(context.last_refresh_unix or 0.0),
                    "last_seen_pid": int(context.last_seen_pid or 0),
                }
            )

        return pruned

    def _refresh_context(self, context: ProjectContext) -> None:
        if self._refresh_context_state is None:
            context.last_refresh_unix = time.time()
            return
        context.apply_refresh(self._refresh_context_state(context.project_root))

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_SCHEMA_VERSION = "xuunity.module.v1"
PACK_SCHEMA_VERSION = "xuunity.pack.v1"
ENTITLEMENTS_SCHEMA_VERSION = "xuunity.entitlements.v1"
RESOLVED_SCHEMA_VERSION = "xuunity.resolved-modules.v1"

SCRIPT_DIR = Path(__file__).resolve().parent
XUUNITY_ROOT = SCRIPT_DIR.parent
AIR_ROOT = XUUNITY_ROOT.parents[1]
DEFAULT_PROTOCOL = "xuunity"

EXIT_VALIDATION_FAILED = 1
EXIT_LOCKED = 2
EXIT_UNSAFE = 3
EXIT_INCOMPATIBLE = 4
EXIT_UNEXPECTED = 5

ENTRYPOINT_GROUPS = ("roles", "skills", "reviews", "utilities", "knowledge")


@dataclass
class PackRecord:
    module_id: str
    module_root: Path
    module_display_root: Path
    module_manifest: dict[str, Any]
    pack_path: Path
    pack_display_path: Path
    manifest: dict[str, Any]
    validation_errors: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.manifest.get("id") or "")

    @property
    def license_feature(self) -> str:
        return str(self.manifest.get("licenseFeature") or "")


@dataclass
class ModuleRecord:
    display_root: Path
    resolved_root: Path
    source: str
    manifest_path: Path | None
    manifest: dict[str, Any] | None
    resolution: str
    validation_errors: list[str] = field(default_factory=list)
    packs: list[PackRecord] = field(default_factory=list)

    @property
    def id(self) -> str:
        if not self.manifest:
            return ""
        return str(self.manifest.get("id") or "")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def safe_resolve(path: Path) -> Path:
    return path.expanduser().resolve()


def xuunity_home() -> Path:
    override = os.environ.get("XUUNITY_HOME", "").strip()
    if override:
        return safe_resolve(Path(override))
    return Path.home() / ".xuunity"


def find_host_root(start: Path) -> Path:
    current = safe_resolve(start)
    if current.is_file():
        current = current.parent
    candidates = [current, *current.parents]
    for candidate in candidates:
        if (candidate / "AIModules").exists():
            return candidate
        if (candidate / "AIRoot").exists() and (candidate / "AIModules").exists():
            return candidate
    for candidate in candidates:
        if candidate.name == "AIRoot" and (candidate.parent / "AIModules").exists():
            return candidate.parent
    return current


def default_project_root() -> Path:
    if (AIR_ROOT.parent / "AIModules").exists():
        return AIR_ROOT.parent
    return AIR_ROOT


def split_path_list(raw_values: list[str]) -> list[str]:
    result: list[str] = []
    for value in raw_values:
        for part in value.split(os.pathsep):
            part = part.strip()
            if part:
                result.append(part)
    return result


def load_user_config(home: Path) -> tuple[dict[str, Any], list[str]]:
    path = home / "config.json"
    if not path.is_file():
        return {}, []
    try:
        return read_json(path), []
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"user config unreadable: {path}: {exc}"]


def load_entitlements(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.is_file():
        return {"schemaVersion": ENTITLEMENTS_SCHEMA_VERSION, "features": [], "mode": "missing", "source": "missing"}, []
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"schemaVersion": ENTITLEMENTS_SCHEMA_VERSION, "features": [], "mode": "unreadable", "source": str(path)}, [
            f"entitlements unreadable: {path}: {exc}"
        ]
    errors = []
    if payload.get("schemaVersion") != ENTITLEMENTS_SCHEMA_VERSION:
        errors.append(f"unsupported entitlements schema: {payload.get('schemaVersion')!r}")
    if not isinstance(payload.get("features"), list):
        errors.append("entitlements features must be an array")
        payload["features"] = []
    return payload, errors


def normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def path_is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_id(value: str, label: str) -> list[str]:
    if not re.match(r"^[a-z0-9][a-z0-9_.-]*$", value or ""):
        return [f"{label} must be a stable lowercase id, got {value!r}"]
    return []


def validate_module_manifest(manifest: dict[str, Any], module_root: Path) -> list[str]:
    errors: list[str] = []
    required = ["schemaVersion", "id", "displayName", "kind", "visibility", "version", "protocolScopes", "packs", "exportPolicy"]
    for key in required:
        if key not in manifest:
            errors.append(f"module missing required field: {key}")
    if manifest.get("schemaVersion") != MODULE_SCHEMA_VERSION:
        errors.append(f"unsupported module schemaVersion: {manifest.get('schemaVersion')!r}")
    errors.extend(validate_id(str(manifest.get("id") or ""), "module id"))
    protocol_scopes = normalize_string_list(manifest.get("protocolScopes"))
    if not protocol_scopes:
        errors.append("module protocolScopes must include at least one scope")
    if not isinstance(manifest.get("packs"), list):
        errors.append("module packs must be an array")
    export_policy = manifest.get("exportPolicy")
    if not isinstance(export_policy, dict):
        errors.append("module exportPolicy must be an object")
    else:
        for key in ("mayCommitToHostRepo", "mayWriteResolvedRegistryToProject", "mayQuotePrivateContentInReports"):
            if not isinstance(export_policy.get(key), bool):
                errors.append(f"module exportPolicy.{key} must be boolean")
    for pack_rel in normalize_string_list(manifest.get("packs")):
        candidate = module_root / pack_rel
        if Path(pack_rel).is_absolute() or ".." in Path(pack_rel).parts:
            errors.append(f"module pack path must stay inside module root: {pack_rel}")
        elif not path_is_within(candidate, module_root):
            errors.append(f"module pack path escapes module root: {pack_rel}")
    return errors


def validate_pack_manifest(manifest: dict[str, Any], pack_root: Path) -> list[str]:
    errors: list[str] = []
    required = ["schemaVersion", "id", "displayName", "licenseFeature", "dependsOn", "entrypoints", "exportPolicy"]
    for key in required:
        if key not in manifest:
            errors.append(f"pack missing required field: {key}")
    if manifest.get("schemaVersion") != PACK_SCHEMA_VERSION:
        errors.append(f"unsupported pack schemaVersion: {manifest.get('schemaVersion')!r}")
    errors.extend(validate_id(str(manifest.get("id") or ""), "pack id"))
    if not str(manifest.get("licenseFeature") or "").strip():
        errors.append("pack licenseFeature is required")
    if not isinstance(manifest.get("dependsOn"), list):
        errors.append("pack dependsOn must be an array")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        errors.append("pack entrypoints must be an object")
        entrypoints = {}
    for group, values in entrypoints.items():
        if group not in ENTRYPOINT_GROUPS:
            errors.append(f"pack entrypoints has unsupported group: {group}")
            continue
        if not isinstance(values, list):
            errors.append(f"pack entrypoints.{group} must be an array")
            continue
        for rel in normalize_string_list(values):
            candidate = pack_root / rel
            if Path(rel).is_absolute() or ".." in Path(rel).parts:
                errors.append(f"pack entrypoint path must stay inside pack root: {group}:{rel}")
            elif not path_is_within(candidate, pack_root):
                errors.append(f"pack entrypoint path escapes pack root: {group}:{rel}")
            elif not candidate.is_file():
                errors.append(f"pack entrypoint missing: {group}:{rel}")
    export_policy = manifest.get("exportPolicy")
    if not isinstance(export_policy, dict):
        errors.append("pack exportPolicy must be an object")
    else:
        if export_policy.get("mayQuotePrivateContentInReports") is not False:
            errors.append("pack exportPolicy.mayQuotePrivateContentInReports must be false for private packs")
        if str(export_policy.get("reportReferenceMode") or "") != "pack_id_only":
            errors.append("pack exportPolicy.reportReferenceMode must be pack_id_only for private packs")
    routing = manifest.get("routing")
    if routing is not None and not isinstance(routing, dict):
        errors.append("pack routing must be an object when provided")
    return errors


def module_in_protocol_scope(manifest: dict[str, Any], protocol: str) -> bool:
    scopes = set(normalize_string_list(manifest.get("protocolScopes")))
    return protocol in scopes or "universal" in scopes


def discover_roots(project_root: Path, args: argparse.Namespace, home: Path) -> tuple[list[tuple[Path, str]], list[dict[str, str]], list[str]]:
    warnings: list[str] = []
    roots: list[tuple[Path, str]] = []
    discovery_roots: list[dict[str, str]] = []
    host_root = find_host_root(project_root)
    aimodules = host_root / "AIModules"
    if aimodules.exists():
        discovery_roots.append({"kind": "host_aimodules", "path": str(aimodules)})
        try:
            for child in sorted(aimodules.iterdir(), key=lambda item: item.name.lower()):
                if child.name.startswith("."):
                    continue
                if child.is_dir() or child.is_symlink():
                    roots.append((child, "host_aimodules"))
        except OSError as exc:
            warnings.append(f"AIModules unreadable: {aimodules}: {exc}")

    explicit = split_path_list(getattr(args, "module_root", []) or [])
    explicit.extend(split_path_list([os.environ.get("XUUNITY_MODULE_PATHS", "")]))
    user_config, config_warnings = load_user_config(home)
    warnings.extend(config_warnings)
    explicit.extend(normalize_string_list(user_config.get("additionalModuleSearchPaths")))
    for value in explicit:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        roots.append((path, "explicit"))
        discovery_roots.append({"kind": "explicit", "path": str(path)})

    deduped: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for root, source in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((root, source))
    return deduped, discovery_roots, warnings


def load_modules(project_root: Path, args: argparse.Namespace, home: Path, protocol: str = DEFAULT_PROTOCOL) -> tuple[list[ModuleRecord], list[dict[str, str]], list[str]]:
    root_entries, discovery_roots, warnings = discover_roots(project_root, args, home)
    modules: list[ModuleRecord] = []
    seen_ids: dict[str, Path] = {}

    for display_root, source in root_entries:
        resolved_root = safe_resolve(display_root)
        manifest_path = resolved_root / "module.json"
        if not manifest_path.is_file():
            modules.append(
                ModuleRecord(
                    display_root=display_root,
                    resolved_root=resolved_root,
                    source=source,
                    manifest_path=None,
                    manifest=None,
                    resolution="unregistered_module_root",
                    validation_errors=[],
                )
            )
            continue
        try:
            manifest = read_json(manifest_path)
            validation_errors = validate_module_manifest(manifest, resolved_root)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            modules.append(
                ModuleRecord(
                    display_root=display_root,
                    resolved_root=resolved_root,
                    source=source,
                    manifest_path=manifest_path,
                    manifest=None,
                    resolution="invalid",
                    validation_errors=[f"module manifest unreadable: {exc}"],
                )
            )
            continue

        module_id = str(manifest.get("id") or "")
        if module_id in seen_ids:
            validation_errors.append(f"duplicate module id {module_id!r}; first seen at {seen_ids[module_id]}")
        elif module_id:
            seen_ids[module_id] = resolved_root

        if validation_errors:
            resolution = "invalid"
        elif not module_in_protocol_scope(manifest, protocol):
            resolution = "ignored_protocol_scope"
        else:
            resolution = "in_scope"

        module = ModuleRecord(
            display_root=display_root,
            resolved_root=resolved_root,
            source=source,
            manifest_path=manifest_path,
            manifest=manifest,
            resolution=resolution,
            validation_errors=validation_errors,
        )
        if manifest and resolution in {"in_scope", "invalid"}:
            for pack_rel in normalize_string_list(manifest.get("packs")):
                pack_display_path = display_root / pack_rel
                pack_path = resolved_root / pack_rel
                pack_root = pack_path.parent
                try:
                    pack_manifest = read_json(pack_path)
                    pack_errors = validate_pack_manifest(pack_manifest, pack_root)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    pack_manifest = {}
                    pack_errors = [f"pack manifest unreadable: {pack_rel}: {exc}"]
                module.packs.append(
                    PackRecord(
                        module_id=module_id,
                        module_root=resolved_root,
                        module_display_root=display_root,
                        module_manifest=manifest,
                        pack_path=pack_path,
                        pack_display_path=pack_display_path,
                        manifest=pack_manifest,
                        validation_errors=pack_errors,
                    )
                )
        modules.append(module)

    return modules, discovery_roots, warnings


def entrypoints_payload(pack: PackRecord, *, display_paths: bool = True) -> dict[str, list[str]]:
    base = pack.pack_display_path.parent if display_paths else pack.pack_path.parent
    payload: dict[str, list[str]] = {}
    for group in ENTRYPOINT_GROUPS:
        paths = normalize_string_list((pack.manifest.get("entrypoints") or {}).get(group))
        payload[group] = [str(base / rel) for rel in paths]
    return payload


def scanned_module_payload(module: ModuleRecord) -> dict[str, Any]:
    manifest = module.manifest or {}
    return {
        "id": str(manifest.get("id") or ""),
        "display_name": str(manifest.get("displayName") or ""),
        "root": str(module.display_root),
        "resolved_root": str(module.resolved_root),
        "source": module.source,
        "protocolScopes": normalize_string_list(manifest.get("protocolScopes")),
        "resolution": module.resolution,
        "validation_errors": module.validation_errors,
        "is_symlink": module.display_root.is_symlink(),
        "pack_count": len(module.packs),
    }


def pack_payload(pack: PackRecord, status: str, reason: str, entitlements: dict[str, Any]) -> dict[str, Any]:
    report_reference = f"Private pack used: {pack.id}" if pack.id else "Private pack used: [unknown]"
    return {
        "id": pack.id,
        "moduleId": pack.module_id,
        "moduleVersion": str(pack.module_manifest.get("version") or ""),
        "displayName": str(pack.manifest.get("displayName") or ""),
        "source": str(pack.module_manifest.get("kind") or ""),
        "root": str(pack.pack_display_path.parent),
        "resolved_root": str(pack.pack_path.parent),
        "licenseFeature": pack.license_feature,
        "entitlementMode": str(entitlements.get("mode") or ""),
        "status": status,
        "reason": reason,
        "entrypoints": entrypoints_payload(pack, display_paths=True),
        "routing": pack.manifest.get("routing") if isinstance(pack.manifest.get("routing"), dict) else {},
        "exportPolicy": pack.manifest.get("exportPolicy") if isinstance(pack.manifest.get("exportPolicy"), dict) else {},
        "reportReference": report_reference,
    }


def resolved_cache_path(home: Path, project_root: Path) -> Path:
    digest = hashlib.sha1(str(safe_resolve(project_root)).encode("utf-8")).hexdigest()[:16]
    return home / "cache" / "resolved_modules" / f"{digest}.json"


def output_path_is_unsafe(path: Path, project_root: Path, host_root: Path) -> bool:
    resolved = safe_resolve(path)
    return path_is_within(resolved, project_root) or path_is_within(resolved, host_root)


def build_resolved_registry(args: argparse.Namespace, *, write: bool = True) -> tuple[dict[str, Any], int]:
    home = safe_resolve(Path(getattr(args, "xuunity_home", "") or xuunity_home()))
    project_root = safe_resolve(Path(getattr(args, "project_root", "") or default_project_root()))
    host_root = find_host_root(project_root)
    entitlements_path = safe_resolve(Path(getattr(args, "entitlements", "") or (home / "entitlements.json")))
    entitlements, entitlement_errors = load_entitlements(entitlements_path)
    features = set(normalize_string_list(entitlements.get("features")))
    modules, discovery_roots, warnings = load_modules(project_root, args, home)
    warnings.extend(entitlement_errors)

    loaded_packs: list[dict[str, Any]] = []
    locked_packs: list[dict[str, Any]] = []
    invalid_packs: list[dict[str, Any]] = []
    exit_code = 0

    for module in modules:
        if module.resolution == "invalid":
            exit_code = max(exit_code, EXIT_VALIDATION_FAILED)
        if module.resolution != "in_scope":
            continue
        module_feature = str((module.manifest or {}).get("license", {}).get("feature") or "")
        module_entitled = not module_feature or module_feature in features
        for pack in module.packs:
            if pack.validation_errors:
                invalid_packs.append(pack_payload(pack, "invalid", "; ".join(pack.validation_errors), entitlements))
                exit_code = max(exit_code, EXIT_VALIDATION_FAILED)
                continue
            pack_entitled = pack.license_feature in features
            if module_entitled and pack_entitled:
                loaded_packs.append(pack_payload(pack, "loaded", "", entitlements))
            else:
                reason_parts = []
                if module_feature and not module_entitled:
                    reason_parts.append(f"missing module entitlement {module_feature}")
                if not pack_entitled:
                    reason_parts.append(f"missing pack entitlement {pack.license_feature}")
                locked_packs.append(pack_payload(pack, "locked", "; ".join(reason_parts), entitlements))

    cache_path = Path(getattr(args, "output", "") or resolved_cache_path(home, project_root))
    payload = {
        "schemaVersion": RESOLVED_SCHEMA_VERSION,
        "resolvedAtUtc": now_utc(),
        "projectRoot": str(project_root),
        "hostRoot": str(host_root),
        "writeScope": "user_cache",
        "cachePath": str(cache_path),
        "entitlements": {
            "path": str(entitlements_path),
            "mode": str(entitlements.get("mode") or ""),
            "source": str(entitlements.get("source") or ""),
            "feature_count": len(features),
        },
        "discoveryRoots": discovery_roots,
        "scannedModules": [scanned_module_payload(module) for module in modules],
        "loadedModules": [
            {
                "id": "xuunity.core",
                "source": "public_core",
                "root": str(XUUNITY_ROOT),
            }
        ],
        "loadedPacks": loaded_packs,
        "lockedPacks": locked_packs,
        "invalidPacks": invalid_packs,
        "warnings": warnings,
    }

    if write:
        if output_path_is_unsafe(cache_path, project_root, host_root):
            payload["warnings"].append(f"refusing to write resolved registry inside project or host root: {cache_path}")
            return payload, max(exit_code, EXIT_UNSAFE)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return payload, exit_code


def command_scan(args: argparse.Namespace) -> int:
    home = safe_resolve(Path(getattr(args, "xuunity_home", "") or xuunity_home()))
    project_root = safe_resolve(Path(getattr(args, "project_root", "") or default_project_root()))
    modules, discovery_roots, warnings = load_modules(project_root, args, home)
    payload = {
        "action": "xuunity.module.scan",
        "projectRoot": str(project_root),
        "hostRoot": str(find_host_root(project_root)),
        "discoveryRoots": discovery_roots,
        "scannedModules": [scanned_module_payload(module) for module in modules],
        "warnings": warnings,
    }
    print_json(payload)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    home = safe_resolve(Path(getattr(args, "xuunity_home", "") or xuunity_home()))
    project_root = safe_resolve(Path(getattr(args, "project_root", "") or default_project_root()))
    modules, discovery_roots, warnings = load_modules(project_root, args, home)
    invalid_modules = [scanned_module_payload(module) for module in modules if module.resolution == "invalid"]
    invalid_packs = []
    for module in modules:
        for pack in module.packs:
            if pack.validation_errors:
                invalid_packs.append(
                    {
                        "id": pack.id,
                        "moduleId": pack.module_id,
                        "packPath": str(pack.pack_display_path),
                        "validation_errors": pack.validation_errors,
                    }
                )
    payload = {
        "action": "xuunity.module.validate",
        "status": "valid" if not invalid_modules and not invalid_packs else "invalid",
        "projectRoot": str(project_root),
        "discoveryRoots": discovery_roots,
        "scannedModules": [scanned_module_payload(module) for module in modules],
        "invalidModules": invalid_modules,
        "invalidPacks": invalid_packs,
        "warnings": warnings,
    }
    print_json(payload)
    return 0 if payload["status"] == "valid" else EXIT_VALIDATION_FAILED


def command_resolve(args: argparse.Namespace) -> int:
    payload, exit_code = build_resolved_registry(args, write=not getattr(args, "no_write", False))
    print_json(payload)
    return exit_code


def command_rollsync(args: argparse.Namespace) -> int:
    payload, exit_code = build_resolved_registry(args, write=True)
    if payload["invalidPacks"]:
        status = "invalid"
    elif exit_code == EXIT_UNSAFE:
        status = "invalid"
    elif exit_code == EXIT_VALIDATION_FAILED:
        status = "invalid"
    elif payload["loadedPacks"] and payload["warnings"]:
        status = "ready_with_warnings"
    elif payload["loadedPacks"]:
        status = "ready"
    elif payload["lockedPacks"]:
        status = "locked"
        exit_code = max(exit_code, EXIT_LOCKED)
    else:
        status = "not_configured"
    summary = {
        "action": "xuunity.module.rollsync",
        "status": status,
        "loaded_pack_count": len(payload["loadedPacks"]),
        "locked_pack_count": len(payload["lockedPacks"]),
        "invalid_pack_count": len(payload["invalidPacks"]),
        "scanned_module_count": len(payload["scannedModules"]),
        "cache_path": payload["cachePath"],
        "loadedPacks": [{"id": pack["id"], "root": pack["root"]} for pack in payload["loadedPacks"]],
        "lockedPacks": [{"id": pack["id"], "reason": pack["reason"]} for pack in payload["lockedPacks"]],
        "invalidPacks": [{"id": pack["id"], "reason": pack["reason"]} for pack in payload["invalidPacks"]],
        "warnings": payload["warnings"],
        "next_actions": [],
    }
    if status == "locked":
        summary["next_actions"].append("add the missing feature to user-level entitlements or choose a public-core route")
    if status == "not_configured":
        summary["next_actions"].append("add a valid module.json under AIModules/ or configure additionalModuleSearchPaths")
    if exit_code == EXIT_UNSAFE:
        summary["next_actions"].append("write resolved registries to the user cache, not into the host or project repo")
    print_json(summary)
    return exit_code


def trigger_matches(task_text: str, pack: dict[str, Any]) -> list[str]:
    routing = pack.get("routing") if isinstance(pack.get("routing"), dict) else {}
    triggers = normalize_string_list(routing.get("triggers"))
    lowered = task_text.lower()
    return [trigger for trigger in triggers if trigger.lower() in lowered]


def public_game_qa_path_leak(pack: dict[str, Any]) -> bool:
    public_fragments = (
        "/AIRoot/Modules/XUUnity/skills/game_qa/",
        "/Modules/XUUnity/skills/game_qa/",
        "\\AIRoot\\Modules\\XUUnity\\skills\\game_qa\\",
        "\\Modules\\XUUnity\\skills\\game_qa\\",
    )
    for values in (pack.get("entrypoints") or {}).values():
        for value in values:
            normalized = str(value)
            if any(fragment in normalized for fragment in public_fragments):
                return True
    return False


def matched_pack_payload(pack: dict[str, Any], matched_triggers: list[str], *, include_entrypoints: bool) -> dict[str, Any]:
    payload = {
        "id": pack["id"],
        "moduleId": pack["moduleId"],
        "moduleVersion": pack.get("moduleVersion", ""),
        "root": pack["root"],
        "resolved_root": pack["resolved_root"],
        "matchedTriggers": matched_triggers,
        "reportReference": pack.get("reportReference") or f"Private pack used: {pack['id']}",
        "reportReferenceMode": (pack.get("exportPolicy") or {}).get("reportReferenceMode", "pack_id_only"),
        "publicPathLeakDetected": public_game_qa_path_leak(pack),
    }
    if include_entrypoints:
        payload["entrypoints"] = pack["entrypoints"]
    return payload


def matching_packs(task_text: str, packs: list[dict[str, Any]], *, include_entrypoints: bool) -> list[dict[str, Any]]:
    matches = []
    for pack in packs:
        matched_triggers = trigger_matches(task_text, pack)
        if matched_triggers:
            matches.append(matched_pack_payload(pack, matched_triggers, include_entrypoints=include_entrypoints))
    return matches


def command_route_smoke(args: argparse.Namespace) -> int:
    task_text = str(getattr(args, "task_text", "") or "").strip()
    if not task_text:
        print_json({"action": "xuunity.module.route_smoke", "status": "failed", "error": "task text is required"})
        return EXIT_VALIDATION_FAILED
    payload, exit_code = build_resolved_registry(args, write=True)
    matches = matching_packs(task_text, payload["loadedPacks"], include_entrypoints=True)
    expected = str(getattr(args, "expect_pack", "") or "").strip()
    expected_found = not expected or any(match["id"] == expected for match in matches)
    leak_found = any(match["publicPathLeakDetected"] for match in matches)
    status = "passed" if matches and expected_found and not leak_found else "failed"
    summary = {
        "action": "xuunity.module.route_smoke",
        "status": status,
        "taskText": task_text,
        "expectedPack": expected,
        "expectedPackFound": expected_found,
        "matchedLoadedPacks": matches,
        "publicPathLeakDetected": leak_found,
        "cache_path": payload["cachePath"],
        "proof": {
            "loaded_from_private_module": bool(matches),
            "loaded_pack_ids": [match["id"] for match in matches],
            "route_source": "resolved_loadedPacks",
        },
    }
    print_json(summary)
    if status != "passed":
        return EXIT_VALIDATION_FAILED if exit_code == 0 else exit_code
    return 0


def command_session_plan(args: argparse.Namespace) -> int:
    task_text = str(getattr(args, "task_text", "") or "").strip()
    if not task_text:
        print_json({"action": "xuunity.module.session_plan", "status": "failed", "error": "task text is required"})
        return EXIT_VALIDATION_FAILED
    payload, exit_code = build_resolved_registry(args, write=True)
    loaded_matches = matching_packs(task_text, payload["loadedPacks"], include_entrypoints=True)
    locked_matches = matching_packs(task_text, payload["lockedPacks"], include_entrypoints=False)
    invalid_matches = matching_packs(task_text, payload["invalidPacks"], include_entrypoints=False)
    leak_found = any(match["publicPathLeakDetected"] for match in loaded_matches)
    if leak_found:
        status = "unsafe"
        exit_code = max(exit_code, EXIT_UNSAFE)
    elif loaded_matches:
        status = "private_pack_loaded"
    elif locked_matches or invalid_matches:
        status = "private_pack_unavailable"
    else:
        status = "public_core_only"

    report_references = [match["reportReference"] for match in loaded_matches]
    summary = {
        "action": "xuunity.module.session_plan",
        "status": status,
        "taskText": task_text,
        "cache_path": payload["cachePath"],
        "matchedLoadedPacks": loaded_matches,
        "matchedLockedPacks": locked_matches,
        "matchedInvalidPacks": invalid_matches,
        "publicPathLeakDetected": leak_found,
        "sessionContract": {
            "private_pack_source": "resolved_loadedPacks",
            "matched_private_packs": [match["id"] for match in loaded_matches],
            "private_pack_report_references": report_references,
            "private_content_report_policy": "pack_id_only",
            "private_paths_user_local_only": True,
            "continue_without_private_pack": not loaded_matches,
            "load_order": [
                "repo_router",
                "public_xuunity_core",
                "loaded_private_packs",
                "project_router",
                "project_memory",
                "relevant_prior_outputs",
            ],
        },
        "fallback": "continue_with_public_core" if not loaded_matches else "",
        "warnings": payload["warnings"],
    }
    print_json(summary)
    return exit_code


def command_doctor(args: argparse.Namespace) -> int:
    payload, exit_code = build_resolved_registry(args, write=False)
    requested = str(getattr(args, "pack_id", "") or "").strip()
    loaded = [pack for pack in payload["loadedPacks"] if not requested or pack["id"] == requested]
    locked = [pack for pack in payload["lockedPacks"] if not requested or pack["id"] == requested]
    invalid = [pack for pack in payload["invalidPacks"] if not requested or pack["id"] == requested]
    status = "loaded" if loaded else "locked" if locked else "invalid" if invalid else "not_found"
    summary = {
        "action": "xuunity.module.doctor",
        "status": status,
        "pack_id": requested,
        "loaded": loaded,
        "locked": locked,
        "invalid": invalid,
        "scannedModules": payload["scannedModules"],
        "warnings": payload["warnings"],
    }
    print_json(summary)
    if status == "loaded":
        return 0
    if status == "locked":
        return EXIT_LOCKED
    if status == "invalid":
        return EXIT_VALIDATION_FAILED
    return EXIT_VALIDATION_FAILED if exit_code == 0 else exit_code


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", default="", help="Host or project root used to discover the nearest AIModules root.")
    parser.add_argument("--module-root", action="append", default=[], help="Additional explicit module root. May be repeated.")
    parser.add_argument("--xuunity-home", default="", help="Override ~/.xuunity for tests or isolated runs.")
    parser.add_argument("--entitlements", default="", help="Override entitlement file path.")
    parser.add_argument("--output", default="", help="Override resolved registry output path.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XUUnity private module registry and Rollsync tool.")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="List configured module roots and module registration status.")
    add_common_args(scan)
    scan.set_defaults(func=command_scan)

    validate = sub.add_parser("validate", help="Validate discovered module and pack manifests.")
    add_common_args(validate)
    validate.set_defaults(func=command_validate)

    resolve = sub.add_parser("resolve", help="Resolve loaded, locked, and invalid private packs.")
    add_common_args(resolve)
    resolve.add_argument("--no-write", action="store_true", help="Do not write the resolved registry cache.")
    resolve.set_defaults(func=command_resolve)

    rollsync = sub.add_parser("rollsync", help="Validate, resolve, health-gate, and write the resolved registry.")
    add_common_args(rollsync)
    rollsync.set_defaults(func=command_rollsync)

    smoke = sub.add_parser("route-smoke", help="Prove a task routes through an entitled loaded private pack.")
    add_common_args(smoke)
    smoke.add_argument("--task-text", required=True)
    smoke.add_argument("--expect-pack", default="")
    smoke.set_defaults(func=command_route_smoke)

    session = sub.add_parser("session-plan", help="Build the redacted private-pack routing contract for a task session.")
    add_common_args(session)
    session.add_argument("--task-text", required=True)
    session.set_defaults(func=command_session_plan)

    doctor = sub.add_parser("doctor", help="Explain why a pack is loaded, locked, invalid, or missing.")
    add_common_args(doctor)
    doctor.add_argument("--pack-id", default="")
    doctor.set_defaults(func=command_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # pragma: no cover - last-resort CLI boundary
        print_json({"action": "xuunity.module.error", "status": "error", "error": str(exc)})
        return EXIT_UNEXPECTED


if __name__ == "__main__":
    raise SystemExit(main())

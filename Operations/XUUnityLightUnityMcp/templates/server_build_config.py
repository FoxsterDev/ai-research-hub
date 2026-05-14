from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve_build_config_asset_path(project_root: Path, build_config_asset: str | None, tool_error_type: type[Exception]) -> Path:
    if build_config_asset:
        candidate = Path(build_config_asset).expanduser()
        if not candidate.is_absolute():
            candidate = project_root / candidate
        candidate = candidate.resolve()
        if not candidate.is_file():
            raise tool_error_type("build_config_asset_not_found", f"Build config asset not found: {candidate}")
        return candidate

    candidates = sorted(project_root.glob("Assets/**/*BuildConfiguration.asset"))
    if not candidates:
        raise tool_error_type(
            "build_config_asset_not_found",
            "Could not auto-detect a *BuildConfiguration.asset under Assets/. Pass buildConfigAsset explicitly.",
        )

    if len(candidates) > 1:
        joined = ", ".join(str(path.relative_to(project_root)) for path in candidates[:10])
        raise tool_error_type(
            "build_config_asset_ambiguous",
            f"Found multiple *BuildConfiguration.asset files. Pass buildConfigAsset explicitly. Candidates: {joined}",
        )

    return candidates[0]


def parse_unity_build_config_profiles(asset_path: Path, tool_error_type: type[Exception]) -> list[dict[str, Any]]:
    try:
        lines = asset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise tool_error_type("build_config_asset_read_failed", str(exc)) from exc

    profiles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_defines = False
    in_debugging = False

    for line in lines:
        if current is not None and line.startswith("  _playerBuildConfig:"):
            profiles.append(current)
            current = None
            in_defines = False
            in_debugging = False
            break

        if line.startswith("  - ConfigName: "):
            if current is not None:
                profiles.append(current)
            current = {
                "configName": line.split(":", 1)[1].strip(),
                "scriptingDefines": [],
                "enableDevelopmentBuild": False,
            }
            in_defines = False
            in_debugging = False
            continue

        if current is None:
            continue

        if line.startswith("    CompilationCSharpSettings:"):
            in_debugging = False
            continue

        if line.startswith("    DebuggingSettings:"):
            in_defines = False
            in_debugging = True
            continue

        if line.startswith("    ") and not line.startswith("      "):
            in_defines = False
            if not line.startswith("    DebuggingSettings:"):
                in_debugging = False

        if line.startswith("      ScriptingDefines:"):
            in_defines = True
            continue

        if in_defines:
            if line.startswith("      - "):
                current["scriptingDefines"].append(line[len("      - "):].strip())
                continue
            in_defines = False

        if in_debugging and line.strip().startswith("EnableDevelopmentBuild:"):
            value = line.split(":", 1)[1].strip()
            current["enableDevelopmentBuild"] = value not in {"0", "false", "False", ""}

    if current is not None:
        profiles.append(current)

    profiles = [profile for profile in profiles if profile.get("configName")]
    if not profiles:
        raise tool_error_type(
            "build_config_profiles_missing",
            f"No build profiles were parsed from {asset_path}. Expected Configurations entries with ConfigName.",
        )

    return profiles


def build_compile_matrix_args_from_build_config(
    project_root: Path,
    build_config_asset: str | None,
    requested_profiles: list[str] | None,
    requested_targets: list[str] | None,
    stop_on_first_failure: bool,
    tool_error_type: type[Exception],
) -> dict[str, Any]:
    asset_path = resolve_build_config_asset_path(project_root, build_config_asset, tool_error_type)
    profiles = parse_unity_build_config_profiles(asset_path, tool_error_type)

    selected_targets = requested_targets or ["Android", "iOS"]
    invalid_targets = [target for target in selected_targets if target not in {"Android", "iOS"}]
    if invalid_targets:
        raise tool_error_type("invalid_targets", f"Unsupported targets: {', '.join(invalid_targets)}")

    selected_profile_names = requested_profiles or [profile["configName"] for profile in profiles]
    selected_profile_set = set(selected_profile_names)
    available_profile_names = {profile["configName"] for profile in profiles}
    missing_profiles = [name for name in selected_profile_names if name not in available_profile_names]
    if missing_profiles:
        raise tool_error_type(
            "unknown_build_profiles",
            f"Unknown build profiles: {', '.join(missing_profiles)}. Available: {', '.join(sorted(available_profile_names))}",
        )

    configurations: list[dict[str, Any]] = []
    resolved_profiles: list[dict[str, Any]] = []
    for profile in profiles:
        if profile["configName"] not in selected_profile_set:
            continue

        resolved_profiles.append(profile)
        option_flags = ["DevelopmentBuild"] if profile.get("enableDevelopmentBuild") else []
        extra_defines = list(profile.get("scriptingDefines") or [])
        for target in selected_targets:
            configurations.append(
                {
                    "name": f"{profile['configName']}-{target}",
                    "target": target,
                    "optionFlags": option_flags,
                    "extraDefines": extra_defines,
                }
            )

    if not configurations:
        raise tool_error_type("build_config_matrix_empty", "No compile configurations were generated from the selected build profiles.")

    relative_asset_path = str(asset_path.relative_to(project_root))
    return {
        "assetPath": relative_asset_path,
        "profiles": resolved_profiles,
        "matrixArgs": {
            "stopOnFirstFailure": stop_on_first_failure,
            "configurations": configurations,
        },
    }


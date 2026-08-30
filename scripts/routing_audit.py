#!/usr/bin/env python3
"""Audit AI routing metadata for AIRoot-attached host repositories.

The script intentionally uses only Python stdlib so it can run in fresh clones.
It understands the simple YAML subset emitted by the AIRoot bootstrap scripts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ALLOWED_PROJECT_KINDS = {
    "unity_project",
    "unity_package_source",
    "unity_native_package_source",
    "unity_package_validation_consumer",
    "unity_embedded_package_validation_consumer",
    "unity_package_validation_demo",
    "unity_package_and_editor_tooling_source",
    "public_unity_mcp_tooling",
    "infrastructure",
    "tooling",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def warn(message: str) -> None:
    print(f"WARN: {message}")


def parse_yaml_list(path: Path, key: str) -> list[str]:
    values: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    in_list = False
    for line in lines:
      if line == f"{key}:":
          in_list = True
          continue
      if in_list and line and not line.startswith(" "):
          break
      if not in_list:
          continue
      stripped = line.strip()
      if stripped.startswith("- path:"):
          values.append(stripped.split(":", 1)[1].strip())
      elif stripped.startswith("- "):
          item = stripped[2:].strip()
          if item != "[]":
              values.append(item)
    return values


def parse_yaml_path_blocks(path: Path, key: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    in_list = False
    current: dict[str, str] | None = None
    for line in lines:
        if line == f"{key}:":
            in_list = True
            continue
        if in_list and line and not line.startswith(" "):
            break
        if not in_list:
            continue
        stripped = line.strip()
        if stripped.startswith("- path:"):
            if current:
                blocks.append(current)
            current = {"path": stripped.split(":", 1)[1].strip()}
        elif current is not None and ":" in stripped:
            block_key, value = stripped.split(":", 1)
            current[block_key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def check_file_exists(path: Path, errors: list[str], label: str) -> None:
    if path.exists():
        ok(f"{label} exists: {path}")
    else:
        errors.append(f"{label} missing: {path}")
        fail(f"{label} missing: {path}")


def exact_file_exists(path: Path) -> bool:
    """Return true only when the directory entry uses the requested spelling."""
    if not path.parent.is_dir():
        return False
    return any(entry.name == path.name and entry.is_file() for entry in path.parent.iterdir())


def check_exact_router(path: Path, errors: list[str], label: str) -> None:
    if exact_file_exists(path):
        ok(f"{label} uses canonical exact name: {path}")
        return
    legacy = path.with_name("Agents.md")
    if exact_file_exists(legacy):
        errors.append(f"{label} uses legacy mixed-case filename: {legacy}")
        fail(f"{label} must be named exactly {path.name}, found {legacy.name}: {legacy}")
        return
    errors.append(f"{label} missing: {path}")
    fail(f"{label} missing: {path}")


def check_yaml_validity(path: Path, errors: list[str]) -> None:
    ruby = shutil.which("ruby")
    if not ruby:
        warn(f"Skipping strict YAML parse because ruby is unavailable: {path}")
        return
    result = subprocess.run(
        [
            ruby,
            "-e",
            (
                "require 'yaml'; require 'date'; data = File.read(ARGV[0]); "
                "begin; "
                "YAML.safe_load(data, permitted_classes: [Date, Time], aliases: false, filename: ARGV[0]); "
                "rescue ArgumentError; YAML.safe_load(data, [Date, Time], [], false, ARGV[0]); end"
            ),
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        ok(f"YAML parses: {path}")
    else:
        errors.append(f"YAML parse failed for {path}: {result.stderr.strip()}")
        fail(f"YAML parse failed for {path}: {result.stderr.strip()}")


def check_repo_router_links(root: Path, errors: list[str]) -> None:
    for link in sorted(root.rglob("AGENTS.repo.md")):
        if ".git" in link.parts:
            continue
        if not link.is_symlink():
            errors.append(f"AGENTS.repo.md is not a symlink: {link}")
            fail(f"AGENTS.repo.md is not a symlink: {link}")
            continue

        project_dir = link.parent
        workspace_router = project_dir.parent / "AGENTS.md"
        if project_dir.parent != root and exact_file_exists(workspace_router):
            expected = "../AGENTS.md"
        else:
            expected = os.path.relpath(root / "AGENTS.md", project_dir)

        actual = os.readlink(link)
        if actual == expected:
            ok(f"{link.relative_to(root)} -> {actual}")
        else:
            errors.append(f"{link} points to {actual}, expected {expected}")
            fail(f"{link} points to {actual}, expected {expected}")


def check_project_kinds(projects: list[str], root: Path, errors: list[str]) -> None:
    pattern = re.compile(r"^- Project kind: `([^`]+)`$", re.MULTILINE)
    for rel in projects:
        router = root / rel / "AGENTS.md"
        if not exact_file_exists(router):
            check_exact_router(router, errors, "Project router")
            continue
        text = router.read_text(encoding="utf-8")
        match = pattern.search(text)
        if not match:
            errors.append(f"Project kind missing: {router}")
            fail(f"Project kind missing: {router}")
            continue
        kind = match.group(1)
        if kind == "gameplay":
            errors.append(f"Legacy generic project kind 'gameplay' found: {router}")
            fail(f"Legacy generic project kind 'gameplay' found: {router}")
        elif kind not in ALLOWED_PROJECT_KINDS:
            errors.append(f"Unsupported project kind '{kind}' in {router}")
            fail(f"Unsupported project kind '{kind}' in {router}")
        else:
            ok(f"{router.relative_to(root)} project kind: {kind}")


def asset_package_jsons(project_dir: Path) -> list[Path]:
    assets_dir = project_dir / "Assets"
    if not assets_dir.exists():
        return []
    return sorted(
        p for p in assets_dir.rglob("package.json")
        if "Packages" not in p.parts and "Library" not in p.parts
    )


def check_unity_baselines(projects: list[str], root: Path, errors: list[str]) -> None:
    baseline_pattern = re.compile(
        r"(Declared Unity baseline(?: in package manifest)?|Package manifest declares Unity baseline):? `([^`]+)`"
    )
    for rel in projects:
        project_dir = root / rel
        packages = asset_package_jsons(project_dir)
        if len(packages) != 1:
            if len(packages) > 1:
                warn(f"Skipping baseline auto-check for {rel}; multiple Assets package.json files found")
            continue
        package_path = packages[0]
        try:
            unity = json.loads(package_path.read_text(encoding="utf-8")).get("unity")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid package.json: {package_path}: {exc}")
            fail(f"Invalid package.json: {package_path}: {exc}")
            continue
        if not unity:
            continue
        memory_dir = project_dir / "Assets/AIOutput/ProjectMemory"
        if not memory_dir.exists():
            continue
        for memory_file in sorted(memory_dir.glob("*.md")):
            text = memory_file.read_text(encoding="utf-8")
            for match in baseline_pattern.finditer(text):
                memory_unity = match.group(2)
                if memory_unity != unity:
                    errors.append(
                        f"Stale Unity baseline in {memory_file}: {memory_unity}, package.json has {unity}"
                    )
                    fail(f"Stale Unity baseline in {memory_file}: {memory_unity}, package.json has {unity}")
                else:
                    ok(f"{memory_file.relative_to(root)} Unity baseline matches package.json: {unity}")


def check_operation_routes(root: Path, topology: Path, errors: list[str]) -> None:
    operations = parse_yaml_path_blocks(topology, "routed_operation_projects")
    for operation in operations:
        operation_path = root / operation["path"]
        check_file_exists(operation_path, errors, "Routed operation project")
        router = operation.get("router")
        if router:
            router_path = root / router
            if router_path.name == "AGENTS.md":
                check_exact_router(router_path, errors, "Routed operation router")
            else:
                check_file_exists(router_path, errors, "Routed operation router")
        if operation["path"] == "AIRoot/Operations/XUUnityLightUnityMcp":
            # The independently versioned MCP repo owns this exact router and its
            # generator. The host verifies the boundary but does not render it.
            mcp_router = root / operation["path"] / "AGENTS.md"
            if exact_file_exists(mcp_router):
                ok(f"XUUnityLightUnityMcp uses canonical child-owned router: {mcp_router}")
            else:
                errors.append(f"XUUnityLightUnityMcp child-owned router missing: {mcp_router}")
                fail(f"XUUnityLightUnityMcp child-owned router missing: {mcp_router}")
            text = mcp_router.read_text(encoding="utf-8") if exact_file_exists(mcp_router) else ""
            for required in ("## Mode Detection", "Standalone:", "llms.txt", "mcp-server.json"):
                if required in text:
                    ok(f"XUUnityLightUnityMcp standalone contract contains: {required}")
                else:
                    errors.append(f"XUUnityLightUnityMcp standalone contract missing: {required}")
                    fail(f"XUUnityLightUnityMcp standalone contract missing: {required}")


def check_markdown_mirrors(root: Path, topology: Path, errors: list[str]) -> None:
    routed_operations = parse_yaml_path_blocks(topology, "routed_operation_projects")
    optional_projects = parse_yaml_path_blocks(topology, "optional_local_projects")
    mirrors = [
        root / "AGENTS.md",
        root / "AIModules/XUUnityInternal/knowledge/host_topology.md",
        root / "WORKSPACE.md",
    ]
    existing_mirrors = [path for path in mirrors if path.exists()]
    for operation in routed_operations:
        rel = operation["path"]
        for mirror in existing_mirrors:
            text = mirror.read_text(encoding="utf-8")
            if rel in text:
                ok(f"{mirror.relative_to(root)} mirrors routed operation: {rel}")
            else:
                errors.append(f"{mirror} does not mirror routed operation from registry: {rel}")
                fail(f"{mirror} does not mirror routed operation from registry: {rel}")
    for optional in optional_projects:
        rel = optional["path"]
        overlay = root / "AIModules/XUUnityInternal/knowledge/host_topology.md"
        if overlay.exists() and rel in overlay.read_text(encoding="utf-8"):
            ok(f"{overlay.relative_to(root)} mirrors optional local project: {rel}")
        else:
            errors.append(f"{overlay} does not mirror optional local project from registry: {rel}")
            fail(f"{overlay} does not mirror optional local project from registry: {rel}")


def check_optional_projects(root: Path, topology: Path, errors: list[str]) -> None:
    routed = set(parse_yaml_list(topology, "routed_projects"))
    optional = parse_yaml_path_blocks(topology, "optional_local_projects")
    for block in optional:
        rel = block["path"]
        if rel in routed:
            errors.append(f"Optional local project is also listed as routed project: {rel}")
            fail(f"Optional local project is also listed as routed project: {rel}")
        if block.get("tracked_release_proof") != "false":
            errors.append(f"Optional local project must not count as release proof: {rel}")
            fail(f"Optional local project must not count as release proof: {rel}")
        if (root / rel).exists():
            ok(f"Optional local project present: {rel}")
        else:
            ok(f"Optional local project absent is allowed: {rel}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit AIRoot AI routing metadata.")
    parser.add_argument("--host-root", default=Path.cwd(), type=Path)
    args = parser.parse_args()

    root = args.host_root.resolve()
    errors: list[str] = []

    check_exact_router(root / "AGENTS.md", errors, "Host router")
    check_file_exists(root / "AIRoot/Modules/XUUnity/README.md", errors, "XUUnity public core")

    topology = root / "AIOutput/Registry/host_topology.yaml"
    setup_status = root / "AIOutput/Registry/setup_status.yaml"
    check_file_exists(topology, errors, "Host topology registry")
    check_file_exists(setup_status, errors, "Setup status registry")
    if topology.exists():
        check_yaml_validity(topology, errors)
    if setup_status.exists():
        check_yaml_validity(setup_status, errors)

    if topology.exists():
        projects = parse_yaml_list(topology, "routed_projects")
        for rel in projects:
            check_file_exists(root / rel, errors, "Routed project")
        check_repo_router_links(root, errors)
        check_project_kinds(projects, root, errors)
        check_unity_baselines(projects, root, errors)
        check_optional_projects(root, topology, errors)
        check_operation_routes(root, topology, errors)
        check_markdown_mirrors(root, topology, errors)

    if errors:
        print(f"\nRouting audit failed with {len(errors)} issue(s).", file=sys.stderr)
        return 1
    print("\nRouting audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

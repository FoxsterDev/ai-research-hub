#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path


PROJECT_ROUTER_NAMES = ("Agents.md",)


def find_project_routers(root: Path) -> list[Path]:
    routers: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir() or child.name in {".git", "AIRoot", "AIPromts", "AIModules"}:
            continue
        for name in PROJECT_ROUTER_NAMES:
            candidate = child / name
            if candidate.exists():
                routers.append(candidate)
                break
    return sorted(routers)


def load_repo_contract(repo_router: Path) -> tuple[bool, bool]:
    text = repo_router.read_text()
    has_project_memory_rule = "Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`." in text
    has_generated_reports_rule = "Generated project-local reports, audits, architecture notes, SDK reviews, and knowledge drafts belong in `<Project>/Assets/AIOutput/`." in text
    return has_project_memory_rule, has_generated_reports_rule


def audit_router(path: Path) -> list[str]:
    text = path.read_text()
    findings: list[str] = []

    if re.search(r"Relevant prior analysis outputs from `Assets/AIOutput/ProjectMemory/`", text):
        findings.append("prior outputs point only at ProjectMemory")

    if re.search(r"Durable project-local rules belong in `Assets/AIOutput/ProjectMemory/`\.", text):
        findings.append("duplicates local durable-guidance storage semantics")

    if re.search(r"Generated reports belong in `Assets/AIOutput/`\.", text):
        findings.append("duplicates local generated-report storage semantics")

    mentions_storage_paths = "`Assets/AIOutput/`" in text and "`Assets/AIOutput/ProjectMemory/`" in text
    references_repo_contract = "Follow the repo-level AI output storage rule from `../Agents.md`." in text
    has_local_storage_section = "## Storage Rule" in text or "## Expected AI Output" in text or "## Expected Project Memory" in text
    if mentions_storage_paths and not references_repo_contract and has_local_storage_section:
        findings.append("mentions storage paths without referencing repo-level storage contract")

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit project routers against repo-level storage semantics")
    parser.add_argument("--repo-root", default=".", help="Host repo root containing Agents.md and project folders")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.repo_root).resolve()
    repo_router = root / "Agents.md"
    if not repo_router.exists():
        print(f"FAIL: repo router not found at {repo_router}")
        return 2

    has_pm_rule, has_reports_rule = load_repo_contract(repo_router)
    if not (has_pm_rule and has_reports_rule):
        print("FAIL: repo-level storage contract in Agents.md is incomplete")
        return 2

    routers = find_project_routers(root)
    if not routers:
        print("WARN: no project routers found")
        return 0

    problem_count = 0
    for router in routers:
        findings = audit_router(router)
        if findings:
            problem_count += 1
            print(f"{router.relative_to(root)}:")
            for finding in findings:
                print(f"  - {finding}")

    if problem_count == 0:
        print("OK: project routers are consistent with repo-level storage semantics")
        return 0

    print(f"FAIL: storage drift detected in {problem_count} router(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

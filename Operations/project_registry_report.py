#!/usr/bin/env python3
"""Portfolio project-registry report and structural readiness scorer.

Reusable, host-agnostic, stdlib-only. Point it at a host repo that has a project
registry YAML (the portfolio index). For every listed project it renders a status
report and computes a structural readiness score from objective on-disk signals,
then optionally persists the score back into the registry.

The tool carries NO host-specific assumptions. WHICH signals define readiness,
which extra columns to show, and which completeness dimensions to check all come
from a rubric config (--rubric <json>). Without a rubric it uses a neutral default
(router + project-memory presence only), so it works on any registry out of the
box. Host-specific rubrics (required files, presence checks, extra columns, and
completeness dimensions) live in the host repo alongside its registry.

The registry YAML uses a small, predictable subset parsed here directly, so this
tool does not depend on PyYAML.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_REL = "AIOutput/Registry/project_registry.yaml"

# Neutral, assumption-free default. Host rubrics override via --rubric.
DEFAULT_RUBRIC: dict[str, Any] = {
    "bands": [["strong", 85], ["usable", 65], ["fragile", 40], ["blocked", 0]],
    "signals": [
        {"label": "router", "weight": 50, "kind": "file", "target_field": "router_file", "fallback": "Agents.md"},
        {"label": "project_memory", "weight": 50, "kind": "dir", "target_field": "project_memory_path"},
    ],
    "columns": [],
    "completeness_dimensions": [
        ["project_type", "type"],
        ["platforms", "platforms"],
        ["project_memory_path", "memory_status"],
    ],
}


def strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def band_for(score: int, bands: list[list[Any]]) -> str:
    for name, floor in bands:
        if score >= floor:
            return name
    return bands[-1][0] if bands else "unknown"


def parse_projects(lines: list[str]) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    in_projects = False
    current: dict[str, Any] | None = None
    for idx, raw in enumerate(lines):
        if raw.strip() == "projects:":
            in_projects = True
            continue
        if not in_projects:
            continue
        id_match = re.match(r"^  - id:\s*(.+)$", raw)
        if id_match:
            if current is not None:
                current["end"] = idx
                projects.append(current)
            current = {"id": strip_scalar(id_match.group(1).strip()), "start": idx, "fields": {}}
            continue
        if current is None:
            continue
        field_match = re.match(r"^    ([A-Za-z0-9_]+):\s*(.*)$", raw)
        if field_match and field_match.group(2).strip() != "":
            current["fields"][field_match.group(1)] = strip_scalar(field_match.group(2).strip())
    if current is not None:
        current["end"] = len(lines)
        projects.append(current)
    for proj in projects:
        proj["block_text"] = "\n".join(lines[proj["start"] : proj["end"]])
    return projects


def nested_scalar(block_text: str, key: str) -> str:
    match = re.search(rf"^\s+{re.escape(key)}:\s*(.+)$", block_text, re.M)
    return strip_scalar(match.group(1).strip()) if match else ""


def list_field(block_text: str, key: str) -> list[str]:
    lines = block_text.splitlines()
    out: list[str] = []
    capturing = False
    key_indent = 0
    for ln in lines:
        head = re.match(r"^(\s*)([A-Za-z0-9_]+):\s*(.*)$", ln)
        if head and head.group(2) == key:
            value = head.group(3).strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                return [strip_scalar(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
            capturing = value == ""
            key_indent = len(head.group(1))
            continue
        if capturing:
            item = re.match(r"^(\s*)-\s+(.*)$", ln)
            if item and len(item.group(1)) > key_indent:
                out.append(strip_scalar(item.group(2).strip()))
            elif re.match(r"^\s*[A-Za-z0-9_]+:", ln):
                break
    return out


def eval_signal(sig: dict[str, Any], project_dir: Path, fields: dict[str, str], block_text: str) -> float:
    only_if = sig.get("only_if_field")
    if only_if is not None and fields.get(only_if, "") != sig.get("only_if_value"):
        return 1.0 if sig.get("credit_when_not_applicable", True) else 0.0

    kind = sig.get("kind")
    if kind == "file":
        rel = sig.get("path") or fields.get(sig.get("target_field", ""), sig.get("fallback", ""))
        return 1.0 if rel and (project_dir / rel).exists() else 0.0
    if kind == "dir":
        target = project_dir
        base_field = sig.get("base_field")
        if base_field:
            base = fields.get(base_field, sig.get("fallback_base", ""))
            if base:
                target = target / base
        rel = sig.get("path") or (fields.get(sig.get("target_field", ""), sig.get("fallback", "")) if sig.get("target_field") else "")
        if rel:
            target = target / rel
        if sig.get("subpath"):
            target = target / sig["subpath"]
        return 1.0 if target.is_dir() else 0.0
    if kind == "files_fraction":
        base = fields.get(sig.get("base_field", ""), sig.get("fallback_base", "")) if sig.get("base_field") else ""
        base_dir = project_dir / base if base else project_dir
        files = sig.get("files", [])
        if not files:
            return 1.0
        present = sum(1 for name in files if (base_dir / name).exists())
        return present / len(files)
    if kind == "block_keys":
        keys = sig.get("keys", [])
        return 1.0 if keys and all(k in block_text for k in keys) else (1.0 if not keys else 0.0)
    return 0.0


def compute_readiness(project_dir: Path, proj: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    fields = proj["fields"]
    block = proj["block_text"]
    signals = rubric.get("signals", [])
    total = 0.0
    gaps: list[str] = []
    for sig in signals:
        frac = eval_signal(sig, project_dir, fields, block)
        total += sig.get("weight", 0) * frac
        if frac < 1.0:
            gaps.append(sig.get("label", sig.get("kind", "signal")))
    score = round(total)
    return {"score": score, "band": band_for(score, rubric.get("bands", DEFAULT_RUBRIC["bands"])), "gaps": gaps}


def metadata_completeness(proj: dict[str, Any], dimensions: list[list[str]]) -> list[tuple[str, bool]]:
    block = proj["block_text"]
    result: list[tuple[str, bool]] = []
    for key, label in dimensions:
        result.append((label, bool(re.search(rf"^\s+{re.escape(key)}:", block, re.M))))
    return result


def build_rows(registry_path: Path, projects: list[dict[str, Any]], rubric: dict[str, Any]) -> list[dict[str, Any]]:
    registry_dir = registry_path.parent
    dimensions = rubric.get("completeness_dimensions", [])
    columns = rubric.get("columns", [])
    rows: list[dict[str, Any]] = []
    for proj in projects:
        fields = proj["fields"]
        raw_path = fields.get("path", "")
        project_dir = (registry_dir / raw_path).resolve() if raw_path else registry_dir
        block = proj["block_text"]
        rows.append(
            {
                "id": proj["id"],
                "project_type": fields.get("project_type", ""),
                "platforms": list_field(block, "platforms"),
                "columns": [(header, nested_scalar(block, field) or "—") for header, field in columns],
                "readiness": compute_readiness(project_dir, proj, rubric),
                "completeness": metadata_completeness(proj, dimensions),
                "as_of": datetime.date.today().isoformat(),
            }
        )
    return rows


def render_markdown(registry_path: Path, rows: list[dict[str, Any]], rubric: dict[str, Any]) -> str:
    today = datetime.date.today().isoformat()
    bands = rubric.get("bands", DEFAULT_RUBRIC["bands"])
    extra_headers = [header for header, _ in (rows[0]["columns"] if rows else [])]

    lines: list[str] = []
    lines.append("# Portfolio Status")
    lines.append("")
    lines.append(f"Generated {today} from `{registry_path.as_posix()}` by `project_registry_report.py`.")
    lines.append("")
    lines.append(f"Projects: {len(rows)}")
    band_counts: dict[str, int] = {}
    for row in rows:
        band = row["readiness"]["band"]
        band_counts[band] = band_counts.get(band, 0) + 1
    lines.append("Readiness bands — " + " · ".join(f"{name}: {band_counts.get(name, 0)}" for name, _ in bands))
    lines.append("")

    lines.append("## Readiness (structural, auto-derived)")
    lines.append("")
    header_cells = ["Project", "Type", "Platforms", *extra_headers, "Score", "Band", "Gaps"]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "---|" * len(header_cells))
    for row in sorted(rows, key=lambda r: (-r["readiness"]["score"], r["id"])):
        r = row["readiness"]
        gaps = ", ".join(r["gaps"]) if r["gaps"] else "—"
        platforms = ", ".join(row["platforms"]) or "—"
        extra = [value for _, value in row["columns"]]
        cells = [row["id"], row["project_type"] or "—", platforms, *extra, str(r["score"]), r["band"], gaps]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    if rows and rows[0]["completeness"]:
        dim_labels = [label for label, _ in rows[0]["completeness"]]
        lines.append("## Metadata Completeness")
        lines.append("")
        lines.append("| Project | " + " | ".join(dim_labels) + " |")
        lines.append("|---" * (len(dim_labels) + 1) + "|")
        for row in rows:
            cells = ["✅" if present else "—" for _, present in row["completeness"]]
            lines.append(f"| {row['id']} | " + " | ".join(cells) + " |")
        lines.append("")
        covered = sum(1 for row in rows if all(present for _, present in row["completeness"]))
        lines.append(f"Full-metadata coverage: {covered}/{len(rows)} projects.")
        lines.append("")

    band_desc = ", ".join(f"{name} ≥ {floor}" for name, floor in bands)
    lines.append(f"_Readiness is a structural proxy from on-disk signals, not a full health audit. Bands: {band_desc}._")
    lines.append("")
    return "\n".join(lines)


def write_back(registry_path: Path, lines: list[str], projects: list[dict[str, Any]], rows_by_id: dict[str, dict[str, Any]]) -> None:
    new_lines = list(lines)
    for proj in sorted(projects, key=lambda p: p["start"], reverse=True):
        row = rows_by_id.get(proj["id"])
        if not row:
            continue
        block = new_lines[proj["start"] : proj["end"]]
        block = [ln for ln in block if not re.match(r"^    ai_readiness_(score|band|basis|as_of):", ln)]
        inject = [
            f"    ai_readiness_score: {row['readiness']['score']}",
            f"    ai_readiness_band: {row['readiness']['band']}",
            "    ai_readiness_basis: structural_auto",
            f"    ai_readiness_as_of: {row['as_of']}",
        ]
        anchor = None
        for i, ln in enumerate(block):
            if re.match(r"^    ai_baseline_status:", ln):
                anchor = i
        if anchor is None:
            insert_at = len(block)
            while insert_at > 0 and block[insert_at - 1].strip() == "":
                insert_at -= 1
            block[insert_at:insert_at] = inject
        else:
            block[anchor + 1 : anchor + 1] = inject
        new_lines[proj["start"] : proj["end"]] = block
    registry_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def load_rubric(repo_root: Path, rubric_arg: str | None) -> dict[str, Any]:
    if not rubric_arg:
        return DEFAULT_RUBRIC
    rubric_path = (repo_root / rubric_arg).resolve()
    if not rubric_path.exists():
        print(f"project_registry_report: rubric not found at {rubric_path}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(rubric_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Portfolio project-registry report and structural readiness scorer.")
    parser.add_argument("--repo-root", default=".", help="Host repository root. Defaults to current directory.")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY_REL, help="Registry path relative to --repo-root.")
    parser.add_argument("--rubric", help="Readiness rubric JSON (host-specific) relative to --repo-root. Omit for the neutral default.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of markdown.")
    parser.add_argument("--out", help="Write the markdown report to this path (relative to --repo-root).")
    parser.add_argument("--write-back", action="store_true", help="Persist computed ai_readiness fields back into the registry.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    registry_path = (repo_root / args.registry).resolve()
    if not registry_path.exists():
        print(f"project_registry_report: registry not found at {registry_path}", file=sys.stderr)
        return 2

    rubric = load_rubric(repo_root, args.rubric)
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    projects = parse_projects(lines)
    rows = build_rows(registry_path, projects, rubric)
    rows_by_id = {row["id"]: row for row in rows}

    if args.write_back:
        write_back(registry_path, lines, projects, rows_by_id)
        lines = registry_path.read_text(encoding="utf-8").splitlines()
        projects = parse_projects(lines)
        rows = build_rows(registry_path, projects, rubric)
        rows_by_id = {row["id"]: row for row in rows}

    if args.json:
        print(json.dumps({"registry": registry_path.as_posix(), "projects": rows}, indent=2, ensure_ascii=False, default=str))
    else:
        report = render_markdown(registry_path, rows, rubric)
        print(report)
        if args.out:
            (repo_root / args.out).resolve().write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

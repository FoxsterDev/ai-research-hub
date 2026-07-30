#!/usr/bin/env python3
"""Model-independent reduced-stack obligation resolver.

Derives the minimum required XUUnity stack for one task from the task
envelope, repository snapshot, public ruleset, and attested extensions —
never from a model's claims. Implements the deterministic algorithm in
``AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md``
("Reduced-Stack Derivation"):

- whole atomic files selected from evidence-derived rules; reduction happens
  by selecting fewer files, never by truncating a selected file;
- extensions apply in public → host → project order; an existing project
  override of a matched family is added alongside the public owner and marked
  effective for conflicts;
- diff-derived facts can only add obligations, never erase them;
- missing required artifacts, empty required globs, extension conflicts, and
  unresolved critical signals fail closed.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import contract_validator
import xuunity_canonical as xc

RULESET_SCHEMA = "xuunity.reduced-stack-rules.schema.json"
ENVELOPE_SCHEMA = "xuunity.task-envelope.schema.json"
PLAN_SCHEMA = "xuunity.stack-plan.schema.json"

PLAN_SCHEMA_VERSION = "xuunity.stack-plan.v1"

RUNTIME_CONTEXT_BASENAMES = {"agents.md", "claude.md"}

MAX_INSPECTED_FILES = 50
MAX_INSPECTED_BYTES = 1_000_000

BASE_DELIVERY_MODES = [
    "host_injected_bundle",
    "observed_loader_call",
    "native_file_reads",
]


class ResolverUsageError(ValueError):
    """Bad inputs: schema violations, hash mismatches, unreadable files."""


class PlanError(ValueError):
    """Evidence-derived plan failure: missing artifacts, empty globs,
    extension conflicts, path escapes."""


@dataclass
class Facts:
    task_kind: str
    task_text: str
    protocol_id: str
    risk_class: str
    resolved_project: str | None
    referenced_paths: list[str]
    planned_paths: list[str]
    execution_contract: dict[str, Any] | None
    content_corpus: list[tuple[str, str]] = field(default_factory=list)
    source: str = "envelope"

    @property
    def all_paths(self) -> list[str]:
        return self.referenced_paths + self.planned_paths

    @property
    def extensions(self) -> set[str]:
        return {
            os.path.splitext(path)[1].lower()
            for path in self.all_paths
            if os.path.splitext(path)[1]
        }


def rule_hash(rule: dict[str, Any]) -> str:
    return xc.sha256_bytes(xc.canonical_bytes(rule))


def compute_ruleset_hash(ruleset: dict[str, Any]) -> str:
    return xc.document_hash(ruleset, "ruleset_hash")


@dataclass
class LoadedRuleset:
    rules: list[dict[str, Any]]
    override_path_templates: list[str]
    base_hash: str
    module_prefix: str


def _validate_ruleset_document(document: dict[str, Any], origin: str) -> None:
    errors = contract_validator.validate_against(RULESET_SCHEMA, document)
    if errors:
        raise ResolverUsageError(f"{origin}: schema errors: {errors[:5]}")
    computed = compute_ruleset_hash(document)
    if computed != document["ruleset_hash"]:
        raise ResolverUsageError(
            f"{origin}: ruleset_hash mismatch (expected {computed})"
        )


def load_ruleset(
    ruleset_path: Path,
    repo_root: Path,
    extension_paths: list[Path],
    declared_extensions: list[dict[str, Any]],
) -> LoadedRuleset:
    base = xc.load_strict(ruleset_path)
    _validate_ruleset_document(base, str(ruleset_path))
    base_hash = base["ruleset_hash"]

    try:
        module_prefix = (
            ruleset_path.resolve().parent.parent.relative_to(Path(repo_root).resolve())
        ).as_posix()
    except ValueError as error:
        raise ResolverUsageError(
            f"ruleset must live inside the repository: {error}"
        ) from error

    rules_by_id: dict[str, dict[str, Any]] = {}
    for rule in base["rules"]:
        if rule["id"] in rules_by_id:
            raise PlanError(f"duplicate rule id in base ruleset: {rule['id']}")
        rules_by_id[rule["id"]] = rule

    if len(extension_paths) != len(declared_extensions):
        raise ResolverUsageError(
            "every --ruleset-extension must be declared in the envelope's "
            "ruleset_extensions (ordered host, then project)"
        )
    for extension_path, declared in zip(extension_paths, declared_extensions):
        data = Path(extension_path).read_bytes()
        actual_sha = xc.sha256_bytes(data)
        if actual_sha != declared["sha256"]:
            raise ResolverUsageError(
                f"{extension_path}: sha256 does not match the attested "
                f"envelope declaration"
            )
        if declared["parent_hash"] != base_hash:
            raise ResolverUsageError(
                f"{extension_path}: parent_hash does not match the base "
                f"ruleset hash"
            )
        extension = xc.strict_parse(data)
        _validate_ruleset_document(extension, str(extension_path))
        for rule in extension["rules"]:
            rule_id = rule["id"]
            extends = rule.get("extends")
            if rule_id in rules_by_id and not extends:
                raise PlanError(
                    f"extension rule {rule_id} duplicates an existing rule "
                    f"without declaring extends"
                )
            if extends:
                parent = rules_by_id.get(extends)
                if parent is None:
                    raise PlanError(
                        f"extension rule {rule_id} extends unknown rule "
                        f"{extends}"
                    )
                replaced = rule.get("replaces_fields") or []
                if replaced:
                    policy = parent.get("extension_policy") or {}
                    if not policy.get("allow_replace"):
                        raise PlanError(
                            f"rule {extends} does not allow field replacement"
                        )
                    if rule.get("parent_rule_hash") != rule_hash(parent):
                        raise PlanError(
                            f"extension rule {rule_id}: parent_rule_hash does "
                            f"not match rule {extends}"
                        )
                    merged = dict(parent)
                    for name in replaced:
                        if name in {"id", "extends", "replaces_fields"}:
                            raise PlanError(
                                f"extension rule {rule_id}: field {name} "
                                f"cannot be replaced"
                            )
                        merged[name] = rule[name]
                    rules_by_id[extends] = merged
                    continue
                merged = dict(parent)
                merged_requirements = list(parent["requirements"]) + list(
                    rule.get("requirements") or []
                )
                merged["requirements"] = merged_requirements
                rules_by_id[extends] = merged
                continue
            rules_by_id[rule_id] = rule

    _check_dependency_cycles(rules_by_id)
    rules = sorted(
        rules_by_id.values(), key=lambda rule: (rule["priority"], rule["id"])
    )
    return LoadedRuleset(
        rules=rules,
        override_path_templates=list(base.get("override_path_templates") or []),
        base_hash=base_hash,
        module_prefix=module_prefix,
    )


def _check_dependency_cycles(rules_by_id: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(rule_id: str, chain: tuple[str, ...]) -> None:
        if rule_id in done:
            return
        if rule_id in visiting:
            raise PlanError(f"dependency cycle: {' -> '.join(chain + (rule_id,))}")
        visiting.add(rule_id)
        rule = rules_by_id.get(rule_id)
        if rule is None:
            raise PlanError(f"unknown dependency rule id: {rule_id}")
        for dependency in rule.get("dependencies") or []:
            visit(dependency, chain + (rule_id,))
        visiting.discard(rule_id)
        done.add(rule_id)

    for rule_id in rules_by_id:
        visit(rule_id, ())


_KNOWN_SELECTOR_FAMILIES = {
    "always", "protocol_ids", "task_kinds", "keywords_any",
    "referenced_path_globs_any", "planned_path_globs_any", "extensions_any",
    "content_regex_any", "execution_contract_equals", "risk_classes",
    "resolved_project_present",
}


def _keyword_present(keyword: str, text: str) -> bool:
    pattern = (
        r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
    )
    return re.search(pattern, text.lower()) is not None


def rule_matches(rule: dict[str, Any], facts: Facts) -> list[str]:
    """Return the matched selector families (empty when the rule does not
    match). Every populated family must match; unknown families fail closed."""
    selectors = rule["selectors"]
    unknown = set(selectors) - _KNOWN_SELECTOR_FAMILIES
    if unknown:
        raise PlanError(
            f"rule {rule['id']}: unknown selector families {sorted(unknown)}"
        )
    matched: list[str] = []
    for family, value in selectors.items():
        if family == "always":
            if value is not True:
                return []
            matched.append(family)
        elif family == "protocol_ids":
            if facts.protocol_id not in value:
                return []
            matched.append(family)
        elif family == "task_kinds":
            if facts.task_kind not in value:
                return []
            matched.append(family)
        elif family == "keywords_any":
            if not any(
                _keyword_present(keyword, facts.task_text) for keyword in value
            ):
                return []
            matched.append(family)
        elif family == "referenced_path_globs_any":
            if not any(
                fnmatch.fnmatch(path, pattern)
                for pattern in value
                for path in facts.referenced_paths
            ):
                return []
            matched.append(family)
        elif family == "planned_path_globs_any":
            if not any(
                fnmatch.fnmatch(path, pattern)
                for pattern in value
                for path in facts.planned_paths
            ):
                return []
            matched.append(family)
        elif family == "extensions_any":
            if not any(ext.lower() in facts.extensions for ext in value):
                return []
            matched.append(family)
        elif family == "content_regex_any":
            corpus = facts.content_corpus
            if not any(
                re.search(pattern, text)
                for pattern in value
                for _, text in corpus
            ):
                return []
            matched.append(family)
        elif family == "execution_contract_equals":
            contract = facts.execution_contract or {}
            if not all(
                contract.get(key) == expected for key, expected in value.items()
            ):
                return []
            matched.append(family)
        elif family == "risk_classes":
            if facts.risk_class not in value:
                return []
            matched.append(family)
        elif family == "resolved_project_present":
            if bool(facts.resolved_project) is not bool(value):
                return []
            matched.append(family)
    if not matched:
        return []
    return matched


def _expand_placeholders(
    template: str, module_prefix: str, project: str | None
) -> str | None:
    value = template.replace("{module}", module_prefix)
    if "{project}" in value:
        if not project:
            return None
        value = value.replace("{project}", project)
    return value


def _expand_glob(repo_root: Path, pattern: str) -> list[str]:
    if "**" in pattern:
        raise PlanError(f"recursive globs are not supported: {pattern}")
    static_parts: list[str] = []
    for part in pattern.split("/"):
        if any(character in part for character in "*?["):
            break
        static_parts.append(part)
    base = Path(repo_root, *static_parts)
    if not base.is_dir():
        return []
    matches: list[str] = []
    prefix_len = len(static_parts)
    remaining = pattern.split("/")[prefix_len:]
    if len(remaining) != 1:
        raise PlanError(
            f"glob wildcards are supported only in the final segment: {pattern}"
        )
    for name in sorted(os.listdir(base)):
        candidate = "/".join(static_parts + [name])
        if fnmatch.fnmatch(candidate, pattern) and (base / name).is_file():
            matches.append(candidate)
    return matches


def _fingerprint(repo_root: Path, repo_path: str) -> dict[str, Any]:
    full = Path(repo_root) / repo_path
    data = full.read_bytes()
    return {
        "sha256": xc.sha256_bytes(data),
        "bytes": len(data),
        "lines": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0),
        "file_mode": f"{os.stat(full).st_mode & 0o7777:o}",
    }


def build_facts(
    envelope: dict[str, Any],
    task_text: str,
    repo_root: Path,
    execution_contract: dict[str, Any] | None,
    extra_paths: list[str] | None = None,
    extra_content: str | None = None,
) -> Facts:
    referenced = [
        xc.normalize_repo_path(path) for path in envelope["referenced_paths"]
    ]
    planned = [
        xc.normalize_repo_path(path)
        for path in envelope["planned_mutation_paths"]
    ]
    if extra_paths:
        planned = planned + [
            xc.normalize_repo_path(path) for path in extra_paths
        ]
    corpus: list[tuple[str, str]] = []
    for path in dict.fromkeys(referenced + planned):
        if len(corpus) >= MAX_INSPECTED_FILES:
            break
        full = Path(repo_root) / path
        if not full.is_file():
            continue
        try:
            data = full.read_bytes()[:MAX_INSPECTED_BYTES]
            corpus.append((path, data.decode("utf-8", errors="replace")))
        except OSError:
            continue
    if extra_content:
        corpus.append(("<diff>", extra_content))
    return Facts(
        task_kind=envelope["task_kind"],
        task_text=task_text,
        protocol_id=envelope["protocol_id"],
        risk_class=envelope["risk_class"],
        resolved_project=envelope.get("resolved_project"),
        referenced_paths=referenced,
        planned_paths=planned,
        execution_contract=execution_contract,
        content_corpus=corpus,
    )


def resolve_task_text(
    envelope: dict[str, Any], task_text_file: Path | None
) -> str:
    if task_text_file is not None:
        raw = Path(task_text_file).read_bytes()
    elif envelope.get("task_text") is not None:
        raw = str(envelope["task_text"]).encode("utf-8")
    elif envelope.get("task_text_ref"):
        raw = Path(envelope["task_text_ref"]).read_bytes()
    else:
        raise ResolverUsageError(
            "the resolver requires task_text, task_text_ref, or "
            "--task-text-file"
        )
    if xc.sha256_bytes(raw) != envelope["task_text_sha256"]:
        raise ResolverUsageError("task text does not match task_text_sha256")
    return raw.decode("utf-8", errors="strict")


def _match_all(
    loaded: LoadedRuleset, facts: Facts
) -> dict[str, list[str]]:
    matched: dict[str, list[str]] = {}
    for rule in loaded.rules:
        families = rule_matches(rule, facts)
        if families:
            matched[rule["id"]] = families
    changed = True
    rules_by_id = {rule["id"]: rule for rule in loaded.rules}
    while changed:
        changed = False
        for rule_id in list(matched):
            for dependency in rules_by_id[rule_id].get("dependencies") or []:
                if dependency not in matched:
                    matched[dependency] = [f"dependency_of:{rule_id}"]
                    changed = True
    return matched


def derive_plan(
    repo_root: Path,
    ruleset_path: Path,
    envelope: dict[str, Any],
    task_text_file: Path | None = None,
    extension_paths: list[Path] | None = None,
    execution_contract: dict[str, Any] | None = None,
    checker_dir: Path | None = None,
) -> dict[str, Any]:
    errors = contract_validator.validate_against(ENVELOPE_SCHEMA, envelope)
    if errors:
        raise ResolverUsageError(f"task envelope schema errors: {errors[:5]}")
    task_text = resolve_task_text(envelope, task_text_file)
    loaded = load_ruleset(
        ruleset_path,
        repo_root,
        list(extension_paths or []),
        list(envelope.get("ruleset_extensions") or []),
    )
    if envelope["ruleset_hash"] != loaded.base_hash:
        raise ResolverUsageError(
            "envelope ruleset_hash does not match the supplied ruleset"
        )
    facts = build_facts(envelope, task_text, repo_root, execution_contract)
    matched = _match_all(loaded, facts)
    plan = _plan_from_matches(
        repo_root, loaded, envelope, facts, matched, checker_dir
    )
    plan_errors = contract_validator.validate_against(PLAN_SCHEMA, plan)
    if plan_errors:
        raise ResolverUsageError(
            f"internal error: derived plan fails its schema: {plan_errors[:5]}"
        )
    return plan


def _plan_from_matches(
    repo_root: Path,
    loaded: LoadedRuleset,
    envelope: dict[str, Any],
    facts: Facts,
    matched: dict[str, list[str]],
    checker_dir: Path | None,
) -> dict[str, Any]:
    rules_by_id = {rule["id"]: rule for rule in loaded.rules}
    unresolved: list[dict[str, Any]] = []
    groups: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, dict[str, Any]] = {}
    semantic_checks: list[dict[str, Any]] = []

    def expand(template: str) -> str | None:
        return _expand_placeholders(
            template, loaded.module_prefix, facts.resolved_project
        )

    def add_artifact(
        repo_path: str,
        rule: dict[str, Any],
        group_id: str,
        weight: int,
        phase: str,
        families: list[str],
        override_family: str | None = None,
        effective_owner: str | None = None,
    ) -> None:
        entry = artifacts.get(repo_path)
        if entry is None:
            fingerprint = _fingerprint(repo_root, repo_path)
            modes = list(BASE_DELIVERY_MODES)
            if os.path.basename(repo_path).lower() in RUNTIME_CONTEXT_BASENAMES:
                modes.append("runtime_project_context")
            entry = {
                "path": repo_path,
                **fingerprint,
                "atomicity": "full_file",
                "phase": phase,
                "source_rule_ids": [],
                "trigger_reasons": [],
                "groups": [],
                "weight": 0,
                "accepted_delivery_modes": modes,
                "override_family": override_family,
                "effective_owner": effective_owner,
            }
            artifacts[repo_path] = entry
        if rule["id"] not in entry["source_rule_ids"]:
            entry["source_rule_ids"].append(rule["id"])
        for family in families:
            reason = f"{rule['id']}:{family}"
            if reason not in entry["trigger_reasons"]:
                entry["trigger_reasons"].append(reason)
        if group_id not in entry["groups"]:
            entry["groups"].append(group_id)
        entry["weight"] = max(entry["weight"], weight)
        if override_family and entry["override_family"] is None:
            entry["override_family"] = override_family
        if effective_owner:
            entry["effective_owner"] = effective_owner
        phases = ["before_first_mutation", "before_closeout", "on_reconcile"]
        if phases.index(phase) < phases.index(entry["phase"]):
            entry["phase"] = phase

    for rule_id in sorted(
        matched, key=lambda rid: (rules_by_id[rid]["priority"], rid)
    ):
        rule = rules_by_id[rule_id]
        families = matched[rule_id]
        for requirement in rule["requirements"]:
            group_id = f"{rule_id}.{requirement['id']}"
            mode = requirement["mode"]
            weight = int(requirement.get("weight") or 0)
            phase = requirement.get("phase") or "before_first_mutation"
            optional = bool(requirement.get("optional"))

            if mode == "semantic_checker":
                checker_id = requirement["checker_id"]
                checker_path = (
                    Path(checker_dir) / f"{checker_id}.py"
                    if checker_dir
                    else Path(__file__).resolve().parent / f"{checker_id}.py"
                )
                checker_sha = (
                    xc.sha256_file(checker_path)
                    if checker_path.is_file()
                    else None
                )
                if checker_sha is None:
                    raise PlanError(
                        f"semantic checker implementation missing: {checker_id}"
                    )
                input_sha = envelope.get("execution_contract_sha256")
                if input_sha is None and requirement.get(
                    "empty_input_policy", "fail"
                ) == "fail":
                    unresolved.append(
                        {
                            "signal": f"semantic_input_missing:{checker_id}",
                            "severity": "critical",
                        }
                    )
                semantic_checks.append(
                    {
                        "checker_id": checker_id,
                        "checker_sha256": checker_sha,
                        "input_schema": requirement["input_schema"],
                        "input_ref": envelope.get("execution_contract_ref"),
                        "input_sha256": input_sha,
                        "required_fields": list(
                            requirement.get("required_fields") or []
                        ),
                        "empty_input_policy": requirement.get(
                            "empty_input_policy", "fail"
                        ),
                        "phase": phase,
                        "severity": requirement.get("severity", "blocking"),
                    }
                )
                continue

            member_paths: list[str] = []
            if mode in {"all_of", "any_of"}:
                expanded = [expand(path) for path in requirement["paths"]]
                candidates = [
                    xc.normalize_repo_path(path)
                    for path in expanded
                    if path is not None
                ]
                existing = [
                    path
                    for path in candidates
                    if xc.exact_case_path_exists(repo_root, path)
                ]
                if mode == "all_of":
                    missing = sorted(set(candidates) - set(existing))
                    if missing:
                        if optional:
                            unresolved.append(
                                {
                                    "signal": (
                                        f"optional_requirement_dropped:"
                                        f"{group_id}:{','.join(missing)}"
                                    ),
                                    "severity": "informational",
                                }
                            )
                            continue
                        raise PlanError(
                            f"required artifacts missing for {group_id}: "
                            f"{missing}"
                        )
                    member_paths = candidates
                else:
                    if not existing:
                        if optional:
                            unresolved.append(
                                {
                                    "signal": (
                                        f"optional_requirement_dropped:"
                                        f"{group_id}"
                                    ),
                                    "severity": "informational",
                                }
                            )
                            continue
                        raise PlanError(
                            f"no any_of candidate exists for {group_id}: "
                            f"{candidates}"
                        )
                    member_paths = existing
            elif mode == "at_least":
                pattern = expand(requirement["from_glob"])
                if pattern is None:
                    continue
                member_paths = _expand_glob(repo_root, pattern)
                minimum = int(requirement["min_count"])
                if len(member_paths) < minimum:
                    if optional:
                        unresolved.append(
                            {
                                "signal": (
                                    f"optional_requirement_dropped:{group_id}"
                                ),
                                "severity": "informational",
                            }
                        )
                        continue
                    raise PlanError(
                        f"required glob for {group_id} matched "
                        f"{len(member_paths)} < {minimum}: {pattern}"
                    )
            else:
                raise PlanError(f"unknown requirement mode: {mode}")

            conflicts = xc.case_alias_conflicts(member_paths)
            if conflicts:
                raise PlanError(
                    f"ambiguous case aliases in {group_id}: {conflicts}"
                )
            groups[group_id] = {
                "group_id": group_id,
                "mode": mode,
                "member_paths": member_paths,
                "min_count": (
                    int(requirement["min_count"]) if mode == "at_least" else None
                ),
                "weight": weight,
                "phase": phase,
                "source_rule_ids": [rule_id],
            }
            for path in member_paths:
                add_artifact(
                    path, rule, group_id, weight, phase, families,
                    override_family=rule.get("override_family"),
                    effective_owner=(
                        "public" if rule.get("override_family") else None
                    ),
                )

        override_family = rule.get("override_family")
        if override_family and facts.resolved_project:
            for template in loaded.override_path_templates:
                candidate = template.replace(
                    "{project}", facts.resolved_project
                ).replace("{family}", override_family)
                candidate = xc.normalize_repo_path(candidate)
                if xc.exact_case_path_exists(repo_root, candidate):
                    group_id = f"{rule_id}.project_override"
                    groups[group_id] = {
                        "group_id": group_id,
                        "mode": "all_of",
                        "member_paths": [candidate],
                        "min_count": None,
                        "weight": 3,
                        "phase": "before_first_mutation",
                        "source_rule_ids": [rule_id],
                    }
                    add_artifact(
                        candidate, rule, group_id, 3,
                        "before_first_mutation", families,
                        override_family=override_family,
                        effective_owner="project",
                    )

    if envelope["planned_mutation_paths"] and not envelope.get(
        "resolved_project"
    ):
        unresolved.append(
            {
                "signal": "mutation_planned_without_resolved_project",
                "severity": "critical",
            }
        )

    envelope_hash = xc.document_hash(
        envelope, "task_envelope_hash_unused",
        extra_excluded=("task_text", "task_text_ref"),
    )
    plan: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "task_envelope_hash": envelope_hash,
        "ruleset_hash": loaded.base_hash,
        "repository_content_hash": envelope["repository_content_hash"],
        "protocol_content_hash": envelope["protocol_content_hash"],
        "matched_rule_ids": sorted(matched),
        "requirement_groups": sorted(
            groups.values(), key=lambda group: group["group_id"]
        ),
        "required_artifacts": [
            {
                **entry,
                "source_rule_ids": sorted(entry["source_rule_ids"]),
                "trigger_reasons": sorted(entry["trigger_reasons"]),
                "groups": sorted(entry["groups"]),
            }
            for entry in sorted(
                artifacts.values(), key=lambda entry: entry["path"]
            )
        ],
        "semantic_checks": sorted(
            semantic_checks, key=lambda check: check["checker_id"]
        ),
        "planned_mutation_scope": sorted(
            xc.normalize_repo_path(path)
            for path in envelope["planned_mutation_paths"]
        ),
        "unresolved_signals": sorted(
            unresolved, key=lambda signal: signal["signal"]
        ),
    }
    plan["plan_hash"] = xc.document_hash(plan | {"plan_hash": ""}, "plan_hash")
    return plan


def diff_changed_paths(diff_text: str) -> list[str]:
    changed: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            changed.add(line[6:])
        elif line.startswith("--- a/"):
            changed.add(line[6:])
    return sorted(path for path in changed if path and path != "/dev/null")


def diff_added_text(diff_text: str) -> str:
    return "\n".join(
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def reconcile_additions(
    repo_root: Path,
    ruleset_path: Path,
    envelope: dict[str, Any],
    plan: dict[str, Any],
    diff_text: str,
    task_text_file: Path | None = None,
    extension_paths: list[Path] | None = None,
    execution_contract: dict[str, Any] | None = None,
    checker_dir: Path | None = None,
) -> dict[str, Any]:
    """Second derivation from the actual diff. Additions only: obligations in
    the immutable plan can never be erased here."""
    task_text = resolve_task_text(envelope, task_text_file)
    loaded = load_ruleset(
        ruleset_path,
        repo_root,
        list(extension_paths or []),
        list(envelope.get("ruleset_extensions") or []),
    )
    changed = diff_changed_paths(diff_text)
    added_text = diff_added_text(diff_text)

    original_facts = build_facts(
        envelope, task_text, repo_root, execution_contract
    )
    diff_facts = build_facts(
        envelope, task_text, repo_root, execution_contract,
        extra_paths=changed, extra_content=added_text,
    )
    original_matched = _match_all(loaded, original_facts)
    diff_matched = _match_all(loaded, diff_facts)

    diff_plan = _plan_from_matches(
        repo_root, loaded, envelope, diff_facts, diff_matched, checker_dir
    )
    known_paths = {
        artifact["path"] for artifact in plan["required_artifacts"]
    }
    additions: list[dict[str, Any]] = []
    for artifact in diff_plan["required_artifacts"]:
        if artifact["path"] in known_paths:
            continue
        resolver_defect = all(
            rule_id in original_matched
            for rule_id in artifact["source_rule_ids"]
        )
        additions.append(
            {
                "path": artifact["path"],
                "phase": artifact["phase"],
                "source_rule_ids": artifact["source_rule_ids"],
                "derivable_from_original_facts": resolver_defect,
            }
        )
    return {
        "additions": additions,
        "diff_changed_paths": changed,
        "diff_plan": diff_plan,
    }

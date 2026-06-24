# Reusable Prompt — Agent-Protocol Entrypoint Effectiveness Review

**Updated:** 2026-06-24.

**What it is.** A portable, project-agnostic review prompt that finds and fixes ONE failure class in agent instruction systems: **load-bearing instructions the model never reliably acts on** — buried in a file's tail, sized past the harness's read/config window, trusted to prose the model is assumed to read in full, diluted by long context, duplicated until they drift, or never re-asserted before output. It also catches the common follow-on failures: prose-only routing, unbounded review context, oversized permanent scripts, and missing machine checks. Works on any repo / any harness (Claude Code, Codex CLI/App, Cursor, Windsurf, Copilot, Gemini CLI). Public-safe: no project-specific names.

**Current evidence basis.** Long context is capacity, not reliable working attention. Recent long-context work indicates that newer frontier models have improved positional robustness, but performance still degrades as total context grows, especially for complex or multi-hop work:
- https://arxiv.org/abs/2602.14188 — GPT-5/Gemini/Grok-style frontier models still degrade sharply on high-volume long-context tasks past roughly 70K tokens in the reported setup; positional "lost in the middle" is improved, not a license to load everything.
- https://arxiv.org/abs/2603.15723 — multi-hop QA degrades substantially faster than single-span extraction as irrelevant context grows.
- https://www.trychroma.com/research/context-rot — context length alone can degrade model performance; structured/coherent long inputs are not automatically safer than shuffled/noisy ones.
- https://developers.openai.com/codex/config-reference — Codex behavior is configurable; calibrate current `project_doc_max_bytes`, `tool_output_token_limit`, `model_context_window`, and compaction settings instead of assuming old fixed truncation limits.

**How to use.** Paste everything between the markers into an agent running in the target repo. Fill the `CALIBRATION` block (or let the agent infer it and state confidence). Run it once to get findings + a fix plan; run again with "apply the authorized fixes" once you have reviewed the plan. Do not install this entire prompt as always-loaded project guidance; it is a review tool, not a permanent router.

---
========================= PROMPT START =========================

You are a **Protocol Effectiveness Auditor** for agent instruction systems. You hunt and fix one failure class: load-bearing instructions that fail to reach the model's working attention at the moment of need — because they are buried in a file's tail, sized past the harness read window, delivered as prose the model is trusted to read fully, duplicated until they drift, or never re-asserted before output. You reason from first principles: the objective is **reliable delivery of the right instruction to working attention at the point of need**, not file size or aesthetics. Be direct, evidence-based, and willing to overturn the existing structure.

## PHASE 0 — CALIBRATE (do this first, before judging anything)

CALIBRATION (fill in, or infer and state your inference):
- Target harness(es): {e.g. Claude Code, Codex CLI, Cursor, …}
- Multi-agent fan-out used? {yes/no} (subagents re-pay always-loaded content per cold start)
- Current date and versions/docs checked: {date, tool versions, config docs, local config keys}

Then:
1. **Find the always-loaded / entrypoint surfaces** in this repo — the files injected or read every session: `CLAUDE.md`, `AGENTS.md`/`agents.md`, `.cursorrules`, `.windsurfrules`, system prompts, any "start-session"/router/protocol entrypoint, and any file the tooling auto-loads. List them with line + byte counts.
2. **Determine each harness's file-read window. Do not assume — verify.** Known defaults (they drift by version, confirm against current docs):
   - Codex CLI/App: inspect current config/docs for `project_doc_max_bytes` (project instructions), `tool_output_token_limit` (tool output), `model_context_window`, and auto-compaction settings. Historical Codex builds used small head+tail tool-output truncation; do not treat that as timeless.
   - Claude Code: verify current `Read` behavior, partial-view notices, paging, and any project instruction limits.
   - Cursor, Windsurf, Copilot, Gemini CLI: verify current file-read/tool-output limits and whether truncation is head-only, tail-only, head+tail, paged, or token-based.
   - If exact limits are not discoverable, run an empirical read test and use a conservative budget.
3. Set **`SMALLEST_RELIABLE_WINDOW`** = the smallest reliable single-read or auto-loaded instruction window across the target harnesses, expressed in **BYTES** and lines/tokens where known. If any harness truncates mid-file, the byte budget is the hard constraint and the removed middle is unavailable.
4. Separately set **`TOOL_OUTPUT_WINDOW`** for shell/MCP/tool outputs. Instruction-file loading and tool-output truncation are different channels; do not mix them.

## CORE MODEL (apply to every judgement)
- A model obeys only what is **present AND salient at generation time**. Presence ≠ retention ≠ adherence.
- **Length still matters even when retrieval is good:** frontier models can read large contexts but still lose reliability as total context grows. Positional "lost in the middle" may be improved in newer systems, but long-context dilution and multi-hop reasoning degradation remain.
- **Position still matters for contracts:** put binding obligations early, re-assert them near output, and avoid placing critical rules only in the middle of large context.
- **Middle-dropping truncation gives middle content ZERO probability of being followed** — absolute, not probabilistic.
- An entrypoint carries three payloads with different physics:
  - **BIND** — contracts/obligations the model must HOLD across the task and have salient at output time (output contract, safety/approval gates, root-cause gates).
  - **ROUTE** — one-shot lookups (command→file, alias→role, signal→policy). This is queryable **DATA**, ideally in a manifest/resolver, not prose to attend.
  - **KNOWLEDGE** — lazy reference; load on demand.
- The real units are **bytes** (truncation) and **attention/position** (adherence). "Lines" is a proxy native to neither.
- **Always-loaded == always-needed.** Anything not needed every turn is recurring cost (multiplied under fan-out) and middle-dilution.
- **Review context is a product too.** A project review should be packetized around changed files, risk type, entrypoints, recent verification, and open risks; broad repo reading is a fallback, not the default.

## DETECTION CHECKLIST (run on each always-loaded / large instruction file)
1. **Tail-buried obligations** — does any output contract, required-format spec, safety/approval gate, or hard rule live in the LAST third? (Grep `## Output`, `must`, `never`, `always`, `do not`, approval/secret/delete rules; record byte offset.)
2. **Head-completeness** — are the must-load rule, routing procedure, and output/execution contract all byte-complete within `SMALLEST_RELIABLE_WINDOW`? List each marker's byte offset.
3. **Oversize** — file bytes/lines vs `SMALLEST_RELIABLE_WINDOW`; flag every always-loaded file that exceeds it.
4. **Output-contract position** — is "what to produce" at the TOP (primacy) and restated near the END (recency), or only buried at EOF?
5. **Prose-trusted routing** — is a deterministic mapping sitting as a large inline table the model must read, instead of a queried manifest / verified resolver?
6. **Self-contradiction** — does the file state a size/structure rule it violates itself?
7. **Always-loaded bloat** — conditionally-relevant content (per-task branches, catalogs) loaded every turn.
8. **No integrity guarantee** — nothing lets the agent detect a partial/truncated read; correctness rests on reader discipline.
9. **Duplication-that-drifts** — the same rule stated in 2+ places that can diverge.
10. **Re-assertion gap** — long-turn obligations never re-stated near the output moment.
11. **No protocol manifest** — entrypoint lists, required markers, budgets, and route ownership live only in scripts/prose instead of data checked by a validator.
12. **Unpacketized reviews** — project review instructions do not define bounded packets by review type, changed files, risk, required evidence, and output shape.
13. **Oversized permanent tools** — validators/scripts mix CLI, routing data, parsing, policy, IO, and reporting until they are hard to review. Flag scripts that should split or externalize data.

## SEVERITY
- **critical** — a safety/correctness instruction is physically droppable on a target harness (middle-drop) or always missed.
- **high** — load-bearing obligation in the decay/truncation zone, or routing that can silently mis-resolve.
- **medium** — bloat / oversize / drift-prone duplication with bounded risk.
- **low** — cosmetic / position with low behavioral risk.

## FIX PATTERNS (recommend the minimal set that holds; prefer structure over reader discipline)
- **Kernel-first** — collapse must-load rule + output/execution contract + route procedure into a head-complete KERNEL within `SMALLEST_RELIABLE_WINDOW`, placed FIRST; restate the contract in one line at EOF (recency).
- **Externalize routing** — move catalogs/matrices/maps into a machine-readable manifest + a resolver the agent QUERIES; generate any human-readable view from it; CI-check drift.
- **Verify, don't trust** — gate the session's declared stack/route against the manifest; reject mis-routes.
- **Re-assert at output** — re-emit the compact contract immediately before final output.
- **Byte-invariant CI (not a line rule)** — assert every must-survive marker is byte-complete within `SMALLEST_RELIABLE_WINDOW` and restated in the tail; fail CI otherwise. Provide the check.
- **Progressive disclosure** — always-loaded = router + manifest pointers; bodies are lazy owner files (larger is fine, loaded per task).
- **Split by USAGE** (task-specific / rarely-used / mutually-exclusive), never by a magic line count.
- **Review packets** — create a bounded packet for each broad review: entrypoints loaded, changed files, risk matrix, relevant contracts, latest verification, open risks, and source citations.
- **Tool-size governance** — keep permanent tools small and boring; externalize policy/catalog data to YAML/JSON/Markdown when useful. Scripts above a local threshold need a split/exemption plan.
- **Findings-first review contract** — review output should lead with findings ordered by severity, then questions/assumptions, verification, and reusable-lesson impact.

## OPERATING RULES
- Read every audited file **first line through EOF** before judging it (use ranged reads if your harness truncates; reassemble).
- Cite `path:line` and/or byte offset for every finding. No unverifiable claims.
- **Preserve content** — fixes relocate/restructure; never silently drop an instruction. Verify nothing was lost (grep key sections before/after).
- Propose before applying for anything structural; apply only mechanical, verified fixes when explicitly authorized.
- Do not recommend one huge prompt, one huge AGENTS file, or one huge validator as the fix. Prefer small entrypoint kernels, routed owner files, manifests, packets, and model-free checks.

## OUTPUT
1. **Calibration summary** — entrypoint files found (lines/bytes); harnesses; `SMALLEST_RELIABLE_WINDOW` and `TOOL_OUTPUT_WINDOW`; fan-out?
2. **Findings table** — file · marker · byte offset/line · severity · what is lost · evidence.
3. **Head-completeness verdict per always-loaded file** — markers vs `SMALLEST_RELIABLE_WINDOW`.
4. **Prioritized fix plan** — waves, effort, what relocates where, acceptance criteria per item.
5. **Architecture improvements** — protocol manifest, review packet workflow, output contract, risk matrix, and tool-size gate if useful.
6. **(Optional) ready-to-run byte-invariant CI check** tailored to this repo.
7. **The single highest-leverage move.**

========================= PROMPT END =========================

---

## Appendix — reference byte-invariant CI check (adapt to the target repo)

A model-free guard that replaces "max N lines" with "kernel byte-complete in the calibrated reliable window + restated in the tail". Point it at the always-loaded entrypoint(s); set the marker strings to the ones present in the target's kernel. Keep the budget conservative until the target harness/config has been verified.

```python
#!/usr/bin/env python3
import sys
HEAD = 8192          # calibrated smallest reliable instruction window in bytes
HEAD_MARKERS = [     # must START+END within the head window
    ("must-load rule", "first line through EOF"),
    ("route procedure", "Route"),
    ("execution/output contract", "Required output"),
    ("safety/root-cause gate", "gate"),
]
TAIL_MARKER = ("contract restatement", "Re-state")
def check(path):
    data = open(path, "rb").read(); tail = data[-HEAD:]; errs = []
    for label, m in HEAD_MARKERS:
        i = data.find(m.encode())
        if i == -1: errs.append(f"MISSING [{label}]: {m!r}")
        elif i + len(m) > HEAD: errs.append(f"OUT-OF-HEAD [{label}]: {m!r} at byte {i} (>{HEAD})")
    if TAIL_MARKER[1].encode() not in tail: errs.append(f"MISSING tail restatement: {TAIL_MARKER[1]!r}")
    print(f"{path}: {len(data)} bytes — {'FAIL' if errs else 'OK'}")
    [print("  - " + e) for e in errs]
    return not errs
if __name__ == "__main__":
    sys.exit(0 if all(check(p) for p in sys.argv[1:]) else 1)
```

## Notes
- Tune `SMALLEST_RELIABLE_WINDOW` to your actual harness mix and current config. If you only ever run capable harnesses with larger verified windows, you may relax the byte budget, but keep the position rules (contract at top + restate at EOF), "always-loaded == always-needed", and bounded review packets — those are model-level, not one-tool quirks.
- For Codex, calibrate project instruction loading separately from shell/MCP/tool-output truncation. Current docs expose config keys such as `project_doc_max_bytes`, `tool_output_token_limit`, `model_context_window`, and compaction settings; old 10 KB / 256-line head+tail behavior is historical/version-specific, not a universal law.
- For repo-scale work, the best fix is usually not "more prompt"; it is a smaller entrypoint, a manifest/resolver for routing, task-specific review packets, and validators for deterministic rules.
- The check above is intentionally model-free so it runs in CI and cannot itself be "skimmed".

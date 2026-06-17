# XUUnity Utility: Design Retro Review

## Goal
Review a corpus of design documents — especially retrospective ("retro") and legacy plans you did not
write — and produce an evidence-backed, prioritized registry that scores each design for relevance
(actuality), importance, implementation status, and remaining effort against the LIVE repository, not
against the document's own self-assessment.

## Use For
- periodic audit of a `Design/` or `<Surface>/Designs/` folder
- onboarding to an unfamiliar design corpus
- deciding which design work is done, stale, or next
- creating or refreshing a scored design registry
- triaging legacy / retro designs for archive versus keep
- answering "what is actually built versus what is only written down?"

## When Not To Use
- shaping a single new feature -> `tasks/feature_design_brief.md` or `tasks/architecture_plan.md`
- product-system roadmap progress -> `utilities/system_progress_review.md`
- prompt-system structural health -> `utilities/system_health_review.md` (which runs a light registry
  reconciliation step; this protocol is the deep, scored audit that step can defer to)

## Inputs
- the target design folder(s)
- the live surfaces the designs claim to describe: module/source tree, `scripts/`, `schemas/`, tests,
  CLI entrypoints, configs, generated artifacts
- the roadmap / execution plan if present
- the existing registry/README for the folder if present
- prior review provenance if present

## Core Principle
Importance and implementation are INDEPENDENT axes:
- a design can be load-bearing (Imp. 5) yet unbuilt (`planned`)
- a fully implemented design can be peripheral (Imp. 2)

Never collapse the two. For "is it built / still current?", the repository wins over the document.

## Process
1. Enumerate every design in the folder and cross-check against the existing registry. A design on disk
   but missing from the registry — or a registry row with no file — is registry drift; record it.
2. Read each design in full. Do not trust its self-declared status, version, or "done" claims.
3. Trace each design's claims to the LIVE repo and gather concrete evidence — real file/dir/script/schema/
   test paths, and where relevant actual CLI or test output. A claim with no live evidence is `unverified`,
   not `done`. Grade each piece of evidence `confidence: high` (path/CLI/test shows it directly), `medium`
   (strong inference), or `low` (assumed); for `low`, name the exact command or file still needed to confirm.
4. Score each design on independent axes:
   - **Importance (1–5):** 5 = foundation the rest depends on; 1 = peripheral or a historical tombstone.
   - **Actuality / Relevance:** `current` · `draft` (not finalized) · `legacy` (superseded) · `unknown` (insufficient evidence to judge).
   - **Implementation:** actual % wired into the live system, evidence-backed —
     ✅ done · 🟡 partial · ⬜ not built · 📦 work delivered, doc is a recipe · 🗄 superseded.
     A `%` is an estimate unless backed by a count/ratio: write provable ones as `100% (25/25 tests)`;
     tag the rest `~NN% (est.)` or keep them qualitative. Never present a guess as precision.
   - **Effort to 100%:** rough remaining work (size · time · complexity), e.g. `M · ~3–5d · High`.
   - **Left to 100%:** the concrete remaining gap (named files/steps), or `none`.
   - **Why it matters (or does not):** 1–2 sentences justifying the importance score.
5. Assign a lifecycle Status, separating four easily-confused cases:
   - `implemented` — ≈100% built AND still the source of truth (reference; no work pending)
   - `active` — in force and still being finished
   - `draft` — design not finalized
   - `planned` — approved direction, not built
   - `archived` — `historical` (a generator/plan whose output already shipped and is now the live artifact)
     or `legacy` (a retired approach). Decision test: *is this doc still read to understand or change current
     behavior?* If no, it is `archived` — even at 100% implementation.
6. Detect governance issues (report them; do not silently rewrite the system to match a doc):
   - registry status that overstates or understates maturity versus the repo
   - a design missing from the registry, an orphan file on disk that was never registered, or an archived doc still referenced as live
   - dead links: references to files or sections that no longer exist
   - design self-violations: the doc mandates X but the repo does Y
   - reverse drift: behavior implemented in the repo with no design source to explain or govern it
7. For a large corpus, fan out: one assessor per design (or per theme) gathering evidence in parallel, then
   an adversarial verifier that re-checks each claim against the repo and flags overstated / understated /
   fabricated facts. Never record an unverified figure (e.g. a test count) — run or read it first.
8. Reconcile the registry table, sorted by **priority = importance (desc), then remaining effort (asc)** —
   most important and cheapest-to-finish first. Columns: Design · Status · Imp. · Impl. · Effort ·
   Why it matters. Do not give `Left to 100%` its own column: fold the concrete gap into the Why cell on a
   second line (`…why…<br>**Left to 100%:** <gap>`) only for designs with work remaining, and omit it for
   `implemented` / done rows whose status already says so.
9. Archive retired or fully-consumed designs into an `Archived/` subfolder via `git mv` — never delete (keep
   them recoverable and auditable) — and fix inbound links.
10. Produce a Priority Backlog of actionable-only items (exclude `implemented` and `archived`), ordered by
    leverage (impact × what it unblocks), each with its concrete next action.
11. Stamp provenance: method + date. Mark Importance as the subjective/opinionated axis. Keep the registry in
    the repository's documentation language (English by default). Invite independent re-verification and
    record dissent rather than silently overwriting.

### First-principles framing (recommended for retro / legacy corpora)
- **Assumption autopsy** — before scoring, surface the assumptions baked into the docs and the task:
  project tradition, old architecture, fear of breaking legacy, desire to preserve past work, the doc's
  self-assessment, registry/README status, unverified test numbers, stale roadmap claims. Tabulate as
  `Assumption | Source | Why it may be false | Verification needed`, then verify each against the repo
  before trusting it.
- **Aristotelian move** — after scoring, name the single highest-leverage action: concrete, doable now,
  grounded in verified truths, stronger than "update the docs", aimed at the largest reduction of
  doc↔repo drift. State `Do now`, `Why it beats normal review`, and `Expected unlock`.

## Output
- executive verdict — 5–10 lines, no filler, up front
- reconciled registry table (sorted by importance then effort)
- maturity map (tiers: implemented / active / draft / planned / archived)
- per-design scoring with cited evidence
- priority backlog (actionable-only, by leverage)
- archived set with reasons
- governance findings (overstated/understated maturity, missing rows, orphan files, dead links, self-violations, reverse drift)
- score by theme / workstream
- current bottleneck + recommended next milestone + next deliverables
- single highest-leverage move (the Aristotelian move)
- review provenance block

## Code Review Mode
When a design's claim can only be settled by reading code — or the task explicitly asks for code review —
review the code, do not just score the doc. Reuse the existing protocols instead of duplicating them:
delegate to `tasks/code_review.md`, `reviews/feature_code_review.md`, or `reviews/git_change_review.md`,
and fold their findings back into the design's evidence and lifecycle status.

Report findings first, ordered by severity. No style notes without a behavioral risk; do not say "looks
good" before checking the risks; if nothing is wrong, say so and name the residual risk. Finding shape:

```md
**[P1|P2|P3] Title**
File: `path/to/file:line`
Problem: <concrete failure mode>
Impact: <what breaks, and when>
Evidence: <path / command / test output>
Fix: <smallest correct change>
```

## Rules
- Importance ≠ implementation; keep the axes separate.
- Evidence over self-assessment; cite real paths; never record an unverified number.
- Never delete a retired design — archive it.
- Sort to surface priority (importance desc, effort asc); keep a separate actionable-only backlog.
- Do not reward document volume. Reward operational readiness, evidence quality, and leverage.
- Keep the registry in the repo's doc language; stamp provenance; flag the subjective axis.
- A `%` is an estimate unless backed by a count/ratio — mark provable ones (`100% (25/25 tests)`) and tag the rest `(est.)`; never present a guess as precision.
- Grade evidence confidence (high/medium/low); when low, name the command or file needed to confirm.
- For code risk, review the code via Code Review Mode (delegating to the existing code-review protocols), not just the doc.
- Treat any review (including this one) as a first pass to be challenged, not ground truth; the repo can
  drift after the sample date.

## Templates

### Assumption autopsy
```md
| Assumption | Source | Why it may be false | Verification needed |
| --- | --- | --- | --- |
```

### Registry row
The `Left to 100%` gap lives inside the Why cell (second line), not as its own column. Append it only
when work remains; omit it for `implemented` / done rows.
```md
| `<DESIGN_FILE>` | implemented\|active\|draft\|planned\|archived | <1-5> | <✅\|🟡\|⬜\|📦\|🗄> <impl%> | <S/M/L/XL · ~time · cx> | <why it matters, or does not><br>**Left to 100%:** <concrete gap, only if work remains> |
```

### Per-design scoring block
```md
- **`<DESIGN_FILE>`** — importance **<1-5>**, <current\|draft\|legacy\|unknown>, **<impl glyph + % (est. unless count-backed)>**.
  Evidence: <real paths / CLI / tests proving the status> — confidence <high\|medium\|low>.
  Gap to 100%: <concrete remaining work, or none>.
  *Status: <lifecycle>. <one-line recommendation>.*
```

### Review provenance block
```md
## Review Provenance
- **Review:** `xuunity design retro review`, <YYYY-MM-DD>.
- **Method:** each design read in full and reconciled against the live repo; claims backed by cited
  files/scripts/CLI, not the documents' self-assessment.
- **Commands run:** <key grep / test / CLI commands, or none>.
- **Files sampled:** <files and dirs actually inspected>.
- **Tests run:** <suite + result, or `none — review only`>.
- **Subjective axis:** Importance (1–5) is an opinionated scoring; Status, Implementation %, and Actuality
  are evidence-based but sampled at a point in time.
- **For reviewers:** treat as a first pass to challenge; re-verify each row against the current repo
  before acting; record dissent rather than overwrite.
```

## Rule
Reward verified current-truth and leverage, not the length or confidence of the design documents.

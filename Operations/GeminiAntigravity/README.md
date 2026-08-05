# Gemini / Antigravity configuration engine

Host-agnostic, reusable parts of a Gemini 3.x configuration for the Antigravity IDE and the
Antigravity CLI (`agy`). Nothing here is specific to any repository, project or machine — a
consuming host supplies its own workspace payloads and paths.

Two limits to know before you plan around a CLI: the standalone Gemini CLI (`gemini`) **cannot
sign in an individual Google account** any more — it redirects to the Antigravity suite — and
`agy` loads the rules but does **not** fire workspace hooks. So the enforcement layer is
IDE-only; CLI sessions get advice-only discipline. Evidence in the platform contract, §7.

The design target is a model that is fast but shallow, drops instructions mid-session,
hallucinates APIs and file contents, and is weaker than its peers on multi-file changes.
The countermeasures are: a small always-on kernel that fits the measured injection window,
progressive disclosure for everything else, and **hooks as the only real enforcement layer**.

---

## Start here

[`docs/PLATFORM_CONTRACT.md`](docs/PLATFORM_CONTRACT.md) — the verified platform contract.
Read it before writing a single rule. Five of its findings contradict Antigravity's own
built-in documentation, and each one silently produces a configuration that loads and then
does nothing:

- global always-on rules live in `~/.gemini/config/rules/`, **not** `~/.gemini/rules/`;
- `.agents/rules/*.md` without a `trigger:` key is discovered and then ignored;
- `globs:` must be a comma-separated string — YAML lists never fire;
- `~/`-relative `skills.json` entries do not resolve, despite being documented;
- a single always-on file is truncated at ~24 KB, and an oversized always-on set triggers
  context truncation on the first turn — which *is* the instruction-dropping failure.

Everything in that document was established by probe, and what remains unmeasured is listed
as unmeasured.

---

## Layout

```
docs/PLATFORM_CONTRACT.md   verified platform behaviour + what is still unverified
rules/                      the always-on kernel (5 files, ≤ 8 KB total)
hooks/                      the enforcement layer + hooks.env.template
probe/                      headless agent harness, platform probes, planted-bug fixtures
tools/                      payload validator, hook self-test, leak-checker
```

### `rules/` — the always-on kernel

Five files, 8 KB total, deployed to `~/.gemini/config/rules/`:

| File | Owns |
|---|---|
| `00_operating_contract.md` | depth ladder, owner-chain root-cause gate, finish-or-blocker, decision packs |
| `10_evidence_and_no_hallucination.md` | verified-vs-assumed labelling, proof ladder, banned completion words |
| `20_router_discovery.md` | how to find and obey a workspace's own router before doing work in it |
| `30_secrets_and_boundaries.md` | redaction, public/private boundary, act-on-behalf limits |
| `40_language_and_output.md` | reply language, answer skeleton, comment policy, durable-output rule |

Every line is imperative and carries no rationale — rationale belongs in the corpus a rule
points at, not in always-on text. If you add a line, remove one: the budget is the point.

### `hooks/` — enforcement

Rules are advice; hooks are the only mechanism that can actually stop the agent.

| Hook | Event | Does |
|---|---|---|
| `discipline_heartbeat.sh` | `PreInvocation` | re-injects the discipline every Nth model call, and nags about an open edit batch |
| `pre_tool_gate.sh` | `PreToolUse` | denies workspace-forbidden commands, force-asks on destructive ones, tracks edit batches |
| `no_premature_stop.sh` | `Stop` | blocks termination while background work runs, when an edit had no validation after it, or when the answer has no Validation section |

All three **fail open** — every error path emits a valid permissive decision, so a broken hook
can never brick the agent. Note what "permissive" must mean for `PreToolUse`: see below. All three are counter-guarded so they cannot loop. Behaviour is driven
entirely by `hooks.env` (copy [`hooks/hooks.env.template`](hooks/hooks.env.template)), so the
scripts stay identical across workspaces and only the config differs.

Three hard-won rules encoded here, each explained in the platform contract:

- **Never emit a bare `{}` from `PreToolUse`.** `decision` is required; an empty object makes the
  platform reject the tool call as `invalid_args` with an empty reason, and nothing runs.
  Measured: with the gate emitting `{}`, `pwd` was blocked; without the gate it ran. Pass through
  with a real decision — `PASSTHROUGH_DECISION`, default `allow`, which matches the no-hook
  baseline. Set it to `ask` when auto-execution is off and the prompt should come back.
- **Never a wildcard matcher.** `"*"` intercepts `ask_permission` and stalls the permission
  handshake; the agent gives up instead of working.
- **Never gate edits via `PreToolUse`.** It is not dispatched for file-edit steps. Detect
  edits by reading the transcript in the `Stop` hook instead.

### `probe/` — the empirical harness

`agy.py` drives Antigravity headlessly through its undocumented `agentapi`, resolving the
language-server address, CSRF token and project id itself, and reads results out of the
conversation transcript rather than trusting the model's self-report.

```bash
python3 probe/agy.py <workspace-dir> <project-id> <flash|pro> prompt.txt
```

[`probe/fixtures/`](probe/fixtures/) holds planted defects for the depth probe — each built so the
first plausible cause is wrong and the shallow fix compiles, hides the symptom, and leaves the bug.

`setup_probe.py`, `setup_probe2.py`, `setup_probe3.py` build throwaway workspaces that measure
discovery, trigger semantics, glob syntax, the injection cutoff and hook dispatch. Re-run them
after an Antigravity update — the platform contract is version-specific, and these are what
make re-verification cheap instead of a manual GUI session.

### `tools/` — validators

```bash
python3 tools/validate_payloads.py \
  --global-rules rules \
  --workspace mylabel:/path/to/payload:/path/to/repo \
  --secret-scan /path/to/payload

sh tools/test_hooks.sh /path/to/hooks.env

python3 tools/leakcheck.py --patterns private/leak_patterns.json .
```

The validator catches exactly the silent-failure modes above: missing `trigger:`, YAML-list
`globs:`, `~/` skills.json entries, duplicate skill names, per-file and total budget overruns,
corpus references that do not resolve, and secret patterns. The hook self-test feeds each hook
realistic payloads and asserts its JSON decision, including fail-open on malformed input.

`leakcheck.py` guards the public/private boundary. Its pattern list is the private part, so it is
never hardcoded — pass a JSON file that stays on the private side. Confirm it actually fires before
trusting a CLEAN: point it at something you know is private and check it reports hits.

Run all three before installing or publishing anything. They found three real defects in these very
hooks, two unresolvable corpus references, and one false-negative in the leak-checker itself.

---

## Consuming this from a host

The host owns paths, workspace payloads and its own bootstrap; this directory owns the
reusable engine. A host bootstrap typically:

1. runs `tools/validate_payloads.py` and `tools/test_hooks.sh` as a preflight, and refuses to
   install if either fails;
2. copies `rules/*.md` into `~/.gemini/config/rules/`;
3. does **not** write `~/.gemini/GEMINI.md`. Antigravity loads that file as a user-global rule, so
   generating it injects the whole always-on kernel a second time — a doubled footprint for no
   benefit, since the standalone Gemini CLI cannot sign in an individual account anyway;
4. copies `hooks/*.sh` + `hooks.json` plus its own `hooks.env` into each workspace's
   `.agents/`, and gitignores `.agents/.state/`;
5. merges its MCP servers into `~/.gemini/config/mcp_config.json` without clobbering others.

Cross-host notes worth knowing before you design: `agy` authenticates off the Antigravity app
session (no API key, no browser step) and loads global rules, but fires no workspace hooks. The
Gemini CLI reads the same `.agents/skills/` and needs the repo in `~/.gemini/trustedFolders.json`,
does **not** honour `.agents/skills.json` entries, and on an individual plan cannot authenticate at
all. MCP config is read at language-server startup, so a running IDE needs a restart to see a newly
added server. Details and evidence in the platform contract.

---

## Boundary

This directory is public and reusable. Keep host-private material out of it: no project or
protocol names, no machine paths, no workspace payloads, no reports about a specific host.
Those belong in the consuming host's own operations directory. Point both
`tools/validate_payloads.py --secret-scan` and `tools/leakcheck.py` at this directory as a standing
check.

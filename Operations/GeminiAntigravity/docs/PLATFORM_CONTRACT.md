# Antigravity / Gemini customization — verified platform contract

Measured on macOS, Antigravity 2.0 (`language_server` build of 2026-07-30), Gemini CLI `0.53.1`,
Antigravity CLI (`agy`) `1.1.10`. Date: 2026-08-04.

Everything here was established by running a probe and reading the result, not by reading
documentation. Five of these findings **contradict** the product's own built-in docs
(`~/.gemini/antigravity/builtin/skills/agy-customizations/`), and each one silently produces an
inert configuration — no warning, no log line, no UI indication. Re-run
[`probe/`](../probe/) after any Antigravity update: this contract is version-specific.

---

## 1. Where things actually load from

| Customization | Location that works | Notes |
|---|---|---|
| Global always-on rules | `~/.gemini/config/rules/*.md` | **Not** `~/.gemini/rules/` — see §2.1 |
| Workspace rules | `<repo>/.agents/rules/*.md` | frontmatter mandatory — see §2.2 |
| Directory routers | `GEMINI.md`, `AGENTS.md`, `Agents.md`, `Gemini.md` | walked from CWD up to repo root; **case-insensitive match** |
| Workspace skills | `<repo>/.agents/skills/<name>/SKILL.md` | frontmatter `name` + `description` |
| External skills | `<repo>/.agents/skills.json` → `entries[].path` | absolute paths only — see §2.4 |
| Plugins | `<repo>/.agents/plugins/<name>/` | `plugin.json` + `rules/` + `skills/`; auto-discovered, no `plugins.json` needed |
| Hooks | `<repo>/.agents/hooks.json` | cwd for each command = the directory holding `hooks.json` |
| MCP servers | `~/.gemini/config/mcp_config.json` | read at language-server **startup** — see §5 |

Loading priority, high → low: workspace hierarchical discovery → workspace declared JSON configs →
global discovery (`~/.gemini/config/`) → built-ins → global declared configs. Rules are deduplicated
by resolved path, so a file is never injected twice in one turn.

---

## 2. The five documentation defects

### 2.1 Global rules live under `~/.gemini/config/`, not `~/.gemini/`

Identical marker rules were placed in `~/.gemini/rules/` and `~/.gemini/config/rules/` in the same
probe run. Only the `config/rules/` marker reached the model. A rule sitting in `~/.gemini/rules/`
is never loaded — including one created through the UI, which is where the UI puts it.

Files written into `~/.gemini/config/rules/` are picked up **without restarting the app**.

### 2.2 `.agents/rules/*.md` requires a `trigger:` key

Three variants, one run:

| File | Loaded? |
|---|---|
| no frontmatter at all | **no** |
| frontmatter with `description` but no `trigger` | **no** |
| frontmatter with `trigger` | yes |

The product docs state that rules "do not support frontmatter" — true only of bare
`GEMINI.md`/`AGENTS.md` files, and actively misleading for `.agents/rules/`.

Valid `trigger` values, recovered from the `CortexMemory` proto in the `language_server` binary:
`always_on`, `glob`, `manual`, `model_decision`. The proto also accepts `description`, `globs`,
`priority`, `base_dir_uris` and `corpus_names`. `manual` never auto-injects. `priority` parses
without error; its ordering effect was **not** measured.

### 2.3 `globs:` must be a comma-separated string

Six variants against the same file:

| frontmatter | fires? |
|---|---|
| `globs: "*.cs"` | **yes** |
| `globs: "**/*.cs"` | **yes** |
| `globs: "*.cs,*.swift"` | **yes**, both extensions |
| `globs: ["*.cs"]` | no |
| `globs: ["**/*.cs"]` | no |
| `globs:` then `  - "*.cs"` | no |

YAML list and sequence forms are silently ignored. `*.<ext>` matches at any depth — a root-level
`root.cs` and a nested `deep/nested/Deep.cs` both matched `*.cs`, so the `**/` prefix buys nothing.

### 2.4 `~/`-relative paths in `skills.json` do not resolve

The docs explicitly show `{"path": "~/personal-skills"}`. Probed twice, in two runs, against two
sibling directories of identical structure: the absolute-path entry registered its skill, the
`~/` entry registered nothing. Use absolute paths. Workspace-relative paths are documented to
resolve from the repo root but were **not** verified here.

### 2.5 Hook payload paths point into the brain directory

`transcriptPath` and `artifactDirectoryPath` resolve to
`~/.gemini/antigravity/brain/<conversationId>/.system_generated/logs/…`, not into the workspace as
the docs' example implies. A hook that reconstructs them workspace-relative finds nothing.

---

## 3. Injection budget — measured

**A single always-on rule file is truncated at ~24 KB.** Measured with a 64 KB rule carrying a
numbered marker at every 1 KB boundary (`MARKER_KB_001` … `MARKER_KB_064`) and asking the model for
the highest marker it could see: `HIGHEST_KB=024`.

**More important:** a workspace carrying ~84 KB of always-on rules fired a context `CHECKPOINT` on
its *first* turn — *"The earlier parts of this conversation have been truncated due to its long
length."* Over-stuffing always-on rules does not merely waste tokens, it triggers the
truncate-and-summarise path, which is itself the "model drops instructions mid-session" failure.

Recommended budget: **≤ 8 KB total** for the global always-on layer and **≤ 8 KB** for a
per-workspace always-on kernel, with every individual file far below the 24 KB cutoff. 8192 bytes is
also the head-window invariant this repo's entrypoint checker enforces, so the two agree.

Nothing in the platform sums bytes across a directory. [`tools/validate_payloads.py`](../tools/validate_payloads.py) does.

---

## 4. Hooks — the only real enforcement layer

All five events fire. Verified behaviour:

| Event | Verified |
|---|---|
| `PreInvocation` | fires before every model call; `{"injectSteps":[{"ephemeralMessage":"…"}]}` reaches the model |
| `PostToolUse` | fires, including on non-tool steps (`toolCall: null`) |
| `PostInvocation` | fires after tool calls finish |
| `Stop` | `{"decision":"continue","reason":"…"}` **blocks termination and re-enters the loop**; the reason arrives verbatim as `<SYSTEM_MESSAGE> stop hook blocked termination due to reason: …` |
| `PreToolUse` | `{"decision":"deny","reason":"…"}` **hard-blocks the call**; the model sees `invalid tool call error (invalid_args) tool call denied with reason: <reason>` |

Payload facts that differ from the docs: `invocationNum` and `executionNum` start at **0**;
`terminationReason` was observed as `NO_TOOL_CALL` (docs name `model_stop`); `workspacePaths` is
present and correct. cwd is the `hooks.json` directory, `~` expands, shell is `sh -c`.

### 4.1 `PreToolUse` is NOT dispatched for file-edit steps

This is the most consequential hook finding. With a wildcard matcher (`"matcher": "*"`) a session
that edited a file produced `PreToolUse` events for `view_file`, `grep_search`, `list_dir`,
`run_command`, `ask_permission` and `list_permissions` — and **never** for the `CODE_ACTION` step
that actually wrote the file. Any "did an edit happen?" gate built on `PreToolUse` silently never
fires.

Workable alternative: the `Stop` hook reads `transcriptPath` and looks for a `CODE_ACTION` step with
no validation-shaped step after it. [`hooks/no_premature_stop.sh`](../hooks/no_premature_stop.sh)
does exactly this, and it is verified to fire.

### 4.2 A wildcard matcher breaks the permission flow

`"matcher": "*"` also intercepts `ask_permission` and `list_permissions`. Returning `{}` for those
stalls the permission handshake — in two runs the agent gave up instead of editing. **Match
explicitly; never wildcard.**

### 4.3 Never return `{"decision":"allow"}` as a default

`allow` auto-approves the call and defeats the user's own auto-execution policy. For "no opinion",
return `{}`. A gate that blanket-allows is worse than no gate.

### 4.4 Real tool names

Derived by lowercasing the step type and stripping `CORTEX_STEP_TYPE_`. Observed in practice:
`view_file`, `grep_search`, `list_dir`, `run_command`, `ask_permission`, `list_permissions`,
`code_action`. Others present in the binary include `shell_exec`, `mcp_tool`, `propose_code`,
`write_blob`, `file_change`, `edit_notebook`, `move`, `delete_directory`, `git_commit`, `compile`,
`view_file_outline`, `read_terminal`, `search_web`, `read_url_content`.

### 4.5 Glob rules ride along with file reads

When a `glob` rule matches, its body is appended to the `view_file` result under
*"The following text is not part of the file, it is a list of user-defined rules that you MUST
follow"*. This is the strongest available surface for codestyle: the rule arrives welded to the file
the model is about to change.

---

## 5. MCP

`~/.gemini/config/mcp_config.json`, schema `{"mcpServers": {"<name>": {"command", "args", "env"}}}`
for stdio or `{"serverUrl"}` for SSE.

**It is read at language-server startup.** A config written while the IDE is running is not picked
up until the app restarts — verified by timestamp: an LS started at 09:24 never saw a config written
at 12:31, while a CLI process started afterwards discovered all 65 tool schemas from the same file.
Cached tool schemas land in `~/.gemini/antigravity-cli/mcp/<server>/*.json`, which is a cheap way to
confirm a config was consumed.

Write one resolved absolute path as a single `args` element. Avoid `bash -c` one-liners, `$HOME`/`$PWD`
expansion, and embedded quotes: clients quote argv with C-runtime rules and mangle them.

---

## 6. Headless operation — `agentapi`

Antigravity ships an undocumented headless agent CLI at `~/.gemini/antigravity/bin/agentapi`
(a one-line `exec` wrapper onto `language_server agentapi`):

```
agentapi new-conversation [--model=<flash_lite|flash|pro>] [--title=…] [--profile=…] <prompt>
agentapi get-conversation-metadata <conversation_id>
agentapi send-message [--title=…] <recipient_id> <content>
```

Three environment variables gate it:

| Variable | How to resolve |
|---|---|
| `ANTIGRAVITY_LS_ADDRESS` | `127.0.0.1:<port>` — the **higher** of the two ports the running `language_server` listens on; the lower one returns `error reading server preface: EOF` |
| `ANTIGRAVITY_CSRF_TOKEN` | the `--csrf_token` argument of the running `language_server` process |
| `ANTIGRAVITY_PROJECT_ID` | basename of a `~/.gemini/config/projects/*.json` file |

The app must already be running; `agentapi` talks to its language server, it does not start one.
Registering a workspace is a plain file write to `~/.gemini/config/projects/<uuid>.json` with
`projectResources.resources[].gitFolder.folderUri`, and takes effect without a restart.

Each conversation writes a machine-readable transcript to
`~/.gemini/antigravity/brain/<conversationId>/.system_generated/logs/transcript.jsonl`
(one JSON object per step: `step_index`, `source`, `type`, `status`, `content`). That transcript —
not the model's self-report — is the ground truth for what was injected and what ran.

[`probe/agy.py`](../probe/agy.py) wraps all of this. It is what makes this contract reproducible and
what makes agent-behaviour validation a scripted step rather than a manual GUI session.

---

## 7. Cross-host reuse

A single `.agents/` payload serves more than one host:

- **Antigravity IDE** — discovers `.agents/rules`, `.agents/skills`, `.agents/hooks.json`, `.agents/plugins`.
- **Gemini CLI (`gemini`)** — **cannot currently authenticate an individual Google account.**
  With `security.auth.selectedType: oauth-personal` the sign-in fails with *"This client is no
  longer supported for Gemini Code Assist for individuals. To continue using Gemini, please migrate
  to the Antigravity suite of products"* (verified 2026-08-04, CLI 0.53.1). On an individual plan the
  remaining options are an API key or an enterprise Vertex/Code-Assist account, so treat this client
  as unavailable unless you have one; `agy` is the supported path. Everything below about it was
  verified before that wall and still describes its config surface.
  It discovers the same `.agents/skills/` (verified: 12 skills listed by
  `gemini skills list`), and has `skills`/`hooks`/`mcp` subcommands of its own. It requires the
  folder to be **trusted**: add the repo path to `~/.gemini/trustedFolders.json` with the value
  `TRUST_FOLDER`, or it reports *"Skipping project agents due to untrusted folder"*.
  It does **not** honour `.agents/skills.json` `entries` (verified: a workspace whose skills come
  only from `skills.json` reported "No skills discovered" while Antigravity registered all 34).
  Set `contextFileName` to `["GEMINI.md","AGENTS.md","Agents.md","Gemini.md"]` so it walks the same
  router network. Auth type lives at `security.auth.selectedType` in `~/.gemini/settings.json`
  (`oauth-personal` for Google-account login, `gemini-api-key`, `vertex-ai`, `cloud-shell`).
- **Antigravity CLI (`agy`)** — installs to `~/.local/bin/agy` from
  `https://antigravity.google/cli/install.sh` (the script verifies a SHA512 from a per-platform
  manifest; its last step edits shell rc files, so install the binary by hand if that is out of
  scope). Shares `~/.gemini/config/`, keeps state in `~/.gemini/antigravity-cli/`, and has
  `--print` for non-interactive runs. Headless runs auto-deny anything needing a permission prompt
  unless an allow-rule exists under `permissions.allow` in its settings.
  **It authenticates without a separate login** — it reuses the Antigravity app's session, so no API
  key and no browser step (verified: a `--print` run returned its answer on a machine with no
  Gemini API key configured and no `gemini` CLI credentials).
  **It loads global `~/.gemini/config/rules/` but does NOT fire workspace `.agents/hooks.json`
  hooks** (verified: an `agy --print` run in a workspace whose `PreInvocation` hook writes a log on
  every model call produced its answer and created no log, while the same hook fires on every
  `agentapi`/IDE run in that workspace). Consequence: the enforcement layer is IDE-only. Rules and
  skills carry over to `agy`; deny-gates, the discipline heartbeat and the stop-gate do not. Plan
  for advice-only discipline in CLI sessions.

---

## 8. What is still unverified

Stated plainly so nothing here is mistaken for measurement:

- `priority:` ordering semantics on rules.
- Workspace-relative (non-absolute, non-`~`) `skills.json` entry paths.
- Whether `~/.gemini/config/rules/` honours `glob` and `model_decision` triggers, or only `always_on`.
- The exact always-on total at which `CHECKPOINT` truncation begins (bracketed between 8 KB, which
  was clean, and 84 KB, which truncated on turn 1).
- Gemini CLI hook discovery (`gemini hooks` exposes only a `migrate` subcommand) — and now moot on
  an individual plan, since the client cannot sign in at all.
- `agy`'s `permissions.allow` rule grammar for MCP tools.
- Whether `agy` fires hooks in **interactive** mode. Only `--print` was tested, and it did not.
- Whether `agy` reads workspace `.agents/rules/` (only global rules were confirmed loaded).

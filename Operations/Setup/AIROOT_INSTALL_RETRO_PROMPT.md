# AIRoot Install Retro Prompt

Date: `2026-06-18`
Status: `active public prompt`

## Purpose

Use this prompt after installing or onboarding `AIRoot` into a new client repo
when setup failed, felt confusing, required manual workaround, or succeeded only
after undocumented help.

The goal is to collect a structured install retro report that can improve:
- `AI_EASY_SETUP.md`
- `AI_ASSISTED_SETUP_PROMPT.md`
- `AIROOT_SETUP_PROTOCOL.md`
- setup scripts under `AIRoot/scripts/`
- generated routers, setup checks, and recovery diagnostics

This prompt is intentionally about AIRoot setup itself. It is not a normal
project work prompt and it is not the XUUnity Light Unity MCP install retro.

## Use When

- the easy setup path did not get the client to a working repo
- the AI-assisted setup prompt produced unclear or wrong actions
- the client tried to set up AIRoot manually and got stuck
- `.sh`, `.cmd`, `.bat`, `.ps1`, Git Bash, PowerShell, `cmd.exe`, WSL, or an AI
  client terminal behaved differently than expected
- a script failed because of CRLF/LF line endings, executable bits, shell
  selection, path quoting, or missing Bash
- clone, auth, local folder selection, or "open the repo root" was confusing
- the agent started from the wrong directory or tried to mutate the `AIRoot`
  repo itself instead of a host repo containing `AIRoot/`
- topology classification was ambiguous: single-project versus monorepo
- `--dry-run`, apply, `--check`, or `--fix` failed
- `Agents.md`, `AIOutput/Registry/setup_status.yaml`,
  `AIOutput/Registry/host_topology.yaml`, project routers, or
  `Assets/AIOutput/ProjectMemory/` did not appear as expected
- setup succeeded but the next user-facing step was unclear

## Do Not Use When

- normal project work is already running through `xuunity`
- the problem is specifically XUUnity Light Unity MCP package installation or
  MCP client wiring; use the MCP install retro prompt for that surface
- the report would require exposing private source, secrets, tokens, passwords,
  private repo URLs, customer names, or unrelated logs

## Redaction Rule

Before sharing the report, replace private values with stable placeholders:

- `<client-repo>`
- `<host-root>`
- `<unity-project>`
- `<user-home>`
- `<private-remote>`
- `<ai-client>`

Do not include API keys, auth tokens, passwords, private SSH keys, private repo
URLs with credentials, machine usernames, or full unrelated logs.

Keep useful public-safe evidence:
- OS and shell names
- AIRoot commit, tag, or branch
- command names
- sanitized paths
- exact error codes and short error excerpts
- Git line-ending metadata
- setup script output
- generated file presence or absence

## Inputs To Gather First

At minimum, collect:

1. OS and version.
2. Shell or terminal used for each command: PowerShell, `cmd.exe`, Git Bash,
   WSL, macOS Terminal, VS Code terminal, AI client terminal, or other.
3. AI client used: VS Code, ChatGPT desktop, Codex CLI, Claude Desktop, Claude
   Code, Cursor, Rider, or other.
4. Whether the AI client had local folder access and terminal execution.
5. Repo clone URL source, redacted as `<private-remote>` if needed.
6. Local folder chosen, redacted as `<host-root>`.
7. Whether the opened folder was the host repo root or `AIRoot/` itself.
8. AIRoot version evidence: commit, branch, tag, or archive date.
9. Which setup doc was followed first.
10. Exact commands attempted, in order, with current directory for each.
11. First visible error, before any retry changed state.
12. Any manual workaround applied.
13. Whether files were modified by setup before the failure.
14. Which generated files exist now and which are missing.
15. If Windows or mixed shell behavior was involved, the launcher flavor for
    each command: `.sh`, `.cmd`, `.bat`, `.ps1`, direct `bash`, direct `python`,
    Git Bash, PowerShell, `cmd.exe`, WSL, or AI client stdio.

If a command cannot run, record the command, current directory, and exact error
instead of guessing.

## Preferred Command Evidence

Run only the commands that match the actual setup route. Prefer `--dry-run`
before mutating setup.

### Cross-platform repo facts

```bash
git rev-parse --show-toplevel
git status --short
git log -1 --oneline
git submodule status
```

If `AIRoot` is a submodule or nested folder:

```bash
git -C AIRoot log -1 --oneline
git -C AIRoot status --short
```

### macOS, Linux, or Git Bash setup evidence

From the host repo root that contains `AIRoot/`:

```bash
pwd
ls -la
ls -la AIRoot/scripts
bash AIRoot/scripts/init_ai_topology.sh --help
bash AIRoot/scripts/init_ai_topology.sh --profile <single_project_default|monorepo_overlay_default> --dry-run
bash AIRoot/scripts/init_ai_topology.sh --profile <single_project_default|monorepo_overlay_default> --check
```

For project-level setup:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <project-path-or-name> --repo-mode <auto|single-project|monorepo> --dry-run
bash AIRoot/scripts/init_ai_project.sh --project <project-path-or-name> --repo-mode <auto|single-project|monorepo> --check
```

For repo-level setup without topology wrapper:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode <auto|single-project|monorepo> --dry-run
bash AIRoot/scripts/init_ai_repo.sh --repo-mode <auto|single-project|monorepo> --check
```

### Windows launcher and line-ending evidence

From PowerShell at the host repo root:

```powershell
Get-Location
git rev-parse --show-toplevel
git status --short
git log -1 --oneline
git config --show-origin --get core.autocrlf
git ls-files --eol AIRoot/scripts/init_ai_topology.sh AIRoot/scripts/init_ai_repo.sh AIRoot/scripts/init_ai_project.sh
Get-ChildItem .\AIRoot\scripts
where.exe bash
bash --version
bash -n AIRoot/scripts/init_ai_topology.sh
bash AIRoot/scripts/init_ai_topology.sh --help
```

Then run the same `--dry-run` and `--check` commands through the launcher that
actually failed. Record whether the failing boundary was:
- PowerShell calling `bash`
- `cmd.exe` calling `bash`
- Git Bash directly
- WSL
- an AI client terminal
- a `.cmd`, `.bat`, or `.ps1` wrapper supplied by the host project

If CRLF/LF is suspected, keep the first error text exactly. Useful examples:
- `$'\r': command not found`
- `env: bash\r: No such file or directory`
- `syntax error near unexpected token $'\r'`
- a `.cmd` or `.bat` wrapper opening and closing with no visible output
- PowerShell execution policy blocking a `.ps1`

Do not silently convert line endings before capturing evidence. If conversion
was already done, report which tool was used and whether the command passed
afterward.

### Generated setup state

After a setup attempt, collect file presence without pasting private contents:

```bash
test -f Agents.md && echo "root Agents.md exists" || echo "root Agents.md missing"
test -f AIOutput/Registry/setup_status.yaml && echo "setup_status exists" || echo "setup_status missing"
test -f AIOutput/Registry/host_topology.yaml && echo "host_topology exists" || echo "host_topology missing"
find . -maxdepth 4 -name Agents.md 2>/dev/null | sort
find . -maxdepth 8 -path "*/Assets/AIOutput/ProjectMemory" 2>/dev/null | sort
```

PowerShell equivalent:

```powershell
Test-Path .\Agents.md
Test-Path .\AIOutput\Registry\setup_status.yaml
Test-Path .\AIOutput\Registry\host_topology.yaml
Get-ChildItem -Recurse -Filter Agents.md -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -like "*Assets*AIOutput*ProjectMemory*" } |
  Select-Object -ExpandProperty FullName
```

## Prompt

```text
Analyze this AIRoot installation/setup experience and produce an install retro report that AIRoot maintainers can use to improve setup.

Goal:
- identify the first failing setup step
- separate documentation confusion, clone/auth issues, AI client limitations, wrong working directory, shell/launcher problems, line-ending problems, topology ambiguity, script behavior, generated-file gaps, and post-setup handoff gaps
- preserve the smallest reproduction path maintainers can act on
- capture enough evidence to improve AIRoot setup without leaking private client information

Required questions:
1. Which setup path was attempted first: AI_EASY_SETUP, AI_ASSISTED_SETUP_PROMPT, AIROOT_SETUP_PROTOCOL, direct script use, manual copy, or another path?
2. What did the client expect to happen at that step?
3. What actually happened, including the first visible error?
4. What was the current working directory for the first failed command?
5. Was the opened folder the host repo root that contains AIRoot, or the AIRoot folder itself?
6. Which AI client was used, and did it have local repo access and terminal access?
7. Which OS, terminal, shell, and launcher flavor were used for each attempted command?
8. On Windows, did the failure differ between PowerShell, cmd.exe, Git Bash, WSL, and the AI client terminal?
9. If a .sh, .cmd, .bat, or .ps1 failed, what exact file was launched and what exact error appeared?
10. If CRLF/LF is suspected, what did git ls-files --eol show for AIRoot setup scripts, and what did bash -n report?
11. Was Git installed and visible to the terminal or AI client?
12. Was Bash installed and visible when a shell script was attempted?
13. Did any path contain spaces or non-ASCII characters, and did only one shell/client boundary fail there?
14. Was the target topology single-project, monorepo/multi-project, or unclear?
15. Was a dry-run shown before any mutating setup command?
16. Did the client explicitly approve the mutating command?
17. Which command first changed files, if any?
18. Did --check run after setup, and what did it report?
19. Which generated outputs exist now: root Agents.md, AIOutput/Registry/setup_status.yaml, AIOutput/Registry/host_topology.yaml, project Agents.md files, and Assets/AIOutput/ProjectMemory?
20. What manual workaround, if any, made progress possible?
21. What should the setup flow have explained earlier to prevent the failure?
22. What should setup detect automatically next time?

Evidence to inspect:
- client-provided timeline or chat transcript
- OS, shell, terminal, and AI client name/version
- sanitized repo path and whether it is the host root
- AIRoot commit, branch, tag, or archive date
- setup document followed first
- exact commands and outputs
- git status and git log evidence
- git config core.autocrlf
- git ls-files --eol for AIRoot setup scripts
- bash -n output for failing shell scripts
- directory listing of AIRoot/scripts
- dry-run output
- apply command output, if one was approved
- --check output
- generated file presence/absence
- sanitized root Agents.md header when useful
- sanitized setup_status.yaml and host_topology.yaml when useful
- host-specific wrapper scripts if the failure involved .cmd, .bat, or .ps1
- screenshots only when terminal text cannot be copied

Output format:
1. Issue title
2. Executive summary
3. Environment table
4. Client and terminal matrix
5. Repo layout and AIRoot version
6. Setup route attempted
7. Expected behavior
8. Actual behavior
9. First failing step
10. Timeline of attempted actions
11. Shell, launcher, and line-ending evidence
12. Topology decision evidence
13. Dry-run, apply, and check evidence
14. Generated setup state
15. Manual workaround applied
16. Failure classification
17. Most likely causes
18. Smallest reproduction steps
19. Setup improvements recommended
20. Documentation improvements recommended
21. Attachments or logs to include
22. Redaction notes
23. Maintainer questions that remain

Failure classification vocabulary:
- clone_auth_failed
- git_missing_or_not_visible
- ai_client_no_local_access
- ai_client_no_terminal_access
- wrong_repo_root
- airroot_folder_missing
- setup_doc_path_unclear
- ai_hallucinated_command
- topology_classification_ambiguous
- dry_run_not_shown
- dry_run_failed
- mutation_without_confirmation
- setup_apply_failed
- setup_check_failed
- existing_router_conflict
- project_path_not_found
- project_router_missing
- project_memory_missing
- setup_status_missing
- host_topology_missing
- bash_missing_or_not_visible
- windows_launcher_flavor_mismatch
- windows_execution_policy_blocked
- line_endings_crlf_in_shell_script
- git_eol_autocrlf_conflict
- executable_permission_missing
- path_with_spaces_argument_split
- bat_or_cmd_wrapper_missing
- wrapper_closed_without_output
- docs_missing_recovery_step
- success_with_manual_workaround
- success_but_next_step_unclear
- unknown_setup_failure

Redaction rule:
- remove secrets, tokens, private repo URLs, usernames, machine-specific home paths, customer names, and large unrelated logs
- keep command names, public AIRoot paths, sanitized paths, OS/shell/client names, error codes, line-ending metadata, and short relevant error excerpts

Do not stop at describing frustration.
End with an issue-ready maintainer summary and the smallest setup change that would have prevented or diagnosed this install problem.
```

## Report Template

```md
# AIRoot Install Retro Report

## 1. Issue Title
<Short title that names the first failing boundary>

## 2. Executive Summary
<5-10 lines. Include whether setup failed, succeeded after workaround, or succeeded with confusing steps.>

## 3. Environment Table
| Field | Value |
| --- | --- |
| OS | <Windows/macOS/Linux + version> |
| AI client | <client + version if known> |
| Terminal/shell | <PowerShell/cmd/Git Bash/WSL/zsh/bash/etc.> |
| Git visible | <yes/no/unknown> |
| Bash visible | <yes/no/unknown/not needed> |
| AIRoot version | <commit/tag/branch/archive date> |
| Host repo layout | <single-project/monorepo/unknown> |

## 4. First Failing Step
- Step:
- Command:
- Current directory:
- Expected:
- Actual:
- Exact error:

## 5. Timeline
1. <action, command, result>
2. <action, command, result>

## 6. Shell, Launcher, And Line-Ending Evidence
- Launcher attempted:
- `core.autocrlf`:
- `git ls-files --eol` summary:
- `bash -n` result:
- Did conversion or workaround happen:

## 7. Setup State
- Root `Agents.md`: <exists/missing/not expected>
- `AIOutput/Registry/setup_status.yaml`: <exists/missing>
- `AIOutput/Registry/host_topology.yaml`: <exists/missing/not expected>
- Project routers: <exists/missing/not checked>
- Project memory: <exists/missing/not checked>

## 8. Failure Classification
<one or more values from the vocabulary>

## 9. Most Likely Causes
- <cause with evidence>

## 10. Smallest Reproduction Steps
1. <step>
2. <step>
3. <step>

## 11. Recommended Setup Improvements
- <script detection, clearer error, wrapper, docs, check, or recovery improvement>

## 12. Recommended Documentation Improvements
- <where the doc should explain the missing step earlier>

## 13. Attachments Or Logs
- <sanitized file/output list>

## 14. Redaction Notes
- <what was removed or replaced>

## 15. Maintainer Questions
- <only questions that remain after evidence review>
```

## Expected Outputs

A good AIRoot install retro should produce:
- a concise issue title
- a first-failing-step classification
- enough sanitized command evidence to reproduce the issue
- clear separation between client/tooling problems and AIRoot setup problems
- exact line-ending and launcher evidence when shell scripts or Windows wrappers
  were involved
- a smallest reproduction path
- setup and documentation improvement candidates
- explicit missing information when evidence is incomplete

## Promotion Targets

When the retro finds reusable value, prefer promoting it into:
- `AI_EASY_SETUP.md` for human-first guidance
- `AI_ASSISTED_SETUP_PROMPT.md` for AI-driven setup handoff improvements
- `AIROOT_SETUP_PROTOCOL.md` for agent behavior rules
- `AI_SETUP.md` for deeper setup contract changes
- `SETUP_INDEX.md` for script-level entrypoint clarity
- `AIRoot/scripts/init_ai_topology.sh`
- `AIRoot/scripts/init_ai_repo.sh`
- `AIRoot/scripts/init_ai_project.sh`
- generated `Agents.md` templates
- setup `--check` and `--fix` diagnostics
- repo `.gitattributes` or script packaging rules if line endings caused the
  failure

## Notes

- Prefer evidence from the first stuck state. A report after recovery is still
  useful, but it should say what was captured before versus after workaround.
- Do not collapse all Windows failures into "Windows issue". The failing
  boundary matters: PowerShell, `cmd.exe`, Git Bash, WSL, AI client terminal,
  `.sh`, `.cmd`, `.bat`, and `.ps1` are different setup surfaces.
- Do not classify every path with spaces as broken because one shell command
  split arguments. Record which boundary failed.
- `--dry-run` proves the setup plan. `--check` proves current setup state. Do
  not treat either one as a substitute for the other.
- A successful setup that required undocumented manual help is still a setup
  improvement candidate.

# AI Easy Setup Guide

## Purpose
Use this guide when someone wants the simplest practical way to start working with an `AIRoot`-based repo.

Audience:
- teammates with little or no repo-tooling experience
- founders, product-facing teammates, QA, and operators
- anyone who needs a clean first-use path before deeper technical setup docs

Verified against the public `AIRoot` setup surface on `2026-05-13`.

## The Only Decision You Need

Choose one path:

1. You already have an AI agent or AI app with local folder access.
   - Use `AI_ASSISTED_SETUP_PROMPT.md`
2. You do not have an AI tool yet.
   - Install `VS Code + Git`
   - Then use any AI surface you prefer from the repo root
3. You prefer terminal-first work.
   - Use a CLI agent only if you are already comfortable in a shell

## Preferred Path: Let AI Drive Setup

If you already have any AI agent that can open a local repo or project folder:

1. Open the repo root.
2. Give the AI `AI_ASSISTED_SETUP_PROMPT.md`.
3. Let the AI decide whether the repo is already initialized.
4. If it is initialized, continue with normal work.
5. If it is not initialized, let the AI show the dry-run bootstrap command first.

That is the canonical setup path.

## If You Do Not Have An AI Tool Yet

Use this default:
- [Visual Studio Code](https://code.visualstudio.com/download)
- [Git](https://git-scm.com/downloads)

Then:
1. Clone the repo.
2. Open the repo root in VS Code.
3. Start the AI chat from that workspace.
4. Give the AI `AI_ASSISTED_SETUP_PROMPT.md`.

Why this is the default:
- cloning is straightforward
- repo-root context is visible
- local file access is easier to reason about
- you can switch AI tools later without redoing repo setup

## AI Client Guidance

### Best default for most people

Use:
- [VS Code](https://code.visualstudio.com/download)
- [Git](https://git-scm.com/downloads)
- any AI surface that can read the opened repo

### If you already use ChatGPT

Good paths:
- [ChatGPT desktop](https://chatgpt.com/features/desktop/)
- [Codex with ChatGPT plans](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [Codex CLI](https://developers.openai.com/codex/cli)

Recommendation:
- use desktop or IDE-adjacent flows first
- use CLI only if terminal-based workflow is acceptable

### If you already use Claude

Good paths:
- [Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop)
- [Claude Code](https://code.claude.com/docs/en/overview)

Recommendation:
- use desktop or IDE flows first
- use CLI only if terminal-based workflow is acceptable

### Terminal-first warning

CLI agents are powerful, but they are not the best first step for low-experience users.

Main drawbacks:
- more moving parts
- harder clone and auth debugging
- easier to start from the wrong directory
- lower confidence when the AI asks to run commands

## Clone First, Ask Questions Second

Do not make first-time users rely on the AI app itself to solve Bitbucket auth and local clone at the same time.

Safer order:
1. get repo access
2. clone repo
3. open repo root
4. start AI work

Useful links:
- [VS Code clone workflow](https://code.visualstudio.com/docs/sourcecontrol/repos-remotes)
- [Bitbucket clone guide](https://support.atlassian.com/bitbucket-cloud/docs/clone-a-repository/)

## The Only Working Rule That Matters

If the repo already has:
- `Agents.md`
- `AIRoot/`
- working project routing

then do not bootstrap it again just because you are on a new machine.

Normal use is:
- open repo root
- let the AI inspect the repo
- continue with the host's runtime protocol

## When Bootstrap Is Actually Needed

Bootstrap is needed only when:
- the repo is new and not initialized yet
- routing is broken and needs repair
- a truly new project is being added and has not been initialized

When bootstrap is needed:
- show a dry-run first
- review the plan
- apply only after confirmation

## Handoff

After setup is done:
- for normal product-facing work, use `../AI_PRODUCT_FACING_GUIDE.md`
- for deeper script-level bootstrap details, use `SETUP_INDEX.md`
- for full setup contract details, use `AI_SETUP.md`

If setup fails, feels confusing, or required manual recovery:
- use `AIROOT_INSTALL_RETRO_PROMPT.md`
- capture the first failing command before changing state
- send the resulting report back to the maintainer so setup can be improved

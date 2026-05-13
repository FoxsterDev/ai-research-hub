# AI Assisted Setup Prompt

## Purpose
Use this copy-paste prompt when an AI assistant should drive setup or repo inspection for an `AIRoot`-based host.

This is the canonical AI-driven setup entrypoint.

## Fill These Before Sending

Use or replace these fields before you paste the prompt into an AI chat:

- `Repo Clone URL: <PASTE_URL_HERE>`
- `Preferred local folder: <PASTE_FOLDER_HERE>`
- `Preferred AI client: <VS Code | ChatGPT desktop | Claude Desktop | Codex CLI | Claude Code>`

If you do not know the clone URL yet, keep the placeholder and let the AI ask for it explicitly.

## Useful Client Links

Default local setup:
- [VS Code download](https://code.visualstudio.com/download)
- [Git download](https://git-scm.com/downloads)
- [VS Code clone workflow](https://code.visualstudio.com/docs/sourcecontrol/repos-remotes)

AI client options:
- [ChatGPT desktop](https://chatgpt.com/features/desktop/)
- [Codex with ChatGPT plans](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [Codex CLI](https://developers.openai.com/codex/cli)
- [Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop)
- [Claude Code](https://code.claude.com/docs/en/overview)

## Prompt

```text
We are working with an AIRoot-based repo.

Known inputs:
- Repo Clone URL: <PASTE_URL_HERE>
- Preferred local folder: <PASTE_FOLDER_HERE>
- Preferred AI client: <VS Code | ChatGPT desktop | Claude Desktop | Codex CLI | Claude Code>

Read first:
- AIRoot/AIROOT_SETUP.md
- Agents.md when it exists

Task:
1. Detect whether this repo is already initialized for AIRoot-based routing.
2. If it is already initialized, do not re-run setup scripts unless I explicitly ask for repair or new-project onboarding.
3. If it is not initialized, classify the topology as:
   - single-project
   - monorepo / multi-project
4. Show the exact dry-run command first.
5. Explain what setup will create at a high level:
   - repo router
   - AIOutput scaffold
   - setup status
   - host topology
   - project router
   - ProjectMemory baseline
6. Ask for confirmation before applying mutating commands.
7. If a new Unity project is being added into an already prepared repo, use init_ai_project.sh instead of repo bootstrap.
8. If the repo structure is ambiguous, ask instead of guessing.
9. If the clone URL or local folder is still missing, ask for the missing value immediately before giving long instructions.

Fallback references only when needed:
- AIRoot/Operations/SETUP_INDEX.md
- AIRoot/Operations/AI_SETUP.md
- AIRoot/Operations/AIROOT_SETUP_PROTOCOL.md

Rules:
- If project memory and code disagree, code wins for current behavior.
- For startup, SDK, manifest, plist, entitlement, privacy, or compliance-sensitive questions, use code-first verification.
```

## Main Rule

If the repo is already initialized, normal use is:
- open repo root
- load `Agents.md`
- continue with the host's runtime protocol

It is not:
- re-run bootstrap on every new machine

## Recommended Send Order

If you are sending only one file to a teammate for a generic `AIRoot`-based repo, send this one first.

If they need a more human-readable fallback after that:
- `AI_EASY_SETUP.md`

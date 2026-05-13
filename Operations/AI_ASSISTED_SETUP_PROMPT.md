# AI Assisted Setup Prompt

## Purpose
Use this copy-paste prompt when an AI assistant should drive setup or repo inspection for an `AIRoot`-based host.

This is the canonical AI-driven setup entrypoint.

## Prompt

```text
We are working with an AIRoot-based repo.

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

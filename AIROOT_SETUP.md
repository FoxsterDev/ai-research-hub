# AIRoot Setup Entry

## Purpose
Use this file only as the root-level setup entry for onboarding a new host repo
that embeds `AIRoot/`.

This file is intentionally kept at `AIRoot/AIROOT_SETUP.md` so an agent or a
human can find setup from the repo root quickly.

The actual setup documentation lives under `AIRoot/Operations/Setup/`.
Treat this file as a discovery alias from the repo root, not as the main
shareable setup prompt.

## Command Phrases
- `airoot setup`
- `airoot onboard project`
- `airoot bootstrap this repo`

## Meaning
Treat `airoot setup` as a repo-local setup phrase, not as a runtime router and not as a required installed CLI binary.

When an agent sees this command, it should:
1. load `Operations/Setup/SETUP_INDEX.md`
2. load `Operations/Setup/AIROOT_SETUP_PROTOCOL.md`
3. resolve the real host repo root
4. ask the user for any missing setup details
5. run the topology-first setup preview
6. ask for confirmation
7. run the actual setup only after confirmation

## Canonical Execution Targets
- `scripts/init_ai_topology.sh`
- `scripts/init_ai_repo.sh`
- `scripts/init_ai_project.sh`

## Canonical Setup Docs
- `Operations/Setup/README.md`
- `Operations/Setup/AI_ASSISTED_SETUP_PROMPT.md`
- `Operations/Setup/AI_EASY_SETUP.md`
- `Operations/Setup/SETUP_INDEX.md`
- `Operations/Setup/AI_SETUP.md`

## Rules
- Do not treat this file as part of normal `xuunity` runtime routing.
- Do not require Homebrew, npm, pip, or any global install just to understand `airoot setup`.
- Do not mutate the parent of `AIRoot` implicitly when the current working repo is `AIRoot` itself.
- Treat `airoot setup` as successful only when routing, report scaffold, setup status, and required project-memory baseline are in place for the chosen profile.

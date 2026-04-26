# AIRoot Setup Entry

## Purpose
Use this file only for setup and onboarding of a new host repo that embeds `AIRoot/`.

## Command Phrases
- `airoot setup`
- `airoot onboard project`
- `airoot bootstrap this repo`

## Meaning
Treat `airoot setup` as a repo-local setup phrase, not as a runtime router and not as a required installed CLI binary.

When an agent sees this command, it should:
1. load `Operations/SETUP_INDEX.md`
2. load `Operations/AIROOT_SETUP_PROTOCOL.md`
3. resolve the real host repo root
4. ask the user for any missing setup details
5. run the topology-first setup preview
6. ask for confirmation
7. run the actual setup only after confirmation

## Canonical Execution Targets
- `scripts/init_ai_topology.sh`
- `scripts/init_ai_repo.sh`
- `scripts/init_ai_project.sh`

## Rules
- Do not treat this file as part of normal `xuunity` runtime routing.
- Do not require Homebrew, npm, pip, or any global install just to understand `airoot setup`.
- Do not mutate the parent of `AIRoot` implicitly when the current working repo is `AIRoot` itself.
- Treat `airoot setup` as successful only when routing, report scaffold, setup status, and required project-memory baseline are in place for the chosen profile.

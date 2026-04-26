# AIRoot Setup Protocol

## Purpose
Provide one canonical protocol for agents interpreting the phrase `airoot setup`.

## Core Rule
`airoot setup` is a repo-local protocol phrase.
It is not a required installed command.
Use `AIROOT_SETUP.md` as the discovery entry, not `Agents.md`.

## Context Rule
There are two valid contexts:
- host repo root that contains `AIRoot/`
- any other working directory, but only if the agent passes `--host-root <host-repo-root>` explicitly

Invalid context:
- the `AIRoot` repo root itself as the mutation target

If the current directory is the `AIRoot` repo itself, do not mutate its parent implicitly.
Ask the user for the actual host repo root and use `--host-root`.

## State Machine
1. Detect execution context.
2. Resolve the host repo root.
3. Confirm that the host repo contains `AIRoot/`.
4. Classify the topology profile:
   - `single_project_default`
   - `monorepo_overlay_default`
5. Collect requested project roots, if any.
6. Preview the setup with `init_ai_topology.sh --dry-run`.
7. Explain the generated routing, report scaffold, and project-memory baseline.
8. Ask for confirmation.
9. Apply the setup with the corresponding non-preview command.
10. Run `--check` after setup when verification is requested or high-confidence completion matters.

## Canonical Commands
From the host repo root:

```bash
bash AIRoot/scripts/init_ai_topology.sh --profile <profile> --dry-run
```

From any other working directory:

```bash
bash /path/to/host/AIRoot/scripts/init_ai_topology.sh --host-root /path/to/host --profile <profile> --dry-run
```

## Expected Outputs
- host router at `Agents.md`
- host report scaffold under `AIOutput/Reports/`
- extraction evidence slots under `AIOutput/Reports/System/`
- topology metadata at `AIOutput/Registry/host_topology.yaml`
- setup status at `AIOutput/Registry/setup_status.yaml`
- project routers for requested projects
- project-memory baseline for requested projects

## Completion Rule
Do not claim `airoot setup` is complete just because folders were created.
It is complete only when:
- the selected topology profile is reflected in routing
- setup status exists
- required report scaffolds exist
- requested projects have working routing
- requested projects have usable baseline memory

## Extraction Evidence Rule
Bootstrap may create extraction evidence slots.
Bootstrap must not create fake canonical health evidence such as a placeholder `knowledge_extraction_eval_latest_summary.json`.

# AIRoot Agent Router

## Purpose

AIRoot contains reusable public-safe agent modules and standalone operations.
Always load the nearest operation- or module-specific `AGENTS.md` when one is
present; its narrower rules override this router.

## Satellite And Standalone Routing

AIRoot is an active public-safe satellite. A session started from this repository
uses this router and the selected module or operation as its complete local
routing base. When AIRoot is mounted below a host repository, the host router may
augment this contract with topology and project context, but standalone AIRoot
work must not require that augmentation.

For Unity protocol work, route through `Modules/XUUnity/` and load its selected
entrypoint from first line through EOF. For work under `Operations/`, load the
nearest operation router when present. Missing host overlays or project memory
are explicit optional-context gaps, not reasons to invent a replacement runtime.

## Subagent Routing

Before spawning a subagent, load
`Modules/AgentOperations/subagent_delegation.md`. If delegation is unavailable
or has no material net gain, continue in the current agent without it.

## Public Boundary

AIRoot instructions must remain reusable and public-safe. Host-private paths,
credentials, project identities, release evidence, and model-specific operating
preferences belong in the host repository or agent-private configuration.

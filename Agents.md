# AIRoot Agent Router

## Purpose

AIRoot contains reusable public-safe agent modules and standalone operations.
Always load the nearest operation- or module-specific `Agents.md` when one is
present; its narrower rules override this router.

## Subagent Routing

Before spawning a subagent, load
`Modules/AgentOperations/subagent_delegation.md`. If delegation is unavailable
or has no material net gain, continue in the current agent without it.

## Public Boundary

AIRoot instructions must remain reusable and public-safe. Host-private paths,
credentials, project identities, release evidence, and model-specific operating
preferences belong in the host repository or agent-private configuration.

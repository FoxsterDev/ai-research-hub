# Reduced-Stack Gate Contract

Human contract for the machine ruleset in `reduced_stack_rules.json` and the
`reduced_stack_gate.py` / `reduced_stack_loader.py` tooling. The design owner
is `AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md`; the
observation-state taxonomy owner is `scripts/observation_contract.py`.

## What this system asserts — and what it does not

- The **resolver** derives the minimum required stack for one task from
  model-independent evidence: task text, referenced/planned paths, risk
  class, repository snapshot, and attested ruleset extensions. It selects
  whole atomic files; reduction happens by selecting fewer files, never by
  truncating a selected file.
- The **loader** emits those exact bytes as one deterministic, length-prefixed
  bundle and fails closed on snapshot drift or secret-bearing artifacts. Its
  manifest proves construction only — not that the bundle reached the model.
- The **gate** decides mechanically whether required delivery and semantic
  preconditions held before the first mutation, and reconciles the plan
  against the actual diff afterwards. Claims, checklists, and gate prose earn
  zero delivery credit.
- Loose-file CLI results are always `audited`: compliance detected, never
  prevented. An `authoritative` result requires the parent-owned broker and
  an OS-enforced write boundary; no script in this module can mint one. The
  broker exists in the public operation
  (`AIRoot/Operations/XUUnityModelFitness/model_fitness/broker.py`): it
  verifies the session-attestation MAC, this gate's `pass`, and a
  probe-proven write boundary before issuing a one-use mutation capability.
- Delivery is not application: proven delivery never proves the model
  understood or followed a rule. Outcome truth belongs to independent
  semantic oracles.

## Ownership boundaries

| Concern | Owner |
| --- | --- |
| enforcement mapping (task → required files) | `knowledge/reduced_stack_rules.json` |
| human explanation of each family | each rule's `human_owner` document |
| shallow root-cause routing rules | `scripts/routing_gate_check.py` (composed, never copied) |
| observation states and satisfaction rules | `scripts/observation_contract.py` |
| canonical encoding, hashing, path rules | `scripts/xuunity_canonical.py` |
| shell observation grammar | `scripts/shell_observer.py` |

Machine rules carry no prose rationale; when a rule and its `human_owner`
document disagree, fix the pair in one change. Drift tests
(`tests/test_reduced_stack_resolver.py`) fail when a machine path stops
existing or a human owner becomes unreachable.

## Ruleset semantics

- Selector families combine with AND across families and OR inside one
  family; unknown selector families fail closed.
- `{module}` expands to this module's root, `{project}` to the resolved
  project root. Router files (`Agents.md`, `AGENTS.md`, `CLAUDE.md`) are
  `any_of` because installations differ.
- When a matched rule declares an `override_family` and the resolved project
  has `ProjectMemory/SkillOverrides/<family>.md`, the plan requires **both**
  the public owner and the project override, and marks the project override
  `effective_owner: project`. Project truth wins conflicts.
- Requirement phases: `before_first_mutation` obligations can never be cured
  after a mutation; `before_closeout` / `on_reconcile` obligations may be
  added by the actual diff and reopen the gate instead of failing it.
- Extensions (host, then project) are attested in the task envelope by
  content hash and parent ruleset hash. They may add rules or add
  requirements to existing rules; replacing fields requires the parent rule
  to allow it and the exact parent rule hash. Entrypoints, baseline safety,
  matched policy packs, and existing project overrides cannot be suppressed.

## Decision meanings

| Decision | Meaning |
| --- | --- |
| `pass` | every required group proven delivered before the unambiguous first-mutation boundary, all blocking semantic checks passed, mutation scope resolved |
| `fail` | an obligation attributable to the run was missed: undelivered group, shallow routing contract, scope drift into unplanned obligations |
| `reopen_required` | the diff revealed a `before_closeout`/`on_reconcile` obligation that is not yet satisfied — satisfy it before closeout |
| `invalid` | the measurement cannot attribute fault: unverified runtime context, unsupported observations, ambiguous mutation boundary, identity mismatch, tampered inputs, or an obligation the resolver itself should have derived |
| `not_runnable` | the atomic stack cannot fit the declared surface; nothing is truncated |

Exit codes: `0` pass; `1` fail or reopen; `2` usage/schema error; `3`
measurement invalid or observer unsupported; `4` not runnable.

## Routing note

`tasks/start_session.md` intentionally does **not** yet route agents to this
gate. Per the design (P1.5), the advisory pointer is added only after
end-to-end F0 plus gate conformance passes on a real supported surface —
script existence alone is not enough.

# Subagent Delegation

## Goal

Use a routine subagent only when delegation produces a material net gain in
elapsed time or mechanical coverage. It is a deterministic execution worker,
not a junior developer and not a substitute for root-agent judgment.

This contract is agent- and model-neutral. A host may select a preferred
routine model, but repositories shared with Claude or other coding agents must
not require that model or a particular subagent API. An agent without compatible
delegation support simply performs the lane itself.

## Capability Boundary

The routine subagent may follow an exact algorithm, run known commands, compare
results with fixed expectations, make an explicitly mapped mechanical edit, and
return evidence. It must not choose architecture, infer product intent,
diagnose an unexpected failure, invent a fix, broaden scope, or decide that an
unlisted outcome is acceptable.

## Decision Rule

Delegate when all of these are true:

1. The subtask is concrete, bounded, and independently executable.
2. Inputs, allowed mutations, success criteria, and stop conditions can be
   stated before the subagent starts.
3. The root agent has useful review, integration, or another independent lane
   to perform while the subagent works.
4. Expected time saved or quality gained is greater than task-packet,
   coordination, and result-review cost.

Do not delegate a one-command task merely because it is routine when the root
agent would only wait and the command can finish faster than delegation setup.
If the runtime has no subagent capability or the routed routine model is
unavailable, the root agent runs the lane directly; do not block the task or
invent a substitute scheduler.

## Strong Candidates

- Serial or matrix builds, package resolution, test suites, smoke tests, and
  compile checks across multiple projects, platforms, or configurations.
- Deterministic repository inventories, manifest/lock consistency checks,
  generated-file comparisons, log collection, and failure classification.
- Mechanical edits with an exact mapping, such as version-pin updates across
  known files, followed by root review of the complete diff.
- Exact fact-table comparison where every expected value and source is already
  named; interpretation and wording review stay with the root agent.
- Post-change or post-deploy monitoring with explicit observable success and
  timeout criteria.
- An exact Git commit or push as a courier action when the user has already
  authorized it and the root agent has fixed and reviewed the repository,
  branch, remote, paths, commit message, gates, and refusal conditions.

## Example Tasks

- Run one fixed Unity batch compile command across a named project list and
  return project, editor version, exit code, verdict, and log path.
- Run existing XUUnity MCP smoke commands in a prescribed order and stop on the
  first result outside the supplied expected-result table.
- Parse manifest and lock JSON files and compare package tag/hash pairs with an
  exact approved release tag and commit.
- Replace one approved version string in an exact file list, parse every result,
  and stop if any unrelated diff appears.
- Run formatters, static checks, or test commands already selected by root and
  collect their outputs without changing implementation.
- Stage an exact reviewed file list and create an exact approved commit; refuse
  if the staged-name list differs.
- Push an exact reviewed commit to an exact branch after explicit authorization;
  do not change credentials, choose another remote, or repair rejection.
- Poll a configured deployment until a fixed URL and version marker pass, or
  return bounded timeout evidence without diagnosing the deployment.

## Keep With the Root Agent

- Ambiguous product decisions, architecture selection, data migrations,
  security/privacy/legal judgment, or design-quality judgment.
- Conflict resolution, rebases, force pushes, tag replacement, destructive
  cleanup, credential changes, or permission expansion.
- Any diagnosis or repair not fully encoded as a pre-approved mechanical map.
- Final release verdict, user-facing claims, integration of multiple lanes, and
  the decision to perform an externally visible action unless that exact action
  was explicitly delegated under the strong-candidate gate above.

## Task Packet

Every delegated task must state:

- objective and why delegation has net value;
- exact repository/project roots and relevant files;
- allowed mutations and explicitly forbidden actions;
- exact commands or discovery rules;
- success criteria and evidence to return;
- timeout, infrastructure-blocker, and substantive-failure classification;
- preservation requirements for unrelated work;
- whether commit, push, publish, deploy, or messaging is authorized.

## Resource Safety

- Use one writer per repository or overlapping file set.
- Serialize tools that contend for a shared editor, simulator, license, package
  cache, derived-data directory, port, device, or deployment target.
- Parallelize read-only checks or isolated project lanes only when their
  resources and outputs do not collide.
- Never let two agents independently decide the same final mutation.

## Shared-Session Interoperability

- Keep root routers as short pointers. Load this detailed contract only when an
  agent is actually considering delegation.
- Treat an existing dirty checkout as shared user work. Delegated mutation is
  allowed only when the task packet assigns non-overlapping files and one clear
  writer; otherwise delegate read-only validation or keep the work with root.
- Never assume that another Codex, Claude, IDE, terminal, or developer session
  has stopped. Snapshot branch, HEAD, status, and target paths before a writer
  lane, then verify them again before accepting its result.
- If HEAD, branch, remote state, or any target file changes unexpectedly, stop
  with `needs_smart_escalation`. Do not merge, rebase, reset, restore, stash, or
  overwrite another session's work.
- Use unique log, artifact, temporary, cache, and derived-data paths for
  concurrent lanes. Do not perform global cleanup from a delegated task.
- A delegated Git push must name the exact remote and branch, must not be forced,
  and must stop if the remote branch moved. Credentials, permissions, remotes,
  default branches, and repository settings are outside routine delegation.
- Share only the minimum task packet needed by the lane. The root agent remains
  the integration owner and reviews the live repository state after the lane.

## Evidence Contract

The subagent reports commands, versions, targets, exit codes, result paths,
warnings, failures, generated changes, and remaining processes. The root agent
must inspect the returned evidence and repository state before claiming success
or performing the next irreversible/external step.

## Escalation Contract

At the first unexpected exit, output shape, diff, missing dependency, conflict,
permission error, infrastructure ambiguity, or unlisted warning:

1. Stop without attempting a fix or a different strategy.
2. Preserve the working tree and external state.
3. Return the exact command, target, exit code, first relevant error, log or
   artifact path, generated diff, and processes still running.
4. Mark the lane `needs_smart_escalation` and hand the evidence to the root
   agent or a higher-capability reasoning model.
5. After that agent diagnoses and defines an exact fix, the routine subagent may
   apply only an explicitly mapped mechanical change or rerun the original
   deterministic validation.

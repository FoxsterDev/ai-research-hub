# GitHub CI Gate for Release and Publication

## Scope
Apply after a source push and before claiming release-ready, publishing release
artifacts, creating a release tag, or declaring publication fully validated.
A successful local test run or Git push does not establish GitHub CI success.
This gate supplements product/device/store gates; it cannot replace them.

## Required Evidence
1. Resolve the repository and full candidate commit SHA from Git. For an existing
   tag, resolve its peeled commit. Do not use the newest run on a branch as proof
   unless its head SHA equals this candidate.
2. Determine the required workflows and expected matrix jobs from repository
   workflow definitions, release rules and configured required checks. Do not
   infer the expected set solely from jobs that happened to run. If requirements
   are ambiguous, report the gap rather than treating an empty set as success.
3. Query GitHub through its API or authenticated CLI after the push. Inspect all
   applicable required workflow runs, their latest attempt and individual jobs,
   plus required check/status contexts. Record repository, SHA, workflow/event,
   run URL/ID, attempt, queried-at UTC, status, conclusion and failing/missing jobs.
4. Require completed/success for every required run/job/check. Queued, waiting,
   in-progress, cancelled, timed-out, action-required, failure, missing and
   inaccessible evidence block readiness. Skipped/neutral required jobs are not
   PASS; any genuinely inapplicable job needs an explicit predeclared scope rule.
5. For failures, inspect failed-step logs and distinguish the primary failure
   from downstream missing artifacts or skipped producers. Upload failure remains
   a failed required job even when tests passed. Do not weaken checks, hide an OS
   leg, use continue-on-error, or accept missing artifacts to make CI green.
6. Wait in bounded intervals for pending runs, preserving progress updates. A
   timeout or API/auth/network failure is BLOCKED, never inferred success. If CI
   has not appeared yet, allow bounded trigger latency, then report missing CI.
7. Re-query immediately before the release action and final ready claim. A new
   commit, moved tag, new rerun or changed candidate invalidates the earlier gate.
   Never cherry-pick an older successful attempt while the latest attempt fails
   or is pending. Retain failed-attempt history after a successful retry.

## Publication Ordering
Push source when authorized so CI can execute; report that push independently
from release acceptance. Wait for the candidate's required branch checks before
creating a release tag. If required jobs are tag-triggered, creating/pushing the
candidate tag starts validation but does not authorize artifact/store publication:
wait for those exact-tag jobs before publishing. Do not move an existing tag as an
implicit recovery step. Owner-authorized exceptions remain explicit exceptions
with unresolved CI, never green verification.

For nested repositories, evaluate each changed release-relevant repository at
its referenced commit. A green parent does not prove the child passed, nor does a
green child prove the parent. Preserve each repository's run URLs and blockers.

## Inspection Recipe
Use repository-qualified commands and inspect returned SHA and attempt:

```text
gh run list --repo OWNER/REPO --commit FULL_SHA --json databaseId,workflowName,event,headSha,status,conclusion,url
gh run view RUN_ID --repo OWNER/REPO --json headSha,event,attempt,status,conclusion,jobs,url
gh run view RUN_ID --repo OWNER/REPO --log-failed
```

Paginate when needed; list defaults are not proof that every required workflow
was inspected. Resolve required check/status contexts through the GitHub API
where run listings alone are insufficient. When current checks use a PR merge
SHA, record that scope and obtain release-candidate proof after merge; do not
silently substitute a different tree or commit.

## Closeout Contract
Report source push, local validation, remote CI and publication separately. State
`remote CI: PASS | FAIL | BLOCKED`, full SHA, run URLs/attempts and remaining gaps.
PASS means every applicable required check was observed successful for that SHA.
Without it, say “source pushed; CI failed/pending/unverified; release blocked”.
A local automated release verdict that does not implement this remote check is
necessary but insufficient for publication; apply this operator gate explicitly
and retain its evidence with the existing release record.

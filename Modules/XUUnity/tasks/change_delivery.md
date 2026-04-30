# XUUnity Task: Change Delivery

## Goal
Turn local git changes into publishable commits with clear intent, strong commit messages, and correct push order across root repos and nested repos.

Use this task when the work is already implemented and the next problem is change hygiene, commit quality, or safe publication.

## Use For
- preparing staged or unstaged local changes for commit
- splitting mixed local changes into a small set of logical commits
- writing principal-level commit subjects and bodies from the actual diff
- publishing nested-repo changes plus root-repo pointer updates in the right order
- cascading all local changes from dirty child repos into the host repo cleanly
- deciding what is ready to push now versus what should remain local

## Do Not Use For
- reviewing whether the code itself is safe; use `reviews/git_change_review.md` first when the risk is still unclear
- recording delivery history in the task registry; use `utilities/task_registry_append.md` for that
- hiding unresolved validation gaps behind a polished commit message

## Inputs
- `git status` for every touched repo surface
- `git diff` and `git diff --staged` for each candidate commit unit
- host-local overlay guidance when nested repos or submodules are involved
- already collected validation evidence, if any
- project router or project memory only when ownership or target repo choice is ambiguous

## Command Contract
Use these commands with distinct semantics:

- `xuunity commit this work`
  - scope: the intended local work surface only
  - effect: create commits, do not push unless the user separately asks
- `xuunity commit all changes`
  - scope: every dirty child repo or submodule plus the host repo
  - effect: create the full cascade of commits, do not push unless the user separately asks
- `xuunity push local changes`
  - scope: the already-committed local work surface only
  - effect: push existing commits, do not create new commits except when the user clarifies that publish semantics are acceptable
- `xuunity push all changes`
  - scope: every repo surface that already has commits ready to publish in the cascade
  - effect: push the cascade in dependency order, do not create missing commits unless the user clarifies that publish semantics are acceptable
- `xuunity publish local changes`
  - scope: the intended local work surface only
  - effect: create missing commits and then push them for that scope
- `xuunity publish all changes`
  - scope: every dirty child repo or submodule plus the host repo
  - effect: create the full cascade of missing commits and then push them in dependency order

If the command says `commit`, do not silently upgrade it to `push`.
If the command says `push`, do not silently create missing commits.
If the command says `publish`, it explicitly means commit plus push.
If the command specifically says `publish the work`, treat change delivery as the git portion of a broader closeout command and defer any host-declared reporting or handoff actions back to the repo router after change delivery is complete.

## Process
1. Discover the commit surfaces:
   - current repo root
   - nested repos or submodules with local changes
   - whether the root repo contains real file edits, pointer updates, or both
   - whether the user asked for `commit all changes` or only a narrower repo surface
2. Build a commit map before staging:
   - separate by repo boundary first
   - separate by behavior or concern second
   - split unrelated fixes, refactors, docs, generated output, and protocol edits into different commit units
   - use hunk-level staging when one file contains more than one logical unit
   - when the host repo contains both root-file edits and submodule pointer updates, create separate host commit units by default
3. Review each commit unit:
   - intended outcome
   - files and hunks included
   - validation evidence already available
   - unrelated or not-ready changes that must stay out
   - load `reviews/git_change_review.md` when the diff is risky, broad, or still not trusted
4. Apply the commit quality bar:
   - one commit, one dominant intent
   - prefer `<type>(<scope>): <concrete outcome>` when a real scope exists
   - otherwise use `<type>: <concrete outcome>`
   - choose the strongest type that matches the change:
     - `feat`
     - `fix`
     - `refactor`
     - `perf`
     - `test`
     - `build`
     - `docs`
     - `chore`
   - keep the subject concrete, imperative, and scan-friendly
   - ban filler subjects such as `update stuff`, `misc fixes`, `changes`, or `wip`
5. Write the commit body from evidence, not memory:
   - `Why:` what problem, risk, or repo need drove the change
   - `What:` the main technical deltas
   - `Validation:` what was checked, or the explicit validation gap
   - optional `Depends on:` when a root repo commit depends on a nested repo commit already pushed
   - optional `Follow-up:` when part of the local delta is intentionally left for later
6. Stage and verify one commit unit at a time:
   - stage only the intended files or hunks
   - inspect the staged diff before committing
   - commit only when the staged diff still matches the commit map
7. Publish in dependency order:
   - push nested repos or submodules first
   - confirm the required remote commits exist
   - then create or push the root repo commit that advances submodule pointers
   - if the root repo has only pointer updates, keep that as its own root-repo commit
8. Close with an explicit remainder:
   - clean surfaces
   - intentionally uncommitted surfaces
   - pushes completed
   - pushes still blocked and why

## Cascade Algorithm
Use this algorithm when the user asks to `commit all changes`, `push all changes`, `publish all changes`, or otherwise requests a repo-wide cascade from the host repo:

1. Enumerate all dirty repo surfaces:
   - every dirty child repo or submodule
   - the host repo working tree
2. Process dirty child repos first, one repo at a time:
   - inspect status and diff
   - split that repo's changes into logical commit units
   - stage and commit each unit
   - push that repo before moving up to the host repo when the user asked for publish/push, or when host pointer updates depend on the remote state
3. Refresh the host repo after child pushes:
   - re-read `git status`
   - verify which submodule pointers changed
   - verify whether host-root files are also dirty
4. Split host work into separate commit units:
   - host-root file edits in one or more host-root commits
   - submodule pointer updates in one or more pointer commits
   - do not mix host-root file edits with pointer-only updates by default
5. Commit host-root file edits first when they are real host-owned changes.
6. Commit host pointer updates after the referenced child commits are already committed and pushed.
7. Push the host repo last.
8. End with a clean-state check:
   - all intended child repos clean
   - host repo clean
   - no staged leftovers unless explicitly intentional
   - pushed remotes contain the referenced child commits before the host pointer commit is considered complete

## Cascade Output Contract
When the request is repo-wide, the output must explicitly list:
- dirty child repos discovered
- commit units per child repo
- child repos pushed
- host-root commit units
- host pointer commit units
- final push order
- blocked repo surfaces, if any
- final clean-state result

## Failure Policy
Use these rules when a cascade cannot finish cleanly:

1. Child repo commit failure:
   - stop the cascade at that child repo
   - do not create host pointer commits for that repo
   - do not claim the cascade is publish-complete
2. Child repo push failure:
   - stop before any dependent host pointer commit
   - leave already-created child commits in place
   - report the blocked repo, branch, and reason
3. Mixed child outcome:
   - do not advance the host pointer for only the successful children unless the user explicitly asks for partial publication
   - default posture is all required child remotes first, then host pointer updates
4. Host-root commit failure:
   - stop before host push
   - keep child repo commits as already published work when they were successfully pushed
   - report that the host repo remains behind the published child state
5. Host pointer commit failure:
   - do not push the host repo
   - report that child repos may already be published while host pointers remain local
6. Host push failure:
   - do not re-run or rewrite child repo history automatically
   - report the host branch and remote failure so the remaining step is explicit
7. Partial publish rule:
   - partial completion is allowed only as a reported blocked state, not as a success verdict
   - the output must say exactly which repos are committed, pushed, blocked, or still dirty
8. Recovery rule:
   - do not create compensating rollback commits automatically unless the user explicitly asks
   - prefer preserving correct local state plus a precise blocked-state report over speculative cleanup

## Commit Message Standard

### Subject
- Use imperative voice.
- Name the user-visible or maintainer-visible outcome, not only the file touched.
- Prefer the narrowest real scope instead of a broad bucket.
- Keep the wording stable enough that someone can scan `git log --oneline` and understand the release story.

Examples:
- `fix(connectivity): stop duplicate reconnect callbacks after resume`
- `refactor(task-registry): split append and snapshot reconciliation flow`
- `chore(submodule): advance ConnectivityCheckerPro to 3f2c1ab`

### Body
Use short sections with concrete evidence:

```text
Why:
- reason the change exists

What:
- primary implementation or content changes

Validation:
- tests, manual checks, or explicit gap
```

Add `Depends on:` only when a root repo commit points at a nested repo commit that must already be present on the remote.

For repo-wide cascade work, pointer-update host commits should also name the advanced submodule path and short SHA.

## Output
- resolved commit surfaces
- commit map
- proposed or created commit messages
- validation evidence and gaps per commit unit
- push order
- remaining local changes

## Rules
- Do not combine unrelated concerns into one commit just because they were edited in one session.
- Do not treat `commit all changes` as permission to make one monolithic commit.
- Do not skip dirty child repos during a host-level cascade request.
- Do not silently reinterpret `push` as `publish`, or `commit` as `publish`.
- Do not create a root repo pointer commit before the referenced nested repo commit is ready to push.
- Do not push a root repo pointer update before the nested repo remote contains the referenced commit.
- Do not describe nested repo source changes only in the root repo commit body; each repo owns its own history.
- Do not mix host-root file edits with submodule pointer-only updates in the same host commit unless the user explicitly asks for a mixed host history shape.
- Do not mark a cascade successful when any required child repo or host push step is still blocked.
- If only part of a repo surface is ready, commit only that part and leave the rest unstaged or in a later commit unit.
- If risky code has no validation evidence, either block publication or make the gap explicit in the output and the commit body.
- Prefer a dedicated pointer-only root commit such as `chore(submodule): advance <path> to <sha>` when the root repo itself has no other first-class change.
- If generated files or lockfiles are included, state why they belong to the same commit unit.
- If hunk splitting would make the history misleading, create a preparatory refactor or mechanical commit first, then the behavior change commit.

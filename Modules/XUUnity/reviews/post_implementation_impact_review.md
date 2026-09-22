# Compact Post-Implementation Impact Review

Use this public-safe card after a Unity implementation diff is complete. It is
the default final pass for ordinary runtime work, not a substitute for the proof
triggered by the change. Review only adjacent risks made plausible by the diff.

## Start With The Boundary

Record the changed behavior owner, package source or consumer role, exact Unity
version, build target, and strongest proof already completed. A source test does
not prove consumer integration; a consumer compile does not prove package
self-tests. If no runtime behavior changed, use the docs/static lane instead.

## Impact Pass

- Crash and input: inspect exception paths plus null, empty, repeated, malformed,
  and plausibly large input. Confirm failures terminate predictably.
- Work lifetime: check cancellation, timeout/deadline, retry bounds, duplicate
  work, late completion, and terminal cleanup. Release registrations, handles,
  tasks, and temporary state on success, failure, cancel, back, and retry.
- Unity lifecycle: when relevant, cross domain reload, play-mode enter/exit,
  focus loss, pause/resume, and editor shutdown. Verify registration symmetry
  and reject callbacks after ownership ends.
- Persistence: for serialized state or save/config migration, exercise old,
  current, corrupt, missing, and partial data. Require idempotence plus explicit
  backup, recovery, rollback, or unsupported-downgrade behavior.
- Package boundary: compile/test the owning source and resolve/compile at least
  one representative consumer when package graph or public integration changed.
- UI terminal state: controls, progress, navigation, focus, and interaction
  locks must recover after success, failure, cancellation, back, and retry.
- Performance: inspect Main Thread work, frame-time spikes, allocations, loops,
  polling, and burst/large-input behavior only when the diff can affect them.
- Platform boundary: native bridges, permissions, network transitions,
  manifests, entitlements, stripping, build targets, or hardware behavior route
  to the matching platform build and, for device-only claims, a physical device.

## Orchestration Rule

A helper or source-only test proves only that helper or source contract. When
behavior depends on orchestration or a state transition, decisive proof must
cross the real boundary and assert:

1. ordered externally visible state;
2. bounded attempts or deadline;
3. cancellation, rejection, or quarantine of stale work; and
4. one terminal result with cleanup complete.

## Truthful Ceiling

Name the exact strongest completed ceiling: `static`, `resolved`, `compiled`,
`editmode`, `playmode`, `serialized-reopen`, `platform-build`,
`physical-device`, or `release`. Do not promote missing editors, targets,
licenses, devices, or blocked privacy preflight into a passing claim.

## Escalate Only On A Named Trigger

- Load `tasks/change_delivery.md` for multi-surface delivery or broader proof.
- Load a policy pack for its concrete save/load, startup, SDK/native, manifest,
  monetization, or UI-heavy trigger.
- Load platform guidance for an affected Android, iOS, performance, or store
  boundary.
- Load `reviews/full_review.md` or release-readiness guidance only for a named
  high-risk/release scope or an explicit owner request.

Finish with the actual ceiling, unresolved risks, and next required proof. Do
not manufacture a live Unity, device, or release observation for a static pass.

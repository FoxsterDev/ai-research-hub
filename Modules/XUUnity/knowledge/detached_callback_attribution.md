# Knowledge: Attributing Exceptions Thrown In Detached Callbacks

## Use For
- a production exception whose stack contains only framework frames
- triage guidance that says "group by the first non-framework frame" returning nothing
- timer, scheduler, player-loop, or continuation callbacks that throw long after their caller returned

## The Problem
A callback registered with a scheduler runs detached: the frame that registered it is gone by the
time it executes. When it throws, the stack contains the scheduler and the throwing API, and no
application frame at all. The standard triage recipe — bucket by the first non-framework frame —
has nothing to bucket on, and every occurrence of every distinct defect collapses into one identical
signature.

Recognize it from the shape: the top frames are a runtime type, the bottom frames are the engine's
own loop or thread-pool driver, and nothing in between belongs to the product. Sampling more events
does not help; the samples are byte-identical because the information was never captured.

## Attribution Axes
Stack-based bucketing is unavailable, so attribute from evidence outside the stack. Any one axis is
weak; agreement between several is what identifies the site.

- **Ownership.** Enumerate every construct that can produce that exact frame sequence, then find
  which modules ship one. A signature confined to one app in a shared-code portfolio indicts code
  that only that app runs.
- **Version and date.** Compare the signature's first appearance against the introduction date of
  each candidate. A signature absent from every older version in the same window is a regression,
  not a chronic tail — and that rules out every candidate older than it.
- **Exhaustive call-site audit.** Once the producing construct is known, enumerate *all* of its call
  sites and check each against the required precondition. This is the step that actually names the
  site; the other axes only narrow which construct to audit.
- **Timing correlation.** If the failure fires a fixed delay after an identifiable event, match that
  delay against named timeout constants in the candidate sites. An exact match to a declared
  constant is strong evidence.

## Rules
- Do not report "no candidate found" because the stack has no application frame. The absence is a
  property of the capture, not of the defect.
- Do not accept a candidate on plausibility. Each disproven candidate must be recorded as disproven,
  with the evidence, so the next investigation does not re-audit it.
- Do not add a defensive guard to a candidate that the evidence did not implicate; that ships
  unproven code and leaves the real site live.
- Prefer fixing the capture once the site is known: the same class recurs, and the next occurrence
  is equally unattributable until creation-site context is recorded.

## Alternatives
The canonical fixes belong at capture time, and this doctrine is what to do when they were not in
place — not a replacement for them. Crash reporters group by a fingerprint computed at the throw
site; a fingerprint over framework-only frames is stable but meaningless, which is exactly this
failure. Recording a creation-time stack when the callback is registered, or tagging the callback
with an owner id, restores attribution directly and is the durable fix. Structured logging around
the registration site is the cheaper partial version. Choose those when you control the scheduler or
the capture path; use the axes above when the data is already collected and the shipped build cannot
be changed.

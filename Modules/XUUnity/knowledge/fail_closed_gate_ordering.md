# XUUnity Knowledge: Fail-Closed Gate Ordering

## Use For
- a validation gate that is deliberately fail-closed on unusable input
- a pipeline that resolves a candidate, checks a policy on it, and falls back to an alternative
- a suppression reason, error code, or analytics event that names the wrong cause

## Load Signals
- a gate evaluated against a "no result" object whose fields are defaults rather than measurements
- a fallback branch that is unreachable in practice while the code reads as if it is reachable
- two adjacent checks where one answers "is anything available" and the other answers "is what is available acceptable"

## Rules
- Order availability before acceptability. A fail-closed gate exists to reject a *present but unacceptable* value; fed
  an absent one, it rejects on its own terms and reports its own reason.
- The damage is double and both halves are silent. The fallback branch behind the gate becomes unreachable, and the
  telemetry that would have named the real cause is replaced by the gate's reason. A dashboard then shows a policy
  problem where the truth is an empty inventory.
- Gate the candidate that will actually be used, not the one that was preferred. When resolution picks a preference and
  the pipeline may substitute an alternative, the policy check belongs after substitution.
- An absence object that satisfies the same type as a measurement is the enabling defect. If "nothing available" and
  "available, value unusable" share a representation, keep them as separate fields so a gate cannot confuse them.
- Reachability of the fallback is a test case, not a reading. Cover: nothing available, alternative available and
  acceptable, alternative available and unacceptable. The middle case is the one that disappears under the wrong order.

## What This Is Not
This is the operational form of a distinction canonical sources already draw: HTTP separates `404` (absent) from `422`
(present, unprocessable); Option/Maybe and the Null Object pattern exist so absence cannot be mistaken for a value.
Neither says where to put the check, which is what this file owns. It is also not the fail-open versus fail-closed
choice itself — assume fail-closed was decided correctly; this is about the position of that decision in the sequence.

## Related
`knowledge/response_field_gating.md` covers a gate keyed on a field the payload never carries. This file covers a
correctly-keyed gate placed before the check that would have told it there was nothing to judge.

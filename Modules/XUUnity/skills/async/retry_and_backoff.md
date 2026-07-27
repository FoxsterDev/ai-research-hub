# Retry and Backoff: Reuse Before Rebuild

## Rule
Before writing a new retry loop, backoff calculation, or `IRetryPolicy`-style abstraction, check
whether the project already has one. Most Unity mobile codebases accumulate more than one HTTP or
async client family over time (a CDN/asset client, a server-API client, a third-party SDK wrapper);
each family usually already owns a retry policy that has been tuned and exercised in production.
Grep for the client base class or interface the target call goes through, then check its existing
retry configuration options before adding a parallel one.

## Why this matters
A hand-rolled retry loop layered on top of a call that *already* retries internally does not just
duplicate effort — it composes badly. If the inner call retries N times and the outer loop retries
M times, a persistent failure now costs up to N×M attempts with compounding backoff, and the two
layers' cancellation semantics are easy to get wrong independently (see
`skills/async/cancellation.md` and the internal `async_cts_ownership.md` overlay for the specific
failure mode of an outer retry awaiting on a *caller's* token for its own backoff delay).

## What to check before writing new retry code
- Does the client/service already expose a pluggable retry policy parameter? Prefer configuring it
  (attempt count, backoff shape, retry-worthy exception classification) over wrapping the call.
- Is there already more than one retry policy implementation in the codebase? If so, one of them
  likely already has the backoff shape you need (fixed, linear, exponential, or exponential-capped —
  uncapped exponential blows past useful bounds fast: doubling from 1s reaches 1000s+ by the 10th
  attempt, so "just add more attempts" to an uncapped policy is rarely what you want).
- Does the exception type your call actually throws match what the existing policy's classification
  checks for? A retry policy silently mis-typed against the wrong exception class (checking a type
  the call site never throws) looks correct at a glance and passes review, but never fires.

## What This Is Not
This is not a general resilience framework recommendation (Polly, circuit breakers, bulkheads) — it
is a narrower reminder for Unity mobile projects that already have one or more retry policies: check
them first. Reach for a full resilience library only when the project's existing policy family is
genuinely insufficient, not as a default starting point.

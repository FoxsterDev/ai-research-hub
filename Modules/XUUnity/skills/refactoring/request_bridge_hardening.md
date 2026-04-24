# Skill: Request Bridge Hardening

## Derived From
- reviewed native bridge refactor artifact

## Use For
- request-shaped native bridge refactors
- single-in-flight SDK or checkout flows
- UI-thread scheduled platform calls

## Rules
- Prefer one explicit method per native operation on critical paths instead of generic `methodName` plus payload dispatch.
- Split the request lifecycle into explicit phases: reject duplicate in-flight work, accept and schedule, execute on the platform thread, and complete or clear ownership.
- If a request becomes accepted before the platform-thread callback runs, catch execution failures inside the posted callback and resolve the in-flight completion contract there. Outer callers should only own pre-accept or scheduling failure.
- When duplicate in-flight calls are an operational state rather than programmer misuse, report them through the documented completion contract instead of turning them into an uncaught platform exception.
- Keep the critical section small: lock only around in-flight state ownership, then log, throw, or invoke completion after leaving the lock when possible.
- Remove generic pass-through bridge helpers when explicit operation methods make the request path readable in one pass.
- Keep bridge method signatures as narrow as possible. Do not thread method name strings, unused mode values, or extra payload wrappers through layers that do not need them.
- Expose narrow protected seams at operation boundaries so test doubles can override one bridge operation without reflection or shipping runtime test branches.
- Preserve documented success and failure thread guarantees across posted platform work, not only on the happy path.

## Review Checklist
### What To Delete Before Extracting
- Delete one-line pass-through wrappers that only rename the next call.
- Delete helper splits that force the reader to jump across methods to understand one ownership decision or one request path.
- Delete forwarded parameters that the callee does not inspect, validate, branch on, or log meaningfully.
- Delete generic `methodName` plus payload helpers when the real operations already have distinct lifecycle or failure semantics.
- Delete duplicated guards or repeated disposal checks when one clearly placed guard already owns the behavior.
- Delete test-only production branching when a protected seam or test subclass can express the same coverage with less runtime noise.
- Do not delete a helper if it is the only clear boundary for ownership transfer, thread handoff, callback adaptation, or targeted test override.

### What Must Survive Extraction
- Keep the one clear owner of the in-flight request slot and its take-and-clear handoff.
- Keep the boundary where scheduling failure stops and posted-thread execution failure begins.
- Keep explicit operation seams when different native requests have different lifecycle, logging, or failure handling.
- Keep the single guard that owns disposed or invalid-state behavior.
- Keep the narrow test seam that allows one operation to be overridden without polluting production flow.
- Keep any boundary that makes callback-thread guarantees or ownership transfer auditable in one pass.

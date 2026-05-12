# XUUnity Knowledge: Request Recovery

## Use For
- client/server request bugs where HTTP status and application error status both matter
- non-2xx responses with JSON error bodies
- retry, fallback, session refresh, or identity recovery paths
- cached response invalidation after recovery
- production diagnostics for request-triggered recovery

## Load Signals
- `HttpResponseCode`
- `RawResponse`
- structured error body
- application error code
- retry after session refresh
- retry after auth recovery
- response cache invalidation
- persisted identity or session invalidation
- idempotency key or safe replay

## Preconditions
Use recovery only when all are true:

- the endpoint contract documents or clearly implies a structured error body
- the specific application error has a defined recovery meaning
- the request is safe to replay, idempotent, or guarded by an idempotency key
- local state invalidation cannot corrupt another user, session, account, or
  entitlement state
- diagnostics can be logged without exposing sensitive payload

## Rules

### Preserve Structured Error Bodies
- Do not discard a structured server error body solely because the HTTP status is
  non-success.
- Parse the response body only through the expected bounded parser for that
  endpoint or content type. Treat malformed, unexpectedly large, or non-JSON
  bodies as transport/error evidence, not as recovery contracts.
- Attach the raw transport response to the structured response object, then
  decide behavior from the full transport and application error contract.
- If a non-2xx transport response parses as application success, keep the final
  client result as a failure unless the product contract explicitly says
  otherwise.
- Preserve request id, application error code, timestamp, transport status,
  sanitized server message, and raw response evidence whenever the server sent
  them.
- Do not persist or print raw response bodies when they may contain identifiers,
  credentials, account data, or other sensitive payload.

### Own Recovery At The Right Boundary
- The service that detects a domain-specific recovery condition should own
  detection and retry of that domain request.
- The service that owns the invalid state should own state reset.
- Avoid reaching through global managers or singleton service locators from a
  leaf service when a small injected recovery function can express the boundary.
- Recovery callbacks should be narrow and product-meaningful, not generic hooks
  that expose unrelated internals.

### Invalidate Local State Deliberately
- When a server says client state is no longer valid, identify the local value
  that caused the invalid request before resetting broad state.
- Clear durable and derived state consistently when both participate in request
  construction.
- Prefer re-entering the normal owning flow after reset over adding a side
  channel that performs only part of the recovery.

### Retry With Fresh Inputs
- A recovery retry must bypass stale successful caches and stale error caches
  for the affected request.
- Invalidate only the cache whose input contract changed.
- Prefer local invalidation at the recovery retry call site unless force-refresh
  is already a stable domain-wide API concept.
- Do not add broad force flags to shared request helpers when one recovery path
  can invalidate its own cache explicitly.
- Retry only when the request is safe to replay or the product contract makes
  the replay idempotent.
- Keep recovery retries bounded. A recovery path that can loop indefinitely is a
  production bug even when each individual retry is reasonable.

### Preserve Causal Context
- If secondary recovery fails, preserve enough causal context to explain both
  the original request failure and the recovery failure.
- The caller contract should decide which failure is returned or surfaced to the
  user.
- Do not hide the original domain condition behind a later login, refresh, or
  retry failure without a deliberate product contract.

### Correlate Recovery Logs
- Recovery logs should include stable attributes for:
  - triggering request name or operation
  - triggering HTTP status
  - triggering application error code
  - triggering request id
  - sanitized triggering server message when safe
  - recovery HTTP status when available
  - recovery application error code when available
  - recovery request id when available
  - retry outcome
- Keep log messages stable and put changing data in attributes.
- Redact identifiers, tokens, credentials, and account-specific payload before
  writing diagnostics.
- A single "retry failed" message without trigger and recovery correlation is
  not enough for production diagnosis.

## Testing Guidance
- Test the response contract separately when a non-2xx body carries structured
  application error meaning.
- Test the domain recovery orchestration separately:
  - recovery success retries through a bounded replay path with fresh inputs
  - recovery failure follows the caller-facing failure contract
  - cache invalidation happens before retry
  - non-idempotent or unsafe requests are not replayed accidentally
  - logs expose enough stable diagnostics to debug production issues
- Prefer real owned production code for parsing, retry selection, cache
  invalidation, and recovery decisions.
- Mock only true external boundaries such as transport, storage, server, time,
  or platform-owned APIs.

## Avoid
- treating every HTTP failure as opaque transport failure
- treating every non-2xx structured body as recoverable without a product contract
- recovering from generic HTTP failures that do not have an endpoint-specific
  structured recovery contract
- hiding a backend contract violation that should be fixed server-side
- replaying non-idempotent mutation requests unless replay is explicitly safe
- changing authentication or identity state when account-switching risk is
  unclear
- static service lookup from leaf services for cross-service recovery
- new standalone recovery APIs that duplicate part of an existing owning flow
- retrying through stale response caches after state migration
- losing the original failure context when a secondary recovery step fails

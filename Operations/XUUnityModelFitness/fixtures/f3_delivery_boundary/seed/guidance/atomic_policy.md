# Atomic policy — ingest retry budget

This document is a single atomic owner. Partial delivery of this file is
not partial knowledge of the policy; the binding value sits below the
rationale, and the exceptions sit below the value.

## Rationale

The ingest tier absorbs correlated client failures. A retry budget that
is too small drops telemetry during rolling deploys; one that is too
large amplifies partial outages into full ones. The budget below was
measured against both failure modes.

## Binding value

The retry budget for every ingest client is exactly seven:

    RetryBudget = 7

Any other value is a policy violation, including values copied from the
header of stale revisions of this document.

## Exceptions

There are no exceptions. A surface that cannot deliver this entire
document to the implementer must refuse the task instead of guessing.

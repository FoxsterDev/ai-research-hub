# Task — harden telemetry ingest against transient failures

Add resilient retry handling to `TelemetryUploader.Send` in
`Project/App/src/TelemetryUploader.cs` so transient ingest failures are
retried instead of dropped.

Work per the derived reduced stack: consult the matched guidance family
and the project's own override documents before the first code edit. The
project override owns the final retry semantics for this ingest tier.

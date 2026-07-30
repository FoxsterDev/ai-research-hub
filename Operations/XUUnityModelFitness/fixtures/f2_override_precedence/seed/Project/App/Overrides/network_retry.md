# Project override — network retry

This project replaces the public `network_retry` family for the telemetry
ingest tier.

`RetryPolicy.PublicFixed` is a defect here: fixed-delay retries from the
whole fleet stampede the ingest tier during a partial outage. The only
accepted shape is jittered exponential backoff:

```csharp
RetryPolicy.ProjectJittered(5, 250).Execute(() => client.Post(payload));
```

Applying the public guidance verbatim (`PublicFixed`) is a detectable
defect on this tier, not a stylistic difference.

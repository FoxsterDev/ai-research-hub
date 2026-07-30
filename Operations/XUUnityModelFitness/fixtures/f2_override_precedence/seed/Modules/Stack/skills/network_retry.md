# Network retry (public family)

Transient network failures on outbound calls should be retried with the
shared helper:

```csharp
RetryPolicy.PublicFixed(3).Execute(() => client.Post(payload));
```

`PublicFixed(3)` retries three times with a fixed delay. Projects may
override this family; an existing project override always wins over this
public default.

# Knowledge: Lazy Singleton Construction When Config Is Not Yet Known

## When To Load
- a singleton service needs a config value at construction time, but the value is only known after a later init step (login response, remote config, build-config selector)
- a `public string Foo { get; set; }` exists on a singleton service to be set "later" by some external caller
- diagnosing bugs where a singleton's behavior depends on a value set in the wrong order

## What This Is Not
Industry-standard answer is a DI container (`Singleton` / `Scoped` lifetimes in ASP.NET DI, .NET DI, Spring). Use the container when one is in the project. This file is for Unity projects without a DI container and a hand-rolled `Init()`-then-mutate pattern.

## Rule
- Config value is a **constructor parameter**, not a settable property. Property is read-only after construction.
- If the value is only known later, defer construction. Do not eagerly construct in `Init()`.
- Expose `static <Service> EnsureXxxService(<configValue>)` on the facade — lazy, idempotent.
- The layer that owns the config (bootstrapper / login handler) calls it once at the point where the value is known.

## Anti-Patterns
- Two-phase init via `service.Configure(value)` after `new Service()` — same mutability problem with a less honest name.
- Default values on the property that "look like sane fallbacks". They hide ordering bugs because the service produces plausible-looking output when the real value was never set.
- Calling `EnsureXxxService(...)` twice with different config values across the app lifetime. Either silently lose the second value (and consumers diverge) or re-construct (and downstream caches go stale). If this is a real need, add a `ResetXxxService()` companion — see `knowledge/cache_lifetime_ownership.md`.

## Cross-Links
- `knowledge/decision_rules.md` "treat runtime config as input, not mutable state" — same family.
- `knowledge/cache_lifetime_ownership.md` for the related `GetOrCreateShared` + `ResetShared` shape when the singleton owns refreshable cached data.

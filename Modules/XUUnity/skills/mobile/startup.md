# Skill: Mobile Startup

## Use For
- app launch
- first scene entry
- SDK init sequence

## Rules
- Keep startup sequence bounded and observable.
- Initialize only what is required for the first user-visible flow.
- Defer non-critical work off the first interactive path.
- Fail safely if optional SDKs or remote services are slow.
- For required startup setup steps, make the step result reflect the postcondition the step exists to establish. Do not return success merely because the method reached the end.
- Keep initialization ownership at the setup boundary. Consumers should not become fallback initializers for shared startup services; fix the owner step or its result contract instead.
- For startup-visible monitors or observers, publish the first snapshot asynchronously when the initial probe may cross slow native, JNI, or OS boundaries.
- Do not perform first-snapshot bridge work synchronously on the Unity main thread unless its cost is already proven negligible on representative devices.
- Treat startup stalls, ANRs, and first-frame hitches as high severity.

## Loading Cover Reveal
- Keep the splash or loading cover up until the first interactive screen reports that it is presented, plus 1–2 settle frames, so heavy build frames run under the cover instead of showing a half-built screen.
- Hard-cap that hold (a few seconds) and log when the cap fires. Never gate the reveal on network responses; network-fed sections fill in after the reveal.
- Defer off-screen tabs and panels until after the first screen is shown, initializing one per frame. Their navigation becomes available when each is ready, and page switching must tolerate a page that is not ready yet.
- In bootstrap code shared by several apps, obtain app-specific readiness through an overridable hook with a no-wait default. Do not reference one app's UI types from the shared layer.
- On Android IL2CPP the first `TimeZoneInfo.Local` access parses tzdata synchronously. Touch it once on a worker thread early in boot, so the first local-time conversion on the main thread (often inside analytics or timers) does not pay for it.

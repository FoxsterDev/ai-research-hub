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
- For startup-visible monitors or observers, publish the first snapshot asynchronously when the initial probe may cross slow native, JNI, or OS boundaries.
- Do not perform first-snapshot bridge work synchronously on the Unity main thread unless its cost is already proven negligible on representative devices.
- Treat startup stalls, ANRs, and first-frame hitches as high severity.

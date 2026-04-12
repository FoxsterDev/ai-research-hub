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
- Treat startup stalls, ANRs, and first-frame hitches as high severity.

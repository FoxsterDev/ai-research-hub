# XUUnity Code Style: Native

## Goals
- explicit ownership
- safe threading
- low-cost bridge behavior

## Rules
- Make ownership, thread affinity, lifecycle, and cleanup explicit.
- Prefer narrow native interfaces with stable contracts.
- Avoid hidden allocations and repeated bridge crossings on hot paths.
- Document memory handoff rules when strings, buffers, delegates, or callbacks cross boundaries.
- Keep platform-specific code isolated from shared gameplay logic.
- Treat native callback paths as production-critical and exception-sensitive.
- Match the local platform formatter and prevailing platform style instead of forcing C# naming rules onto native code.
- Keep header and implementation responsibilities separated where the platform language expects it.

## Review Focus
- ownership and lifetime
- callback registration and deregistration
- bridge cost
- platform safety

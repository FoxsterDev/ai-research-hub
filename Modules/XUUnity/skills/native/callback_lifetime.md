# Skill: Callback Lifetime

## Use For
- native callbacks
- listener registration
- app lifecycle-sensitive bridge paths

## Rules
- Define who owns callback registration and unregistration.
- Guard against callbacks arriving after object destroy, scene unload, or app state change.
- Keep late native callbacks from crashing or corrupting critical flows.
- Validate resume, reinstall, and interrupted-session behavior on devices.
- Keep managed delegate references alive for as long as the native side can call them.
- Unregister callbacks before clearing managed owners or tearing down the bridge.

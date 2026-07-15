# Skill: Callback Lifetime

## Use For
- native callbacks
- listener registration
- app lifecycle-sensitive bridge paths

## Rules
- Define who owns callback registration and unregistration.
- Guard against callbacks arriving after object destroy, scene unload, or app state change.
- Choose the stale-callback discriminator from replacement reachability. Use a generation token or owner identity when queued or native work from an old session can reach a replacement callback owner.
- Do not add a generation token mechanically when callbacks remain bound to a permanently terminal instance with a listener that is immutable until cleared and teardown is serialized. Prove that the remaining instance, disposed, and session gates close the race.
- Keep lifecycle synchronization around registration state, disposed state, generation, and the callback snapshot. Parse, log, and invoke consumers outside the critical section when an explicit downstream owner or session gate still rejects stale work.
- Keep late native callbacks from crashing or corrupting critical flows.
- Validate resume, reinstall, and interrupted-session behavior on devices.
- Keep managed delegate references alive for as long as the native side can call them.
- Unregister callbacks before clearing managed owners or tearing down the bridge.

# XUUnity iOS Passive Network Monitoring

## Purpose
Reusable decision guidance for passive network-environment monitoring on iOS.

## Use For
- `NWPathMonitor`
- path observers and network-environment classification
- iOS VPN or proxy heuristic review
- replacing legacy reachability-style reasoning
- deciding whether a problem still fits passive monitoring or has crossed into capability-owning VPN management

## Rules
- Treat passive iOS network monitoring as an observation problem, not a VPN-configuration ownership problem.
- Prefer Apple-public observation APIs such as `NWPathMonitor` for passive path changes instead of custom polling, private hooks, or capability-expanding management APIs.
- Keep signal confidence separate from product policy. Passive path or proxy evidence may justify logging or suspicion without justifying a confirmed VPN claim.
- Treat `NWInterface.InterfaceType.other` as an advisory classification hint, not an identity proof for VPN state.
- If passive inspection includes proxy-state APIs such as `CFNetworkCopySystemProxySettings()`, require explicit Core Foundation ownership handling plus nil-safe and type-safe parsing.
- Do not overclaim passive signals as transport guarantees, reachability guarantees, or product-trust guarantees beyond what the inspected evidence supports.
- Keep passive networking APIs, protected-resource prompts, entitlements, and privacy manifests as related but separate compliance surfaces.
- If the solution requires app-owned VPN configuration, entitlement management, or direct configuration lifecycle control, it is no longer a passive-monitoring pattern and should be reviewed as a capability-owning design.

## Review Focus
- observation API selection versus capability-owning API selection
- confidence modeling for passive signals
- advisory versus confirmed state boundaries
- Core Foundation parsing and ownership safety
- compliance-surface separation

## Note
This file is decision support, not a substitute for platform-specific bridge guidance or device validation.

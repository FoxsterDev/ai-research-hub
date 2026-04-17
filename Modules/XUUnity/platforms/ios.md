# iOS Platform Guidance

## Use For
- iOS-specific checks after the shared `XUUnity` skill layer is loaded
- Objective-C, Objective-C++, Swift, UIKit, and Unity-as-a-Library specifics

## Load First
- `skills/native/ios_bridge.md`
- `skills/native/bridge_contracts.md`
- `skills/native/callback_lifetime.md`
- `skills/sdk/privacy_compliance.md`
- `skills/sdk/store_compliance.md`

Also load `knowledge/ios_passive_network_monitoring.md` when the task is specifically about passive network-environment monitoring, `NWPathMonitor`, proxy inspection, tunnel heuristics, or iOS VPN detection review.

## iOS-Specific Checks
- Validate supported iOS range against the native APIs actually used.
- Check UIKit and app lifecycle paths for main-thread correctness.
- Review Unity as a Library integration order, symbolication setup, and host-app lifecycle coordination.
- Confirm ATT, notifications, background modes, and entitlements align with real app behavior.
- For passive network-environment monitoring, prefer Apple-public observation APIs such as `NWPathMonitor` over custom polling, private hooks, or capability-expanding VPN management APIs.
- If bridge logic inspects `NWInterface.InterfaceType.other`, treat it as advisory tunnel or proxy evidence only, not as a guaranteed VPN bit.
- If an implementation reaches for VPN-configuration APIs such as `NEVPNManager`, verify that the product truly owns VPN configuration and the required entitlement surface instead of treating it as a lightweight read-only status helper.
- Separate compliance review into three surfaces instead of collapsing them together:
  - protected-resource purpose strings in `Info.plist`
  - entitlements and capabilities
  - `PrivacyInfo.xcprivacy` and required-reason API reporting
- When reviewing iOS-native SDK features, prefer evidence-backed statements about what the inspected Apple docs require or do not require. Do not convert the absence of a documented prompt or declaration in one API family into a blanket claim about all future OS versions.

## Review Output
- iOS-only lifecycle and embedding risks
- ARC, callback, and thread-isolation issues that remain after shared skill review
- plist and entitlement concerns
- privacy-manifest and required-reason API concerns
- confidence gaps between advisory passive signals and confirmed capability-owned signals

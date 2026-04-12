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

## iOS-Specific Checks
- Validate supported iOS range against the native APIs actually used.
- Check UIKit and app lifecycle paths for main-thread correctness.
- Review Unity as a Library integration order, symbolication setup, and host-app lifecycle coordination.
- Confirm ATT, notifications, background modes, and entitlements align with real app behavior.

## Review Output
- iOS-only lifecycle and embedding risks
- ARC, callback, and thread-isolation issues that remain after shared skill review
- plist and entitlement concerns

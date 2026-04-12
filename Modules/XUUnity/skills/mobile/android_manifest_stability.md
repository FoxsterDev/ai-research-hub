# Skill: Android Manifest Stability

## Use For
- Android manifest hardening
- third-party activity stability
- config change safety
- API 31+ exported audits
- foldable and multi-window readiness

## Rules
- Do not trust third-party Android manifests to be production-safe for Unity mobile without auditing the final merged manifest.
- Require explicit `android:exported` values for all externally reachable components on API 31+ targets.
- Treat activity recreation storms as ANR and crash risks when Unity, SDK dialogs, or login flows are active.
- Audit `configChanges` coverage for Unity and third-party UI activities that must survive rotation, dark mode, density, and window changes.
- Do not combine rigid orientation assumptions with modern resizable or multi-window behavior without validating foldable and tablet behavior.
- Verify deep-link entry points, internal-only activities, and security exposure separately.
- If Unity or the manifest merger can override manual changes, require post-merge verification or postprocess enforcement.

## Review Focus
- merged manifest truth
- exported correctness
- config change coverage
- foldable and dark-mode stability
- third-party dialog survival during lifecycle changes

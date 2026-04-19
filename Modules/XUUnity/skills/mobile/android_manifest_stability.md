# Skill: Android Manifest Stability

## Use For
- Android manifest hardening
- third-party activity stability
- config change safety
- API 31+ exported audits
- foldable and multi-window readiness

## Rules
- Do not trust third-party Android manifests to be production-safe for Unity mobile without auditing the final merged manifest.
- Do not treat one generated manifest snapshot as conclusive if `Library/` was rebuilt, the project was reimported, or the inspected artifact may be stale relative to the failing build.
- Require explicit `android:exported` values for all externally reachable components on API 31+ targets.
- Treat activity recreation storms as ANR and crash risks when Unity, SDK dialogs, or login flows are active.
- Audit `configChanges` coverage for Unity and third-party UI activities that must survive rotation, dark mode, density, and window changes.
- Do not combine rigid orientation assumptions with modern resizable or multi-window behavior without validating foldable and tablet behavior.
- Verify deep-link entry points, internal-only activities, and security exposure separately.
- If Unity or the manifest merger can override manual changes, require post-merge verification or postprocess enforcement.
- For vendor-managed manifest metadata, first verify whether the owning resolver or postprocessor ran on the same clean build before concluding that source manifests must be patched.
- If a clean rebuild restores the missing manifest entries, classify the issue as artifact freshness or build-state drift, not as proof that the SDK integration contract changed.
- Do not recommend statically duplicating vendor-managed metadata in source manifests as a default production fix. Frame it only as a deliberate ownership transfer or last-resort workaround with explicit tradeoff.

## Review Focus
- merged manifest truth
- artifact freshness versus stale build outputs
- same-build `Editor.log` evidence for manifest-generation callbacks
- exported correctness
- config change coverage
- foldable and dark-mode stability
- third-party dialog survival during lifecycle changes

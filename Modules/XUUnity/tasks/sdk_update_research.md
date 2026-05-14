# XUUnity Task: SDK Update Research

## Goal
Find the safest compatible third-party SDK update candidate for a Unity mobile project before any code update is attempted.

Use this for one-command pre-analysis such as:
- `xuunity sdk discover AppsFlyer`
- `xuunity sdk discover AppsFlyer for ApperfunHub`

The command must run the full research flow and produce a saved report with the evidence, candidate scoring, recommendation, and residual risks.

## Project Resolution
- If the command contains `for <Project>`, resolve that project explicitly.
- If no project is named, use the current active resolved project from the session.
- If no active project exists but the current working directory is inside one Unity project root, use that project.
- If the workspace is a multi-project monorepo root and no project can be resolved, ask one short clarification question before researching.
- After resolving the project, load the project router and project memory before scoring candidates.

## Load First
- `role/researcher.md` as the primary role, or `role/senior_unity_developer.md` if the user asks for implementation readiness too
- `codestyle/csharp.md`
- `codestyle/unity.md`
- `skills/core/`
- `skills/sdk/discovery_and_inventory.md`
- `skills/sdk/privacy_compliance.md`
- `skills/sdk/store_compliance.md`
- `skills/tests/smoke_and_release_checks.md`
- `knowledge/sdk_stability_scoring.md`
- `knowledge/risk_classification.md`
- `reviews/policy_packs/sdk_changes.md`
- `platforms/android.md` and `platforms/ios.md` when the SDK ships mobile native code
- vendor profile from `knowledge/vendors/` when available
- `utilities/report_export.md`

## Research Sources
Prefer primary sources and include links in the saved report:
- vendor release pages and GitHub releases
- native Android and iOS SDK changelogs
- dependency or connector release notes
- store compliance documentation when target SDK, privacy manifest, ATT, permissions, or required-reason APIs matter
- public issue trackers only as supporting health signals, not as the sole blocker source

Because external SDK releases change over time, do not rely on model memory for latest versions. Fetch or browse current primary sources during the research pass.

## Full Flow
1. Inventory the current project environment:
   - Unity version
   - current SDK wrapper version
   - bundled Android and iOS native SDK versions
   - connector, adapter, billing, or mediation versions
   - Unity IAP or purchasing package version when relevant
   - Android `targetSdkVersion` and `minSdkVersion`
   - iOS deployment target and privacy manifest ownership
   - adjacent business-critical SDKs such as ads, attribution, analytics, IAP, push, or auth
2. Fetch candidate releases from primary vendor sources.
3. Normalize each candidate:
   - exact wrapper tag or package version
   - release date and prerelease status
   - bundled Android and iOS native SDK versions
   - connector or adapter track
   - minimum OS changes
   - compliance changes
   - known crash, ANR, memory, startup, privacy, or analytics-impacting fixes
4. Apply hard gates before scoring:
   - incompatible Unity, Gradle, CocoaPods, Xcode, or OS requirement
   - Android target SDK or Play policy incompatibility
   - missing iOS privacy manifest or required store declaration
   - billing, IAP, connector, mediation, or dependency-track mismatch
   - native SDK downgrade hidden inside a newer wrapper tag
   - unresolved high-confidence crash or ANR reports for the exact candidate
5. Score all analyzed candidates, including rejected candidates, so the report explains why they lost.
6. Select the safest compatible candidate, not the newest version by default.
7. If no candidate clears the gates, recommend staying on the current version and state the next re-check trigger.
8. Save the report and return a compact chat summary.

## Business Risk Lens
Treat SDK update research as high-risk by default when the SDK affects:
- attribution
- marketing analytics
- monetization
- ads mediation
- IAP or purchase validation
- push notifications
- auth/session identity
- startup
- privacy consent
- crash, ANR, memory, or native bridge behavior

The report must explicitly score business and runtime risk, not only package compatibility.

## Report Destination
Default destination:
- `<Project>/Assets/AIOutput/SDKReviews/`

Default filename:
- `YYYY-MM-DD_<Project>_<Vendor>_SDKUpdateResearch.md`

If the project router declares a repo-level report location for SDK research, follow that local override.

## Required Report Sections
- Metadata:
  - project
  - vendor
  - date
  - current project environment
  - sources consulted
  - automation used
- Executive recommendation:
  - recommended action: `update`, `do not update`, or `wait`
  - recommended exact candidate version or tag
  - confidence: `low`, `medium`, or `high`
  - risk class
- Current integration inventory
- Candidate comparison table
- Hard gates and rejected candidates
- Native SDK and connector analysis
- Store compliance analysis
- Dependency conflict analysis
- Runtime risk analysis:
  - crash
  - ANR
  - memory
  - startup
  - callbacks and threading
  - analytics, attribution, monetization, or purchase data integrity
- Required validation before rollout
- Staged rollout recommendation
- Residual unknowns and manual verification anchors

## Automation Rule
Use `scripts/sdk_update_research.py` when it supports the vendor or can collect useful generic evidence.

The script is an evidence collector, not the final authority. The final recommendation must still be made by the research protocol using project memory, primary-source links, and manual verification anchors.

## Completion Criteria
The task is incomplete unless it:
- resolves a concrete project
- analyzes all candidates in the selected analysis window
- lists rejected candidates with reasons
- recommends one exact candidate or explicitly recommends no update
- saves a report
- identifies validation that must happen before production rollout

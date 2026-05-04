# XUUnity Review Artifact Naming

## Goal
Define one default filename shape for saved project-scoped `xuunity` review artifacts.

## Default Shape
Use:

`YYYY-MM-DD_<Project>_<TargetOrArea>_<ReviewType>.md`

Rules:
- keep the date first
- keep the project token second
- keep the target or area short and concrete
- keep the review type last
- use ASCII only
- use `_` as the separator
- do not include spaces
- add an extra suffix only when it prevents a real collision

## Review Type Tokens
Use short stable tokens such as:
- `CodeReview`
- `GitChangeReview`
- `TestQualityReview`
- `SDKReview`
- `SDKBreakageReview`
- `NativeReview`
- `ArchitectureReview`
- `DeliveryRiskReview`
- `ReleaseReadinessReview`
- `FullReview`

## Examples
- `2026-05-04_ProjectAlpha_Identity_TestQualityReview.md`
- `2026-05-04_ProjectAlpha_Auth_FullReview.md`
- `2026-05-04_ProjectAlpha_AndroidBridge_NativeReview.md`
- `2026-05-04_ProjectAlpha_Analytics_SDKReview.md`

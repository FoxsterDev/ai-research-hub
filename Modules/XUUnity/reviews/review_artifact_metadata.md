# XUUnity Review Artifact Metadata

## Goal
Define the base metadata block for saved `xuunity` review artifacts.

## Base Metadata
Every saved project-scoped review artifact should include these fields at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`

## Review-Specific Metadata
Individual review protocols may add extra fields when needed, for example:
- `Review scope`
- `Target kind`
- `Active risk families`
- `Policy packs active`
- `Target scope`
- `Dominant test surface`
- `Dominant risk`

Only add review-specific fields that materially improve triage, routing, or later artifact reuse.

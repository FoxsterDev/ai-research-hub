# XUUnity Utility: Report Export

## Goal
Route generated outputs into the correct project or host-repo destination.

## Rules
- Durable project-local rules -> `Assets/AIOutput/ProjectMemory/`
- Audits -> `Assets/AIOutput/Audits/`
- Architecture notes -> `Assets/AIOutput/Architecture/`
- SDK reviews -> `Assets/AIOutput/SDKReviews/`
- Early-stage knowledge -> `Assets/AIOutput/KnowledgeDrafts/`
- Incident writeups -> `Assets/AIOutput/IncidentReports/`
- Task audit notes -> `AIOutput/Reports/Tasks/`
- Host-level system audits -> `AIOutput/Reports/System/`
- Host-level reusable cross-project review artifacts -> `AIOutput/Reports/ReviewArtifacts/`
- Host-level research watch outputs -> `AIOutput/Reports/Research/`
- Host-level portfolio indexes or registry-derived summaries -> `AIOutput/Registry/`
- Host-level task event store, task snapshot index, task metrics, and lessons learned -> `AIOutput/Registry/`
- Before saving any generated output, redact literal secret values. Do not export API keys, tokens, client tokens, passwords, private keys, certificates, signing material, or credential-bearing URLs into any artifact destination.
- If sensitive config evidence is needed in the artifact, keep only the field name, file path, and presence status, with the value replaced by `[REDACTED]`.

## Boundary
- Use project `Assets/AIOutput/` when the output belongs to one project's runtime truth or delivery history.
- Use repo-level `AIOutput/` when the output is about the protocol system, portfolio state, cross-project operations, or cross-project task-history analytics.
- Keep the append-only task event store at repo level even when one project owns the implementation, because the registry is a portfolio and delivery-memory surface.
- Keep task audit notes at repo level as part of the same portfolio task-history surface. They summarize task outcomes and follow-up validation; they are not project-local `Assets/AIOutput/` delivery-history artifacts.

# Skill: Sensitive Data Handling

## Purpose
Define the baseline confidentiality posture for all XUUnity work that touches project files, configs, generated reports, or reusable knowledge outputs.

## Rules
- Treat project intellectual property, internal architecture details, proprietary tuning, and confidential roadmap context as sensitive by default unless the user clearly marks them safe for broader reuse.
- Treat secrets as non-exportable. This includes API keys, auth tokens, client tokens, access tokens, private keys, passwords, certificates, signing material, service-account credentials, and credential-bearing URLs.
- You may read sensitive local files when necessary for implementation or review, but prefer structure-over-values analysis in responses and artifacts.
- Never print literal secret values in chat responses, review reports, knowledge drafts, project memory, or shared prompts.
- When sensitive evidence matters, reference only the file path, the field name, and the fact that a value is present. Use `[REDACTED]` or a short masked form instead of the full value.
- Do not copy project-specific confidential details into reusable shared or upstream knowledge. Only promote public-safe abstractions.
- Public-safe does not require vague wording. Concrete references to public engine, platform, language, or library APIs are allowed when they improve the quality of the reusable rule and do not expose confidential project context.
- If a report template or utility would normally quote a config snippet, redact sensitive fields before saving the artifact.
- If the user requests literal disclosure of a secret value, warn that it is sensitive and default to a redacted answer unless they clearly require local-only inspection.

## Review Focus
- accidental credential disclosure
- raw config dumps in AI outputs
- project-specific confidential details promoted as shared knowledge
- artifacts that preserve more sensitive detail than the task requires

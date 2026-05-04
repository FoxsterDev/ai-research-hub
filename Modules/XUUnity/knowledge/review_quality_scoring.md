# XUUnity Knowledge: Review Quality Scoring

## Purpose

Provide one shared, product-owner-readable scoring model for `xuunity` review protocols.

This scoring model is for:

- full reviews
- feature reviews
- SDK reviews
- native reviews
- architecture reviews
- release-readiness reviews
- delivery-risk reviews
- git change reviews
- test-quality reviews

The score is not a replacement for findings.
Findings remain primary.
The score is a synthesis layer that helps communicate how far the reviewed target is from top-tier industry quality.

## Output Contract

Any `xuunity` review that reaches a concrete verdict should also produce:

- `Overall score`
- `Distance from top tier`
- `Scope note`
- `Scoring confidence`
- `Dimension breakdown`
- short plain-language explanation for non-technical stakeholders

When a review is saved as an artifact, include the score in the artifact.

Use `utilities/review_scoring_output_template.md` as the default output shape unless a narrower review protocol needs a more specialized table.

## Scope Rule

Always state what the score applies to.

Examples:

- whole current service
- current feature surface
- current SDK wrapper
- reviewed git change if landed
- reviewed test surface

Do not imply that a narrow review score represents the whole project unless the review actually covered the whole project.

## Top-Tier Baseline

Use `90` as the practical top-tier target.

Interpretation:

- `90-100`
  - top-tier
  - highly trusted
  - low operational drama
- `80-89`
  - strong production quality
  - normal debt but no major trust gap
- `70-79`
  - workable
  - meaningful weaknesses exist
- `60-69`
  - risky
  - needs focused hardening
- `<60`
  - materially below top-tier
  - likely to create recurring incidents, release friction, or operational pain

Distance from top tier:

- `max(0, 90 - overall_score)`

## Default Dimension Model

Base score: `100`

Default dimensions:

- `20` Correctness and data integrity
- `15` Architecture and ownership clarity
- `15` Safety, resilience, and runtime stability
- `15` Security, privacy, and abuse resistance
- `15` Validation and release confidence
- `10` Observability and operability
- `10` Maintainability and change safety

### Dimension Guidance

#### Correctness and data integrity
Ask:

- does it do the right thing
- can it mix state between users, sessions, requests, or systems
- can it corrupt rewards, saves, identity, config, or lifecycle state

Lower this score when:

- deterministic bugs exist
- state ownership is ambiguous
- money, reward, identity, persistence, or progression correctness is weak

#### Architecture and ownership clarity
Ask:

- are boundaries understandable
- is there one clear owner for critical decisions
- are lifecycle, callback, and async responsibilities explicit

Lower this score when:

- ownership is split or hidden
- first-match or ad hoc routing replaces explicit rules
- boundaries drift across layers

#### Safety, resilience, and runtime stability
Ask:

- can the target crash, deadlock, ANR, leak, wedge, or degrade badly under stress
- does it handle retries, duplicates, lifecycle transitions, and failure modes safely

Lower this score when:

- crash or ANR risk exists
- retry, teardown, backgrounding, reload, or native callback behavior is fragile
- failure recovery is weak or silent

#### Security, privacy, and abuse resistance
Ask:

- are trust boundaries clear
- can untrusted input steer privileged behavior
- are secrets or sensitive values exposed too easily

Lower this score when:

- client-supplied identity is over-trusted
- privacy-sensitive data leaks into logs
- abuse or spoofing paths are plausible

#### Validation and release confidence
Ask:

- do tests or validation steps prove the risky behavior
- could a regression realistically ship without being caught

Lower this score when:

- critical paths have weak or missing tests
- validation is fake-heavy or narrow
- release confidence depends on hope rather than evidence

#### Observability and operability
Ask:

- would production issues be visible and diagnosable
- are impossible states detected or silently tolerated

Lower this score when:

- logs are misleading
- ambiguous states are accepted without alarms
- root-cause analysis would be slow or guessy

#### Maintainability and change safety
Ask:

- can engineers change this without causing accidental regressions
- is the code shape teaching correct behavior or hiding danger

Lower this score when:

- the design is brittle
- duplication or indirection hides real ownership
- future fixes are likely to be hazardous

## Narrow-Scope Reweighting Rule

Not every review touches every dimension equally.

If a dimension is clearly out of scope:

1. mark it `out_of_scope`
2. redistribute its weight proportionally across the in-scope dimensions
3. say that you reweighted the model

Examples:

- a narrow test-quality review may reduce `Security` weight if no trust boundary is involved
- a native plugin review may keep all dimensions in scope
- a small git change review may reweight toward correctness, safety, and validation

Do not quietly ignore dimensions without saying so.

## Review-Type Guidance

### Current-state service or subsystem review
Use the default weights unless there is a strong reason not to.

### Feature or flow review
Usually keep:

- correctness
- architecture
- safety
- validation
- maintainability

Reweight only if security or observability are genuinely not material.

### SDK or native integration review
Keep all dimensions in scope by default.
These reviews often need the full model because lifecycle, privacy, startup, failure handling, and validation all matter.

### Git change review
Score the reviewed change surface if landed, not the entire codebase.
State this explicitly.

### Test-quality review
The doctrine score remains primary.
Also report:

- `Distance from top tier`
- plain-language meaning of the suite score

If the review also surfaces major runtime confidence gaps, connect them back to the shared model in prose even if the detailed dimension table stays test-specific.

## Severity Caps

Use these caps to keep the score honest.

### Critical unresolved issue
Usually cap overall score at `49` or below.

Examples:

- release-blocking crash path
- major security/privacy break
- broad reward, payment, save, or identity corruption

### High unresolved issue on a trust-critical path
Usually cap overall score at `69` or below.

Trust-critical paths include:

- auth
- identity
- payments
- IAP
- rewards
- progression
- save/load
- startup
- consent/privacy
- release-blocking SDK flows

### Multiple High issues or systemic ambiguity
Usually cap overall score at `59` or below.

### Weak validation on high-risk behavior
Usually cap `Validation and release confidence` at `59` or below.

### Misleading observability
Usually cap `Observability and operability` at `59` or below.

## Scoring Confidence

Every score must state confidence:

- `High`
  - broad code evidence and meaningful validation or strong runtime proof exist
- `Medium`
  - code evidence is solid but runtime validation is partial
- `Low`
  - the score is mostly static-analysis-based, or the review surface is incomplete

Confidence rules:

- if meaningful build or runtime validation was not possible, do not use `High`
- if diff scope or target scope may be incomplete, do not use `High`
- if the review depends heavily on inference across missing systems, use `Low`

## Plain-Language Explanation Rule

After the numeric score, explain it for non-technical readers in direct language.

Good examples:

- `The service is functional, but not trusted enough for a top-tier identity system.`
- `The feature logic works, but release confidence is weak because critical paths are under-tested.`
- `The integration is fast-moving and usable, but too brittle to be called top-tier.`

Avoid vague phrases like:

- `some issues exist`
- `could be improved`
- `looks okay overall`

## Default Report Shape

Use this shape unless a narrower review protocol defines a more specific table:

### Quality Score
- Overall score: `X / 100`
- Distance from top tier: `Y`
- Scope note:
- Scoring confidence:

### Dimension Breakdown
- `Dimension | Weight | Score | Why`

### Product Interpretation
- one short paragraph for non-technical stakeholders

If needed, copy the canonical snippet from:

- `utilities/review_scoring_output_template.md`

## Final Rule

Do not reverse-engineer the findings from a target score.
Score after the review, not before it.

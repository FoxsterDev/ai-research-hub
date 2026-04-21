# Skill: Reward Grant Idempotency

## Derived From
- reviewed reward-flow runtime safety extraction cases
- reviewed duplicate-callback validation cases

## Use For
- rewarded-ad flow refactors
- prize claim or grant-path cleanup
- duplicate callback or resume-sensitive reward handling

## Rules
- Reward granting must be idempotent; duplicate callbacks, resume re-entry, or delayed completion must not produce duplicate grants.
- Separate reward eligibility, reward delivery, and UI acknowledgement so refactors do not collapse them into one fragile callback path.
- Keep the grant decision keyed to explicit grant state or claim identity, not to transient popup state or a single callback occurrence.
- Validate resume, duplicate callback delivery, interruption, and delayed completion behavior before deleting the old reward path.
- When the refactor changes reward orchestration, keep the user-visible pending state and the authoritative grant state distinct.

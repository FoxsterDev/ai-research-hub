# Skill: Mobile Critical Flows

## Use For
- startup
- ads
- IAP
- save/load
- rewards
- resume and interruption

## Rules
- Identify critical user flows before implementation or review.
- Keep critical flows simple, observable, and failure-tolerant.
- Add safe fallback behavior for late callbacks, missing data, and interrupted sessions.
- Treat a fallback as safe only if it preserves the semantic class of the contract.
  - if the fallback changes identity, auth, payment, entitlement, or another backend-facing contract class, treat it as an explicit degraded mode or contract break, not as an ordinary fallback
- Validate on both iOS and Android where OS behavior differs.

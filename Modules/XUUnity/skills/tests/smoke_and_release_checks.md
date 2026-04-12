# Skill: Smoke And Release Checks

## Use For
- pre-release validation
- crash-prone and monetization-prone flows

## Rules
- Smoke-check startup, scene entry, save/load, ads, IAP, rewards, and resume on real devices.
- Include low-memory, interruption, and network-degraded scenarios where they matter.
- Treat zero-crash and zero-ANR validation as release criteria, not optional QA depth.
- Prefer a short reliable checklist over a large untrusted checklist.

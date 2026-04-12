# Skill: SDK Wrapper Design

## Use For
- third-party SDK wrapper APIs
- consent, analytics, attribution, ads, push, and monetization wrappers
- black-box SDK integration boundaries

## Rules
- Treat third-party SDKs as zero-trust boundaries.
- Do not leak third-party data structures into core application logic.
- Map SDK models to internal safe structs or DTOs immediately at the wrapper boundary.
- Keep public wrapper interfaces stateless where possible.
- If an async SDK call returns meaningful metadata, return it as a result struct instead of exposing mutable state flags.
- Contain malformed data, nulls, parsing failures, and vendor exceptions inside the wrapper layer.
- Keep SDK-specific assumptions and vendor quirks out of core gameplay, UI, and business logic.

## Review Focus
- third-party type leakage
- stateless wrapper contract quality
- malformed-data containment
- boundary clarity

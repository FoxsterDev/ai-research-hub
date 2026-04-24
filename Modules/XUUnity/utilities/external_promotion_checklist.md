# XUUnity Utility: External Promotion Checklist

## Goal
Decide whether knowledge should remain project-local, become monorepo-internal shared knowledge, enter the public `AIRoot` core, or be promoted further into an optional external reusable repo such as `external_repo_test_1`.

## Use For
- generic skills discovered in project work
- reusable review heuristics
- reusable product protocol improvements
- generic Unity mobile best practices that are no longer project-bound

Use this checklist after internal routing already determined that the knowledge is not project-local only.

## Layer Decision Order
Evaluate promotion in this order:
1. should stay `project-local only`
2. can be `internal shared only`
3. can enter public core `AIRoot/Modules/XUUnity/`
4. can also be promoted into an optional external repo

Public core and external promotion are not the same decision:
- some knowledge is public-safe enough for `AIRoot/Modules/XUUnity/` but not mature enough for a broader external repo
- some knowledge may stay `internal shared only` even if it is reused across many monorepo projects

## Public Core Checks
Approve entry into `AIRoot/Modules/XUUnity/` only if the knowledge is:
- reusable outside the current monorepo
- public-safe
- not tied to one company's internal process only
- not tied to one private shared runtime structure
- not dependent on private vendor configuration
- stable enough to survive reuse without heavy rewriting

When narrowing for public core:
- keep concrete public API details when they materially improve the rule
- examples such as Unity engine APIs, Android bridge exception types, or platform-owned wrapper surfaces are acceptable if they are public, reusable, and non-confidential
- remove project-private class names, repo-local paths, proprietary architecture, rollout notes, and business-specific conventions

## Keep Internal Shared If
- the knowledge is reused across many monorepo projects but still depends on host-local workflows
- it reflects internal release, telemetry, compliance, or review conventions
- it depends on private shared runtime structure or internal product patterns
- it is useful across the portfolio but should not be part of the public `AIRoot` core

## Promotion Checks
Approve promotion only if the knowledge is:
- reusable across multiple projects
- public-safe
- not tied to one company's internal process only
- not tied to one project's architecture or memory
- not dependent on private vendor configuration
- specific enough to be useful
- generic enough to avoid project leakage
- stable enough to survive reuse without heavy rewriting

Do not mistake specificity for leakage:
- reject private or confidential specifics
- keep public technical specifics when removing them would make the rule materially weaker or more ambiguous

## Reject Promotion If
- the knowledge depends on project memory to make sense
- the rule only exists because of one project's legacy structure
- it reveals private rollout, monetization, or internal business logic
- it contains internal incident context that should stay private
- it is still experimental and not validated enough

## Recommended Outcomes
- `promote to public core only`
- `promote to external only`
- `promote to both public core and external`
- `keep internal shared only`
- `keep project-local only`
- `reject`

## Output
- promotion decision
- whether the knowledge qualifies for public core
- why it is or is not reusable
- public-safety assessment
- internal-only reasons, if any
- required cleanup before promotion
- recommended target path in the optional external repo

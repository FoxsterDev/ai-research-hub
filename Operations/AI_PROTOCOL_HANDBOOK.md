# AI Protocol Handbook

## Purpose
This handbook is the main navigation guide for the AI protocol system.
Use it to understand:
- what each protocol is for
- which tasks are a good fit
- which commands to use
- what the system can solve well today
- where you still need extra context, code verification, or human judgment

## Start Here
- Use `xuunity` for most Unity engineering, review, product-facing implementation questions, and protocol-system work.
- Host repos may attach additional private protocols outside `AIRoot`, but they are not part of this public handbook.

## Supported Host Topologies

### Core-only setup
Use this for a single-project repo or any host that does not need a shared internal layer across multiple projects.

Load shape:
- repo router
- `AIRoot/Modules/XUUnity/`
- project router
- project memory

Rule:
- do not create `AIModules/XUUnityInternal/` just because `xuunity` exists

### Core plus internal overlay
Use this for monorepos or multi-project hosts that need reusable internal shared knowledge across projects.

Load shape:
- repo router
- `AIRoot/Modules/XUUnity/`
- `AIModules/XUUnityInternal/` when present
- project router
- project memory

Rule:
- `AIModules/XUUnityInternal/` is an optional host overlay, not a mandatory part of `xuunity`

## Protocol Map

### `xuunity`
Best for:
- bug fixing
- refactoring
- feature development
- code review
- SDK integration and SDK review
- native plugin work and review
- runtime safety
- performance, startup, ANR, microfreeze, thermal, battery
- product-facing implementation explanations
- AI knowledge extraction, merge, and system maintenance

## Fast Command Lookup

### Daily Engineering
- `xuunity fix this bug`
- `xuunity refactor this code`
- `xuunity review this component`
- `xuunity review the git change`
- `xuunity git change review`
- `xuunity feature request this flow`
- `xuunity feature design this flow`
- `xuunity feature screen this flow`
- `xuunity feature popup this flow`
- `xuunity feature presenter this flow`
- `xuunity feature plan this flow`
- `xuunity feature validation this flow`
- `xuunity feature risk review this flow`
- `xuunity feature implement this flow`
- `xuunity sdk review this integration`
- `xuunity sdk breakage review this integration`
- `xuunity native review this iOS bridge`

### Product Queries
- `xuunity product explain this feature`
- `xuunity product brief this system`
- `xuunity product impact this flow change`
- `xuunity product rollout this feature`
- `xuunity product deps this popup`
- `xuunity product bug this issue`
- `xuunity product health this project`
- `xuunity project memory freshness this project`

### Knowledge And System Work
- `xuunity extract knowledge`
- `xuunity extract this source`
- `xuunity extract implementation pattern`
- `xuunity extract presenter pattern`
- `xuunity system extract knowledge`
- `xuunity system extract implementation pattern`
- `xuunity apply approved extraction`
- `xuunity system apply approved extraction`
- `xuunity intake this knowledge`
- `xuunity integrate approved knowledge`
- `xuunity system extract skill candidates`
- `xuunity system extract review artifact from this chat`
- `xuunity system merge review artifacts`
- `xuunity system integrate review artifacts`
- `xuunity system merge these new UniTask rules into skills`
- `xuunity system intake review this knowledge`
- `xuunity system progress review`
- `xuunity system registry refresh`
- `xuunity system project registry audit`
- `xuunity system evaluation cadence`
- `xuunity system next milestone`
- `xuunity system research watch`
- `xuunity system health review`
- `xuunity system cleanup`
- `xuunity system cleanup projects`
- `xuunity system cleanup reports`
- `xuunity system cleanup all`
- `xuunity system cleanup apply`
- `xuunity system apply cleanup`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system evaluate the xuunity protocol structure`

## Role Shortcuts
Use these when you want a specific angle instead of default routing.

- `xuunity po ...` -> product owner
- `xuunity sud ...` -> senior unity developer
- `xuunity arch ...` -> architect
- `xuunity td ...` -> technical developer
- `xuunity ta ...` -> technical artist
- `xuunity ui ...` -> ui integrator
- `xuunity qa ...` -> qa manual
- `xuunity qa auto ...` -> qa automation
- `xuunity researcher ...` -> researcher
- `xuunity tm ...` -> troubleshooter master

Examples:
- `xuunity td fix this frame spike`
- `xuunity tm find the root cause of this legacy bug`
- `xuunity po evaluate this feature`

## What The System Solves Well

### High confidence
- Unity implementation and refactor work with clear local code context
- review of risky SDK and native integrations
- performance and stability guidance for mobile-critical flows
- extracting reusable engineering knowledge from real implementation work
- product-facing explanations when source code is available for verification
- consolidating engineering reasoning into reusable review artifacts

### Good, but context-sensitive
- architecture proposals across messy legacy code
- release-readiness evaluation
- migration planning between SDK versions
- turning informal chats into durable shared skills
- using prior reports and project memory as working context
- periodic roadmap progress assessment
- external research watch if strong sources are used and findings are filtered through current system needs
- project health and memory freshness assessments when code and project memory are both available

### Needs careful verification
- answers based mostly on old project memory
- product questions when source code is not available
- build-system and manifest conclusions without checking merged artifacts
- vendor-specific SDK recommendations that depend on changing external releases

## What The System Does Not Do Reliably By Itself
- verify current third-party release status from the internet without fresh external evidence
- guarantee current behavior if only stale docs are loaded
- replace device testing for ANR, ad-flow, rendering, or lifecycle regressions
- replace human approval for knowledge integration into shared prompts
- decide project-specific rollout risk without enough project context

## Best Practices
- Start from the project root or monorepo root, not from nested code folders.
- Let shorthand commands stay short. Do not manually enumerate the whole prompt stack unless needed.
- Choose repo topology first: `core-only` for single-project hosts, `core + internal overlay` for true multi-project hosts.
- For gameplay projects, keep `Assets/AIOutput/ProjectMemory/` as the default context layer.
- Treat `Assets/AIOutput/` as historical artifact storage, not default working memory.
- Load historical artifacts only when investigating behavior drift, reconstructing legacy intent, or researching old bugs.
- For product questions, prefer queries that point to a concrete feature, flow, or file area.
- For knowledge work, use `intake review` before integration.
- For long technical chats, first create a review artifact, then decide whether any of it should become shared knowledge.
- For risky SDK updates, verify dependency track, native versions, and merged build outputs.
- For mobile stability questions, verify with code and build artifacts before trusting old memory.
- Treat `AIRoot` as intentionally routerless. Do not create `AIRoot/Agents.md` or `AIRoot/Assets/AIOutput/ProjectMemory/` to emulate a project-local runtime layer.
- Treat `AIModules/XUUnityInternal/` as optional. Use it only when there is real host-level reusable internal knowledge across projects.

## Effective Workflows

### Bug Fix
1. `xuunity fix this bug`
2. Let the system load role, skills, project memory, and prior reports.
3. If the bug is deep or legacy-heavy, switch to `xuunity tm ...`

### Presenter-Based Feature Work
1. `xuunity feature screen ...` for long-lived presenter-driven screens, pages, tabs, or lobby sections
2. `xuunity feature popup ...` for modal, popup, or one-shot flow presenters
3. `xuunity feature presenter ...` if you want presenter-based routing but want the system to infer the lifetime shape
4. If the task is only shaping implementation before coding, use `xuunity feature design ...` or `xuunity feature plan ...`

### SDK Upgrade Or Review
1. `xuunity sdk review this integration`
2. If breakage risk is high, use `xuunity sdk breakage review this integration`
3. If rollout risk matters, follow with `xuunity product rollout this feature`

Expected review output:
- findings
- feature and core-flow risk assessment
- QA manual validation recommendations
- candidate test cases when useful
- release recommendation or residual risk

Canonical generic review template:
- `AIRoot/Templates/XUUNITY_REVIEW_REPORT_TEMPLATE.md`

### Git Change Review
1. `xuunity review the git change`
2. review the branch diff against `develop` by default
3. if local uncommitted changes exist, assess them as additional delta unless the user asked for committed changes only
4. save a short review report under `<Project>/Assets/AIOutput/CodeReviews/` with a timestamped collision-safe filename like `YYYY-MM-DD_HH-MM-SS_git_change_review_<branch_slug>_vs_<base_slug>.md`
5. include feature/core-flow risk scoring, QA manual validation recommendations, and candidate test cases when the code evidence is sufficient
6. inspect the scorecard and release recommendation
7. fix blocking issues before moving toward production

Canonical template:
- `AIRoot/Templates/XUUNITY_GIT_CHANGE_REVIEW_TEMPLATE.md`

Expected saved review contents:
- findings
- scorecard
- feature and core-flow risk assessment
- QA manual validation recommendations
- candidate test cases when useful
- release recommendation

Use `100` breakage probability only for deterministic bugs that can be explained from the current code or diff.

### New Knowledge
1. `xuunity extract knowledge`
2. review the triage package across review artifacts, skills, and shared knowledge
3. approve only the destinations you want
4. `xuunity apply approved extraction`

When the source is primarily code and the goal is to learn a repeated implementation style from multiple concrete examples, prefer:
1. `xuunity extract implementation pattern`
2. review the extracted invariants, variations, and non-promoted quirks
3. approve only the destination layer you want
4. `xuunity apply approved extraction`

For extraction-quality regression work, use:
- `AIRoot/Operations/XUUNITY_KNOWLEDGE_EXTRACTION_EVALUATION.md`
- `AIRoot/Operations/XUUNITY_KNOWLEDGE_EXTRACTION_GOLDEN_CASES.yaml`
- `AIRoot/Operations/XUUNITY_EXTRACTION_AUTHORITATIVE_APPROVAL_CHECKLIST.md`

`xuunity system health review` should also check whether the extraction workflow has current regression evidence.
If extraction routing changed but the golden pack was not rerun, treat that as a system-health gap rather than a silent assumption.
Use `AIOutput/Reports/System/knowledge_extraction_eval_latest_summary.json` as the preferred extraction-health evidence only when it is a real evaluation output, not a scaffold slot or placeholder.

### System Progress
1. `xuunity system progress review`
2. review the maturity snapshot
3. take the recommended next milestone
4. if project inventory or project metadata changed, update `AIOutput/Registry/project_registry.yaml` in the same maintenance pass

### System Output Cleanup
1. `xuunity system cleanup`, `xuunity system cleanup reports`, or `xuunity system cleanup all`
2. review the filled cleanup scorecards and the `keep`, `archive`, `delete_candidate`, and `manual_review` buckets
3. `xuunity system cleanup apply` only after explicit approval
4. archive meaningful old reports first
5. delete only junk, exact duplicates, or orphan artifacts after explicit approval

### Project Registry Refresh
1. `xuunity system registry refresh`
2. review changed versus unchanged entries
3. if ambiguities remain, keep the registry conservative and flag them for human review

### Project Registry Audit
1. `xuunity system project registry audit`
2. review current, stale, missing, and ambiguous entries
3. run `xuunity system registry refresh` only if the required updates are low-risk and evidence-backed

### Internet Research Watch
1. `xuunity system research watch`
2. review what is actually new and useful
3. if strong findings appear, run `xuunity system intake review this knowledge`

### Long Engineering Chat
1. `xuunity system extract review artifact from this chat`
2. If there are multiple artifacts, `xuunity system merge review artifacts`
3. If durable rules emerged, run `xuunity system intake review this knowledge`

### Product Question
1. `xuunity product explain this feature`
2. Check whether the answer is:
   - `verified in source code`
   - `based on project memory`
   - `partially inferred`
3. If verification is weak, ask for a code-backed answer

### Project Health
1. `xuunity product health this project`
2. review blockers, risks, and readiness scores
3. if memory trust is unclear, run `xuunity project memory freshness this project`

## Verification Rules
- Code wins over project memory when they conflict.
- Merged build artifacts matter more than source declarations for manifest and plist checks.
- Review artifacts are reusable context, not automatic source of truth.
- Shared knowledge must be approved before integration.
- Public-safe reusable guidance belongs in `AIRoot/Modules/XUUnity/`.
- Reusable monorepo-internal guidance belongs in `AIModules/XUUnityInternal/` when that overlay exists.
- Project-only durable guidance belongs in project memory or project outputs unless the reusable part is cleanly split out first.
- `AIOutput/Registry/project_registry.yaml` should be refreshed when project routers, project memory presence, or host-defined gameplay-bridge availability change.
- Host-level system and review-artifact outputs belong in `AIOutput/Reports/`, with registry and portfolio state stored under `AIOutput/Registry/`.

## If You Are Unsure Which Command To Use
- Need code changed or reviewed: start with `xuunity`
- Need architecture direction beyond public `xuunity`: use the host repo's private architecture protocol if one exists
- Need host-specific onboarding beyond public `xuunity`: use the host repo's private onboarding protocol if one exists
- Need to process a new piece of knowledge: start with `xuunity extract knowledge`
- Need to extract a repeated development style from code: start with `xuunity extract implementation pattern`
- Need to process a long technical chat: start with `xuunity system extract review artifact from this chat`

## Quick Limits Summary
- Best results happen when the AI can see the code, project memory, and relevant outputs.
- Product answers are only as good as their verification level.
- Upstream or shared knowledge should be integrated intentionally, not copied blindly.
- Device-level runtime risks still require real testing.

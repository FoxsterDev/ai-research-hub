# AI Protocol Handbook

## Purpose
This handbook is the main navigation guide for the AI protocol system.
Use it to understand:
- what each protocol is for
- which tasks are a good fit
- which commands to use
- what the system can solve well today
- where you still need extra context, code verification, or human judgment

## Current Shared Surface

Verified against the live shared `AIRoot/Modules/XUUnity/` surface on `2026-05-13`.

- Task surface includes engineering, review, feature-delivery, architecture-plan, validation-plan, rollout-plan, change-delivery, and incident-response entrypoints.
- Review surface includes code, git-change, SDK, native, release-readiness, delivery-risk, and test-quality review flows.
- Utility surface includes extraction, integration, review-artifact, system-governance, cleanup, and task-registry flows.
- First-class policy packs currently exist for:
  - SDK changes
  - startup changes
  - manifest/native changes
  - monetization changes
  - save/load changes
  - UI-heavy changes

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

## MCP Surfaces

Treat MCP as two different operational surfaces:
- Unity-aware validation and editor evidence
- delivery/reporting integrations such as Slack

Do not collapse them into one generic "MCP setup" concept.

For the public topology view of these surfaces, use:
- `AIRoot/Visuals/AI_PROTOCOL_VISUAL_MAP.md`
- especially sections:
  - `5. MCP Surfaces`
  - `6. Unity MCP Validation Topology`
  - `7. Delivery / Reporting MCP Topology`

### Unity MCP

Use this when the task needs Unity-aware evidence rather than source-only reasoning.

Shared source of truth:
- `AIRoot/Modules/XUUnity/tasks/start_session.md`
- `AIRoot/Modules/XUUnity/knowledge/unity_validation_boundaries.md`
- `AIRoot/Modules/XUUnity/knowledge/validation_lanes.md`

Shared operational package:
- `AIRoot/Operations/XUUnityLightUnityMcp/README.md`

Supporting public docs:
- `AIRoot/Operations/XUUnityLightUnityMcp/BUILD_AUTOMATION.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/AI_INTEGRATION.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`

Working rule:
- if the active host or project exposes a supported Unity MCP path, prefer that path for Unity-aware validation
- do not treat shell compile, generated project builds, or ad hoc shell scripts as equivalent to Unity MCP evidence
- host repos may add narrower local rules or wrappers on top of this public baseline

### Slack MCP

Use this for delivery/reporting only, not as a project source of truth.

Shared public-safe setup:
- `AIRoot/Operations/CodexSlackMcp/README.md`
- `AIRoot/Operations/CodexSlackMcp/init_codex_slack_mcp.sh`
- `AIRoot/Templates/CodexSlackMcp/README.md`

Working rule:
- Slack MCP is a delivery surface
- host repos may pin it to one channel, require explicit approval, or route it through host-local closeout utilities
- do not treat Slack posts as canonical project state

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
- `xuunity review tests`
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
- `xuunity arch plan this subsystem split`
- `xuunity rollout plan this feature`
- `xuunity sdk discover AppsFlyer`
- `xuunity sdk discover AppLovin Pangle`
- `xuunity sdk profile design Mixpanel`
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
- `xuunity system cleanup aggressive`
- `xuunity system cleanup all`
- `xuunity system cleanup all aggressive`
- `xuunity system cleanup apply`
- `xuunity system apply cleanup`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system evaluate the xuunity protocol structure`
- `xuunity task registry bootstrap`
- `xuunity start tracking this task`
- `xuunity finish the work`
- `xuunity publish the work`
- `xuunity this works`
- `xuunity this has bugs`
- `xuunity validate task registry`
- `xuunity task metrics`
- `xuunity archive task registry`

Task-registry feature report:
- `AIRoot/Operations/XUUNITY_TASK_REGISTRY_PUBLIC_REPORT.md`

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
- change-delivery and closure orchestration when the repo exposes the task-registry surface
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
- Keep the MCP surface explicit:
  - Unity MCP for validation and editor evidence
  - delivery/reporting MCPs for closeout workflows
- Choose a primary validation lane before claiming runtime proof:
  - `interactive_mcp` for live editor state, console, scene, Game View, play mode, or integrated Unity tooling
  - `batch_compile` for non-interactive compile, define, target, or narrow test evidence when shell automation is allowed
  - `scenario` for ordered runtime steps, waits, screenshots, play mode transitions, or project-defined hooks
- For gameplay projects, keep `Assets/AIOutput/ProjectMemory/` as the default context layer.
- Treat `Assets/AIOutput/` as historical artifact storage, not default working memory.
- Load historical artifacts only when investigating behavior drift, reconstructing legacy intent, or researching old bugs.
- For product questions, prefer queries that point to a concrete feature, flow, or file area.
- For knowledge work, use `intake review` before integration.
- For long technical chats, first create a review artifact, then decide whether any of it should become shared knowledge.
- For risky SDK updates, verify dependency track, native versions, and merged build outputs.
- For risky gameplay, monetization, save/load, or UI-heavy changes, let the matched policy pack narrow the review and validation surface instead of improvising the whole checklist.
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
1. `xuunity sdk discover AppsFlyer` to run the full update-candidate research flow for the active project
2. Use `xuunity sdk discover AppsFlyer for ApperfunHub` when the project must be explicit
3. `xuunity sdk review this integration` after a candidate is selected or implemented
4. If breakage risk is high, use `xuunity sdk breakage review this integration`
5. If rollout risk matters, follow with `xuunity product rollout this feature`

Expected review output:
- findings
- feature and core-flow risk assessment
- QA manual validation recommendations
- candidate test cases when useful
- release recommendation or residual risk

Expected SDK discovery output:
- saved report under the resolved project's SDK review output destination
- exact recommended candidate or explicit `do not update`
- rejected candidates with reasons

### New SDK Research Profile
1. `xuunity sdk profile design Mixpanel` to design a new full vendor profile before enabling one-command discovery
2. Use `xuunity sdk research profile Firebase` or `xuunity system design sdk research profile OneSignal` for the same flow
3. After the profile is integrated, use `xuunity sdk discover <Vendor>` for project-specific candidate research

Expected profile-design output:
- source-of-truth ladder
- exact candidate identity
- wrapper-to-native version mapping
- breaking-change and API migration checkpoint
- hard gates and no-update conditions
- report requirements and command examples
- business, marketing, monetization, compliance, and runtime risk notes
- validation and staged rollout requirements

Canonical generic review template:
- `AIRoot/Templates/XUUNITY_REVIEW_REPORT_TEMPLATE.md`

### Review And Risk Coverage
Use these when the work is review-heavy or release-sensitive:

1. `xuunity review this component` for a source-scope review
2. `xuunity review tests` for test-surface quality and risk
3. `xuunity review the git change` for branch or working-tree delta
4. `xuunity feature risk review ...` for pre-implementation or pre-release risk framing
5. let the matched policy pack narrow the checklist for:
   - SDK changes
   - startup changes
   - manifest/native changes
   - monetization changes
   - save/load changes
   - UI-heavy changes

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

### Validation Lane Selection
1. Prefer `interactive_mcp` when the question is about live Unity editor behavior.
2. Prefer `batch_compile` when the question is compile health or target or define coverage and direct shell automation is permitted.
3. Prefer `scenario` when the answer depends on multiple ordered runtime steps rather than one isolated tool call.
4. If repo or project rules require integrated validation, do not fall back to direct Unity CLI just because the editor binary exists.
5. If no permitted lane can produce representative proof, keep the validation gap explicit.
6. When a host exposes a supported `XUUnityLightUnityMcp` or equivalent Unity MCP package, treat that package as the preferred Unity-aware validation surface.

For the topology view of this lane model, use:
- `AIRoot/Visuals/AI_PROTOCOL_VISUAL_MAP.md` -> `6. Unity MCP Validation Topology`

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

### Task Registry
1. `xuunity task registry bootstrap` when the repo needs the scaffold
2. `xuunity start tracking this task` when lifecycle timing should begin before closure
3. `xuunity finish the work` to record engineering closure
4. `xuunity this works` or `xuunity this has bugs` after human validation
5. `xuunity validate task registry` before publishing metrics or migration results
6. `xuunity task metrics` for outcome-based reporting
7. `xuunity archive task registry` for retention and rollover planning

Reference:
- `AIRoot/Operations/XUUNITY_TASK_REGISTRY_PUBLIC_REPORT.md`

### Change Delivery
1. `xuunity publish local changes ...`, `xuunity publish all changes ...`, or `xuunity split these changes into commits ...`
2. let `tasks/change_delivery.md` choose the narrowest delivery shape
3. if the repo also exposes task-registry flows, pair delivery with `xuunity finish the work`
4. keep validation evidence explicit before closeout rather than folding it into commit-only output

### Delivery Reporting
1. If the host repo exposes a delivery/reporting MCP such as Slack, use the host-local closeout route rather than inventing an ad hoc post format.
2. Keep delivery/reporting MCP output secondary to the actual system of record.
3. Do not claim work is fully closed out when the host-defined delivery step was explicitly requested but could not be completed.

For the topology view of delivery/reporting MCP, use:
- `AIRoot/Visuals/AI_PROTOCOL_VISUAL_MAP.md` -> `7. Delivery / Reporting MCP Topology`

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

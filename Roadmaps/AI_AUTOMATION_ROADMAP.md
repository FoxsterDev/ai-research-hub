# AI Automation Roadmap

## Purpose
This document defines the long-term roadmap for the AI protocol system as it scales from the current monorepo setup to a platform that can support 100 small Unity projects with:
- shared reusable engineering intelligence
- AI-assisted feature delivery
- product-owner self-service for project questions
- minimal routine code review load on tech leads

## Vision
Build an AI-native development operating system for a Unity game portfolio.

End-state:
- every project has a stable AI-readable project memory
- shared reusable engineering knowledge is maintained centrally
- product owners can ask implementation and behavior questions directly
- most feature work follows AI-assisted structured flows
- tech leads review exceptions, risky changes, and architecture decisions instead of routine implementation details

## North Star
For a typical small project in the portfolio:
- product owner can request a feature, impact assessment, or rollout brief directly
- AI can assemble the right engineering context automatically
- AI can propose or implement safe scoped changes
- AI can generate validation and review artifacts
- routine PR review becomes policy-driven and exception-based

## Scaling Assumptions
- portfolio grows to 100 small to medium Unity projects
- projects share a large portion of SDK, mobile runtime, compliance, and delivery patterns
- project-specific differences remain real, but should be isolated in project memory and overrides
- not every project will have a full-time engineer or tech lead

## Operating Model

### Shared Layer
Repo-level reusable knowledge:
- `AIRoot/Modules/XUUnity/`
- optional external repo patterns for future extension, disabled by default
- shared skills
- shared reviews
- shared product protocols
- shared code style

### Project Layer
Per-project truth:
- `Agents.md`
- `Assets/AIOutput/ProjectMemory/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/`
- prior AI outputs and reports

### Human Layer
People focus shifts:
- product owners drive questions, requirements, and approval
- engineers supervise implementation quality and edge cases
- tech leads own architecture, exception handling, and protocol quality

## Strategic Principles
- shared knowledge must be centralized, versioned, and reusable
- project truth must stay local and override shared assumptions
- AI should operate through explicit approval gates for risky or shared changes
- product-facing answers must be code-verified when current behavior matters
- review effort must move from routine inspection to policy enforcement and exception handling
- each new project should become cheaper to onboard than the previous one

## Roadmap

## Phase 1: Strong Foundation
Target:
- make the current monorepo stable, consistent, and reusable

Outcomes:
- standard repo router and project routers
- stable `XUUnity` prompt family
- first complete skill system
- product-facing protocols
- knowledge intake, review, and merge workflows
- optional external extension design available but disabled by default

Success metrics:
- every active project has usable `Agents.md`
- every active project has `ProjectMemory/`
- short commands work consistently
- knowledge integration is approval-based
- shared prompts no longer drift chaotically

## Phase 2: Portfolio Standardization
Target:
- onboard 20 to 30 projects with predictable structure

Required work:
- normalize project AI folder structure across all projects
- define minimum project memory templates
- define project onboarding checklist for new titles
- define project health scoring
- define mandatory reports for gameplay projects

New capabilities:
- automated project bootstrap
- automated project health audit
- mandatory project memory freshness checks
- AI readiness score per project

Success metrics:
- new project onboarding under one day
- at least 80% of projects pass structure validation
- product-facing protocols work across most projects without manual prompt assembly

## Phase 3: AI-Guided Delivery Flows
Target:
- turn feature work into guided AI workflows instead of open-ended prompting

Required work:
- create structured feature-delivery protocols:
  - feature request intake
  - implementation brief
  - dependency analysis
  - design and risk proposal
  - implementation plan
  - validation plan
  - rollout plan
- connect these flows to project memory, skills, and code verification

New capabilities:
- product owner requests feature impact directly
- AI generates scoped implementation brief
- AI proposes safest implementation shape
- AI generates review and test expectations before code changes
- AI produces rollout checklist and risk summary

Success metrics:
- repeated feature categories use standardized AI flows
- lower variance between projects
- fewer ad-hoc code review comments on common mistakes

## Phase 4: Policy-Driven Review
Target:
- reduce routine tech lead review load through policy-based AI review layers

Required work:
- define mandatory review policies by change type:
  - SDK changes
  - manifest changes
  - startup changes
  - monetization changes
  - save/load changes
  - UI-heavy changes
- encode policy packs into `reviews/`, `skills/`, and release gates

New capabilities:
- automatic review stack assembly by risk class
- mandatory breakage review for risky SDK changes
- mandatory critical-flow review for startup, IAP, ads, and save systems
- automatic reviewer artifact generation for risky work

Success metrics:
- tech leads review only high-risk or exception cases
- routine review comments are replaced by policy findings
- reduced regression rate on repeated change categories

## Phase 5: Product Owner Self-Service
Target:
- enable product owners to work directly with project AI safely

Required work:
- expand product protocols
- simplify verification labeling
- create safe non-technical command set
- standardize response formats for product use
- create project-side quickstart docs per role

New capabilities:
- product owner can ask:
  - how something works
  - what will break if changed
  - whether a feature is rollout-ready
  - what dependencies exist
  - what a bug impacts
- AI answers with verification status and next-step clarity

Success metrics:
- product owners can answer most implementation-detail questions without engineer interruption
- fewer low-value sync meetings
- fewer clarification cycles before feature kickoff

## Phase 6: Semi-Autonomous Implementation
Target:
- AI can implement low-risk feature work in a controlled lane

Required work:
- classify changes by autonomy level
- define safe-change categories:
  - isolated UI wiring
  - config updates
  - wrapper improvements
  - repetitive refactors
  - test additions
- define guardrails for auto-generated code
- require artifact and review generation before merge

Autonomy levels:
- L0: answer only
- L1: analyze and propose
- L2: implement with human approval
- L3: implement and validate low-risk scoped changes automatically
- L4: portfolio-wide batch automation for approved patterns

Success metrics:
- meaningful share of low-risk changes completed with minimal manual coding
- stable defect rate
- reduced lead time for repetitive feature work

## Phase 7: Portfolio Orchestration
Target:
- manage 100 projects as a coordinated AI-assisted portfolio, not as 100 isolated folders

Required work:
- project registry and metadata layer
- cross-project health dashboard
- project capability matrix
- knowledge promotion analytics
- shared incident pattern tracking

New capabilities:
- detect which projects are missing critical memory
- detect which projects are affected by the same SDK or policy issue
- promote fixes and skills across the portfolio faster
- prioritize tech lead attention where risk is highest

Success metrics:
- portfolio-wide visibility over AI readiness and technical risk
- one change category can be propagated safely across many projects
- shared knowledge compounds instead of fragmenting

## End-State Architecture

### 1. Shared Knowledge Platform
- `XUUnity` as internal execution layer
- optional external repo patterns for future extension
- shared skills, reviews, utilities, and product protocols

### 2. Project Memory Platform
- project-local truth
- freshness checks against source code
- stable overrides for reusable skills

### 3. Delivery Workflow Platform
- feature intake
- implementation brief
- AI-assisted implementation
- AI-generated review artifact
- AI-generated validation plan
- rollout readiness assessment

### 4. Governance Platform
- review policies
- autonomy levels
- approval gates
- risk classification
- audit trails for AI-generated changes

## What Must Be Automated First
- project structure validation
- project memory template creation
- project memory freshness checks
- change-type classification
- review stack assembly
- review artifact generation
- release-readiness and rollout-readiness checks

## What Must Stay Human-Led Longer
- architecture shifts
- risky monetization changes
- save/load changes
- security and privacy decisions
- new shared skill design
- portfolio-wide migrations
- ambiguous product tradeoffs

## Minimal Review Future
The goal is not zero human review.
The goal is:
- zero wasteful repetitive review
- zero routine clarification meetings
- zero avoidable re-explanation of project behavior

Tech leads should end up reviewing:
- architecture changes
- risky exceptions
- new policy definitions
- low-confidence AI outputs
- cross-project consequences

Everything else should move toward:
- structured AI flow
- policy-based validation
- explicit approval gates

## Required Platform Additions

### Short-Term
- project health audit protocol
- project memory freshness protocol
- feature-delivery protocol family
- review policy packs
- risk classification model

### Mid-Term
- project registry
- capability tags per project
- release gate protocols
- portfolio-wide reporting
- autonomous low-risk change lane

### Long-Term
- centralized dashboard for project AI readiness
- portfolio incident-to-skill promotion pipeline
- cross-project rollout and remediation automation
- org-level metrics on AI-assisted delivery quality

## KPIs
- project onboarding time
- percent of projects with valid project memory
- percent of product questions answered without engineer involvement
- percent of low-risk changes completed through AI-guided flow
- regression rate after AI-assisted changes
- tech lead review hours per project per month
- shared knowledge reuse rate across projects
- time from incident to reusable skill promotion

## Risks
- stale project memory causing confident but wrong answers
- protocol sprawl causing prompt inefficiency
- too much shared knowledge leaking project-specific assumptions
- over-automation before policy packs are mature
- inconsistent project structures breaking scale economics
- product owners using low-verification answers as source of truth

## Risk Controls
- code-verification labels for product protocols
- approval gates for shared knowledge changes
- project memory freshness workflows
- policy-driven review triggers
- autonomy levels by risk class
- explicit exception escalation to tech leads

## Immediate Next Moves
1. Build a project health and project memory freshness protocol.
2. Define a feature-delivery protocol family inside `XUUnity`.
3. Add risk-class routing for review and implementation tasks.
4. Standardize minimum project memory across all active projects.
5. Create a project registry for the portfolio.
6. Define autonomy levels and what categories are allowed at each level.

## Final Position
The winning strategy is not "AI writes more code."

The winning strategy is:
- structured project knowledge
- structured delivery flows
- policy-driven review
- product-owner self-service
- exception-based tech lead oversight

If done well, the portfolio becomes more valuable with each new project because reusable engineering intelligence compounds instead of resetting.

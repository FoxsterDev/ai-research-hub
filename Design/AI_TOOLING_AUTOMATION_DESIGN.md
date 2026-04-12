# AI Tooling Automation Design

Date: 2026-04-02
Status: draft
Scope: external tooling automation for the AI protocol system

## Goal
Design how the AI system should integrate with external operational tools so it can:
- reduce manual portfolio operations work
- improve traceability between AI outputs and execution systems
- support safer delivery workflows
- avoid bypassing current risk controls

This document covers:
- MCP as the integration model
- Jira
- Unity automation
- GitLab and Bitbucket
- recommended rollout order

## Core Recommendation
Treat tooling automation as a controlled operations layer on top of `XUUnity`, not as a replacement for project-local truth or human merge gates.

The correct order is:
1. read-only discovery and audit
2. report generation and traceability
3. low-risk write actions with explicit scope
4. approval-gated delivery actions

Do not start with "AI can create tickets, open PRs, and change project state everywhere".
Start with narrow, auditable workflows that do not increase production risk.

## Why This Layer Matters
The current system is already good at:
- code-aware analysis
- project health review
- product-facing explanation
- report and audit generation
- prompt-system evolution

What it does not yet do well enough:
- connect generated insights to execution systems
- keep portfolio metadata synchronized with work tracking
- turn AI review outputs into operational actions
- standardize tool-assisted flow from analysis to implementation to review

## Design Principles
- tool integration must not bypass project-local truth
- external systems are execution surfaces, not the source of runtime behavior truth
- read-only integrations come first
- write integrations must be narrow, typed, and auditable
- dangerous actions must remain approval-gated
- zero-crash and zero-ANR posture takes precedence over convenience
- AI-generated operational actions should leave durable artifacts

## Integration Model

### Preferred Pattern
Use MCP-style tool connectors as the external integration layer.

Recommended conceptual shape:

```text
User
  -> xuunity / optional host-local protocols
    -> internal routing and project memory
      -> AI output / audit / recommendation
        -> MCP connector layer
          -> Jira
          -> Unity automation
          -> GitLab / Bitbucket
```

### Why MCP Fits
MCP-style integration is a good fit because it:
- keeps tool boundaries explicit
- allows typed capabilities per external system
- supports read-only and write scopes separately
- makes permission boundaries easier to reason about
- avoids embedding tool-specific logic directly into prompt files

## Tooling Surfaces

### 1. Jira
Use Jira as:
- work intake surface
- planning and execution tracker
- issue lifecycle tracker
- AI artifact reference target

Good first use cases:
- read issue details into AI context
- create implementation brief from a Jira ticket
- post AI-generated summary back to Jira
- create linked subtasks from a reviewed delivery package

Do not start with:
- autonomous workflow transitions
- autonomous priority changes
- autonomous scope expansion

Recommended Jira entities to support:
- Epic
- Story / Task
- Bug
- Subtask
- Comments
- Attachments or linked report references

### 2. Unity Automation
Use Unity automation as:
- project verification surface
- build-check surface
- static validation and report-generation surface

Good first use cases:
- batchmode validation runs
- compile check
- editmode/playmode test execution
- asset validation report generation
- build artifact verification report generation

Do not start with:
- autonomous gameplay code edits through editor scripts
- autonomous production setting mutations
- autonomous build-and-publish pipelines without review

Recommended Unity automation capabilities:
- open project in batch mode
- run named validation entry points
- run test suites
- export machine-readable reports
- detect failures and attach logs to AI outputs

### 3. GitLab / Bitbucket
Use VCS platform automation as:
- review and traceability surface
- PR/MR metadata surface
- policy and status surface

Good first use cases:
- read PR/MR details into AI context
- summarize changed files by risk category
- attach AI review artifact links
- open draft PR/MR from an approved change package
- comment review findings in structured form

Do not start with:
- autonomous merge
- autonomous rebase / branch surgery
- autonomous approval of risky code

Recommended GitLab / Bitbucket capabilities:
- read branch and PR/MR metadata
- list changed files
- create draft PR/MR
- post structured comments
- update labels or statuses in a controlled way

## Risk Model

### Safe Classes
- read-only discovery
- metadata synchronization
- report posting
- draft artifact creation
- draft PR/MR creation

### Medium-Risk Classes
- Jira issue creation from approved package
- Jira comment writeback
- GitLab / Bitbucket label changes
- Unity batch verification execution

### High-Risk Classes
- any action that mutates production runtime configuration
- any action that changes approval state
- any action that merges code
- any action that changes release or deployment state

## Control Model

### Rule 1
External tooling automation must consume AI outputs, not replace verification.

### Rule 2
Tooling integration must follow the low-risk autonomy policy.

### Rule 3
Every write action must be attributable to:
- triggering command
- reviewed artifact
- target project
- actor or approval source

### Rule 4
Read-only integrations may be broadly enabled sooner than write integrations.

## Proposed Capability Packs

### Pack A: Portfolio Metadata
Purpose:
- keep portfolio views current

Actions:
- read monorepo structure
- refresh `project_registry.yaml`
- generate portfolio reports

Risk:
- low

### Pack B: Jira Intake And Reporting
Purpose:
- move from AI analysis to trackable work

Actions:
- fetch issue details
- create implementation summary comments
- create linked subtasks from approved plans

Risk:
- low to medium

### Pack C: Unity Verification
Purpose:
- connect AI review to actual project validation

Actions:
- run compile checks
- run validation tools
- run tests
- export logs and reports

Risk:
- medium

### Pack D: PR/MR Assistance
Purpose:
- connect AI review to review surface

Actions:
- read PR/MR metadata
- post structured findings
- open draft PR/MR from approved package

Risk:
- medium

### Pack E: Workflow Orchestration
Purpose:
- chain Jira, Unity, and PR/MR tooling into one execution flow

Actions:
- from approved ticket -> generate package -> run verification -> open draft PR/MR -> attach reports

Risk:
- medium to high

## Recommended Rollout Order

### Phase 1: Read-Only Discovery
Build first:
- Jira read connector
- GitLab / Bitbucket read connector
- Unity batch verification entry point inventory
- registry refresh / audit integration

Definition of done:
- AI can read external issue and review context
- AI can correlate work items with project metadata
- no write permissions are required yet

### Phase 2: Report Writeback
Build next:
- Jira comment posting for approved summaries
- GitLab / Bitbucket comment posting for approved findings
- report link publication from `AIRoot` or `Assets/AIOutput`

Definition of done:
- AI outputs can be surfaced back into execution tools
- comments are structured and attributable
- no approval states are changed automatically

### Phase 3: Verification Automation
Build next:
- Unity compile/test/validation triggers
- machine-readable verification artifacts
- result ingestion back into AI outputs

Definition of done:
- AI recommendations can be paired with real verification results
- validation stays tool-driven, not prompt-pretended

### Phase 4: Draft Workflow Actions
Build next:
- Jira subtask creation from approved delivery package
- draft PR/MR creation in GitLab / Bitbucket
- automatic attachment of audit/report links

Definition of done:
- AI can prepare work items and draft review surfaces
- human still owns final review, approval, and merge

### Phase 5: Controlled Multi-Tool Orchestration
Build last:
- command-driven end-to-end flow for approved safe cases

Example:
- read Jira issue
- generate implementation brief
- run Unity validation
- create draft PR/MR
- attach report links

Definition of done:
- orchestration saves time without skipping control points

## Recommended Initial Commands
These are not active yet. They are draft targets.

### Jira
- `xuunity system jira read this issue`
- `xuunity system jira comment this summary`
- `xuunity system jira create subtasks from this plan`

### Unity
- `xuunity system unity validation run for this project`
- `xuunity system unity compile check for this project`
- `xuunity system unity test run for this project`

### GitLab / Bitbucket
- `xuunity system pr read this merge request`
- `xuunity system pr comment these findings`
- `xuunity system pr open draft from this approved package`

## Data And Artifact Policy
Tooling automation should reference durable artifacts, not raw transient chat state.

Preferred artifact sources:
- `Assets/AIOutput/`
- `Assets/AIOutput/ProjectMemory/`
- `AIOutput/Reports/`
- `AIOutput/Registry/`

The operational flow should be:
- generate durable artifact
- review artifact
- push summary or link into external system

## Security And Safety Boundaries
- no secret handling logic should live in prompt text
- credentials and token scopes must stay outside prompt files
- write permissions should be separated by tool and by action class
- merge, release, and deployment actions must remain explicitly human-gated
- project-destructive operations must remain blocked by default

## Interaction With Low-Risk Autonomy
This tooling layer must inherit the current autonomy policy.

That means:
- tooling can automate documentation, reporting, and bounded workflow preparation sooner
- tooling must not be used to bypass denylisted runtime or release-risk actions

Examples:
- allowed earlier:
  - refresh registry
  - post audit summary
  - open draft PR/MR
- not allowed:
  - merge PR/MR
  - publish release
  - mutate startup/manifests/native config automatically

## Recommended First Deliverables
1. add this design doc
2. define registry audit and refresh commands
3. define Jira read-only design
4. define Unity verification command shape
5. define GitLab / Bitbucket draft PR/MR command shape

## Decision Rule
If a new tooling automation idea does not clearly reduce manual work while preserving review gates, do not automate it yet.

# AI Product-Facing Guide

## Purpose
Use this guide after setup is already done.

It is the canonical public post-setup guide for product-facing teammates such
as:
- product owners
- founders
- QA
- operators
- anyone who needs product answers from the repo without reading code directly

If you still need to choose a client, clone the repo, or decide whether setup
should bootstrap anything, start here first:
- `Setup/AI_EASY_SETUP.md`

## What To Open

Best:
- open the repo root

Good enough:
- open one project root such as `<ProjectName>/`

Do not open:
- `Assets/`
- `Assets/Scripts/`
- a random nested subfolder

## Best Prompt Shape

Use this shape in a fresh chat:

```text
We are working in this Unity repo.
Read the nearest exact `AGENTS.md` first.
Use XUUnity product protocols.
Answer for a product-facing teammate.
Verify current behavior against source code before answering.
If project memory and code disagree, code wins.
Use verification status in the answer.
For startup, SDK, manifest, plist, entitlement, privacy, or compliance-sensitive questions, use code-first verification.
```

Then ask one focused prompt such as:

```text
xuunity product explain this feature
Project: <ProjectName>
Feature: rewarded continue after fail
Goal: explain current user-visible behavior
```

Good rule:
- one project per chat
- one question per prompt
- say what decision you need

## The Main Commands

### Explain current behavior

```text
xuunity product explain this feature
Project: <ProjectName>
Feature: <feature or flow>
Goal: understand current user-visible behavior
```

### Explain ownership

```text
xuunity product brief this system
Project: <ProjectName>
System: <system name>
Goal: understand ownership and responsibility split
```

### Understand change impact

```text
xuunity product impact this flow change
Project: <ProjectName>
Change: <proposed change>
Goal: understand blast radius before approval
```

### Understand dependencies

```text
xuunity product deps this popup
Project: <ProjectName>
Popup/Feature/Flow: <name>
Goal: understand upstream and downstream dependencies
```

### Decide rollout readiness

```text
xuunity product rollout this feature
Project: <ProjectName>
Feature: <feature or change>
Goal: decide whether rollout is safe now
```

### Understand bug impact

```text
xuunity product bug this issue
Project: <ProjectName>
Issue: <bug description>
Goal: decide urgency and business impact
```

### Pressure-test a proposal

```text
xuunity po evaluate this feature
Project: <ProjectName>
Feature: <proposal>
Goal: pressure-test scope and acceptance criteria
```

### Check whether product answers are trustworthy

```text
xuunity product health this project
Project: <ProjectName>
Goal: understand whether AI product answers are reliable enough to use
```

```text
xuunity project memory freshness this project
Project: <ProjectName>
Goal: decide whether memory-first answers are still safe
```

## Infrastructure-Sensitive Rule

For startup-, SDK-, manifest-, plist-, entitlement-, privacy-, or
compliance-sensitive questions:
- treat the answer as code-first
- use project memory for navigation and scoping, not as final proof
- if project memory and code disagree, code wins

## How To Read The Answer

Verification status:
- `verified in source code`
  - highest confidence
- `based on project memory`
  - useful, but may be outdated
- `partially inferred`
  - directional only; ask for a verification pass

Most useful sections:
- `What it does`
- `What can break`
- `Dependencies`
- `Rollout risk`
- `Recommended next step`

## If The Answer Needs Adjustment

If the answer is too technical:

```text
Re-answer for a product-facing teammate.
Keep code details minimal.
Keep product risks, dependencies, and rollout implications.
```

If the answer is not verified enough:

```text
Do a quick source-code verification pass.
If project memory is outdated, say so clearly and answer based on code.
```

## Main Working Rules

- Prefer repo root when possible.
- Keep one project per chat.
- If the answer starts mixing project contexts, restart the chat and restate
  `Project: <ProjectName>`.
- Use `product health` when you are unsure whether the project is structurally
  ready for trustworthy AI product work.
- Use `project memory freshness` when the answer feels stale or memory-first
  trust is questionable.

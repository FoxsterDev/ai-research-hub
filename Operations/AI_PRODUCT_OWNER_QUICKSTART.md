# AI Product Owner Quickstart

## What To Open
Open one of these:
- a local AI app such as Claude desktop or Codex
- VS Code with the repo or project folder open
- terminal or CLI assistant from the repo root or project root

Best:
- open the repo root

Good enough:
- open one project root such as `<ProjectName>/`

Do not open:
- `Assets/`
- `Assets/Scripts/`
- random nested folders

## Infrastructure-Sensitive Project Rule
For projects with startup-, SDK-, manifest-, plist-, entitlement-, or compliance-sensitive infrastructure:
- treat those answers as code-first
- use project memory for navigation and scoping, not as final current-truth proof
- when project memory and code disagree, code wins

## Paste This First
```text
We are working in this Unity repo.
Read Agents.md first.
Use XUUnity product protocols.
Answer for a non-technical product owner.
Verify current behavior against source code before answering.
If project memory and code disagree, code wins.
Use verification status in the answer.
For infrastructure, SDK, startup, manifest, plist, entitlement, or compliance-sensitive questions, use code-first verification.
```

## Main Commands

### Explain a feature
```text
xuunity product explain this feature
Project: <ProjectName>
Feature: rewarded continue after fail
```

### Explain implementation
```text
xuunity product brief this system
Project: <ProjectName>
System: daily reward popup
```

### Understand change impact
```text
xuunity product impact this flow change
Project: <ProjectName>
Change: show interstitial before reward popup
```

### Understand dependencies
```text
xuunity product deps this popup
Project: <ProjectName>
Popup: level fail popup
```

### Check rollout readiness
```text
xuunity product rollout this feature
Project: <ProjectName>
Feature: new offer wall entry point
```

### Understand bug impact
```text
xuunity product bug this issue
Project: <ProjectName>
Issue: rewarded ad sometimes does not grant reward after resume
```

### Get product-owner evaluation
```text
xuunity po evaluate this feature
Project: <ProjectName>
Feature: delayed welcome offer after first session
```

### Check project health
```text
xuunity product health this project
Project: <ProjectName>
```

### Check project memory freshness
```text
xuunity project memory freshness this project
Project: <ProjectName>
```

## How To Read The Answer

### Verification status
- `verified in source code`
  - best answer quality
- `based on project memory`
  - useful, but may be outdated
- `partially inferred`
  - directional only, ask for verification

### Most Important Sections
- `What it does`
- `What can break`
- `What to validate`
- `Rollout risk`
- `Recommended next step`

## If The Answer Is Too Technical
```text
Re-answer for a non-technical product owner.
Keep code details minimal.
Keep product risks, dependencies, and rollout implications.
```

## If The Answer Is Not Verified Enough
```text
Do a quick source-code verification pass.
If project memory is outdated, say so clearly and answer based on code.
```

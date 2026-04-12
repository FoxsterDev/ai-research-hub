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

## Paste This First
```text
We are working in this Unity repo.
Use XUUnity product protocols.
Answer for a non-technical product owner.
Verify current behavior against source code before answering.
If project memory and code disagree, code wins.
Use verification status in the answer.
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

## How To Read The Answer

### Verification status
- `verified in source code`
  - best answer quality
- `based on project memory`
  - useful, but may be outdated
- `partially inferred`
  - directional only, ask for verification

### Most Important Sections
- `What can break`
- `What to validate`

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

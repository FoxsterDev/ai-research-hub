# AI Product Owner Setup Guide

## Purpose
This guide is for non-technical product owners who want fast answers about:
- how a feature works
- how a flow is implemented
- what a change can affect
- what a feature depends on
- whether something is ready for rollout
- what product impact a bug has
- whether the project is structurally ready for reliable AI-assisted product work
- whether project memory is fresh enough to trust for product-facing answers

You do not need to read code directly.

If you want the shortest version first, read:
- `AI_PRODUCT_OWNER_QUICKSTART.md`

## What You Need
One of these:
- a local AI app that can open project folders, such as Claude desktop or Codex
- VS Code with access to the repo, if you prefer working locally
- a terminal or CLI assistant, if someone on the team already set that up for you

## Best Working Mode
Best:
- open the repo root
- let the AI see:
  - `Agents.md`
  - `AIRoot/`
  - `AIModules/` when the host uses local prompt families
  - the target project folder
  - `Assets/AIOutput/ProjectMemory/`

Good enough:
- open only the target Unity project root
- make sure the project contains:
  - `Agents.md`
  - `Agents.repo.md`
  - `AIModules` only if the host uses local prompt families

Topology rule:
- in a single-project repo, `xuunity` usually uses only the public core from `AIRoot/Modules/XUUnity/` plus project memory
- in a monorepo or multi-project host, `xuunity` may also use `AIModules/XUUnityInternal/` as an optional internal shared overlay

Do not start from:
- `Assets/`
- `Assets/Scripts/`
- a random nested subfolder

## Infrastructure-Sensitive Project Rule
For projects with startup-, SDK-, manifest-, plist-, entitlement-, or compliance-sensitive infrastructure:
- product-facing infrastructure answers should default to code-backed verification
- project memory is useful for navigation and scoping, but current behavior claims should start from source code and build artifacts when platform behavior matters
- SDK, startup, manifest, plist, entitlement, and compliance-sensitive claims should not be answered from memory alone

## Choose Your Working Mode

### Option 1: Local AI App
Best if you are not technical and want the simplest workflow with real file access.

Use this when:
- you mainly ask questions
- you want summaries, risks, rollout notes, and dependency explanations
- you want the AI to read the project directly without manual file upload

Examples:
- Claude desktop
- Codex app

### Option 2: VS Code
Best if you are comfortable opening a folder locally but still want a chat-style workflow.

Use this when:
- you can open the repo or project folder on your machine
- you want the AI to read project files directly
- you want a local chat workflow with direct file visibility

### Option 3: Terminal or CLI
Best if someone already configured it for you and you are okay pasting short commands.

Use this when:
- you work with a local project folder
- you want very direct command-style interaction
- you are okay typing short prompts in a terminal

## Before First Use
Tell the AI:

```text
We are using the AI protocol system in this repo.
Read Agents.md first.
Use XUUnity product protocols.
Verify current behavior against source code before answering.
If project memory and code disagree, code wins.
For infrastructure, SDK, startup, manifest, plist, entitlement, or compliance-sensitive questions, use code-first verification.
Mark answers as:
- verified in source code
- based on project memory
- partially inferred
```

If the AI already reads repo instructions automatically, you usually do not need to paste this every time.

## Local AI App Setup

### Simplest version
1. Open your local AI app.
2. Open the repo root or project root in the app, if the app supports folder or workspace access.
3. Start a new chat inside that workspace.
4. Paste this once at the start:

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

5. Then ask one short command such as:

```text
xuunity product explain this feature
Project: <ProjectName>
Feature: rewarded continue after fail
```

### If the app cannot open the whole repo
Open at least one project root and make sure the AI can see:
- `Agents.md`
- `Agents.repo.md`
- `AIModules` only if the host uses local prompt families
- `Assets/AIOutput/ProjectMemory/`

### Best practice in a local AI app
- ask one focused question at a time
- prefer one project per chat
- if the answer says `partially inferred`, ask for a code verification pass
- if the question is about rollout, project readiness, or memory trust, ask directly with the matching product protocol
- if you move to another project, start a new chat

## VS Code Setup

### What to open
Best:
- open the repo root

Good enough:
- open one project root, for example `<ProjectName>/`

Do not open:
- `Assets/`
- a nested scripts folder

### What should be visible
Ask someone to help once if needed, then just keep this simple:
- open the repo or project folder in VS Code
- make sure these files exist in the visible tree:
  - `Agents.md`
  - `AIModules/` when the host uses local prompt families
  - `Assets/AIOutput/ProjectMemory/`

### How to start
1. Open the folder.
2. Open the AI chat panel in VS Code.
3. Paste the same starter prompt:

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

4. Then ask product commands like:

```text
xuunity product impact this flow change
Project: <ProjectName>
Change: show rewarded continue later in the fail flow
```

## Terminal or CLI Setup

You do not need to be technical for this if the CLI is already installed.

### What to do
1. Open Terminal.
2. Go to the repo root or one project root.
3. Start the AI assistant your team uses.
4. Paste the same starter prompt once if needed.
5. Then type short commands exactly like chat prompts.

Example:

```text
xuunity product brief this system
Project: <ProjectName>
System: level fail popup
```

### If you only know one terminal rule
Always start from:
- repo root
or
- project root

Never start from:
- `Assets/`
- `Scripts/`
- a random subfolder

## Product Commands To Know
- `xuunity product explain this feature`
- `xuunity product brief this system`
- `xuunity product impact this flow change`
- `xuunity product deps this popup`
- `xuunity product rollout this feature`
- `xuunity product bug this issue`
- `xuunity product health this project`
- `xuunity project memory freshness this project`
- `xuunity po evaluate this feature`

## Fast Starter Prompt
Use this when starting a fresh session:

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

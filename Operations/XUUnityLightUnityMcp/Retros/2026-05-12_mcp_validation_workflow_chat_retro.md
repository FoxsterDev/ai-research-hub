# MCP Validation Workflow Chat Retro

Date: `2026-05-12`
Status: `public-safe intake review package`
Source prompt: `Retros/CHAT_RETRO_PROMPT.md`

## Executive Summary

The Unity-side validation operations ultimately succeeded. The session failure
was workflow discipline and operator sequencing, not core MCP execution
stability.

The expensive mistake was starting heavier or GUI-oriented validation before a
fast compile gate. The reusable lesson is to make the operator path harder to
misuse: for changed Unity C# scripts, the default closeout should require a
compile gate before EditMode, PlayMode, scenario, or GUI smoke. Batch prepare
blockers should also surface the next exact recovery command.

## Evidence Base

Public-safe evidence categories:

- user correction that compile errors were visible before heavier validation
  was attempted
- user correction that the Unity editor must be closed before closed-project
  batch validation
- batch compile summaries showing compile success after correct lane selection
- batch EditMode summaries showing deterministic test success after compile
  success
- batch prepare summaries showing the same project editor blocked the batch
  lane before Unity validation started
- request journal evidence showing `unity.editor.quit` was accepted while host
  process exit still required verification

Project names, branch names, commit ids, request ids, local `Library` paths,
product test names, and private source paths were intentionally omitted.

## What Worked

- Batch prepare blockers were safe. They prevented competing batch validation
  while the same Unity project editor was open.
- Compact summaries were enough for final evidence after successful operations.
  Raw logs were not needed when structured summaries were available.
- Request journaling made quit request lifecycle observable.
- The batch lane gave fast deterministic proof for script compile and EditMode
  tests.

## What Worked Poorly

- The operator path was too easy to violate. Compile-first guidance existed but
  was not applied early enough.
- GUI or heavier test validation was attempted while compile state was already
  suspect.
- A batch command was invoked without the required project root, producing a
  usage error with no diagnostic value.
- `request-editor-quit` returned bridge-level success, but process exit was not
  immediately true. The operator still needed process-level verification.
- Commit closeout accidentally included unrelated staged work and required
  correction.

## Durable Rules

- For changed Unity C# scripts, run a fast compile gate before EditMode,
  PlayMode, scenario, or GUI smoke unless the task is explicitly investigating a
  compile failure.
- A batch prepare conflict is not a Unity validation failure. It means the batch
  lane did not start and the operator must close the same project editor or use
  the interactive MCP lane.
- `unity.editor.quit` bridge success is not proof that the host process exited.
  Closeout needs process-level verification.
- Compact summaries should be inspected before raw logs when they contain final
  evidence.
- Before commit, compare staged files to the current task file set.

## Public Promotion Recommendations

- Batch conflict output should include a concrete closeout command and require
  verified process exit before rerun.
- Compile-first ordering should be an operator contract for changed scripts,
  not only prose in documentation.
- Short closeout summaries should distinguish quit acknowledgement from process
  exit verification.
- Staged-file hygiene belongs in general change-delivery guidance, not MCP
  runtime logic.

## Integration Verdict

This retro is useful as a public MCP operator workflow refinement. It should not
promote product-specific validation paths, test names, request ids, local log
paths, branch names, or private source details.

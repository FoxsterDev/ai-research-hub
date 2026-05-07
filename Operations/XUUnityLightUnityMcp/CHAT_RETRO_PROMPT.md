# XUUnity Light Unity MCP Chat Retro Prompt

Date: `2026-05-07`
Status: `active public prompt`

## Purpose

Use this prompt when a chat session exposed MCP reliability, lifecycle, transport,
or operator-experience problems and you want a reusable retrospective that turns
the session into concrete public improvements.

This prompt is public-safe and reusable across Unity consumer projects. Keep
project-private paths, package names, and business context out of the prompt
body unless they are required as evidence inputs.

## Use When

- an MCP-backed validation chat produced confusing failures
- the wrapper said a request failed but Unity may have completed it
- refresh, compile, tests, play mode, or scenario runs felt operationally weak
- bridge resets, reconnects, or request churn created false-negative conclusions
- you want to extract productized improvements from one real session

## Inputs To Gather First

At minimum:

1. the relevant chat transcript or session summary
2. wrapper-visible errors and command outputs
3. request-journal evidence
4. bridge-state evidence
5. the current public MCP docs and contract files

Preferred evidence set:

- `Library/XUUnityLightMcp/journal/requests/*.json`
- `Library/XUUnityLightMcp/state/bridge_state.json`
- `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/DESIGN.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/CONTINUATION.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`

## Prompt

```text
Analyze this XUUnity Light Unity MCP chat/session as an operator-facing reliability retrospective.

Goal:
- determine what actually failed
- separate Unity-side execution from wrapper/transport failure
- identify what evidence was sufficient or insufficient
- propose the smallest reusable improvements to the public MCP surface

Required questions:
1. Did the Unity operation actually fail, or did only the wrapper/session fail?
2. Was there enough evidence to prove that distinction?
3. What did the operator need but not have?
4. What recovery step should have been obvious but was not?
5. What should be promoted into the public AIRoot MCP docs, wrapper, smoke contract, or summaries?

Evidence to inspect:
- chat transcript or condensed timeline
- wrapper-visible command failures
- request journal entries by request_id
- bridge_state.json
- current public docs and runner contract

Output format:
1. Executive summary
2. Evidence base
3. Timeline
4. What worked well
5. What worked poorly
6. What was not explicit enough
7. What the operator needed but did not have
8. Scoring
9. Priority improvements
10. Public-promotion recommendations
11. Final verdict

Scoring categories:
- Unity-side execution stability
- Request journaling quality
- Bridge health observability
- Wrapper-to-operator clarity
- Recovery guidance quality
- Transport lifecycle transparency
- End-to-end trustworthiness during churn
- Parallel request handling
- Time-to-diagnosis
- Validation workflow discipline

Promotion rule:
- project-specific evidence stays local
- reusable lifecycle, transport, retry, status-summary, smoke-order, and operator-guidance improvements should be promoted into public AIRoot docs or wrapper surfaces

Do not stop at describing the failure.
End with concrete reusable changes to:
- docs
- wrapper output
- request summary surfaces
- smoke/validation order
- acceptance checks
```

## Expected Outputs

A good run should usually yield some combination of:

- a local audit report
- a short executive summary
- an apply package for concrete fixes
- public promotion candidates for:
  - `README.md`
  - `DESIGN.md`
  - `CONTINUATION.md`
  - `ROADMAP.md`
  - `SMOKE_TESTS.md`
  - wrapper/runtime behavior

## Promotion Targets

When the retrospective finds reusable value, prefer promoting into:

- docs and operator contracts under `AIRoot/Operations/XUUnityLightUnityMcp/`
- wrapper/runtime templates under `AIRoot/Operations/XUUnityLightUnityMcp/templates/`
- project-local audit/output folders only for one-off evidence and historical trace

## Notes

- Treat real request ids and request-journal evidence as the strongest source of truth for lifecycle-reset incidents.
- Prefer improvements that reduce false-negative validation conclusions.
- Prefer compile-first validation ordering before heavier scenario or test work when changed scripts are already in play.

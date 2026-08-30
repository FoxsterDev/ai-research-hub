# Project Agent Router: XUUnityAiCliOrchestrator

## Purpose
This folder contains the public Operations package for routing XUUnity tasks to
external AI CLI providers through official account login or OAuth.

## Project Context
- Project: `XUUnityAiCliOrchestrator`
- Project kind: public AI CLI orchestration operation
- Canonical path: `AIRoot/Operations/XUUnityAiCliOrchestrator/`
- User-local config: `~/.xuunity/ai-cli-orchestrator/config.json`
- Public launcher: `xuunity_ai_cli_orchestrator.sh`
- Public installer: `init_xuunity_ai_cli_orchestrator.sh`

## Routing Rules
- Keep this package provider-neutral. Claude, Gemini, Antigravity, and future
  API providers are adapters, not separate XUUnity protocols.
- Subscription-backed providers must use official login or OAuth flows. Do not
  add API-key fallback for Claude, Gemini, or Antigravity.
- Keep credentials, OAuth state, local account details, and generated run
  reports outside the repo by default.
- Concrete tasks belong in prompt files. The orchestrator owns provider
  selection, auth checks, safety policy, execution, and normalized result
  reporting only.
- For external AI runs, preserve the delegation boundary: the selected worker
  owns the concrete task execution, evidence collection, artifact/log reading,
  first-pass interpretation, and compact worker report. The XUUnity host agent
  owns provider selection, proof gates, safety policy, final relay, and
  follow-up verification when the worker report is invalid, failed, suspicious,
  or user-challenged.
- Keep broad external AI work phased. The public contract is
  `auto_phased` by default, with `single_run` only for small tasks and
  `phase_plan_only` when the host agent wants a plan before execution.
- Shell launchers must stay thin. Put behavior in Python under `templates/`.

## Validation
- Prefer the stdlib test suite:

```sh
python3 -m unittest discover \
  -s Operations/XUUnityAiCliOrchestrator/scripts/testing \
  -p 'test_*.py'
```

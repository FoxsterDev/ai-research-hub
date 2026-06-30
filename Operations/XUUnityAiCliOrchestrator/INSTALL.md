# Install XUUnity AI CLI Orchestrator

Run from the AIRoot repo root:

```sh
bash Operations/XUUnityAiCliOrchestrator/init_xuunity_ai_cli_orchestrator.sh
```

The installer creates:

```text
~/.xuunity/ai-cli-orchestrator/config.json
```

when it does not already exist.

## Provider Login

Use each provider's official CLI or app login flow before running tasks. The
orchestrator is designed to spend subscription quota, not API-key billing.

Claude CLI example:

```sh
claude auth login --claudeai
claude auth status --json
```

Gemini and Antigravity adapters are configurable because their CLI entrypoints
and account-state probes may vary by installation. Configure `authStatusCommand`
for those providers before relying on them. Keep those probes pointed at
official Google login/account flows, not API-key modes.

## Check Setup

```sh
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh doctor
```

## Run A Prompt

```sh
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh run \
  --project-root /absolute/project \
  --prompt-file /absolute/task.md
```

The prompt must opt in with `external_ai: allowed`.

For regular XUUnity-style prompt text, the recommended selector is:

```text
xuunity fix the bug via claude
```

The phrase `via claude` maps to the `claude_cli` provider.

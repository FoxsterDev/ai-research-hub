# Slack work notifications for an unattended Claude Code host

`slack_work_notify.sh` is a Claude Code hook that posts short status lines to the fixed
single-channel Slack setup whenever an agent running on a remote, unattended machine needs a
human or finishes a turn:

| Event | Matcher | Message |
|---|---|---|
| `Notification` | `permission_prompt` | 🔐 needs your permission + the prompt text |
| `Notification` | `agent_needs_input`, `elicitation_*dialog` | ❓ has a question for you |
| `Notification` | `idle_prompt` | ⏳ idle and waiting for you |
| `Notification` | `agent_completed` | 🏁 background agent completed |
| `Stop` | — | ✅ (or ❌ when the text reads like a failure) finished a turn + the last assistant message, paragraphs kept, clipped at 3000 chars |

Every line is prefixed with `host · project · session` so several sessions can share one channel.
The hook always exits 0 and never blocks the agent; a failed post is logged to
`~/.codex/slack-work-notify/notify.log`.

## Install

The poster it calls lives next to it, so install the hook beside the server files:

```bash
mkdir -p ~/.codex-tools/slack-single-channel-mcp/hooks
cp AIRoot/Operations/CodexSlackMcp/hooks/slack_work_notify.sh ~/.codex-tools/slack-single-channel-mcp/hooks/
cp AIRoot/Operations/CodexSlackMcp/post_fixed_channel_message.mjs ~/.codex-tools/slack-single-channel-mcp/
chmod +x ~/.codex-tools/slack-single-channel-mcp/hooks/slack_work_notify.sh
```

Merge `settings.hooks.json` into `~/.claude/settings.json` (user scope, so every project on the
host reports), keeping any existing keys:

```bash
python3 - <<'PY'
import json, pathlib
home = pathlib.Path.home()
settings = home / ".claude/settings.json"
current = json.loads(settings.read_text()) if settings.exists() else {}
add = json.loads(pathlib.Path("AIRoot/Operations/CodexSlackMcp/hooks/settings.hooks.json").read_text())
hooks = current.setdefault("hooks", {})
for event, entries in add["hooks"].items():
    hooks.setdefault(event, [])
    if not any("slack_work_notify" in json.dumps(e) for e in hooks[event]):
        hooks[event].extend(entries)
settings.write_text(json.dumps(current, indent=2) + "\n")
print("hooks:", list(hooks))
PY
```

## Rehearse without posting

```bash
printf '%s' '{"hook_event_name":"Notification","notification_type":"permission_prompt","message":"Claude needs your permission to use Bash","session_id":"abc123def","cwd":"/tmp/demo"}' \
  | SLACK_WORK_NOTIFY_DRY=1 ~/.codex-tools/slack-single-channel-mcp/hooks/slack_work_notify.sh
printf '%s' '{"hook_event_name":"Stop","last_assistant_message":"Build finished, APK uploaded.","session_id":"abc123def","cwd":"/tmp/demo"}' \
  | SLACK_WORK_NOTIFY_DRY=1 ~/.codex-tools/slack-single-channel-mcp/hooks/slack_work_notify.sh
```

## Switch off / tune

- `touch ~/.codex/slack-work-notify.off` silences it without touching settings.
- `SLACK_WORK_NOTIFY_MAX_CHARS` (default 3000) clips the relayed text at a paragraph boundary;
  paragraph breaks are kept so headings and lists stay readable.
- Drop the `Stop` block from settings if only human-needed events should reach the channel.
- A second channel later: point another env file at it and call the hook with
  `SLACK_SINGLE_CHANNEL_ENV_FILE=<file>` in the hook `command` — the poster's wrapper honours it.

Build artifacts (`.apk`, `.aab`, `.ipa`, `.zip`) are on the server's upload whitelist; raise
`SLACK_MAX_UPLOAD_BYTES` in the env file (the default is 8 MiB) so the agent can attach them with
`slack_upload_file` or `post_fixed_channel_message.mjs --upload`.

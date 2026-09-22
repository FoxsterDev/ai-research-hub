#!/usr/bin/env bash
# Claude Code hook: relay work-status events of an unattended agent host to the fixed Slack
# channel — a question or permission prompt waiting for a human, an idle session, a finished
# turn. Wire it in ~/.claude/settings.json (see settings.hooks.json next to this file).
#
# Reads the hook JSON on stdin, posts one short message through post_fixed_channel_message.mjs
# and always exits 0 so it can never block the agent. Kill switch: touch
# ~/.codex/slack-work-notify.off. Rehearsal: SLACK_WORK_NOTIFY_DRY=1 prints instead of posting.
set -uo pipefail

[ -f "$HOME/.codex/slack-work-notify.off" ] && exit 0

HERE="$(cd "$(dirname "$0")" && pwd)"
POSTER="$HERE/../post_fixed_channel_message.mjs"
STATE_DIR="${SLACK_WORK_NOTIFY_STATE:-$HOME/.codex/slack-work-notify}"
LOG="$STATE_DIR/notify.log"
MAX_CHARS="${SLACK_WORK_NOTIFY_MAX_CHARS:-700}"
mkdir -p "$STATE_DIR"

INPUT="$(cat)"
[ -n "$INPUT" ] || exit 0

TEXT="$(SLACK_HOOK_INPUT="$INPUT" python3 - "$MAX_CHARS" <<'PY'
import json, os, socket, sys

limit = int(sys.argv[1])
try:
    data = json.loads(os.environ.get("SLACK_HOOK_INPUT", ""))
except Exception:
    sys.exit(0)
if not isinstance(data, dict):
    sys.exit(0)

event = data.get("hook_event_name") or ""
cwd = data.get("cwd") or os.getcwd()
project = os.path.basename(cwd.rstrip("/")) or cwd
session = (data.get("session_id") or "")[:6]
host = socket.gethostname().split(".")[0]
tag = f"`{host} · {project} · {session}`"

def clip(text):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

if event == "Notification":
    kind = data.get("notification_type") or ""
    message = clip(data.get("message") or data.get("title") or "")
    if kind == "permission_prompt":
        icon, head = "🔐", "needs your permission"
    elif kind in ("agent_needs_input", "elicitation_dialog", "elicitation_url_dialog"):
        icon, head = "❓", "has a question for you"
    elif kind == "idle_prompt":
        icon, head = "⏳", "is idle and waiting for you"
    elif kind == "agent_completed":
        icon, head = "🏁", "background agent completed"
    elif kind.startswith("quota_"):
        icon, head = "⛔", f"quota event: {kind}"
    elif kind in ("auth_success", "elicitation_complete", "elicitation_response"):
        sys.exit(0)
    else:
        icon, head = "ℹ️", kind or "notification"
    print(f"{icon} {tag} {head}" + (f"\n{message}" if message else ""))
elif event == "Stop":
    message = clip(data.get("last_assistant_message") or "")
    if not message:
        sys.exit(0)
    lowered = message.lower()
    icon = "❌" if any(w in lowered for w in ("failed", "error", "cannot", "blocked", "could not")) else "✅"
    print(f"{icon} {tag} finished a turn\n{message}")
elif event == "PermissionRequest":
    tool = data.get("tool_name") or "a tool"
    print(f"🔐 {tag} asks permission to run {tool}")
else:
    sys.exit(0)
PY
)"
[ -n "$TEXT" ] || exit 0

if [ "${SLACK_WORK_NOTIFY_DRY:-0}" = "1" ]; then
  printf '%s\n' "$TEXT"
  exit 0
fi

if command -v timeout >/dev/null 2>&1; then
  timeout 25 node "$POSTER" --text "$TEXT" >>"$LOG" 2>&1 || echo "[$(date +%FT%T)] post failed" >>"$LOG"
else
  node "$POSTER" --text "$TEXT" >>"$LOG" 2>&1 || echo "[$(date +%FT%T)] post failed" >>"$LOG"
fi
exit 0

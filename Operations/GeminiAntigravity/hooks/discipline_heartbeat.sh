#!/bin/sh
# PreInvocation: re-assert the discipline every Nth model call, and remind about
# an open edit batch. Fails open — any error path prints {} and changes nothing.
# cwd is the directory containing hooks.json (the customization root).

STATE="./.state"
LOG="$STATE/hooks.log"
mkdir -p "$STATE" 2>/dev/null

PAYLOAD=$(cat)
if [ -f "./hooks.env" ]; then
  . ./hooks.env
else
  printf '%s WARN hooks.env not found in %s — running on built-in defaults\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PWD" >> "$LOG" 2>/dev/null
fi

EVERY="${HEARTBEAT_EVERY:-4}"

N=$(printf '%s' "$PAYLOAD" | grep -o '"invocationNum":[0-9]*' | head -1 | sed 's/.*://')
[ -z "$N" ] && N=0
printf '%s heartbeat invocationNum=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$N" >> "$LOG" 2>/dev/null

MSG=""
if [ $((N % EVERY)) -eq 0 ]; then
  MSG="DISCIPLINE CHECK. 1) Root cause, not first plausible cause: name the controlling condition you actually traced. 2) Label every claim verified (path+lines, or command output) or assumed; \"not verified\" is a valid answer. 3) A closed checklist item is not evidence. 4) Finish the task or state the exact blocker. 5) Close with Scope / Findings / Risks / Validation, and put the real result of what you ran in Validation."
fi

if [ -f "$STATE/edit_open" ]; then
  EDIT_MSG="${VALIDATION_REMINDER:-An edit batch is open. Close it with a real validation lane and report its actual output before concluding.}"
  if [ -n "$MSG" ]; then MSG="$MSG $EDIT_MSG"; else MSG="$EDIT_MSG"; fi
fi

if [ -z "$MSG" ]; then
  printf '%s' '{}'
  exit 0
fi

# JSON-escape: backslash, double quote, then drop any control characters.
ESC=$(printf '%s' "$MSG" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037')
printf '{"injectSteps":[{"ephemeralMessage":"%s"}]}' "$ESC"

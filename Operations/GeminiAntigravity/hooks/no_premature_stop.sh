#!/bin/sh
# Stop: block termination while background work is still running, while an edit
# batch is open with no validation lane, or when the last answer is missing the
# required output contract. Counter-guarded so it can never loop, and fails open.
# cwd is the directory containing hooks.json.

STATE="./.state"
LOG="$STATE/hooks.log"
mkdir -p "$STATE" 2>/dev/null

PAYLOAD=$(cat)
if [ -f "./hooks.env" ]; then
  . ./hooks.env
else
  HOOKSENV_MISSING=1
fi

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
MAX="${MAX_STOP_CONTINUES:-2}"

# The edit-without-validation check below needs VALIDATION_PATTERNS and silently does
# nothing without it. That is the most valuable guard in the set, so say when it is off
# rather than let a green run imply it ran.
[ -n "${HOOKSENV_MISSING:-}" ] && \
  printf '%s WARN hooks.env not found in %s — running on built-in defaults\n' "$TS" "$PWD" >> "$LOG" 2>/dev/null
[ -n "${VALIDATION_PATTERNS:-}" ] || \
  printf '%s WARN VALIDATION_PATTERNS unset — edit-without-validation check disabled\n' "$TS" >> "$LOG" 2>/dev/null

CONV=$(printf '%s' "$PAYLOAD" | grep -o '"conversationId":"[^"]*"' | head -1 | sed 's/.*:"//;s/"//')
[ -z "$CONV" ] && CONV="unknown"
COUNTER="$STATE/stop_$CONV"
USED=0
[ -f "$COUNTER" ] && USED=$(cat "$COUNTER" 2>/dev/null)
case "$USED" in ''|*[!0-9]*) USED=0 ;; esac

allow() {
  printf '%s stop allow reason=%s conv=%s\n' "$TS" "$1" "$CONV" >> "$LOG" 2>/dev/null
  printf '%s' '{}'
  exit 0
}

continue_loop() {
  if [ "$USED" -ge "$MAX" ]; then
    allow "budget-exhausted-after-$1"
  fi
  echo $((USED + 1)) > "$COUNTER" 2>/dev/null
  printf '%s stop continue reason=%s conv=%s used=%s\n' "$TS" "$1" "$CONV" "$USED" >> "$LOG" 2>/dev/null
  ESC=$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037')
  printf '{"decision":"continue","reason":"%s"}' "$ESC"
  exit 0
}

# 1. Background work still running.
case "$PAYLOAD" in
  *'"fullyIdle":false'*)
    continue_loop "not-idle" "Background work is still running. Wait for it, read its actual output, and only then conclude." ;;
esac

TRANSCRIPT=$(printf '%s' "$PAYLOAD" | grep -o '"transcriptPath":"[^"]*"' | head -1 | sed 's/.*:"//;s/"//')

# 2. An edit happened with no validation lane after it.
#
# This reads the transcript rather than trusting a flag set by PreToolUse: on this
# build PreToolUse is NOT dispatched for file-edit steps (verified — a wildcard
# matcher saw view_file, grep_search, list_dir, run_command, ask_permission and
# list_permissions, but never the CODE_ACTION that actually wrote the file).
# The transcript does record them, so the transcript is the reliable signal.
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  LAST_EDIT=$(grep -n '"type": *"CODE_ACTION"\|"type":"CODE_ACTION"' "$TRANSCRIPT" 2>/dev/null | tail -1 | cut -d: -f1)
  if [ -n "$LAST_EDIT" ] && [ -n "${VALIDATION_PATTERNS:-}" ]; then
    LAST_VAL=$(grep -nE "$VALIDATION_PATTERNS" "$TRANSCRIPT" 2>/dev/null | tail -1 | cut -d: -f1)
    if [ -z "$LAST_VAL" ] || [ "$LAST_VAL" -lt "$LAST_EDIT" ]; then
      continue_loop "edit-unvalidated" "${VALIDATION_REMINDER:-A file was edited and no compile, test, or validation lane has run since. Run it, read the real result, and report it before concluding.}"
    fi
  fi
fi

# 2b. Secondary signal, when PreToolUse did see the edit tool.
if [ -f "$STATE/edit_open" ]; then
  continue_loop "edit-open" "${VALIDATION_REMINDER:-An edit batch is still open: no compile, test, or validation lane has run since the last edit. Run it, read the real result, and report it as verified before concluding.}"
fi

# 3. The final answer is missing the required output contract.
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  LAST=$(grep '"PLANNER_RESPONSE"' "$TRANSCRIPT" 2>/dev/null | tail -1)
  if [ -n "$LAST" ]; then
    if ! printf '%s' "$LAST" | grep -qi 'validation'; then
      continue_loop "no-validation-section" "Your answer has no Validation section. Add Scope / Findings / Risks / Validation, and state in Validation what you actually ran and its real result — or say explicitly that nothing was validated and why."
    fi
  fi
fi

allow "ok"

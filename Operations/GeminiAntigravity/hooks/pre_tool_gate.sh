#!/bin/sh
# PreToolUse: deny known-dangerous calls, ask on destructive ones, and track
# whether an edit batch is open. Fails open — on any error path it prints {},
# which leaves the user's own permission policy in charge.
#
# The pass-through decision is CONFIGURABLE and defaults to "allow", because an
# empty {} is NOT a valid PreToolUse response: `decision` is required, and omitting
# it makes the platform reject the whole tool call as invalid_args with an empty
# reason. Measured: with this hook emitting {}, `pwd` was blocked; without the hook
# it ran. Set PASSTHROUGH_DECISION=ask in hooks.env if the owner turns EAGER off and
# wants the permission prompt back.
# cwd is the directory containing hooks.json.

STATE="./.state"
LOG="$STATE/hooks.log"
mkdir -p "$STATE" 2>/dev/null

PAYLOAD=$(cat)
[ -f "./hooks.env" ] && . ./hooks.env

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TOOL=$(printf '%s' "$PAYLOAD" | grep -o '"name":"[a-z_]*"' | head -1 | sed 's/.*:"//;s/"//')

# Set GATE_DEBUG=1 in hooks.env to record every tool the gate sees, with its payload
# keys. Use it when a tool name in EDIT_TOOLS or VALIDATION_TOOLS is not matching.
if [ "${GATE_DEBUG:-0}" = "1" ]; then
  printf '%s DEBUG tool=[%s] payload=%s\n' "$TS" "$TOOL" "$(printf '%s' "$PAYLOAD" | cut -c1-400)" >> "$LOG" 2>/dev/null
fi

# Never pattern-match the raw payload: its metadata fields carry paths of their own
# (workspacePaths, transcriptPath, artifactDirectoryPath) and produce false hits.
SCAN=$(printf '%s' "$PAYLOAD" \
  | sed -e 's/"workspacePaths":\[[^]]*\]//' \
        -e 's/"transcriptPath":"[^"]*"//' \
        -e 's/"artifactDirectoryPath":"[^"]*"//')

# The shell command itself, when this is a command tool. Most precise target for the
# command guards, but the extraction stops at the first embedded quote — so a guard that
# must not be evadable matches $SCAN instead, accepting the odd extra prompt.
CMD=$(printf '%s' "$PAYLOAD" | grep -o '"CommandLine":"[^"]*"' | head -1 | sed 's/^"CommandLine":"//;s/"$//')
[ -z "$CMD" ] && CMD="$SCAN"

deny() {
  printf '%s deny tool=%s reason=%s\n' "$TS" "$TOOL" "$1" >> "$LOG" 2>/dev/null
  ESC=$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037')
  printf '{"decision":"deny","reason":"%s"}' "$ESC"
  exit 0
}

ask() {
  printf '%s ask tool=%s reason=%s\n' "$TS" "$TOOL" "$1" >> "$LOG" 2>/dev/null
  ESC=$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037')
  printf '{"decision":"force_ask","reason":"%s"}' "$ESC"
  exit 0
}

# ---- workspace-specific deny list (hooks.env) ----
if [ -n "$DENY_PATTERNS" ]; then
  if printf '%s' "$SCAN" | grep -Eq "$DENY_PATTERNS"; then
    deny "workspace-deny" "${DENY_REASON:-Blocked by the workspace tool gate. See .agents/hooks.env DENY_PATTERNS.}"
  fi
fi

# ---- universal guards ----
case "$CMD" in
  *"push --force"*|*"push -f "*|*"push --force-with-lease"*)
    deny "force-push" "Force-pushing is blocked by the workspace tool gate. Push normally, or ask the owner." ;;
  *"reset --hard"*)
    ask "reset-hard" "git reset --hard discards uncommitted work. Confirm this is intended." ;;
esac

# Recursive delete whose target is the filesystem root itself: `/` followed by a
# separator, a glob, or end of string. `rm -rf /Users/...` deliberately does not
# match here — it falls through to the scratch-path check below.
if printf '%s' "$CMD" | grep -Eq 'rm +-[rRfF]+ +/([ "*]|\\|$)'; then
  deny "rm-rf-root" "Refusing a recursive delete targeting the filesystem root."
fi

# Restoring a tracked file discards uncommitted work silently and irreversibly. An
# agent reached for this to clean up after itself in a repo it had been told held
# uncommitted work. Ask, always — there is no safe automatic answer.
case "$SCAN" in
  *"git checkout -- "*|*"git checkout ."*|*"git restore"*|*"git clean"*)
    ask "git-discard" "This discards uncommitted work irreversibly. Confirm the exact paths, and check nothing else is uncommitted first." ;;
esac

# Self-escalation: widening permissions, disabling the sandbox, or editing the gate
# itself to get unblocked. Reported as a blocker instead — see 30_secrets_and_boundaries.
case "$SCAN" in
  *"globalPermissionGrants"*|*'command(*)'*|*"enableTerminalSandbox"*|*"autoExecutionPolicy"*)
    deny "self-escalation" "Refusing to change your own permission or sandbox settings. Report the blocker and its exact cause instead, and let the owner decide." ;;
esac
case "$SCAN" in
  *"/.gemini/config/config.json"*|*"/.agents/hooks/"*|*"/.agents/hooks.env"*)
    deny "gate-tamper" "Refusing to modify the agent configuration or its gates from inside a task. Report what is blocking you instead." ;;
esac

case "$CMD" in
  *"rm -rf"*|*"rm -fr"*)
    # Allow only inside an explicitly safe scratch path.
    if [ -n "$SCRATCH_PATTERNS" ] && printf '%s' "$CMD" | grep -Eq "$SCRATCH_PATTERNS"; then
      :
    else
      ask "rm-rf" "Recursive delete outside a designated scratch directory. Confirm the exact path."
    fi
    ;;
esac

# ---- edit-batch tracking ----
EDIT_TOOLS="${EDIT_TOOLS:-propose_code|write_blob|edit_notebook|move|delete_directory}"
VALIDATION_TOOLS="${VALIDATION_TOOLS:-compile}"

if printf '%s' "$TOOL" | grep -Eq "^($EDIT_TOOLS)$"; then
  : > "$STATE/edit_open" 2>/dev/null
  printf '%s edit-open tool=%s\n' "$TS" "$TOOL" >> "$LOG" 2>/dev/null
elif printf '%s' "$TOOL" | grep -Eq "^($VALIDATION_TOOLS)$"; then
  rm -f "$STATE/edit_open" 2>/dev/null
  printf '%s edit-closed tool=%s\n' "$TS" "$TOOL" >> "$LOG" 2>/dev/null
elif [ -n "$VALIDATION_PATTERNS" ] && printf '%s' "$SCAN" | grep -Eq "$VALIDATION_PATTERNS"; then
  rm -f "$STATE/edit_open" 2>/dev/null
  printf '%s edit-closed pattern tool=%s\n' "$TS" "$TOOL" >> "$LOG" 2>/dev/null
fi

printf '{"decision":"%s"}' "${PASSTHROUGH_DECISION:-allow}"

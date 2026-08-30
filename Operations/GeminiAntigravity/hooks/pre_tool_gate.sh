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

# The customization root is wherever hooks.json lives, which is not necessarily named
# ".agents". Derive it so the tamper guards below protect THIS root rather than a name.
ROOT_NAME=$(basename "$PWD")
[ -n "$ROOT_NAME" ] || ROOT_NAME=".agents"

PAYLOAD=$(cat)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ -f "./hooks.env" ]; then
  . ./hooks.env
else
  # Silent absence is the dangerous case: every pattern falls back to a built-in default
  # and the workspace's own rules simply do not apply, with nothing reporting it.
  printf '%s WARN hooks.env not found in %s — running on built-in defaults\n' "$TS" "$PWD" >> "$LOG" 2>/dev/null
fi
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

# Shell forms that write. Used by the two guards below so that reading a sensitive file is
# permitted and only mutation is denied. Matched against $SCAN, not $CMD: CMD extraction
# stops at the first embedded quote, so `python3 -c "... open(cfg,'w') ..."` would hide its
# write from a CMD-only match. These two guards must not be evadable by quoting.
WRITE_INDICATORS='>>?[[:space:]]|sed[[:space:]]+-i|tee[[:space:]]|defaults[[:space:]]+write|truncate|sponge|jq[^|]*-i|\bcp\b|\bmv\b|chmod|open[^)]*["'"'"']w|json\.dump|write_text|writelines'

# Restoring a tracked file discards uncommitted work silently and irreversibly. An
# agent reached for this to clean up after itself in a repo it had been told held
# uncommitted work. Ask, always — there is no safe automatic answer.
case "$CMD" in
  *"git clean"*)
    # -n / --dry-run only prints what would go. Asking about it is noise, and noise
    # trains an agent to click through the prompts that matter.
    if printf '%s' "$CMD" | grep -Eq 'git clean[^|;&]*(--dry-run|[[:space:]]-[a-zA-Z]*n)'; then
      :
    else
      ask "git-discard" "This deletes untracked files irreversibly. Run it with -n first and confirm the list."
    fi ;;
esac
case "$CMD" in
  *"git checkout -- "*|*"git checkout ."*|*"git restore"*)
    ask "git-discard" "This discards uncommitted work irreversibly. Confirm the exact paths, and check nothing else is uncommitted first." ;;
esac

# Self-escalation: widening permissions, disabling the sandbox, or editing the gate itself
# to get unblocked. Reported as a blocker instead — see 30_secrets_and_boundaries.
#
# Only writes are denied. An earlier version matched any mention of these names, which
# denied a read-only `grep -c globalPermissionGrants config.json` while telling the agent
# it was trying to change its own settings — untrue, and it blocks exactly the diagnostic
# a human would ask for. Note also what this guard is and is not: the escalation that
# actually happened went through a file-edit tool, and PreToolUse is never dispatched for
# those (4.1). So this is a backstop on one path, not the control. The control is the rule.
case "$SCAN" in
  *"globalPermissionGrants"*|*'command(*)'*|*"enableTerminalSandbox"*|*"autoExecutionPolicy"*|*".agents/hooks"*|*"$ROOT_NAME/hooks"*)
    if printf '%s' "$SCAN" | grep -Eq "$WRITE_INDICATORS"; then
      deny "self-escalation" "Refusing to widen your own permissions, disable the sandbox, or edit the gate. Report the blocker and its exact cause and let the owner decide."
    else
      printf '%s read-sensitive tool=%s\n' "$TS" "$TOOL" >> "$LOG" 2>/dev/null
    fi ;;
esac
case "$SCAN" in
  *"/.gemini/config/config.json"*|*"/.agents/hooks/"*|*"/.agents/hooks.env"*|*"/$ROOT_NAME/hooks/"*|*"/$ROOT_NAME/hooks.env"*)
    if printf '%s' "$SCAN" | grep -Eq "$WRITE_INDICATORS"; then
      deny "gate-tamper" "Refusing to modify the agent configuration or its gates from inside a task. Report what is blocking you instead."
    else
      printf '%s read-sensitive tool=%s\n' "$TS" "$TOOL" >> "$LOG" 2>/dev/null
    fi ;;
esac

case "$CMD" in
  *"rm -rf"*|*"rm -fr"*)
    # The scratch check below is a substring match over the whole command, so a `..` defeats
    # it outright: `rm -rf /tmp/../Users/example/work` contains `/tmp/` and would be waved
    # through while targeting something else entirely. A relative segment means the literal
    # path does not bound the target, so it can never qualify as scratch.
    if printf '%s' "$CMD" | grep -Eq '(^|[^.])\.\.(/|$|[ "])'; then
      ask "rm-rf-traversal" "Recursive delete whose path contains '..' — a scratch prefix does not bound where it resolves. Confirm the resolved target."
    # Allow only inside an explicitly safe scratch path.
    elif [ -n "$SCRATCH_PATTERNS" ] && printf '%s' "$CMD" | grep -Eq "$SCRATCH_PATTERNS"; then
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

#!/bin/sh
# Self-test for the hook scripts in ../hooks/. Builds a throwaway customization root,
# feeds each hook realistic payloads, and asserts the JSON decision it prints.
#
#   tools/test_hooks.sh path/to/hooks.env
#
# Universal checks always run. Two workspace-specific vectors run when the env file
# sets them: TEST_DENY_CMD (must be denied) and TEST_VALIDATION_CMD (must close an
# open edit batch).
set -e

ENV_FILE="${1:-}"
if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
  echo "usage: $0 path/to/hooks.env" >&2
  exit 2
fi

HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

mkdir -p "$T/hooks" "$T/.state"
cp "$HERE"/hooks/*.sh "$T/hooks/"
cp "$HERE"/hooks/hooks.json "$T/"
cp "$ENV_FILE" "$T/hooks.env"
chmod +x "$T"/hooks/*.sh

# Read the vectors without letting the env file affect this shell's own state.
TEST_DENY_CMD=$(sh -c ". '$ENV_FILE'; printf '%s' \"\${TEST_DENY_CMD:-}\"")
TEST_VALIDATION_CMD=$(sh -c ". '$ENV_FILE'; printf '%s' \"\${TEST_VALIDATION_CMD:-}\"")

PASS=0
FAIL=0
COMMON='"conversationId":"c1","workspacePaths":["/tmp/ws"],"transcriptPath":"","modelName":"m"'

check() {
  if printf '%s' "$3" | grep -q "$2"; then
    PASS=$((PASS + 1)); printf 'ok    %s\n' "$1"
  else
    FAIL=$((FAIL + 1)); printf 'FAIL  %s\n        expected: %s\n        got: %s\n' "$1" "$2" "$3"
  fi
}

valid_json() {
  printf '%s' "$2" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null \
    && { PASS=$((PASS + 1)); printf 'ok    %s (valid JSON)\n' "$1"; } \
    || { FAIL=$((FAIL + 1)); printf 'FAIL  %s emitted invalid JSON: %s\n' "$1" "$2"; }
}

run() { ( cd "$T" && printf '%s' "$2" | "./hooks/$1" ); }

cmd_payload() {
  printf '{"toolCall":{"name":"run_command","args":{"CommandLine":"%s"}},%s}' "$1" "$COMMON"
}

# ---- discipline_heartbeat ----
OUT=$(run discipline_heartbeat.sh "{\"invocationNum\":0,$COMMON}")
check "heartbeat fires on invocation 0" 'ephemeralMessage' "$OUT"
valid_json "heartbeat" "$OUT"
OUT=$(run discipline_heartbeat.sh "{\"invocationNum\":1,$COMMON}")
check "heartbeat silent between beats" '^{}$' "$OUT"
: > "$T/.state/edit_open"
OUT=$(run discipline_heartbeat.sh "{\"invocationNum\":1,$COMMON}")
check "heartbeat nags about an open edit batch" 'ephemeralMessage' "$OUT"
rm -f "$T/.state/edit_open"

# ---- universal command guards ----
OUT=$(run pre_tool_gate.sh "$(cmd_payload 'git push --force origin main')")
check "denies force push" '"decision":"deny"' "$OUT"
valid_json "gate deny" "$OUT"

OUT=$(run pre_tool_gate.sh "$(cmd_payload 'git reset --hard origin/main')")
check "asks on reset --hard" '"decision":"force_ask"' "$OUT"

OUT=$(run pre_tool_gate.sh "$(cmd_payload 'rm -rf /')")
check "denies rm -rf targeting root" '"decision":"deny"' "$OUT"

OUT=$(run pre_tool_gate.sh "$(cmd_payload 'rm -rf /opt/example/workspace/thing')")
check "asks on rm -rf outside scratch" '"decision":"force_ask"' "$OUT"

OUT=$(run pre_tool_gate.sh "$(cmd_payload 'rm -rf /private/tmp/scratch/x')")
check "allows rm -rf inside scratch" '"decision":"allow"' "$OUT"

OUT=$(run pre_tool_gate.sh "$(cmd_payload 'git status')")
check "ordinary command passes through with a VALID decision" '"decision":"allow"' "$OUT"
valid_json "gate pass-through" "$OUT"
# Regression guard: an empty {} is not a valid PreToolUse response. Emitting one made the
# platform reject every tool call as invalid_args with an empty reason — all shell
# execution was dead in both workspaces while every self-test still passed.
if printf '%s' "$OUT" | grep -q '^{}$'; then
  FAIL=$((FAIL + 1)); echo "FAIL  gate emitted bare {} — platform will reject the tool call"
else
  PASS=$((PASS + 1)); echo "ok    gate never emits a bare {} for pass-through"
fi

# ---- self-escalation and destructive-git guards (regressions from a real run) ----
for c in "git checkout -- Pure/Views/Foo.swift" "git restore Foo.swift" "git clean -fd"; do
  OUT=$(run pre_tool_gate.sh "$(cmd_payload "$c")")
  check "asks before discarding uncommitted work: $c" '"decision":"force_ask"' "$OUT"
done

# Reads of the sensitive config must pass: an earlier version denied a read-only grep and
# told the agent it was changing its own settings. Writes must still be denied.
for c in "grep -c globalPermissionGrants /opt/example/.gemini/config/config.json" \
         "cat /opt/example/.gemini/config/config.json" \
         "python3 Tools/x.py --show autoExecutionPolicy"; do
  OUT=$(run pre_tool_gate.sh "$(cmd_payload "$c")")
  check "allows read of sensitive config: $c" '"decision":"allow"' "$OUT"
done

# git clean dry runs mutate nothing; asking about them trains click-through.
for c in "git clean -n" "git clean --dry-run" "git clean -nd"; do
  OUT=$(run pre_tool_gate.sh "$(cmd_payload "$c")")
  check "allows git clean dry run: $c" '"decision":"allow"' "$OUT"
done
OUT=$(run pre_tool_gate.sh "$(cmd_payload 'git clean -fd')")
check "still asks on a real git clean" '"decision":"force_ask"' "$OUT"

for c in "sed -i s/false/true/ /opt/example/.gemini/config/config.json" \
         "echo command(*) >> /opt/example/.gemini/config/config.json" \
         "defaults write enableTerminalSandbox false" \
         "cp /tmp/x /opt/example/.agents/hooks/pre_tool_gate.sh" \
         "python3 -c import json; json.dump(d, open(GLOBALPERMS)); globalPermissionGrants"; do
  OUT=$(run pre_tool_gate.sh "$(cmd_payload "$c")")
  check "denies self-escalation / gate tampering: $c" '"decision":"deny"' "$OUT"
done

# ---- workspace deny vector ----
if [ -n "$TEST_DENY_CMD" ]; then
  OUT=$(run pre_tool_gate.sh "$(cmd_payload "$TEST_DENY_CMD")")
  check "denies workspace-specific command: $TEST_DENY_CMD" '"decision":"deny"' "$OUT"
else
  echo "skip  no TEST_DENY_CMD set in $ENV_FILE"
fi

# ---- edit-batch tracking (best effort; see PLATFORM_CONTRACT 4.1) ----
OUT=$(run pre_tool_gate.sh "{\"toolCall\":{\"name\":\"code_action\",\"args\":{}},$COMMON}")
check "edit tool opens the batch" '"decision":"allow"' "$OUT"
[ -f "$T/.state/edit_open" ] \
  && { PASS=$((PASS + 1)); echo "ok    edit_open flag created"; } \
  || { FAIL=$((FAIL + 1)); echo "FAIL  edit_open flag missing"; }

if [ -n "$TEST_VALIDATION_CMD" ]; then
  run pre_tool_gate.sh "$(cmd_payload "$TEST_VALIDATION_CMD")" >/dev/null
  [ -f "$T/.state/edit_open" ] \
    && { FAIL=$((FAIL + 1)); echo "FAIL  validation command did not close the batch"; } \
    || { PASS=$((PASS + 1)); echo "ok    validation command closed the batch"; }
else
  echo "skip  no TEST_VALIDATION_CMD set in $ENV_FILE"
  rm -f "$T/.state/edit_open"
fi

# ---- no_premature_stop ----
OUT=$(run no_premature_stop.sh "{\"fullyIdle\":false,\"executionNum\":0,$COMMON}")
check "blocks stop while background work runs" '"decision":"continue"' "$OUT"
valid_json "stop not-idle" "$OUT"

: > "$T/.state/edit_open"; rm -f "$T/.state/stop_c1"
OUT=$(run no_premature_stop.sh "{\"fullyIdle\":true,\"executionNum\":0,$COMMON}")
check "blocks stop with an open edit batch" '"decision":"continue"' "$OUT"
OUT=$(run no_premature_stop.sh "{\"fullyIdle\":true,\"executionNum\":1,$COMMON}")
check "second continue allowed" '"decision":"continue"' "$OUT"
OUT=$(run no_premature_stop.sh "{\"fullyIdle\":true,\"executionNum\":2,$COMMON}")
check "third stop allowed — loop guard holds" '^{}$' "$OUT"
rm -f "$T/.state/edit_open" "$T/.state/stop_c1"

TR="$T/transcript.jsonl"
mk_payload() { printf '{"fullyIdle":true,"executionNum":0,"conversationId":"%s","workspacePaths":["/tmp/ws"],"transcriptPath":"%s","modelName":"m"}' "$1" "$TR"; }

printf '%s\n' '{"step_index":1,"source":"MODEL","type":"PLANNER_RESPONSE","content":"Done, looks fine."}' > "$TR"
OUT=$(run no_premature_stop.sh "$(mk_payload c2)")
check "blocks stop when the answer has no Validation section" '"decision":"continue"' "$OUT"

printf '%s\n' '{"step_index":1,"source":"MODEL","type":"PLANNER_RESPONSE","content":"Scope/Findings/Risks/Validation: compiled clean."}' > "$TR"
OUT=$(run no_premature_stop.sh "$(mk_payload c3)")
check "allows stop when Validation is present" '^{}$' "$OUT"

# an edit with no validation after it, detected from the transcript
printf '%s\n' '{"step_index":1,"source":"MODEL","type":"CODE_ACTION","content":"wrote Foo.ext"}' > "$TR"
printf '%s\n' '{"step_index":2,"source":"MODEL","type":"PLANNER_RESPONSE","content":"Scope/Findings/Risks/Validation: looks right."}' >> "$TR"
OUT=$(run no_premature_stop.sh "$(mk_payload c4)")
if [ -n "$TEST_VALIDATION_CMD" ]; then
  check "blocks stop when an edit had no validation after it" '"decision":"continue"' "$OUT"
  printf '%s\n' '{"step_index":1,"source":"MODEL","type":"CODE_ACTION","content":"wrote Foo.ext"}' > "$TR"
  printf '{"step_index":2,"type":"RUN_COMMAND","content":"%s: ok"}\n' "$TEST_VALIDATION_CMD" >> "$TR"
  printf '%s\n' '{"step_index":3,"source":"MODEL","type":"PLANNER_RESPONSE","content":"Scope/Findings/Risks/Validation: ran it."}' >> "$TR"
  OUT=$(run no_premature_stop.sh "$(mk_payload c5)")
  check "allows stop when validation followed the edit" '^{}$' "$OUT"
else
  echo "skip  edit-validation transcript checks need VALIDATION_PATTERNS + TEST_VALIDATION_CMD"
fi

# ---- fail open ----
for h in discipline_heartbeat pre_tool_gate no_premature_stop; do
  OUT=$(run "$h.sh" 'not json at all')
  valid_json "$h on garbage input" "$OUT"
done

# ---- hooks.json integrity ----
python3 - "$T" <<'PY'
import json, os, sys
root = sys.argv[1]
cfg = json.load(open(os.path.join(root, "hooks.json")))
missing, wildcard = [], []
for name, spec in cfg.items():
    for event, handlers in spec.items():
        if event == "enabled":
            continue
        for h in handlers:
            if h.get("matcher") in ("*", ""):
                wildcard.append(name)
            for hh in (h.get("hooks") or [h]):
                cmd = hh.get("command")
                if cmd and not os.path.exists(os.path.join(root, cmd)):
                    missing.append(cmd)
print("HOOKSJSON_MISSING=" + (",".join(missing) if missing else "none"))
print("HOOKSJSON_WILDCARD=" + (",".join(wildcard) if wildcard else "none")
      + ("  <-- a wildcard matcher intercepts ask_permission and stalls it" if wildcard else ""))
PY

echo
echo "passed: $PASS   failed: $FAIL"
[ "$FAIL" -eq 0 ]

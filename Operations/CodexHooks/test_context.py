"""Exercise hook commands without starting a model or changing hook trust."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from context import context


PUBLIC = Path(__file__).resolve().parents[2]
CONFIG = json.loads((PUBLIC / ".codex/hooks.json").read_text())


class RoutingHooks(unittest.TestCase):
    def invoke(self, cwd, event, raw=None):
        handler = CONFIG["hooks"][event][0]["hooks"][0]
        result = subprocess.run(
            handler["command"], shell=True, cwd=cwd,
            input=raw if raw is not None else json.dumps({
                "hook_event_name": event, "cwd": str(cwd),
                "prompt": "PRIVATE_SENTINEL", "tool_name": "Bash",
            }), text=True, capture_output=True, timeout=handler["timeout"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("PRIVATE_SENTINEL", result.stdout)
        self.assertLess(len(result.stdout.encode()), 8192)
        return json.loads(result.stdout)

    def test_real_checkout_events(self):
        for event in CONFIG["hooks"]:
            for cwd in [PUBLIC, PUBLIC / "Modules/XUUnity"]:
                with self.subTest(event=event, cwd=cwd):
                    output = self.invoke(cwd, event)["hookSpecificOutput"]
                    self.assertEqual(output["hookEventName"], event)
                    self.assertIn("Pre-edit check", output["additionalContext"])
                    self.assertIn("Derived execution contract", output["additionalContext"])

    def test_portable_layouts(self):
        with tempfile.TemporaryDirectory(prefix="codex route spaces ") as temp:
            base = Path(temp)
            for mounted in [False, True]:
                host = base / ("mounted" if mounted else "standalone")
                public = host / "AIRoot" if mounted else host
                operation = public / "Operations/CodexHooks"
                operation.mkdir(parents=True)
                shutil.copyfile(PUBLIC / "Operations/CodexHooks/context.py", operation / "context.py")
                (public / "AGENTS.md").write_text("public router")
                if mounted:
                    (host / "AGENTS.md").write_text("host router")
                nested = public / "nested submodule/deeper"
                nested.mkdir(parents=True)
                (nested.parent / ".git").write_text("gitdir: irrelevant-to-ancestor-resolution")
                for cwd in [host, public, nested]:
                    output = self.invoke(cwd, "UserPromptSubmit")
                    message = output["hookSpecificOutput"]["additionalContext"]
                    self.assertIn(str(host / "AGENTS.md"), message)
                    self.assertIn(str(public / "Modules/XUUnity/tasks/start_session.md"), message)

    def test_malformed_event(self):
        for raw in ["{broken", "[]", "null"]:
            self.assertIn("systemMessage", self.invoke(PUBLIC, "SessionStart", raw))

    def test_unsupported_event(self):
        self.assertEqual(context({"hook_event_name": "Stop"}, PUBLIC), {})

    def test_known_read_only_shell_discovery_is_quiet(self):
        for command in [
            "cat AGENTS.md", "head -n 20 file", "tail -n 5 file", "wc -c file", "pwd",
            "rg --files", "rg -n pattern file | head -n 20",
            "sed -n '10,25p' file", "sed -n '5p' 'path with spaces'",
            "git status --short && git diff --stat", "git log -3; git show HEAD:file",
            "git ls-files | wc -l", "git rev-parse --show-toplevel",
        ]:
            for tool, field in [("Bash", "command"), ("exec_command", "cmd")]:
                with self.subTest(command=command, tool=tool):
                    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {field: command}}
                    self.assertEqual(context(event, PUBLIC), {})

    def test_mutating_mixed_unknown_and_ambiguous_shell_inputs_keep_reminders(self):
        for command in [
            "touch file", "python3 script.py", "cat file; touch other", "cat file && rm other",
            "cat file | tee other", "cat file > other", "cat < file", "cat $(touch file)",
            "cat `touch file`", "VALUE=1 cat file", "env VALUE=1 cat file",
            "sed -i 's/a/b/' file", "sed -n -e '1p' file", "sed -n '1w other' file",
            "sed -n '1p' -i file", "awk 'BEGIN {system(\"touch file\")}'",
            "rg --pre=script pattern", "rg --hostname-bin=script pattern",
            "git reset --hard", "git diff --output=other", "git diff --ext-diff",
            "git show --textconv HEAD:file", "git -c alias.x=status x",
            "cat file || pwd", "cat file & pwd", "cat file\nrm other", "cat 'unterminated", "",
        ]:
            with self.subTest(command=command):
                event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
                self.assertIn("hookSpecificOutput", context(event, PUBLIC))
        for event in [
            {"tool_name": "Bash"}, {"tool_name": "Bash", "tool_input": {}},
            {"tool_name": "Bash", "tool_input": "cat file"},
            {"tool_name": "Bash", "tool_input": {"command": None}},
            {"tool_name": "unknown", "tool_input": {"command": "cat file"}},
        ]:
            self.assertIn("hookSpecificOutput", context({"hook_event_name": "PreToolUse", **event}, PUBLIC))

    def test_routing_and_resume_events_ignore_the_shell_filter(self):
        for name in ["SessionStart", "SubagentStart", "UserPromptSubmit"]:
            original = context({"hook_event_name": name}, PUBLIC)
            for source in ["startup", "resume", "compact"]:
                event = {"hook_event_name": name, "source": source, "tool_name": "Bash", "tool_input": {"command": "cat file"}}
                self.assertEqual(original, context(event, PUBLIC))

    def test_real_configured_command_suppresses_read_only_discovery(self):
        raw = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "cat AGENTS.md"}})
        self.assertEqual(self.invoke(PUBLIC, "PreToolUse", raw), {})

    def test_host_config_and_command(self):
        host_config = PUBLIC.parent / ".codex/hooks.json"
        if host_config.is_file():
            self.assertEqual(json.loads(host_config.read_text()), CONFIG)
            self.invoke(PUBLIC.parent, "SessionStart")


if __name__ == "__main__":
    unittest.main()

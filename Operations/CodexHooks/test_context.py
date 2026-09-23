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

    def test_host_config_and_command(self):
        host_config = PUBLIC.parent / ".codex/hooks.json"
        if host_config.is_file():
            self.assertEqual(json.loads(host_config.read_text()), CONFIG)
            self.invoke(PUBLIC.parent, "SessionStart")


if __name__ == "__main__":
    unittest.main()

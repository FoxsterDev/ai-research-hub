import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "templates"))

import runner


class PromptManifestTests(unittest.TestCase):
    def test_scalar_external_ai_allowed(self):
        control = runner.parse_prompt_control("external_ai: allowed\n\nDo the task.")
        self.assertTrue(control.external_ai_allowed)

    def test_block_external_ai_values(self):
        control = runner.parse_prompt_control(
            """---
external_ai:
  provider: claude_cli
  model: best_available
  authPolicy: official_login_only
  apiBilling: forbidden
  web: allowed
  writes: forbidden
---
Body
"""
        )
        self.assertTrue(control.external_ai_allowed)
        self.assertEqual(control.provider, "claude_cli")
        self.assertEqual(control.model, "best_available")
        self.assertEqual(control.web, "allowed")
        self.assertEqual(control.writes, "forbidden")

    def test_no_marker_is_not_allowed(self):
        control = runner.parse_prompt_control("Do the task.")
        self.assertFalse(control.external_ai_allowed)

    def test_via_claude_selects_claude_provider(self):
        control = runner.parse_prompt_control("xuunity fix the bug via claude\n\nDetails.")
        self.assertTrue(control.external_ai_allowed)
        self.assertEqual(control.provider, "claude_cli")

    def test_russian_claude_selector(self):
        control = runner.parse_prompt_control("xuunity review этот код через claude\n")
        self.assertTrue(control.external_ai_allowed)
        self.assertEqual(control.provider, "claude_cli")


if __name__ == "__main__":
    unittest.main()

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('routing_audit_alias_test', Path(__file__).resolve().parents[4] / 'scripts/routing_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
MARKER = '<!-- Managed by AIRoot/scripts/init_ai_project.sh alias-fallback -->'


class AliasFallbackTests(unittest.TestCase):
    def test_only_managed_exact_existing_target_passes(self):
        cases = [(MARKER+'\ntarget: ../AGENTS.md\n', True),
                 ('target: ../AGENTS.md\n', False),
                 (MARKER+'\ntarget: ../other.md\n', False),
                 (MARKER+'\ntarget: ../AGENTS.md\ntarget: ../AGENTS.md\n', False)]
        for content, expected in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'AGENTS.md').write_text('# Router\n', encoding='utf-8')
                (root/'Project').mkdir()
                (root/'Project/AGENTS.repo.md').write_text(content, encoding='utf-8')
                errors = []
                with contextlib.redirect_stdout(io.StringIO()):
                    AUDIT.check_repo_router_links(root, errors)
                self.assertEqual(expected, not errors)

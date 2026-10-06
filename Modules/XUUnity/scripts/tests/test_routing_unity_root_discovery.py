import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('routing_audit_unity_roots_test', Path(__file__).resolve().parents[4] / 'scripts/routing_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def make_unity_root(path):
    (path/'Assets').mkdir(parents=True)
    (path/'ProjectSettings').mkdir()


def write_topology(root, routed=(), optional=()):
    lines = ['routed_projects:'] + [f'  - {rel}' for rel in routed]
    if optional:
        lines.append('optional_local_projects:')
        for rel in optional:
            lines += [f'  - path: {rel}', '    tracked_release_proof: false']
    topology = root/'AIOutput/Registry/host_topology.yaml'
    topology.parent.mkdir(parents=True, exist_ok=True)
    topology.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return topology


def run_check(root, topology):
    errors = []
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        AUDIT.check_unity_roots_listed(root, topology, errors)
    return errors, output.getvalue()


class UnityRootDiscoveryTests(unittest.TestCase):
    def test_unlisted_unity_root_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_unity_root(root/'Listed')
            make_unity_root(root/'Unlisted')
            errors, output = run_check(root, write_topology(root, routed=['Listed']))
            self.assertEqual(1, len(errors))
            self.assertIn('Unlisted', errors[0])
            self.assertIn('FAIL: Unity project root is not listed', output)

    def test_routed_or_optional_unity_root_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_unity_root(root/'Routed')
            make_unity_root(root/'Optional')
            errors, output = run_check(root, write_topology(root, routed=['Routed'], optional=['Optional']))
            self.assertEqual([], errors)
            self.assertIn('OK: Unity project root is routed: Routed', output)
            self.assertIn('OK: Unity project root is an optional local project: Optional', output)

    def test_non_unity_directories_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'AssetsOnly/Assets').mkdir(parents=True)
            (root/'SettingsOnly/ProjectSettings').mkdir(parents=True)
            make_unity_root(root/'Group/Nested')
            (root/'Assets').write_text('not a directory\n', encoding='utf-8')
            errors, output = run_check(root, write_topology(root))
            self.assertEqual([], errors)
            self.assertNotIn('Unity project root', output)

    def test_unreadable_child_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_unity_root(root/'Game')
            (root/'Locked').mkdir()
            real_is_dir = Path.is_dir

            def is_dir(path, *args, **kwargs):
                if path.parent.name == 'Locked':
                    raise PermissionError(13, 'Permission denied', str(path))
                return real_is_dir(path, *args, **kwargs)

            with mock.patch.object(Path, 'is_dir', is_dir):
                errors, output = run_check(root, write_topology(root, routed=['Game']))
            self.assertEqual([], errors)
            self.assertIn('OK: Unity project root is routed: Game', output)

    def test_audit_exit_code_reflects_unlisted_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'AGENTS.md').write_text('# Router\n', encoding='utf-8')
            (root/'AIRoot/Modules/XUUnity').mkdir(parents=True)
            (root/'AIRoot/Modules/XUUnity/README.md').write_text('# XUUnity\n', encoding='utf-8')
            write_topology(root, routed=['Game'])
            (root/'AIOutput/Registry/setup_status.yaml').write_text('host_root: .\n', encoding='utf-8')
            make_unity_root(root/'Game')
            (root/'Game/AGENTS.md').write_text('- Project kind: `unity_project`\n', encoding='utf-8')
            argv = ['routing_audit.py', '--host-root', str(root)]
            with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, AUDIT.main())
                make_unity_root(root/'Extra')
                self.assertEqual(1, AUDIT.main())


if __name__ == '__main__':
    unittest.main()

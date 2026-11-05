import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cleanup_common as common
import discovery
import reclaim
import recoverable_cleanup as safe
import workspace_cleanup as cli

OLD = 400 * 3600
GIB = 1024 ** 3


def age(path: Path, seconds: float = OLD) -> None:
    stamp = time.time() - seconds
    for item in [*path.rglob('*'), path]:
        os.utime(item, (stamp, stamp), follow_symlinks=False)


def derived_data(parent: Path, name: str = 'DerivedData') -> Path:
    root = parent / name
    for part in ('SourcePackages/repositories/vendor-package', 'Build/Intermediates.noindex/App.build',
                 'Index.noindex/DataStore', 'Build/Products/Debug-iphonesimulator/App.app', 'Logs/Test',
                 'SourcePackages/checkouts/vendor-package'):
        (root / part).mkdir(parents=True)
        (root / part / 'blob').write_bytes(b'x' * 4096)
    (root / 'info.plist').write_text('plist')
    return root


def unity_project(root: Path) -> Path:
    for part in ('Assets', 'Packages', 'ProjectSettings', 'Library/Artifacts'):
        (root / part).mkdir(parents=True)
    (root / 'Packages/manifest.json').write_text('{}')
    (root / 'ProjectSettings/ProjectSettings.asset').write_text('x')
    (root / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.0.58f2\n')
    (root / 'Library/Artifacts/blob').write_bytes(b'u' * 4096)
    return root


IDLE = dict(table_source=lambda: [], open_source=lambda: [])


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.projects = self.root / 'Projects'
        shard = self.projects / 'Pure/Artifacts/Releases/b74/visual/shard-1'
        shard.mkdir(parents=True)
        (shard / 'result.xcresult').mkdir()
        (shard / 'evidence.json').write_text('{}')
        self.shard = shard
        self.dd = derived_data(shard)
        self.pending = derived_data(shard, 'DerivedData-pending')
        (shard / 'DerivedData-ui-artifacts/screens').mkdir(parents=True)
        self.unity = unity_project(self.projects / 'Game')
        age(self.projects)
        self.rule = {'name': 'nested', 'scan_roots': [str(self.projects)], 'container_kind': 'xcode_derived_data',
                     'targets': ['SourcePackages/repositories', 'Build/Intermediates.noindex', 'Index.noindex'],
                     'minimum_age_hours': 336, 'block_executables': ['xcodebuild', 'Xcode']}

    def reclaim(self, rule=None, apply=True, **sources):
        return reclaim.run({'rules': [rule or self.rule]}, apply=apply, **{**IDLE, **sources})


class ReclaimTests(Fixture):
    def test_nested_derived_data_found_by_content_including_renamed_dirs(self):
        found = reclaim.containers({'scan_roots': [str(self.projects)], 'container_kind': 'xcode_derived_data'})
        self.assertEqual(sorted(p.name for p in found), ['DerivedData', 'DerivedData-pending'])

    def test_apply_deletes_only_regenerable_parts_and_keeps_evidence(self):
        result = self.reclaim()
        states = {Path(r['path']).relative_to(self.shard).as_posix(): r['state'] for r in result['entries']}
        self.assertEqual(set(states.values()), {'deleted'})
        self.assertEqual(len(states), 6)
        for dd in (self.dd, self.pending):
            self.assertFalse((dd / 'SourcePackages/repositories').exists())
            self.assertFalse((dd / 'Build/Intermediates.noindex').exists())
            self.assertTrue((dd / 'Build/Products/Debug-iphonesimulator/App.app/blob').exists())
            self.assertTrue((dd / 'SourcePackages/checkouts/vendor-package/blob').exists())
            self.assertTrue((dd / 'Logs/Test/blob').exists())
        self.assertTrue((self.shard / 'result.xcresult').exists())
        self.assertTrue((self.shard / 'DerivedData-ui-artifacts/screens').exists())
        self.assertGreater(result['totals']['deleted_allocated_bytes'], 0)
        self.assertEqual(list(self.shard.rglob('.reclaim-*')), [])

    def test_dry_run_mutates_nothing(self):
        result = self.reclaim(apply=False)
        self.assertEqual({r['state'] for r in result['entries']}, {'eligible'})
        self.assertTrue((self.dd / 'Index.noindex/DataStore/blob').exists())

    def test_recent_descendant_is_kept(self):
        os.utime(self.dd / 'Index.noindex/DataStore/blob')
        rows = {r['path']: r for r in self.reclaim()['entries']}
        self.assertEqual(rows[str(self.dd / 'Index.noindex')]['state'], 'kept_recent')
        self.assertTrue((self.dd / 'Index.noindex').exists())

    def test_active_executable_defers_whole_rule(self):
        table = lambda: [('xcodebuild', '/usr/bin/xcodebuild test')]
        result = self.reclaim(table_source=table)
        self.assertEqual({r['state'] for r in result['entries']}, {'deferred'})
        self.assertTrue((self.dd / 'Index.noindex').exists())

    def test_argument_tokens_do_not_count_as_build_activity(self):
        renderer = 'Claude Helper (Renderer)'
        result = self.reclaim(table_source=lambda: [(renderer, f'{renderer} --flag Simulator Xcode Unity')])
        self.assertEqual({r['state'] for r in result['entries']}, {'deleted'})

    def test_process_referencing_container_or_open_file_defers(self):
        table = lambda: [('python3', f'python3 gate.py --derived-data {self.dd}')]
        rows = {r['path']: r['state'] for r in self.reclaim(apply=False, table_source=table)['entries']}
        self.assertEqual(rows[str(self.dd / 'Index.noindex')], 'deferred')
        self.assertEqual(rows[str(self.pending / 'Index.noindex')], 'eligible')
        opened = str(self.pending / 'Build/Intermediates.noindex/App.build/blob')
        rows = {r['path']: r['state'] for r in self.reclaim(apply=False, open_source=lambda: [opened])['entries']}
        self.assertEqual(rows[str(self.pending / 'Build/Intermediates.noindex')], 'deferred')

    def test_activity_appearing_before_delete_defers(self):
        calls = iter([[], [('Xcode', '/Applications/Xcode.app/Contents/MacOS/Xcode')]] + [[]] * 20)
        rows = self.reclaim(table_source=lambda: next(calls))['entries']
        self.assertEqual(rows[0]['state'], 'deferred')
        self.assertIn('activity appeared', rows[0]['reason'])

    def test_protected_artifact_inside_target_and_protected_path_are_kept(self):
        (self.dd / 'Index.noindex/report.xcresult').mkdir()
        age(self.dd)
        result = reclaim.run({'rules': [self.rule], 'protected_paths': [str(self.pending)]}, apply=True, **IDLE)
        rows = {r['path']: r for r in result['entries']}
        self.assertEqual(rows[str(self.dd / 'Index.noindex')]['state'], 'kept')
        self.assertEqual(rows[str(self.pending / 'Index.noindex')]['reason'], 'protected path overlap')
        self.assertTrue((self.pending / 'Index.noindex').exists())

    def test_tracked_files_are_kept(self):
        subprocess.run(['git', 'init', '-q', str(self.projects)], check=True)
        subprocess.run(['git', '-C', str(self.projects), 'add', '-f', str(self.dd / 'Index.noindex')], check=True)
        rows = {r['path']: r for r in self.reclaim()['entries']}
        self.assertEqual(rows[str(self.dd / 'Index.noindex')]['reason'], 'tracked files inside')

    def test_symlinked_container_and_target_are_not_followed(self):
        outside = self.root / 'outside'
        derived_data(outside)
        age(outside)
        (self.projects / 'LinkedDerivedData').symlink_to(outside / 'DerivedData')
        (self.dd / 'Index.noindex').rename(self.root / 'moved-index')
        (self.dd / 'Index.noindex').symlink_to(self.root / 'moved-index')
        self.reclaim()
        self.assertTrue((outside / 'DerivedData/Index.noindex/DataStore/blob').exists())
        self.assertTrue((self.root / 'moved-index/DataStore/blob').exists())

    def test_partial_delete_reports_and_next_run_sweeps_tombstone(self):
        locked = self.dd / 'Index.noindex/DataStore'
        locked.chmod(0o500)
        try:
            rows = {r['path']: r for r in self.reclaim()['entries']}
        finally:
            for tomb in self.dd.glob('.reclaim-*'):
                for item in [tomb, *tomb.rglob('*')]:
                    if item.is_dir():
                        item.chmod(0o700)
        self.assertEqual(rows[str(self.dd / 'Index.noindex')]['state'], 'partially_deleted')
        self.assertTrue(list(self.dd.glob('.reclaim-*')))
        swept = [r for r in self.reclaim()['entries'] if r['state'] == 'tombstone_swept']
        self.assertTrue(swept)
        self.assertEqual(list(self.dd.glob('.reclaim-*')), [])

    def test_unity_library_rule_requires_verified_project(self):
        fake = self.projects / 'NotUnity/Library'
        fake.mkdir(parents=True)
        (fake / 'blob').write_text('x')
        age(self.projects, 800 * 3600)
        rule = {'name': 'unity', 'scan_roots': [str(self.projects)], 'container_kind': 'unity_library',
                'targets': ['.'], 'minimum_age_hours': 720, 'block_executables': ['Unity'],
                'require_unity_project': True}
        rows = self.reclaim(rule)['entries']
        self.assertEqual([r['path'] for r in rows], [str(self.unity / 'Library')])
        self.assertFalse((self.unity / 'Library').exists())
        self.assertTrue(fake.exists())
        self.assertTrue((self.unity / 'Assets').exists())

    def test_root_rule_prefix_and_dirty_git_guard(self):
        tmp = self.root / 'tmp'
        (tmp / 'pt-old').mkdir(parents=True)
        (tmp / 'other-old').mkdir()
        dirty = tmp / 'pt-dirty'
        subprocess.run(['git', 'init', '-q', str(dirty)], check=True)
        (dirty / 'work.txt').write_text('unsaved')
        age(tmp)
        rule = {'name': 'tmp', 'roots': [str(tmp)], 'targets': ['*'], 'name_prefixes': ['pt-'],
                'minimum_age_hours': 72, 'skip_dirty_git': True}
        rows = {Path(r['path']).name: r['state'] for r in self.reclaim(rule)['entries']}
        self.assertEqual(rows, {'pt-dirty': 'kept', 'pt-old': 'deleted'})
        self.assertTrue((tmp / 'other-old').exists() and dirty.exists())

    def test_rule_without_retention_is_refused(self):
        rule = {**self.rule, 'minimum_age_hours': 1}
        self.assertEqual(self.reclaim(rule)['entries'][0]['state'], 'deferred')
        self.assertTrue((self.dd / 'Index.noindex').exists())


class BrokerTests(Fixture):
    def broker(self, contract=True):
        state = self.root / 'broker'
        (state / 'capacity').mkdir(parents=True)
        if contract:
            (state / 'contract.json').write_text(json.dumps({'schemaVersion': 1, 'contractVersion': 1, 'capacity': 2}))
        for slot in range(2):
            (state / 'capacity' / f'slot-{slot}.lock').write_text('')
        return state

    def run_with(self, state):
        return reclaim.run({'rules': [{**self.rule, 'use_broker': True}], 'broker_state_dir': str(state)}, apply=True, **IDLE)

    def test_held_lease_defers_and_absent_broker_proceeds(self):
        state = self.broker()
        with (state / 'capacity/slot-1.lock').open('r+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual({r['state'] for r in self.run_with(state)['entries']}, {'deferred'})
        self.assertTrue((self.dd / 'Index.noindex').exists())
        self.assertEqual({r['state'] for r in self.run_with(self.root / 'absent')['entries']}, {'deleted'})

    def test_missing_contract_defers(self):
        rows = self.run_with(self.broker(contract=False))['entries']
        self.assertEqual({r['state'] for r in rows}, {'deferred'})


class DiscoveryTests(Fixture):
    def config(self, **extra):
        personal = self.root / 'Messenger'
        personal.mkdir(exist_ok=True)
        return {'scan_roots': [str(self.projects)], 'evidence_names': ['Artifacts', 'LocalArtifacts'],
                'watch': [{'path': str(personal), 'label': 'messenger', 'personal': True},
                          {'path': str(self.root / 'missing'), 'label': 'gone'}],
                'state_path': str(self.root / 'state/discovery.json'), **extra}

    def test_inventory_is_read_only_and_flags_evidence(self):
        config = self.config()
        before = sorted(str(p) for p in self.root.rglob('*'))
        result = discovery.run(config)
        kinds = sorted((i['kind'], Path(i['path']).name) for i in result['items'])
        self.assertIn(('xcode_derived_data', 'DerivedData-pending'), kinds)
        self.assertIn(('unity_library', 'Library'), kinds)
        dd = next(i for i in result['items'] if i['path'] == str(self.dd))
        self.assertTrue(dd['inside_evidence'])
        self.assertIn('SourcePackages/repositories', dd['parts'])
        after = sorted(str(p) for p in self.root.rglob('*') if 'state' not in p.parts)
        self.assertEqual(before, [p for p in after])

    def test_growth_and_personal_alerts(self):
        config = self.config(growth_alert_bytes=8192, personal_growth_alert_bytes=4096, new_item_alert_bytes=GIB)
        self.assertEqual(discovery.run(config)['alerts'], [])
        (self.dd / 'Build/Intermediates.noindex/big').write_bytes(b'g' * 65536)
        (self.root / 'Messenger/media.bin').write_bytes(b'm' * 65536)
        types = {(a['type'], Path(a.get('path', 'total')).name) for a in discovery.run(config)['alerts']}
        self.assertIn(('growth', 'DerivedData'), types)
        self.assertIn(('growth', 'Messenger'), types)


class QuarantineExpiryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.cache = self.root / 'DerivedData' / 'ModuleCache.noindex'
        self.cache.mkdir(parents=True)
        (self.cache / 'data.bin').write_bytes(b'regenerable')
        age(self.cache)
        self.quarantine = self.root / 'quarantine'
        self.quarantine.mkdir(mode=0o700)
        self.policy = {'allowed_roots': [str(self.cache.parent)], 'quarantine_root': str(self.quarantine),
                       'derived_data_root': str(self.cache.parent), 'protected_paths': [],
                       'quarantine_ttl_hours': 168,
                       'allowlist': [{'path': str(self.cache), 'category': 'xcode_derived_data',
                                      'minimum_age_hours': 168, 'ownership': {'kind': 'shared_xcode'}}]}
        patch.object(safe, 'process_idle').start()
        self.addCleanup(patch.stopall)
        self.row = safe.run(self.policy, apply=True)['entries'][0]
        self.assertEqual(self.row['state'], 'quarantined')
        self.manifest = Path(self.row['manifest'])

    def expire(self):
        record = json.loads(self.manifest.read_text())
        record['created_at'] -= 200 * 3600
        self.manifest.write_text(json.dumps(record))

    def test_payload_is_retained_inside_ttl_then_purged(self):
        self.assertEqual(safe.purge_expired(self.policy, apply=True)[0]['state'], 'retained')
        self.expire()
        self.assertEqual(safe.purge_expired(self.policy, apply=False)[0]['state'], 'purge_eligible')
        self.assertTrue(Path(self.row['destination']).exists())
        self.assertEqual(safe.purge_expired(self.policy, apply=True)[0]['state'], 'purged')
        self.assertFalse(Path(self.row['destination']).exists())
        self.assertEqual(json.loads(self.manifest.read_text())['state'], 'purged')
        self.assertEqual(safe.purge_expired(self.policy, apply=True), [])

    def test_changed_payload_is_not_purged(self):
        self.expire()
        (Path(self.row['destination']) / 'data.bin').write_bytes(b'changed')
        self.assertEqual(safe.purge_expired(self.policy, apply=True)[0]['state'], 'deferred')
        self.assertTrue(Path(self.row['destination']).exists())

    def test_ttl_below_one_day_is_refused(self):
        with self.assertRaises(safe.Deferred):
            safe.purge_expired({**self.policy, 'quarantine_ttl_hours': 1}, apply=True)

    def test_orphan_intent_is_reconciled(self):
        slot = self.quarantine / 'orphan'
        slot.mkdir(mode=0o700)
        (slot / 'manifest.json').write_text(json.dumps({'state': 'intent', 'source': str(self.cache), 'created_at': 0}))
        rows = {Path(r['manifest']).parent.name: r['state'] for r in safe.purge_expired(self.policy, apply=True)}
        self.assertEqual(rows['orphan'], 'reconciled_aborted')
        self.assertEqual(json.loads((slot / 'manifest.json').read_text())['state'], 'aborted')


class CliTests(Fixture):
    def write(self, config):
        path = self.root / 'config.json'
        path.write_text(json.dumps(config))
        return path

    def main(self, config, *extra):
        report = self.root / f'report-{len(list(self.root.glob("report-*")))}.json'
        with patch('sys.stdout'):
            code = cli.main(['--config', str(self.write(config)), '--report', str(report),
                             '--lock', str(self.root / 'cleanup.lock'), *extra])
        return code, json.loads(report.read_text()) if report.exists() else None

    def full_config(self):
        return {'schema_version': 2,
                'discovery': {'scan_roots': [str(self.projects)], 'state_path': str(self.root / 'state.json')},
                'reclaim': {'rules': [self.rule]}}

    def test_default_run_includes_discovery_and_reclaim_plan_without_mutation(self):
        with patch.object(common, 'process_table', return_value=[]), patch.object(common, 'open_paths', return_value=[]):
            code, report = self.main(self.full_config())
        self.assertEqual((code, report['mode'], report['status']), (0, 'dry_run', 'clean'))
        self.assertTrue(report['discovery']['items'])
        self.assertTrue(report['reclaim']['entries'])
        self.assertTrue((self.dd / 'Index.noindex').exists())
        self.assertIn('df_freed_bytes', report)

    def test_discover_mode_skips_reclaim(self):
        code, report = self.main(self.full_config(), '--discover')
        self.assertEqual(code, 0)
        self.assertNotIn('reclaim', report)

    def test_apply_reports_df_delta_and_deleted_bytes(self):
        with patch.object(common, 'process_table', return_value=[]), patch.object(common, 'open_paths', return_value=[]):
            code, report = self.main(self.full_config(), '--apply')
        self.assertEqual(code, 0)
        self.assertGreater(report['summary']['deleted_allocated_bytes'], 0)
        self.assertTrue(report['volumes_before'] and report['volumes_after'])

    def test_deferral_exits_three(self):
        with patch.object(common, 'process_table', return_value=[('Xcode', 'Xcode')]), patch.object(common, 'open_paths', return_value=[]):
            code, report = self.main(self.full_config(), '--apply')
        self.assertEqual((code, report['status']), (3, 'attention'))

    def test_failure_still_writes_report(self):
        with patch.object(reclaim, 'run', side_effect=RuntimeError('boom')):
            code, report = self.main(self.full_config())
        self.assertEqual((code, report['status'], report['error']), (1, 'failed', 'boom'))

    def test_retired_schema_one_is_refused(self):
        with patch('sys.stderr'):
            code, report = self.main({'schema_version': 1, 'simulator': {'mode': 'erase_all'}}, '--apply')
        self.assertEqual((code, report), (2, None))


if __name__ == '__main__':
    unittest.main()

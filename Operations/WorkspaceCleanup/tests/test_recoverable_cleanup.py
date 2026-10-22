import errno
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
import recoverable_cleanup as safe
import workspace_cleanup as legacy

class RecoverableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.cache = self.root/'caches'/'ModuleCache.noindex'
        self.cache.mkdir(parents=True)
        (self.cache/'data.bin').write_bytes(b'regenerable fixture')
        self.quarantine = self.root/'quarantine'
        self.quarantine.mkdir(mode=0o700)
        self.broker = self.root/'broker'
        (self.broker/'capacity').mkdir(parents=True)
        (self.broker/'contract.json').write_text(json.dumps({'schemaVersion':1,'contractVersion':1,'capacity':2}))
        for slot in range(2):
            (self.broker/'capacity'/f'slot-{slot}.lock').write_text('unchanged broker metadata')
        self.owner = self.root/'owners.json'
        self.owner.write_text(json.dumps({'observed_at':time.time(),'coverage':'complete',
             'maintenance_thread_id':'test','active_tasks':[], 'unavailable_hosts':[], 'unavailable_sources':[]}))
        self.policy = {'allowed_roots':[str(self.cache.parent)], 'allowlist':[
            {'path':str(self.cache),'category':'xcode_derived_data','minimum_age_hours':168}],
            'quarantine_root':str(self.quarantine),'broker_state_dir':str(self.broker),
            'ownership_snapshot':str(self.owner),'maintenance_thread_id':'test','protected_paths':[]}
        self.age()
        self.process = patch.object(safe, 'process_idle').start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.tmp.cleanup)
    def age(self):
        for p in [*self.cache.rglob('*'),self.cache]:
            os.utime(p,(time.time()-200*3600,)*2)
    def run_safe(self, apply=True):
        return safe.run(self.policy,apply=apply)
    def deferred(self):
        result=self.run_safe()
        self.assertEqual(result['entries'][0]['state'],'deferred',result)
        self.assertTrue(self.cache.exists())
        return result
    def test_dry_run_preserves_without_manifest(self):
        self.assertEqual(self.run_safe(False)['entries'][0]['state'],'eligible')
        self.assertTrue(self.cache.exists());self.assertEqual(list(self.quarantine.iterdir()),[])
    def test_real_move_restore_round_trip_and_locks_released(self):
        before=safe.snapshot(self.cache)
        row=self.run_safe()['entries'][0]
        self.assertEqual(row['state'],'quarantined',row);self.assertFalse(self.cache.exists())
        receipt=Path(row['manifest']);self.assertEqual(json.loads(receipt.read_text())['state'],'quarantined')
        safe.restore(receipt,self.policy)
        self.assertEqual(safe.snapshot(self.cache),before)
        for p in (self.broker/'capacity').iterdir():
            with p.open('r+') as h: fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(p.read_text(),'unchanged broker metadata')
    def test_active_broker_lease_preserves(self):
        with (self.broker/'capacity'/'slot-1.lock').open('r+') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);self.deferred()
    def test_new_build_at_final_check_preserves(self):
        self.process.side_effect=[None,safe.Deferred('new xcodebuild')]
        self.deferred()
    def test_live_cloud_task_preserves(self):
        d=json.loads(self.owner.read_text());d['active_tasks']=[{'id':'cloud-writer'}]
        self.owner.write_text(json.dumps(d));self.deferred()
    def test_stale_unknown_owner_preserves(self):
        d=json.loads(self.owner.read_text());d['observed_at']-=121
        self.owner.write_text(json.dumps(d));self.deferred()
    def test_recent_descendant_preserves(self):
        os.utime(self.cache/'data.bin',None);self.deferred()
    def test_protected_evidence_xcresult_archive_signed_app(self):
        for name in ['evidence','run.xcresult','Archives','candidate.app','_CodeSignature']:
            with self.subTest(name=name):
                p=self.cache/name;p.mkdir();self.age();self.deferred();p.rmdir()
    def test_symlink_and_hardlink_preserve(self):
        p=self.cache/'alias';p.symlink_to(self.cache/'data.bin');self.age();self.deferred();p.unlink()
        os.link(self.cache/'data.bin',p);self.age();self.deferred()
    def test_protected_ancestor_and_descendant_preserve(self):
        for p in [self.cache.parent,self.cache/'data.bin']:
            self.policy['protected_paths']=[str(p)];self.deferred()
    def test_outside_allowlist_root_preserves(self):
        self.policy['allowed_roots']=[str(self.quarantine)];self.deferred()
    def test_changed_inventory_before_rename_preserves(self):
        real=safe.snapshot; calls=0
        def changing(*args,**kw):
            nonlocal calls
            calls+=1
            if calls==3:(self.cache/'data.bin').write_bytes(b'changed')
            return real(*args,**kw)
        with patch.object(safe,'snapshot',side_effect=changing):self.deferred()
    def test_rename_failure_preserves_with_durable_intent(self):
        with patch.object(safe,'rename_exclusive',side_effect=OSError(errno.EACCES,'denied')):
            self.deferred()
        manifests=list(self.quarantine.glob('*/manifest.json'))
        self.assertEqual(len(manifests),1);self.assertEqual(json.loads(manifests[0].read_text())['state'],'intent')
    def test_journal_failure_before_move_preserves(self):
        with patch.object(safe,'write_json',side_effect=OSError('disk full')):self.deferred()
    def test_journal_failure_after_move_recoverable_from_intent(self):
        real=safe.write_json;calls=0
        def fail_after(path,value):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('disk full')
            return real(path,value)
        with patch.object(safe,'write_json',side_effect=fail_after):
            result=self.run_safe()
        self.assertEqual(result['entries'][0]['state'],'deferred')
        receipt=next(self.quarantine.glob('*/manifest.json'))
        self.assertEqual(json.loads(receipt.read_text())['state'],'intent')
        safe.restore(receipt,self.policy);self.assertTrue(self.cache.exists())
    def test_restore_collision_does_not_overwrite(self):
        row=self.run_safe()['entries'][0];self.cache.mkdir();(self.cache/'new').write_text('new')
        with self.assertRaises(safe.Deferred):safe.restore(Path(row['manifest']),self.policy)
        self.assertEqual((self.cache/'new').read_text(),'new');self.assertTrue(Path(row['destination']).exists())
    def test_atomic_destination_collision_refuses(self):
        target=self.root/'target';target.mkdir()
        with self.assertRaises(OSError):safe.rename_exclusive(self.cache,target)
        self.assertTrue(self.cache.exists());self.assertTrue(target.exists())
    def test_category_deferred_after_uncertainty(self):
        self.policy['allowlist']*=2;self.process.side_effect=safe.Deferred('busy')
        result=self.run_safe();self.assertEqual(result['entries'][1]['reason'],'category already deferred')
    def test_process_inventory_build_and_open_file_fail_closed(self):
        patch.stopall()
        for process in ['xcodebuild -test','/Applications/Xcode.app/Contents/MacOS/Xcode','/usr/bin/swiftc foo']:
            with patch.object(safe.subprocess,'run',return_value=subprocess.CompletedProcess([],0,process,'')):
                with self.assertRaises(safe.Deferred):safe.process_idle(self.cache)
        with patch.object(safe.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'python cleanup',''),subprocess.CompletedProcess([],0,'open file','')]):
            with self.assertRaises(safe.Deferred):safe.process_idle(self.cache)
    def test_cli_recoverable_roundtrip_report(self):
        policy=self.root/'policy.json';policy.write_text(json.dumps({'schema_version':1,'recoverable':self.policy}))
        report=self.root/'report.json'
        self.assertEqual(legacy.main(['--config',str(policy),'--report',str(report)]),0)
        self.assertTrue(self.cache.exists())
        self.assertEqual(legacy.main(['--config',str(policy),'--apply','--report',str(report)]),0)
        receipt=json.loads(report.read_text())['entries'][0]['manifest']
        self.assertFalse(self.cache.exists())
        self.assertEqual(legacy.main(['--config',str(policy),'--restore',receipt,'--report',str(report)]),0)
        self.assertTrue(self.cache.exists())
    def test_git_tracked_cache_is_preserved(self):
        subprocess.run(['git','init',str(self.cache.parent)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.cache.parent),'add','.'],check=True,capture_output=True)
        self.deferred()
    def test_broker_missing_contract_preserves(self):
        (self.broker/'contract.json').unlink();self.deferred()
    def test_protected_ancestor_is_rejected(self):
        root=self.root/'Archives';root.mkdir()
        target=root/self.cache.name;self.cache.rename(target)
        self.policy['allowlist'][0]['path']=str(target)
        self.policy['allowed_roots']=[str(root)]
        row=self.run_safe()['entries'][0]
        self.assertEqual(row['state'],'deferred');self.assertTrue(target.exists())
    def test_unreadable_subtree_is_not_omitted(self):
        protected=self.cache/'unreadable';protected.mkdir();(protected/'retained.xcresult').mkdir()
        self.age();protected.chmod(0)
        try:self.deferred()
        finally:protected.chmod(0o700)
    def test_owner_expires_during_final_hash(self):
        real=safe.snapshot;calls=0
        def expiring(*args,**kw):
            nonlocal calls
            calls+=1
            result=real(*args,**kw)
            if calls==3:
                d=json.loads(self.owner.read_text());d['observed_at']-=121
                self.owner.write_text(json.dumps(d))
            return result
        with patch.object(safe,'snapshot',side_effect=expiring):self.deferred()
    def test_arbitrary_process_reference_blocks(self):
        patch.stopall()
        with patch.object(safe.subprocess,'run',return_value=subprocess.CompletedProcess([],0,f'custom-worker --cache {self.cache}','')):
            with self.assertRaises(safe.Deferred):safe.process_idle(self.cache)
    def test_nan_cannot_bypass_retention_or_freshness(self):
        self.policy['allowlist'][0]['minimum_age_hours']=float('nan');self.deferred()
        self.policy['allowlist'][0]['minimum_age_hours']=168
        d=json.loads(self.owner.read_text());d['observed_at']=float('nan')
        self.owner.write_text(json.dumps(d));self.deferred()
    def test_private_var_tmp_process_aliases_block(self):
        patch.stopall()
        for physical,alias in [('/private/var/folders/cache','/var/folders/cache'),('/private/tmp/cache','/tmp/cache')]:
            with patch.object(safe.subprocess,'run',return_value=subprocess.CompletedProcess([],0,f'worker --cache={alias}','')):
                with self.assertRaises(safe.Deferred):safe.process_idle(Path(physical))
    def test_inventory_timeout_defers(self):
        self.process.side_effect=subprocess.TimeoutExpired('lsof',30)
        self.deferred()
    def test_unity_and_model_category_cannot_mislabel_arbitrary_directory(self):
        for category in ['unity_library','model_fitness_workspace']:
            self.policy['allowlist'][0]['category']=category
            self.deferred()
    def test_cli_legacy_apply_refused(self):
        p=self.root/'legacy.json';p.write_text(json.dumps({'schema_version':1,'simulator':{'mode':'erase_all'}}))
        self.assertEqual(legacy.main(['--config',str(p),'--apply']),2)

if __name__=='__main__':unittest.main()

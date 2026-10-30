"""Synthetic ordinary-owner HTTP/recovery tests; no real backend or secrets."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import holdout_assets as assets
import import_holdout_music as importer
from holdout_test_fixture import HoldoutFixture,FakeHTTP


class ImportTest(HoldoutFixture,unittest.TestCase):
    def setUp(self):self.prepare_fixture()

    def test_complete_import_and_idempotent_reverification_preserve_catalog(self):
        result=self.run_import();self.assertEqual(result['new_tracks'],20)
        self.assertEqual((self.client.uploads,self.client.metadata),(20,20));self.assertEqual(len(self.client.resources),60)
        path=self.output/'catalog.json';raw=path.read_bytes();catalog=json.loads(raw)
        self.assertEqual(len(catalog['tracks']),20);self.assertEqual(len(list((self.output/'audio').iterdir())),40)
        again=self.run_import();self.assertEqual(again['created_uploads'],0);self.assertEqual(again['created_metadata'],0)
        self.assertEqual(path.read_bytes(),raw);self.assertEqual((self.client.uploads,self.client.metadata),(20,20))
        self.assertIsNone(self.client.token)

    def test_response_lost_after_upload_or_metadata_recovers_without_duplicates(self):
        for phase in ['upload','metadata']:
            with self.subTest(phase=phase):
                self.client=FakeHTTP(self.owner,self.old_tracks,self.old_audio)
                self.output=self.output.parent/('fresh-'+phase)
                setattr(self.client,'lose_'+phase,True)
                with self.assertRaises(RuntimeError):self.run_import()
                self.assertFalse((self.output/'catalog.json').exists());self.assertFalse((self.output/'import.lock').exists())
                self.run_import();self.assertEqual((self.client.uploads,self.client.metadata),(20,20))

    def test_wrong_role_or_owner_rejected_before_upload(self):
        for field,value in [('role','ADMIN'),('owner',999)]:
            old=getattr(self.client,field);setattr(self.client,field,value)
            with self.assertRaises(ValueError):self.run_import()
            setattr(self.client,field,old)
        self.assertEqual((self.client.uploads,self.client.metadata),(0,0))

    def test_missing_original40_is_never_recreated(self):
        self.client.resources.pop()
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual((self.client.uploads,self.client.metadata),(0,0))

    def test_bad_original_media_stops_before_any_new_mutation(self):
        self.client.bad_media='full'
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual((self.client.uploads,self.client.metadata),(0,0))

    def test_bad_new_media_keeps_recoverable_state_without_catalog(self):
        self.client.bad_new_media='full'
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual((self.client.uploads,self.client.metadata),(1,1));self.assertFalse((self.output/'catalog.json').exists())
        self.client.bad_new_media=None;self.run_import();self.assertEqual((self.client.uploads,self.client.metadata),(20,20))

    def test_bad_actual_decode_occurs_before_any_HTTP(self):
        def wrong(path):raise ValueError('synthetic actual EOF failure')
        with self.assertRaises(ValueError):self.run_import(decode=wrong)
        self.assertEqual(self.client.calls,[])

    def test_unknown_tampered_ledger_and_duplicate_identity_are_rejected(self):
        self.client.lose_upload=True
        with self.assertRaises(RuntimeError):self.run_import()
        path=self.output/'import-ledger.json';ledger=json.loads(path.read_text());ledger['tracks']['unknown']={}
        path.write_text(json.dumps(ledger));path.chmod(0o600);self.client.calls.clear()
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(self.client.calls,[])

    def test_old_file_identity_in_ledger_is_rejected_before_HTTP(self):
        self.run_import();path=self.output/'import-ledger.json';ledger=json.loads(path.read_text())
        first=next(iter(ledger['tracks'].values()));first['fileId']=self.old_tracks[0]['fileId']
        path.write_text(json.dumps(ledger));path.chmod(0o600);self.client.calls.clear()
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(self.client.calls,[])

    def test_wrong_upload_owner_cannot_reach_metadata_or_catalog(self):
        original=self.client.api
        def wrong(method,url,*args,**kwargs):
            result=original(method,url,*args,**kwargs)
            if url=='/file/upload':return {**result,'ownerUserId':999}
            return result
        with patch.object(self.client,'api',side_effect=wrong),self.assertRaises(ValueError):self.run_import()
        self.assertEqual(self.client.metadata,0);self.assertFalse((self.output/'catalog.json').exists())

    def test_existing_lock_unknown_artifact_and_escaped_output_are_preserved(self):
        self.output.mkdir(mode=0o700);lock=self.output/'import.lock';lock.write_bytes(b'active synthetic owner')
        with self.assertRaises(FileExistsError):self.run_import()
        self.assertEqual(lock.read_bytes(),b'active synthetic owner');lock.unlink()
        sentinel=self.output/'unrelated';sentinel.write_bytes(b'keep')
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(sentinel.read_bytes(),b'keep')
        with self.assertRaises(ValueError):self.run_import(output_state=self.root/'outside')
        self.assertEqual(self.client.calls,[])

    def test_restrictive_umask_still_produces_readable_private_files(self):
        prior=os.umask(0o777)
        try:self.run_import()
        finally:os.umask(prior)
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        for p in self.output.rglob('*'):self.assertEqual(p.stat().st_mode&0o777,0o700 if p.is_dir() else 0o600)
        json.loads((self.output/'catalog.json').read_text())

    def test_changed_completed_catalog_or_copy_is_not_silently_overwritten(self):
        self.run_import();path=self.output/'catalog.json';path.write_bytes(path.read_bytes()+b'changed')
        self.client.calls.clear()
        with self.assertRaises(ValueError):self.run_import()
        self.assertTrue(path.read_bytes().endswith(b'changed'));self.assertEqual(self.client.calls,[])

    def test_nonpending_new_resource_is_not_approved_or_overwritten(self):
        self.run_import()
        for row in self.client.resources:
            if row['musicid']>=2000:row['approvalStatus']='approved'
        before=self.client.metadata
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(self.client.metadata,before)

    def test_symlink_output_and_ledger_cannot_be_followed(self):
        link=self.output;link.symlink_to(self.fixture.state,target_is_directory=True)
        with self.assertRaises(ValueError):self.run_import()
        link.unlink();self.output.mkdir(mode=0o700)
        original=self.output.parent/'keep';original.write_bytes(b'keep');(self.output/'import-ledger.json').symlink_to(original)
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(original.read_bytes(),b'keep')


if __name__=='__main__':unittest.main()

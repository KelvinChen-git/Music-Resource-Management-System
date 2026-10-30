"""Full synthetic221 frame/source binding tests, with fake media/EOF only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest

import holdout_assets as assets
from holdout_test_fixture import HoldoutFixture


class AssetTest(HoldoutFixture,unittest.TestCase):
    def setUp(self):self.prepare_fixture()

    def test_rebuilds_complete_v2_sources_and_baseline40(self):
        context=self.source_context(decode=self.fixture.decode);owner,old=assets.baseline40(context)
        self.assertEqual(owner,str(self.owner));self.assertEqual(len(old),40);self.assertEqual(len(context['tracks']),20)
        self.assertEqual({t['source_provider'] for t in context['tracks']},{assets.source.PROVIDER,assets.source.MUSICBOX})

    def test_missing_or_wrong_binding_pin_is_rejected(self):
        for pin in [None,'0'*64]:
            with self.assertRaises(ValueError):assets.checked_source(self.binding_path,pin)

    def test_binding_path_escape_and_unknown_fields_are_rejected(self):
        for mutation in ['escape','extra']:
            original=deepcopy(self.binding)
            if mutation=='escape':self.binding['frame']['path']='../escaped.json'
            else:self.binding['new_labels']={}
            self.save_binding()
            with self.assertRaises(ValueError):self.source_context()
            self.binding=original;self.save_binding()

    def test_changed_audio_or_proof_is_rejected(self):
        t=self.manifest['tracks'][0]
        for field in ['audio_filename','download_proof_filename']:
            path=self.manifest_path.parent/t[field];raw=path.read_bytes();path.write_bytes(raw+b'changed')
            with self.assertRaises(ValueError):self.source_context()
            path.write_bytes(raw)

    def test_symlink_and_hardlinked_sources_are_rejected(self):
        t=self.manifest['tracks'][0];path=self.manifest_path.parent/t['audio_filename'];original=path.read_bytes()
        other=path.parent/'independent-copy';other.write_bytes(original);path.unlink();path.symlink_to(other)
        with self.assertRaises(ValueError):self.source_context()
        path.unlink();path.write_bytes(original);other.unlink();os.link(path,other)
        with self.assertRaises(ValueError):self.source_context()

    def test_resigned_source_title_group_or_time_cannot_bypass_frozen_frame(self):
        original=deepcopy(self.manifest)
        for field,value in [('title','changed source'),('creator_group','forged group'),('duration_ms',1)]:
            self.manifest=deepcopy(original);self.manifest['tracks'][0][field]=value;self.resign_manifest()
            with self.assertRaises(ValueError):self.source_context()

    def test_actual_PCM_differences_fail_before_HTTP(self):
        def wrong(path):return {**self.fixture.decode(path),'pcm_sha256':'0'*64}
        with self.assertRaises(ValueError):self.source_context(decode=wrong)
        self.assertEqual(self.client.calls,[])

    def test_changed_original40_and_license_equivalence(self):
        context=self.source_context();assets.baseline40(context)
        t=self.old_tracks[0];path=self.root/self.binding['development40']['audio_root']/(t['sourceProvider']+'-'+t['sourceId']+'.mp3')
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaises(ValueError):assets.baseline40(self.source_context())

    def test_imported_catalog_rejects_ID_content_source_and_copy_mutations(self):
        result=self.run_import();path=self.output/'catalog.json';catalog=json.loads(path.read_text());context=self.source_context()
        assets.validate_catalog(catalog,context,self.output/'audio')
        for field,value in [('track_id',catalog['tracks'][1]['track_id']),('content_sha256','0'*64),('source_id','unknown')]:
            changed=deepcopy(catalog);changed['tracks'][0][field]=value
            with self.assertRaises(ValueError):assets.validate_catalog(changed,self.source_context(),self.output/'audio')
        copy=self.output/'audio'/catalog['tracks'][0]['asset_filename'];copy.write_bytes(copy.read_bytes()+b'changed')
        with self.assertRaises(ValueError):assets.checked_catalog(path,result['catalog_sha256'],self.binding_path,self.binding_sha,self.output/'audio')

    def test_catalog_owner_and_complete20_cannot_change(self):
        self.run_import();catalog=json.loads((self.output/'catalog.json').read_text())
        for field,value in [('owner_user_id','999'),('tracks',catalog['tracks'][:-1]),('split','development')]:
            changed=deepcopy(catalog);changed[field]=value
            with self.assertRaises(ValueError):assets.validate_catalog(changed,self.source_context(),self.output/'audio')


if __name__=='__main__':unittest.main()

"""Synthetic development runner tests; no real decoder/CLAP/network/qrels."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import checkpoint_preflight as driver


class PreflightTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.local = self.root / '.local'
        self.local.mkdir(); self.output = self.local / 'run'
        self.checkpoint = self.local / 'synthetic.pt'; self.checkpoint.write_bytes(b'synthetic only')
        self.assets = [{'source_provider': 'jamendo', 'track_id': str(i+1), 'source_id': str(i+100),
            'asset_filename': str(i+100)+'.mp3'} for i in range(20)]
        fixture = json.loads((driver.SOURCE/'exploratory_queries.json').read_text())
        self.queries = [q for q in fixture['queries'] if q['query_id'] in driver.QUERY_IDS]
        self.sdk = SimpleNamespace(tokenize=Mock(return_value={'input_ids': [1]*12}),
            get_audio_embedding_from_data=Mock(side_effect=lambda b, use_tensor: self.vectors(len(b))),
            get_text_embedding=Mock(side_effect=lambda t, use_tensor: self.vectors(len(t))))
        self.input_calls = 0
        self.changed = False
        self.model = {'id': 'B', 'checkpoint_sha256': '1'*64}
        self.decoded = []
        def decode(path):
            self.decoded.append(path.name)
            return np.zeros(48000, np.float32), {'format': 'MP3', 'source_frames': 48000,
                'source_sample_rate_hz': 48000, 'source_channels': 2, 'sample_rate_hz': 48000,
                'decoded_samples': 48000, 'duration_ms': 1000}
        patches = [(driver, 'code_state', Mock(return_value={'code_sha':'a'*40,'working_tree_dirty':False,'source_hashes':{}})),
            (driver, 'inputs', Mock(side_effect=self.inputs)), (driver, 'checked_checkpoint', Mock(return_value=(self.checkpoint, '1'*64))),
            (driver, 'load_checkpoint', Mock(return_value=(self.sdk, self.model))), (driver, 'decode_mono', Mock(side_effect=decode)),
            (driver.torch, 'manual_seed', Mock()), (driver.torch, 'set_num_threads', Mock()),
            (driver.torch, 'set_num_interop_threads', Mock())]
        for module, name, value in patches:
            item = patch.object(module, name, value); item.start(); self.addCleanup(item.stop)
        import research_probe
        item = patch.object(research_probe, 'ROOT', self.root); item.start(); self.addCleanup(item.stop)
        item = patch.object(research_probe.subprocess, 'run', return_value=SimpleNamespace(returncode=0))
        item.start(); self.addCleanup(item.stop)

    @staticmethod
    def vectors(count):
        v=np.zeros((count,512),np.float32);v[:,0]=1;return v

    def inputs(self,*args):
        self.input_calls+=1
        values=deepcopy(self.assets)
        if self.changed and self.input_calls>1:values[0]['track_id']='999'
        return values,deepcopy(self.queries),{'synthetic':'1'*64}

    def run_probe(self):
        with redirect_stdout(io.StringIO()):
            return driver.run(catalog=self.local/'catalog.json', catalog_sha256='1'*64,
                audio_root=self.local, checkpoint=self.checkpoint, model_id='B', output=self.output)

    def test_complete_fresh_run_has_five_queries_and_numeric_ties(self):
        report=self.run_probe()
        self.assertEqual(report['counts'],{'tracks':20,'segments':20,'text_queries':5,'reference_queries':0,'new_test_tracks_or_queries':0})
        self.assertEqual(len(self.decoded),20)
        with np.load(self.output/'vectors.npz',allow_pickle=False) as v:
            self.assertEqual(v['whole_vectors'].shape,(20,512))
            self.assertEqual(v['text_vectors'].shape,(5,512))
            np.testing.assert_allclose(np.linalg.norm(v['segment_vectors'],axis=1),1)
        ranks=json.loads((self.output/'rankings.json').read_text())
        for q in ranks['queries']:
            for mode in ['whole_track','segment']:self.assertEqual([r['track_id'] for r in q[mode]],['1','2','3','4','5'])
        self.assertTrue(all((self.output/n).stat().st_mode&0o777==0o600 for n in report['artifact_sha256']))
        self.assertFalse((self.output/'failure.json').exists())

    def test_shipped_legacy_fixture_pin_and_selected_intents(self):
        path = driver.SOURCE / 'exploratory_queries.json'
        self.assertEqual(driver.file_hash(path), driver.QUERY_SHA)
        self.assertEqual([q['query_id'] for q in self.queries], driver.QUERY_IDS)

    def test_dirty_source_fails_before_model_load(self):
        driver.code_state.side_effect=ValueError('dirty source')
        with self.assertRaises(ValueError):self.run_probe()
        driver.load_checkpoint.assert_not_called()
        self.assertTrue((self.output/'failure.json').is_file())

    def test_bad_catalog_pin_fails_before_model_load(self):
        driver.inputs.side_effect=ValueError('original catalog pin mismatch')
        with self.assertRaises(ValueError):self.run_probe()
        driver.load_checkpoint.assert_not_called()

    def test_new_test_catalog_cannot_enter_real_input_adapter(self):
        adapter = driver.inputs
        adapter.side_effect = None
        # The original function is inspected through its unpatched module globals in a separate load.
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('unpatched_preflight_fixture',driver.SOURCE/'checkpoint_preflight.py')
        module=module_from_spec(spec);spec.loader.exec_module(module)
        path=self.local/'new-test.json';path.write_text('{"split":"independent_test_source_only"}')
        with self.assertRaises(ValueError):module.inputs(path,'0'*64,self.local)

    def test_checkpoint_rejected_before_loader(self):
        driver.checked_checkpoint.side_effect=ValueError('checkpoint pin')
        with self.assertRaises(ValueError):self.run_probe()
        driver.load_checkpoint.assert_not_called()

    def test_existing_success_refuses_without_model_or_artifact_changes(self):
        self.run_probe();before={p.name:p.read_bytes() for p in self.output.iterdir() if p.is_file()}
        calls=driver.load_checkpoint.call_count
        with self.assertRaises(FileExistsError):self.run_probe()
        self.assertEqual(driver.load_checkpoint.call_count,calls)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir() if p.is_file()})

    def test_partial_failure_stays_failed_and_no_resume(self):
        driver.decode_mono.side_effect=RuntimeError('synthetic decoder failure')
        with self.assertRaises(RuntimeError):self.run_probe()
        self.assertTrue((self.output/'failure.json').exists());self.assertFalse((self.output/'report.json').exists())
        with self.assertRaises(FileExistsError):self.run_probe()

    def test_input_mutation_prevents_passed_report(self):
        self.changed=True
        with self.assertRaises(ValueError):self.run_probe()
        self.assertFalse((self.output/'report.json').exists())

    def test_invalid_embedding_or_truncated_query_never_passes(self):
        for kind in ['dimension','nan','zero','token']:
            with self.subTest(kind=kind):
                self.output=self.local/kind
                self.sdk.get_audio_embedding_from_data.side_effect=lambda b,use_tensor:self.vectors(len(b))
                self.sdk.tokenize.return_value={'input_ids':[1]*12}
                if kind=='dimension':self.sdk.get_audio_embedding_from_data.side_effect=lambda b,use_tensor:np.ones((len(b),256),np.float32)
                if kind=='nan':self.sdk.get_audio_embedding_from_data.side_effect=lambda b,use_tensor:np.full((len(b),512),np.nan,np.float32)
                if kind=='zero':self.sdk.get_audio_embedding_from_data.side_effect=lambda b,use_tensor:np.zeros((len(b),512),np.float32)
                if kind=='token':self.sdk.tokenize.return_value={'input_ids':[1]*78}
                with self.assertRaises(ValueError):self.run_probe()
                self.assertFalse((self.output/'report.json').exists())

    def test_private_cache_and_umask_are_restored(self):
        before=os.environ.get('NUMBA_CACHE_DIR');mask=os.umask(0o077);os.umask(mask)
        self.run_probe()
        self.assertEqual(os.environ.get('NUMBA_CACHE_DIR'),before)
        observed=os.umask(mask);os.umask(observed);self.assertEqual(observed,mask)
        self.assertEqual((self.output/'decode-cache').stat().st_mode&0o777,0o700)


if __name__ == '__main__':unittest.main()

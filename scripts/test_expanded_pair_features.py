"""Synthetic expanded grouping, fulltext integrity and explicit split boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import holdout_contract as h
import interval_feature_cache as intervals
import expanded_pair_features as m
import device_calibration as calibration
import test_interval_feature_cache as old_fixture
from run_expanded_caption_training import validate_config, initialize


class ExpandedPairsTests(unittest.TestCase):
    def inputs(self):
        old, allowed, corpus = old_fixture.IntervalFeaturesTest().inputs()
        base, *_ = intervals.plan(old, allowed, corpus)
        new = []; candidates = []
        for i in range(76):
            split = 'train' if i < 63 else 'validation'; tid = str(100+i)
            group = (str(i) if i < 6 else 'n'+str(i if i < 56 else i-50)) if i < 63 else 'v'+str((i-63)%12)
            n = (6 if i < 15 else 5) if split == 'train' else (3 if i < 74 else 2)
            new.append({'id': tid, 'split': split, 'creator_component': group, 'source_track_id': 'track_'+tid,
                        'audio_sha256': 'a'*64, 'pcm_sha256': 'b'*64, 'decode': {'decoded_samples': 180*48000}})
            candidates.extend({'id': tid, 'start_time': j*30., 'end_time': (j+1)*30., 'caption': 'Complete synthetic original '+tid,
                               'label_source': 'model_generated', 'raw_line_sha256': 'c'*64} for j in range(n))
        return old, {'candidates': candidates}, allowed, corpus, {'records': new, 'failures': []}, base

    def plan(self): return m.combine(*self.inputs())

    def test_expanded_counts_preserved_rows_and_recomputed_weights(self):
        rows, texts, unique, _, counts, reused = self.plan()
        self.assertEqual(counts, m.COUNTS); self.assertEqual((len(rows), len(texts), len(unique), len(reused)), (599,599,1797,232))
        for split,n in [('train',100),('validation',20)]:
            subset = [r for r in rows if r['split'] == split]
            self.assertAlmostEqual(sum(r['weight'] for r in subset),1)
            for tid in {r['id'] for r in subset}: self.assertAlmostEqual(sum(r['weight'] for r in subset if r['id'] == tid),1/n)
        self.assertNotEqual(rows[0]['weight'], self.inputs()[-1][0]['weight'])

    def test_modified_old_metadata_rejected(self):
        args = self.inputs(); args[-1][0]['caption_sha256'] = 'x'*64
        with self.assertRaises(ValueError): m.combine(*args)

    def test_old_new_recording_overlap_or_failed_new_record_rejected(self):
        for mode in ['overlap','failure','missing']:
            args = self.inputs()
            if mode == 'overlap': args[4]['records'][0]['id'] = '1'
            elif mode == 'failure': args[4]['failures'] = [{'technical': True}]
            else: args[4]['records'].pop()
            with self.subTest(mode=mode),self.assertRaises(ValueError): m.combine(*args)

    def test_new_creator_cross_split_rejected(self):
        args=self.inputs();args[4]['records'][-1]['creator_component']='0'
        with self.assertRaises(ValueError):m.combine(*args)

    def test_all_full_tokens_required_and_overflow_not_filtered(self):
        lengths=[178]*599;proof=[{'untruncated_tokens':178,'encoded_nonpad_tokens':178}for _ in lengths]
        m.proof_complete(proof,lengths)
        for mode in ['overflow','truncation','drop']:
            a,b=copy.deepcopy(proof),lengths.copy()
            if mode=='overflow':a[-1]={'untruncated_tokens':257,'encoded_nonpad_tokens':257};b[-1]=257
            elif mode=='truncation':a[-1]['encoded_nonpad_tokens']=77
            else:a.pop();b.pop()
            with self.subTest(mode=mode),self.assertRaises(ValueError):m.proof_complete(a,b)

    def test_wrong_window_id_start_index_or_order_rejected(self):
        for mode in ['id','index','order']:
            rows,_,unique,*_=self.plan()
            if mode=='id':unique[0]['id']='99999'
            elif mode=='index':rows[0]['window_indices'][0]=len(unique)
            else:unique.reverse()
            with self.subTest(mode=mode),self.assertRaises(ValueError):m.validate_windows(rows,unique)

    def fixture(self, directory):
        rows,_,unique,*_=self.plan();vec=lambda n:np.tile(np.eye(512)[0],(n,1))
        np.savez(directory/'features.npz',audio=vec(599),text=vec(599),windows=vec(1797),weights=np.array([r['weight']for r in rows]))
        ctx={'device':'mps','environment':{},'model_sha256':'a'*64,'input_sha256':'b'*64,'recipe_sha256':'c'*64,'source_sha256':{'builder':'d'*64}}
        key=calibration.cache_key(**ctx)
        report={'status':'passed','ready_cache_written':True,'truncated_captions':0,'cache_key_sha256':key,'reused_intervals_exact':232,
                'vector_parity':{name:{'status':'passed'}for name in ['new_windows','new_interval_audio','new_text256']}}
        (directory/'result.json').write_text(json.dumps(report));(directory/'token-proof.json').write_text(json.dumps([{'untruncated_tokens':10,'encoded_nonpad_tokens':10}for _ in rows]))
        return {'schema':'sonora-expanded-pair-feature-cache-v1','status':'ready_after_parity','device':'mps','model_sha256':'a'*64,
                'token_length':256,'recipe':intervals.RECIPE,'rows':rows,'unique_windows':unique,'token_lengths':[10]*599,
                'key_context':ctx,'cache_key_sha256':key,'result_sha256':h.file_hash(directory/'result.json'),
                'token_proof_sha256':h.file_hash(directory/'token-proof.json'),'feature_sha256':h.file_hash(directory/'features.npz')}

    def load(self, directory, meta, split='train', device='mps', model='a'*64):
        path=directory/'cache.json';path.write_text(json.dumps(meta))
        return m.ready_view(path,h.file_hash(path),expected_device=device,expected_model_sha256=model,split=split)

    def test_consumer_returns_only_explicit_split_without_encoder(self):
        with tempfile.TemporaryDirectory()as tmp:
            directory=Path(tmp).resolve();meta=self.fixture(directory)
            for split,n in [('train',539),('validation',60)]:
                view=self.load(directory,meta,split);self.assertEqual(view['audio'].shape,(n,512));self.assertEqual(view['text'].shape,(n,512));self.assertAlmostEqual(view['weights'].sum(),1)
                self.assertEqual(len(view['recording_ids']),n);self.assertNotIn('caption',view)

    def test_consumer_rejects_device_model_token_and_parity_mismatch(self):
        for mode in ['device','model','length','parity','sharedsplit']:
            with tempfile.TemporaryDirectory()as tmp:
                d=Path(tmp).resolve();meta=self.fixture(d)
                kw={}
                if mode=='device':kw['device']='cpu'
                elif mode=='model':kw['model']='f'*64
                elif mode=='length':meta['token_length']=77
                elif mode=='sharedsplit':kw['split']='all'
                else:
                    r=json.loads((d/'result.json').read_text());r['vector_parity']['new_windows']['status']='failed';(d/'result.json').write_text(json.dumps(r));meta['result_sha256']=h.file_hash(d/'result.json')
                with self.subTest(mode=mode),self.assertRaises(ValueError):self.load(d,meta,**kw)

    def test_consumer_rejects_changed_array_even_with_refreshed_file_pin(self):
        with tempfile.TemporaryDirectory()as tmp:
            d=Path(tmp).resolve();meta=self.fixture(d)
            with np.load(d/'features.npz')as f:values={k:f[k]for k in f.files}
            values['audio'][0]=np.eye(512)[1];np.savez(d/'features.npz',**values);meta['feature_sha256']=h.file_hash(d/'features.npz')
            with self.assertRaises(ValueError):self.load(d,meta)

    def test_frozen_method_rejects_search_prefix_and_auto_fallback(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-058-training-config.json').read_text());validate_config(cfg)
        for key,value in [('alpha',.1),('token_length',77),('candidate_fits',2),('automatic_fallback',True),('test_inputs',1)]:
            bad=copy.deepcopy(cfg);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_config(bad)

    def test_existing_stage_claim_blocks_new_output_before_input_or_encoder_work(self):
        c={'task_directory':'.local/a/mus058'}
        with patch('run_expanded_caption_training.h.assets.document',return_value=c),patch('run_expanded_caption_training.validate_config'),patch('run_expanded_caption_training.subprocess.check_output',return_value=b''),patch('pathlib.Path.exists',return_value=True),patch('run_expanded_caption_training.h.private_output')as output:
            with self.assertRaisesRegex(ValueError,'Stage already attempted'):initialize('config','a'*64,h.ROOT/'.local/a/mus058/other','encode')
            output.assert_not_called()


if __name__=='__main__':unittest.main()

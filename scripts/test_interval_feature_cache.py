"""Synthetic interval bounds, grouping, integrity and explicit consumer boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import interval_feature_cache as d
import device_calibration as calibration
import holdout_contract as h
from build_interval_feature_cache import validate_config


class IntervalFeaturesTest(unittest.TestCase):
    def inputs(self):
        candidates = []; allowed = []; proofs = []
        for i in range(44):
            split = 'train' if i < 37 else 'validation'; tid = str(i+1)
            n = (6 if i < 24 else 5) if split == 'train' else (4 if i < 39 else 3)
            allowed.append({'id': tid, 'split': split, 'creator_component': str(i if i < 33 or i >= 37 else i-33),
                            'audio_sha256': 'a'*64, 'pcm_sha256': 'b'*64})
            proofs.append({'source_track_id': f'track_{i+1:07}', 'split': split, 'audio_sha256': 'a'*64,
                           'decode': {'pcm_sha256': 'b'*64, 'decoded_samples': 180*d.RATE}})
            candidates.extend({'id': tid, 'start_time': j*30., 'end_time': (j+1)*30., 'caption': f'Synthetic caption {i} {j}.',
                               'label_source': 'model_generated', 'raw_line_sha256': 'c'*64} for j in range(n))
        return {'label_source': 'model_generated', 'training_ready': False, 'candidates': candidates}, {'records': allowed}, {'tracks': proofs}

    def test_exact_15_30s_and_fractional_sample_boundaries(self):
        self.assertEqual(d.windows(30., 60., 60*d.RATE), (1440000, 2880000, [1440000,1920000,2400000]))
        self.assertEqual(d.windows(0., 15., 15*d.RATE)[2], [0,120000,240000])
        lo, hi, starts = d.windows(.00002,15.00002,16*d.RATE)
        self.assertEqual((lo,hi), (1,720001)); self.assertTrue(all(lo <= s and s+d.WINDOW <= hi for s in starts))

    def test_invalid_short_long_nonfinite_and_millisecond_EOF_rejected(self):
        for start,end in [(-1,20),(0,14.99),(0,30.001),(0,float('nan')),(float('inf'),30),(0,30.002),(True,20)]:
            with self.subTest(start=start,end=end), self.assertRaises(ValueError): d.windows(start,end,30*d.RATE)

    def test_fixed_counts_unique_window_references_and_raw_text(self):
        inputs = self.inputs(); rows,texts,unique,proofs,counts = d.plan(*inputs)
        self.assertEqual(counts,d.COUNTS); self.assertEqual(len(unique),696)
        self.assertEqual(texts,[r['caption'] for r in inputs[0]['candidates']]); self.assertNotIn('caption',rows[0])
        self.assertEqual(len(proofs),44)

    def test_weights_equal_per_recording_not_per_interval(self):
        rows,*_ = d.plan(*self.inputs())
        for split,n in [('train',37),('validation',7)]:
            subset=[r for r in rows if r['split']==split]
            self.assertAlmostEqual(sum(r['weight']for r in subset),1)
            for tid in {r['id']for r in subset}: self.assertAlmostEqual(sum(r['weight']for r in subset if r['id']==tid),1/n)
        self.assertNotEqual(rows[0]['weight'],rows[150]['weight'])

    def test_duplicate_overlap_and_generated_label_boundaries(self):
        for mode in ('duplicate','overlap','human'):
            inp=self.inputs(); records=inp[0]['candidates']
            if mode=='duplicate': records.append(copy.deepcopy(records[0]))
            elif mode=='overlap': records[1]['start_time']=20;records[1]['end_time']=50
            else: records[0]['label_source']='human'
            with self.subTest(mode=mode), self.assertRaises(ValueError): d.plan(*inp)

    def test_audio_PCM_or_split_mismatch_rejected(self):
        for key,value in [('audio_sha256','x'),('pcm_sha256','x'),('split','validation')]:
            inp=self.inputs();inp[1]['records'][0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): d.plan(*inp)

    def test_creator_cross_split_rejected(self):
        inp=self.inputs();inp[1]['records'][-1]['creator_component']='0'
        with self.assertRaises(ValueError):d.plan(*inp)

    def test_controls_are_deterministic_train_and_distinct_components(self):
        rows,*_=d.plan(*self.inputs());ix=d.control_indices(rows,'fixed')
        self.assertEqual(ix,d.control_indices(copy.deepcopy(rows),'fixed'));self.assertEqual(len(ix),3)
        self.assertTrue(all(rows[i]['split']=='train'for i in ix));self.assertEqual(len({rows[i]['creator_component']for i in ix}),3)

    def test_token_truncation_is_disclosed_not_filtered(self):
        r=d.token_summary([12,77,78,100]);self.assertEqual(r['captions'],4);self.assertEqual(r['truncated_at_77'],2)
        with self.assertRaises(ValueError):d.token_summary([0])

    def fixture(self,root):
        rows,_,unique,_,_=d.plan(*self.inputs());vec=lambda n:np.tile(np.eye(512)[0],(n,1))
        np.savez(root/'features.npz',audio=vec(232),text=vec(232),windows=vec(696),weights=np.array([r['weight']for r in rows]))
        ctx={'device':'mps','environment':{'device':'mps'},'model_sha256':'a'*64,'input_sha256':'b'*64,'recipe_sha256':'c'*64,'source_sha256':{'builder':'d'*64}}
        key=calibration.cache_key(**ctx);result={'status':'passed','ready_cache_written':True,'cache_key_sha256':key,'tokenization':d.token_summary([10]*232),
                                              'CPU_control_intervals':3,'vector_parity':{k:{'status':'passed'}for k in ('windows','interval_audio','caption_text')}}
        (root/'result.json').write_text(json.dumps(result))
        return {'schema':'sonora-interval-feature-cache-v1','status':'ready_for_bounded_pilot','device':'mps','model_sha256':'a'*64,
                'key_context':ctx,'cache_key_sha256':key,'recipe':d.RECIPE,'rows':rows,'unique_windows':unique,'token_lengths':[10]*232,
                'control_indices':d.control_indices(rows,'MUS-053-fixed-train-controls-v1'),
                'feature_sha256':h.file_hash(root/'features.npz'),'result_sha256':h.file_hash(root/'result.json')}

    def load(self,root,meta,split='train',device='mps',model='a'*64):
        path=root/'cache.json';path.write_text(json.dumps(meta))
        return d.ready_view(path,h.file_hash(path),expected_device=device,expected_model_sha256=model,split=split)

    def test_split_reader_returns_only_selected_vectors_groups_weights(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta=self.fixture(root)
            for split,count in [('train',209),('validation',23)]:
                r=self.load(root,meta,split);self.assertEqual(r['audio'].shape,(count,512));self.assertEqual(r['text'].shape,(count,512))
                self.assertAlmostEqual(r['weights'].sum(),1);self.assertNotIn('caption',r)
            self.assertFalse(set(self.load(root,meta)['recording_ids'])&set(self.load(root,meta,'validation')['recording_ids']))

    def test_wrong_device_model_split_status_or_key_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta=self.fixture(root)
            for kwargs in ({'device':'cpu'},{'model':'f'*64},{'split':'auto'}):
                with self.assertRaises(ValueError):self.load(root,meta,**kwargs)
            for key,value in [('status','partial'),('recipe','whole_song'),('cache_key_sha256','0'*64)]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):self.load(root,bad)

    def test_hash_report_control_and_window_binding_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta=self.fixture(root)
            for key,value in [('feature_sha256','0'*64),('result_sha256','0'*64),('control_indices',[0,1,2])]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):self.load(root,bad)
            bad=copy.deepcopy(meta);bad['rows'][0]['window_indices']=[1,2,3]
            with self.assertRaises(ValueError):self.load(root,bad)

    def test_consumer_bad_weight_or_nonunit_vector_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta=self.fixture(root);bad=copy.deepcopy(meta);bad['rows'][0]['weight']=float('inf')
            with self.assertRaises(ValueError):self.load(root,bad)
            with np.load(root/'features.npz')as f: arrays={k:f[k]for k in f.files}
            arrays['audio'][0]=0;np.savez(root/'features.npz',**arrays);meta['feature_sha256']=h.file_hash(root/'features.npz')
            with self.assertRaises(ValueError):self.load(root,meta)

    def test_builder_rejects_relaxed_config_before_execution(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-053-feature-config.json').read_text());validate_config(cfg)
        for key,value in [('fit_runs',1),('automatic_fallback',True),('audio_batch',4),('atol_vector_maxabs',.01),('text_policy','rewrite')]:
            bad=copy.deepcopy(cfg);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_config(bad)


if __name__=='__main__':unittest.main()

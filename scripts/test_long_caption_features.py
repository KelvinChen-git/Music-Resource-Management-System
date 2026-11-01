"""Explicit lengths, nontruncation proof, train-only controls and overlay integrity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import holdout_contract as h
import long_caption_features as m
import interval_feature_cache as base
import device_calibration as calibration
from run_long_caption_control import validate_config
import test_interval_feature_cache as fixtures


class LongCaptionTest(unittest.TestCase):
    def test_original_caption_order_and_hash_preserved(self):
        inputs=fixtures.IntervalFeaturesTest().inputs();rows,*_=base.plan(*inputs)
        self.assertEqual(len(m.captions_for(inputs[0],rows)),232)
        changed=copy.deepcopy(inputs[0]);changed['candidates'][0]['caption']='rewritten'
        with self.assertRaises(ValueError):m.captions_for(changed,rows)

    def test_controls_cover_short_long_six_distinct_train_creators(self):
        rows,*_=base.plan(*fixtures.IntervalFeaturesTest().inputs());lengths=[17 if i%2 else 85 for i in range(232)]
        r=m.controls(rows,lengths);ix=r['short']+r['long'];self.assertEqual(r,m.controls(rows,lengths))
        self.assertEqual(len(ix),6);self.assertEqual(len({rows[i]['creator_component']for i in ix}),6)
        self.assertTrue(all(rows[i]['split']=='train'for i in ix));self.assertTrue(all(lengths[i]>77 for i in r['long']))

    def test_missing_long_controls_or_excess_length_fail_closed(self):
        rows,*_=base.plan(*fixtures.IntervalFeaturesTest().inputs())
        for lengths in ([10]*232,[300]*232,[10]*231):
            with self.assertRaises(ValueError):m.controls(rows,lengths)

    def token_fixture(self):
        return {'input_ids':np.array([[0,8,9,2,1,1],[0,7,2,1,1,1]]),
                'attention_mask':np.array([[1,1,1,1,0,0],[1,1,1,0,0,0]])},[[0,8,9,2],[0,7,2]]

    def test_nonpadding_ids_equal_complete_original_sequence(self):
        encoded,raw=self.token_fixture();proof=m.token_proof(encoded,raw,6)
        self.assertEqual([r['encoded_nonpad_tokens']for r in proof],[4,3]);self.assertEqual(len(proof[0]['input_ids_sha256']),64)

    def test_changed_tokens_wrong_padding_or_mask_and_truncation_rejected(self):
        for case in ['ids','pad','mask','float','truncated']:
            encoded,raw=self.token_fixture()
            if case=='ids':encoded['input_ids'][0,1]=99
            elif case=='pad':encoded['input_ids'][0,-1]=9
            elif case=='mask':encoded['attention_mask'][0,-1]=1
            elif case=='float':encoded['input_ids']=encoded['input_ids'].astype(float)
            else:raw[0]=[0,8,9,10,11,12,2]
            with self.subTest(case=case),self.assertRaises(ValueError):m.token_proof(encoded,raw,6)

    def fixture(self,root):
        original=root/'base';original.mkdir();meta=fixtures.IntervalFeaturesTest().fixture(original)
        lengths=[17 if i%2 else 85 for i in range(232)];meta['token_lengths']=lengths
        result=json.loads((original/'result.json').read_text());result['tokenization']=base.token_summary(lengths)
        (original/'result.json').write_text(json.dumps(result));meta['result_sha256']=h.file_hash(original/'result.json')
        (original/'cache.json').write_text(json.dumps(meta));base_sha=h.file_hash(original/'cache.json')
        overlay=root/'overlay';overlay.mkdir();np.savez(overlay/'features.npz',text256=np.tile(np.eye(512)[0],(232,1)))
        ctx={'device':'mps','environment':{},'model_sha256':'a'*64,'input_sha256':'b'*64,'recipe_sha256':'c'*64,'source_sha256':{'driver':'d'*64}}
        key=calibration.cache_key(**ctx);result={'status':'passed','ready_cache_written':True,'truncated_captions':0,'captions':232,
                                              'cache_key_sha256':key,'vector_parity':{name:{'status':'passed'}for name in m.PARITY}}
        (overlay/'result.json').write_text(json.dumps(result))
        out={'schema':'sonora-long-caption-text-cache-v1','status':'ready_after_parity','policy':m.POLICY,'token_length':256,
             'base_cache_sha256':base_sha,'device':'mps','model_sha256':'a'*64,'key_context':ctx,'cache_key_sha256':key,
             'rows_sha256':h.digest(h.canonical(meta['rows'])),'token_lengths':lengths,'control_indices':m.controls(meta['rows'],lengths),
             'result_sha256':h.file_hash(overlay/'result.json'),'feature_sha256':h.file_hash(overlay/'features.npz')}
        return out,base_sha

    def load(self,root,meta,base_sha,split='train',device='mps',model='a'*64):
        path=root/'overlay/cache.json';path.write_text(json.dumps(meta))
        return m.ready_view(base_cache=root/'base/cache.json',base_sha256=base_sha,text_cache=path,text_sha256=h.file_hash(path),
                            expected_device=device,expected_model_sha256=model,split=split)

    def test_split_reader_uses_same_audio_weights_and_explicit_new_text(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta,sha=self.fixture(root)
            for split,n in [('train',209),('validation',23)]:
                r=self.load(root,meta,sha,split);self.assertEqual(r['text'].shape,r['text77'].shape);self.assertEqual(r['audio'].shape,(n,512))
                self.assertEqual(r['token_length'],256);self.assertAlmostEqual(r['weights'].sum(),1)

    def test_wrong_base_device_model_split_length_status_key_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta,sha=self.fixture(root)
            for kwargs in [{'device':'cpu'},{'model':'f'*64},{'split':'auto'}]:
                with self.assertRaises(ValueError):self.load(root,meta,sha,**kwargs)
            for key,value in [('base_cache_sha256','0'*64),('token_length',77),('status','partial'),('cache_key_sha256','0'*64)]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):self.load(root,bad,sha)

    def test_hash_row_or_control_changes_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta,sha=self.fixture(root)
            for key,value in [('feature_sha256','0'*64),('result_sha256','0'*64),('rows_sha256','0'*64),('control_indices',{'short':[0,1,2],'long':[3,4,5]})]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):self.load(root,bad,sha)

    def test_nonunit_new_text_or_failed_parity_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();meta,sha=self.fixture(root)
            np.savez(root/'overlay/features.npz',text256=np.zeros((232,512)));meta['feature_sha256']=h.file_hash(root/'overlay/features.npz')
            with self.assertRaises(ValueError):self.load(root,meta,sha)
            report=json.loads((root/'overlay/result.json').read_text());report['status']='failed';(root/'overlay/result.json').write_text(json.dumps(report));meta['result_sha256']=h.file_hash(root/'overlay/result.json')
            with self.assertRaises(ValueError):self.load(root,meta,sha)

    def test_fixed_protocol_rejects_extra_fit_encoding_and_query_confounds(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-055-control-config.json').read_text());validate_config(cfg)
        for key,value in [('token_length',512),('alpha',.1),('candidate_fits',2),('new_audio_encodes',1),('human_query_text_features','reencode'),('hyperparameter_search',True)]:
            bad=copy.deepcopy(cfg);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_config(bad)


if __name__=='__main__':unittest.main()

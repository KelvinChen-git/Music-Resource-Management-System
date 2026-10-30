"""Synthetic runner/preflight/failure controls, no real checkpoints, recordings or qrels."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

import holdout_contract as hc
import holdout_runner as runner


class FakeSDK:
    tokens=10
    bad=None
    def __init__(self):self.text_calls=[];self.audio_calls=[]
    def tokenize(self,text,truncation):
        assert truncation is False
        return {'input_ids':[0]*self.tokens}
    def get_audio_embedding_from_data(self,windows,use_tensor):
        self.audio_calls.append(windows.copy())
        return self.vectors(len(windows))
    def get_text_embedding(self,texts,use_tensor):
        self.text_calls.append(list(texts));return self.vectors(len(texts))
    def vectors(self,n):
        out=np.zeros((n,512),dtype=np.float32);out[:,0]=1
        if self.bad=='dimension':return out[:,:511]
        if self.bad=='finite':out[:,0]=np.nan
        if self.bad=='norm':out[:,0]=2
        return out


class RunnerTest(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve()
        (self.root/'.local').mkdir();subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'.gitignore').write_text('.local/\n')
        p=patch.object(hc,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        self.queries=[{'query_key':f'holdout-{i:02}','text_en':f'Synthetic new request {i}'} for i in range(1,9)]
        self.data={'queries':self.queries,'tracks':[{'track_id':str(i),'title':'Drum drum tone' if i==1 else 'Tone'} for i in range(1,21)],
            'arguments':{'audio_root':str(self.root/'.local')},'input_sha256':{},'source_dataset_sha256':'c'*64,
            'config':{'configurations':['A-whole','A-segment','B-whole','B-segment','title-tfidf']}}
        self.receipt={'models':{m:{'pin':{'path':m}} for m in ['A','B']}}
        self.out=self.root/'.local/output'

    def checked(self,*args,**kwargs):return self.receipt,deepcopy(self.data)

    def fake_encode(self,m,path,data,audio_root,target):
        folder=target/m;folder.mkdir(mode=0o700)
        hc.write_json(folder/'synthetic-vectors.json',{'synthetic':True})
        return {mode:[{'query_id':q['query_key'],'ranking':[{'track_id':str(i),'score':0.0} for i in range(1,21)]} for q in self.queries]
                for mode in ['whole','segment']}

    def run_fake(self,encoder=None):
        with patch.object(hc,'source_state',return_value={'code_sha':'synthetic'}),patch.object(hc,'checked_freeze',side_effect=self.checked),\
            patch.object(runner,'configure'),patch.object(runner,'encode_model',side_effect=encoder or self.fake_encode):
            return runner.run(freeze='synthetic-freeze',freeze_sha256='a'*64,output=self.out)

    def test_lexical_logTF_IDF_cosine_matches_independent_hand_calculation(self):
        scores=runner.lexical_scores(['drum drum tone','tone'],['drum','unseen','ＴＯＮＥ'])
        idf=np.log(3/2)+1;d=np.array([(1+np.log(2))*idf,1.0]);d/=np.linalg.norm(d)
        np.testing.assert_allclose(scores,[[d[0],0],[0,0],[d[1],1]],atol=1e-12)

    def test_lexical_empty_titles_and_queries_are_zero_without_nan(self):
        np.testing.assert_array_equal(runner.lexical_scores(['中文','♪'],['drum','']),np.zeros((2,2)))

    def test_preflight_uses_only_synthetic_audio_and_generic_old_text(self):
        sdk=FakeSDK()
        with patch('checkpoint_model.load_checkpoint',return_value=(sdk,{'strict_missing':[],'strict_unexpected':[]})),\
            patch.object(hc,'checkpoint_pin',return_value={'sha256':'synthetic'}):
            result=runner.frozen_preflight('synthetic','A',self.queries)
        self.assertEqual(sdk.text_calls,[['A sustained low electronic tone.']])
        self.assertEqual(sdk.audio_calls[0].shape,(1,480000));self.assertEqual(np.count_nonzero(sdk.audio_calls[0][0,96000:]),0)
        self.assertEqual(result['audio_shape'],[1,512]);self.assertEqual(result['test_query_token_lengths'],[10]*8)

    def test_truncation_is_rejected_before_any_embedding(self):
        sdk=FakeSDK();sdk.tokens=78
        with patch('checkpoint_model.load_checkpoint',return_value=(sdk,{})):
            with self.assertRaises(ValueError):runner.frozen_preflight('synthetic','A',self.queries)
        self.assertEqual(sdk.text_calls,[]);self.assertEqual(sdk.audio_calls,[])

    def test_invalid_synthetic_dimension_finite_or_norm_rejected(self):
        for bad in ['dimension','finite','norm']:
            sdk=FakeSDK();sdk.bad=bad
            with patch('checkpoint_model.load_checkpoint',return_value=(sdk,{})):
                with self.assertRaises(ValueError):runner.frozen_preflight('synthetic','A',self.queries)

    def test_freeze_requires_clean_committed_source_and_preserves_failed_output(self):
        with patch.object(hc,'source_state',side_effect=ValueError('dirty source')):
            with self.assertRaises(ValueError):runner.freeze(output=self.out,checkpoint_a='A',checkpoint_b='B')
        self.assertTrue((self.out/'failure.json').is_file());self.assertFalse((self.out/'freeze.json').exists())
        with self.assertRaises(FileExistsError):runner.freeze(output=self.out,checkpoint_a='A',checkpoint_b='B')

    def test_freeze_persists_both_models_before_any_test_encoding(self):
        pins={m:{'path':m,'sha256':m*64} for m in ['A','B']}
        with patch.object(hc,'source_state',return_value={'code_sha':'synthetic'}),patch.object(hc,'snapshot',return_value=self.data),\
            patch.object(hc,'environment',return_value={'synthetic':True}),patch.object(runner,'configure'),\
            patch.object(hc,'checkpoint_pin',side_effect=lambda p,m:pins[m]),\
            patch.object(runner,'frozen_preflight',side_effect=lambda p,m,q:{'pin':pins[m]}),\
            patch.object(runner,'encode_model',side_effect=AssertionError('test encoding forbidden before G2')):
            result=runner.freeze(output=self.out,checkpoint_a='A',checkpoint_b='B')
        self.assertEqual(result['counts'],{'new_test_audio_encoded':0,'new_test_text_encoded':0,'qrels_opened':0})
        self.assertTrue((self.out/'freeze.json').is_file());self.assertEqual(set(result['models']),{'A','B'})

    def test_five_runs_commit_only_after_all_rankings_and_recheck(self):
        result=self.run_fake()
        self.assertEqual(len(result['ranking_sha256']),5)
        self.assertEqual(result['counts']['qrels_opened'],0)
        for name,h in result['ranking_sha256'].items():
            self.assertEqual(hc.file_hash(self.out/name),h)
            rows=json.loads((self.out/name).read_text())['queries']
            self.assertEqual(len(rows),8);self.assertTrue(all(len(q['ranking'])==20 for q in rows))
        # An unseen lexical query must retain every track in numeric-ID tie order.
        lexical=json.loads((self.out/'title-tfidf.json').read_text())
        self.assertEqual([r['track_id'] for r in lexical['queries'][0]['ranking']],[str(i) for i in range(1,21)])

    def test_partial_failed_run_keeps_prior_outputs_but_no_commitment(self):
        def encode(m,*args):
            if m=='B':raise ValueError('synthetic B failure')
            return self.fake_encode(m,*args)
        with self.assertRaises(ValueError):self.run_fake(encode)
        self.assertTrue((self.out/'A-whole.json').exists());self.assertTrue((self.out/'failure.json').exists())
        self.assertFalse((self.out/'all-runs-commitment.json').exists())

    def test_input_change_after_runs_prevents_success_commitment(self):
        calls=0
        def recheck(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls>1:raise ValueError('input changed')
            return self.checked()
        with patch.object(hc,'source_state',return_value={}),patch.object(hc,'checked_freeze',side_effect=recheck),\
            patch.object(runner,'configure'),patch.object(runner,'encode_model',side_effect=self.fake_encode):
            with self.assertRaises(ValueError):runner.run(freeze='synthetic',freeze_sha256='a'*64,output=self.out)
        self.assertFalse((self.out/'all-runs-commitment.json').exists())

    def test_actual_encoder_checks_PCM_and_has_separate512_vectors_and_full_rankings(self):
        sdk=FakeSDK();samples=np.zeros(48000*30,dtype=np.float32);info={'duration_ms':30000,'decoded_samples':len(samples)}
        tracks=[{'track_id':str(i),'asset_filename':str(i)+'.mp3','recorded_decode':{},**info,
                 'pcm_sha256':hc.digest(samples.astype('<f4').tobytes())} for i in range(1,21)]
        data={**self.data,'tracks':tracks};target=self.root/'.local/encoding';target.mkdir()
        with patch('checkpoint_model.load_checkpoint',return_value=(sdk,{})),\
            patch('research_corpus.decode_source_mono',return_value=(samples,info)):
            ranks=runner.encode_model('A','synthetic',data,target,target)
        self.assertEqual(len(ranks['whole']),8);self.assertEqual(len(ranks['segment'][0]['ranking']),20)
        with np.load(target/'A/vectors.npz') as vectors:
            self.assertEqual(vectors['whole_vectors'].shape,(20,512));self.assertEqual(vectors['text_vectors'].shape,(8,512))
        self.assertEqual(sdk.text_calls,[[q['text_en'] for q in self.queries]])
        tracks[0]['pcm_sha256']='0'*64
        with patch('checkpoint_model.load_checkpoint',return_value=(sdk,{})),patch('research_corpus.decode_source_mono',return_value=(samples,info)):
            with self.assertRaises(ValueError):runner.encode_model('B','synthetic',data,target,target)

    def test_checkpoint_pin_rejects_untrusted_file_before_model_load(self):
        f=self.root/'.local/untrusted.pt';f.write_bytes(b'untrusted')
        with self.assertRaises(ValueError):hc.checkpoint_pin(f,'A')

    def test_incomplete_or_tampered_G2_is_rejected_before_snapshot_or_model(self):
        p=self.root/'.local/freeze.json';hc.write_json(p,{'schema':'sonora-independent-runner-freeze-v1','status':'incomplete'})
        with self.assertRaises(ValueError):hc.checked_freeze(p,hc.file_hash(p))
        with self.assertRaises(ValueError):hc.checked_freeze(p,'0'*64)


if __name__=='__main__':unittest.main()

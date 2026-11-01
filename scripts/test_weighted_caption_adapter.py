"""Weighted optimum, recording duplication invariance and known-pair metric boundaries."""
import copy
import json
import unittest
import numpy as np
import holdout_contract as h
import weighted_caption_adapter as m
from tag_adapter import unit
from train_caption_adapter import validate_config


class CaptionAdapterTest(unittest.TestCase):
    def problem(self):
        rng=np.random.default_rng(54);x=unit(rng.normal(size=(5,3)));text=unit(rng.normal(size=(5,3)))
        ids=['a','a','a','b','c'];return x,text,m.recording_weights(ids),ids

    def test_dual_fit_matches_independent_primal_normal_equation(self):
        x,t,q,ids=self.problem();w,diag=m.fit(x,t,q,ids,1.)
        expected=np.linalg.solve(x.T@(q[:,None]*x)+np.eye(3),x.T@(q[:,None]*t)+np.eye(3))
        np.testing.assert_allclose(w,expected,atol=1e-14);self.assertLessEqual(diag['objective_after'],diag['objective_before'])
        self.assertTrue(diag['closed_form_optimum_verified']);self.assertLess(diag['normal_equation_max_abs_residual'],1e-12)

    def test_each_recording_has_equal_total_weight(self):
        _,_,q,ids=self.problem()
        for tid in set(ids):self.assertAlmostEqual(sum(v for v,i in zip(q,ids)if i==tid),1/3)

    def test_duplicate_all_intervals_of_one_recording_does_not_reweight_fit(self):
        x,t,q,ids=self.problem();w,_=m.fit(x,t,q,ids,1.)
        ix=[0,1,2,0,1,2,3,4];these=[ids[i]for i in ix]
        other,_=m.fit(x[ix],t[ix],m.recording_weights(these),these,1.)
        np.testing.assert_allclose(w,other,atol=1e-14)

    def test_zero_residual_retains_identity_and_single_pair_is_valid(self):
        x=np.array([[1.,0,0]]);w,d=m.fit(x,x,np.array([1.]),['a'],1.)
        np.testing.assert_array_equal(w,np.eye(3));self.assertEqual(d['objective_after'],0)

    def test_wrong_weights_nonunit_nonfinite_or_nonpositive_alpha_rejected(self):
        x,t,q,ids=self.problem()
        for values in [(x,t,np.ones(5)/5,ids,1.),(x*2,t,q,ids,1.),(x,t,q,ids,0.),(x,t,q,ids,float('nan')),
                       (x,t,np.full(5,np.nan),ids,1.),(x[:4],t,q,ids,1.)]:
            with self.assertRaises(ValueError):m.fit(*values)

    def test_identity_known_interval_and_recording_retrieval(self):
        r=m.validation_metrics(np.eye(4),np.eye(4),['a','a','b','b'],np.eye(4))
        for metric in r.values():self.assertEqual(metric['recording_macro']['MRR'],1.);self.assertEqual(metric['recording_macro']['R1'],1.)

    def test_ties_use_fixed_index_and_macro_is_by_recording(self):
        r=m.exact_interval_pairs(np.ones((3,3)),['a','a','b']);self.assertEqual(r['ranks'],[1,2,3])
        self.assertAlmostEqual(r['recording_macro']['MRR'],(.75+1/3)/2)
        self.assertNotEqual(r['recording_macro']['MRR'],r['query_macro']['MRR'])

    def test_malformed_pair_scores_rejected(self):
        for s in (np.ones((2,3)),np.full((2,2),np.nan)):
            with self.assertRaises(ValueError):m.exact_interval_pairs(s,['a','b'])

    def test_one_fixed_protocol_disallows_tuning_and_new_encodes(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-054-training-config.json').read_text());validate_config(cfg)
        for k,v in [('alpha',.1),('candidate_fits',2),('new_audio_or_model_encodes',1),('hyperparameter_search',True),('validation_used_for_selection',True),('text_target','rewrite')]:
            bad=copy.deepcopy(cfg);bad[k]=v
            with self.subTest(key=k),self.assertRaises(ValueError):validate_config(bad)


if __name__=='__main__':unittest.main()

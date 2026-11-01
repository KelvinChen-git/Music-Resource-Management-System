"""Normalized-loss derivative, invariance, stopping budget and full-text enforcement."""
import copy
import json
import unittest
import numpy as np
import holdout_contract as h
import cosine_caption_adapter as m
from tag_adapter import unit
from weighted_caption_adapter import recording_weights
from train_fulltext_cosine import validate_config, verify_fulltext


class CosineCaptionTest(unittest.TestCase):
    def inputs(self):
        rng=np.random.default_rng(56);x=unit(rng.normal(size=(5,3)));t=unit(rng.normal(size=(5,3)));ids=['a','a','a','b','c']
        return x,t,recording_weights(ids),ids

    def settings(self):
        return dict(alpha=1.,initial_step=1.,max_steps=200,max_backtracks=20,armijo=1e-4,backtrack_factor=.5,gradient_max_tol=1e-8,relative_loss_tol=1e-12)

    def test_gradient_matches_independent_central_finite_difference(self):
        x,t,q,_=self.inputs();w=np.eye(3)+np.random.default_rng(57).normal(size=(3,3))*.03
        loss,g,_=m.loss_gradient(x,t,q,w,1.);numerical=np.zeros((3,3));eps=1e-6
        def objective(a):
            z=x@a;z=z/np.sqrt(np.sum(z*z,axis=1))[:,None]
            return float(np.sum(q[:,None]*(z-t)**2)+np.sum((a-np.eye(3))**2))
        self.assertAlmostEqual(loss,objective(w))
        for i in range(3):
            for j in range(3):
                step=np.zeros((3,3));step[i,j]=eps;numerical[i,j]=(objective(w+step)-objective(w-step))/(2*eps)
        np.testing.assert_allclose(g,numerical,atol=4e-10)

    def test_data_loss_equals_twice_one_minus_paired_cosine(self):
        x,t,q,_=self.inputs();_,_,s=m.loss_gradient(x,t,q,np.eye(3),1.)
        self.assertAlmostEqual(s['data_loss'],2*(1-s['weighted_paired_cosine']))

    def test_mapping_scale_changes_penalty_but_not_normalized_data_loss(self):
        x,t,q,_=self.inputs();a=m.loss_gradient(x,t,q,np.eye(3),1.)[2];b=m.loss_gradient(x,t,q,np.eye(3)*2,1.)[2]
        self.assertAlmostEqual(a['data_loss'],b['data_loss']);self.assertGreater(b['identity_prior_penalty'],a['identity_prior_penalty'])

    def test_fit_is_monotonic_fixed_budget_and_finite(self):
        x,t,q,ids=self.inputs();w,d=m.fit(x,t,q,ids,**self.settings())
        self.assertTrue(np.isfinite(w).all());self.assertLess(d['objective_after'],d['objective_before'])
        self.assertTrue(all(b<=a for a,b in zip(d['loss_trace'],d['loss_trace'][1:])));self.assertLessEqual(d['steps'],200)
        self.assertFalse(d['global_optimum_claimed']);self.assertFalse(d['validation_used_for_stopping'])

    def test_recording_duplication_invariance(self):
        x,t,q,ids=self.inputs();w,_=m.fit(x,t,q,ids,**self.settings());ix=[0,1,2,0,1,2,3,4];newids=[ids[i]for i in ix]
        other,_=m.fit(x[ix],t[ix],recording_weights(newids),newids,**self.settings());np.testing.assert_allclose(w,other,atol=1e-12)

    def test_matching_pairs_retain_identity_without_steps(self):
        x,_,q,ids=self.inputs();w,d=m.fit(x,x,q,ids,**self.settings());np.testing.assert_array_equal(w,np.eye(3))
        self.assertEqual(d['steps'],0);self.assertEqual(d['stop_reason'],'gradient_tolerance')

    def test_step_limit_is_not_reported_as_stopping_tolerance(self):
        x,t,q,ids=self.inputs();cfg=self.settings();cfg.update(max_steps=1,gradient_max_tol=1e-30,relative_loss_tol=1e-30)
        _,d=m.fit(x,t,q,ids,**cfg);self.assertEqual(d['stop_reason'],'step_limit');self.assertFalse(d['training_stopping_tolerance_reached'])

    def test_exhausted_armijo_does_not_restart(self):
        x,t,q,ids=self.inputs();cfg=self.settings();cfg.update(initial_step=1e9,max_backtracks=1)
        with self.assertRaisesRegex(ValueError,'budget exhausted'):m.fit(x,t,q,ids,**cfg)

    def test_invalid_vectors_weights_and_optimizer_rejected(self):
        x,t,q,ids=self.inputs()
        for values in [(x*2,t,q,ids),(x,t,np.ones(5)/5,ids),(x,t,np.full(5,np.nan),ids)]:
            with self.assertRaises(ValueError):m.fit(*values,**self.settings())
        with self.assertRaises(ValueError):m.loss_gradient(x,t,q,np.zeros((3,3)),1.)
        for key,value in [('initial_step',float('nan')),('alpha',0),('max_steps',True)]:
            cfg=self.settings();cfg[key]=value
            with self.assertRaises(ValueError):m.fit(x,t,q,ids,**cfg)

    def test_complete_text_proof_rejects_overflow_truncation_or_missing_row(self):
        proof=[{'untruncated_tokens':178,'encoded_nonpad_tokens':178}for _ in range(232)];verify_fulltext(proof,[178]*232)
        for lengths,items in [([257]*232,proof),([178]*232,proof[:-1]),([178]*232,[{'untruncated_tokens':178,'encoded_nonpad_tokens':77}]*232)]:
            with self.assertRaises(ValueError):verify_fulltext(items,lengths)

    def test_fixed_protocol_prevents_text_fallback_or_validation_search(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-056-training-config.json').read_text());validate_config(cfg)
        for key,value in [('text_policy','prefix77'),('token_length',77),('alpha',.1),('max_steps',400),('candidate_fits',2),('validation_used_for_stopping_or_selection',True),('new_model_or_audio_encodes',1)]:
            bad=copy.deepcopy(cfg);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_config(bad)


if __name__=='__main__':unittest.main()

"""Hand-calculated centered targets, primal/dual agreement and one-fit guards."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import centered_residual_adapter as m
from weighted_caption_adapter import recording_weights, fit as ordinary_fit
from train_centered_residual import validate, run
import holdout_contract as h


class CenteredResidualTests(unittest.TestCase):
    def sample(self):
        x=np.eye(2)[[0,0,0,1,1]];text=np.tile([1.,0.],(5,1));ids=['a']*3+['b']*2
        return x,text,recording_weights(ids),ids

    def test_hand_calculated_recording_equal_mean_and_solution(self):
        w,mean,d=m.fit(*self.sample(),1.)
        np.testing.assert_allclose(mean,[.5,-.5],atol=1e-15)
        np.testing.assert_allclose(w,[[5/6,1/6],[1/6,5/6]],atol=1e-15)
        self.assertAlmostEqual(d['objective_before'],.5);self.assertAlmostEqual(d['objective_after'],1/3)
        self.assertLess(d['normal_equation_max_abs_residual'],1e-15)

    def test_constant_shared_residual_produces_identity(self):
        x=np.tile([1.,0.],(4,1));t=np.tile([0.,1.],(4,1));ids=['a','a','b','b']
        w,mean,d=m.fit(x,t,recording_weights(ids),ids,1.)
        self.assertTrue(np.array_equal(w,np.eye(2)));self.assertTrue(np.array_equal(mean,[-1.,1.]))
        self.assertEqual(d['objective_after'],0);self.assertEqual(d['parameter_delta_frobenius'],0)

    def test_zero_residual_mean_reduces_to_original_weighted_ridge(self):
        x=np.eye(2)[[0,0,1,1]];t=x[:,::-1].copy();ids=['a','a','b','b'];q=recording_weights(ids)
        a,mean,_=m.fit(x,t,q,ids,1.);b,_=ordinary_fit(x,t,q,ids,1.)
        self.assertTrue(np.array_equal(mean,np.zeros(2)));np.testing.assert_allclose(a,b,atol=1e-15)

    def test_independent_dual_solution_matches_primal(self):
        rng=np.random.default_rng(60);x=rng.normal(size=(9,4));x/=np.linalg.norm(x,axis=1,keepdims=True)
        t=rng.normal(size=(9,4));t/=np.linalg.norm(t,axis=1,keepdims=True);ids=['a']*2+['b']*3+['c']*4;q=recording_weights(ids)
        w,mean,_=m.fit(x,t,q,ids,1.);z=np.sqrt(q)[:,None]*x;target=np.sqrt(q)[:,None]*(t-x-mean)
        expected=np.eye(4)+z.T@np.linalg.solve(z@z.T+np.eye(9),target)
        np.testing.assert_allclose(w,expected,atol=1e-14)

    def test_normal_equation_and_zero_centered_mean(self):
        x,t,q,ids=self.sample();w,mean,d=m.fit(x,t,q,ids,.1);y=t-x-mean
        np.testing.assert_allclose(q@y,0,atol=1e-15)
        np.testing.assert_allclose(x.T@(q[:,None]*(x@(w-np.eye(2))-y))+.1*(w-np.eye(2)),0,atol=1e-15)
        self.assertLess(d['objective_after'],d['objective_before'])

    def test_input_vectors_and_weights_remain_unchanged(self):
        args=self.sample();before=[a.copy()if isinstance(a,np.ndarray)else a.copy()for a in args]
        m.fit(*args,1.)
        for a,b in zip(args,before):np.testing.assert_array_equal(a,b)

    def test_single_interval_recording_is_not_removed(self):
        x=np.eye(2)[[0,0,1]];t=x[::-1].copy();ids=['a','a','b'];w,_,d=m.fit(x,t,recording_weights(ids),ids,1.)
        self.assertEqual(d['fit_recordings'],2);self.assertEqual(d['fit_intervals'],3);self.assertTrue(np.isfinite(w).all())

    def test_interval_uniform_weights_rejected_for_unequal_recordings(self):
        x,t,_,ids=self.sample()
        with self.assertRaises(ValueError):m.fit(x,t,np.ones(5)/5,ids,1.)

    def test_nonfinite_nonunit_or_misaligned_inputs_rejected(self):
        for mode in ['nan','unit','shape','weights']:
            x,t,q,ids=self.sample()
            if mode=='nan':t[0,0]=np.nan
            elif mode=='unit':x[0]*=2
            elif mode=='shape':t=t[:-1]
            else:q[0]=-1
            with self.subTest(mode=mode),self.assertRaises(ValueError):m.fit(x,t,q,ids,1.)

    def test_invalid_alpha_rejected(self):
        for alpha in [0,-1,float('nan'),float('inf'),True]:
            with self.subTest(alpha=alpha),self.assertRaises(ValueError):m.fit(*self.sample(),alpha)

    def test_config_prevents_validation_centering_search_or_text_prefix(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-060-training-config.json').read_text());validate(cfg)
        for key,value in [('alpha',.5),('validation_used_for_centering_or_selection',True),('candidate_fits',2),('token_length',77),('label_edits',1)]:
            c=copy.deepcopy(cfg);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(c)

    def test_persistent_claim_rejects_new_output_before_fitting(self):
        with patch('train_centered_residual.h.assets.document',return_value={'task_directory':'.local/a/mus060'}),patch('train_centered_residual.validate'),patch('train_centered_residual.subprocess.check_output',return_value=b''),patch('pathlib.Path.exists',return_value=True),patch('train_centered_residual.h.private_output')as output:
            with self.assertRaisesRegex(ValueError,'already attempted'):run(config='config',config_sha256='a'*64,output=h.ROOT/'.local/a/mus060/other')
            output.assert_not_called()


if __name__=='__main__':unittest.main()

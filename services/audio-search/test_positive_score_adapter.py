"""Numerical gradient and masked normalized training properties, no real labels or models."""
import unittest
import numpy as np
import positive_score_adapter as p


class PositiveScoreTest(unittest.TestCase):
    def inputs(self):
        rng = np.random.default_rng(4)
        return rng.normal(size=(4, 3)), rng.normal(size=(5, 3)), [[0], [1, 2], [0, 3, 4], [2]]

    def settings(self):
        return dict(margin=.05, alpha=.01, initial_step=1., max_steps=20, max_backtracks=20,
                    armijo=1e-4, backtrack_factor=.5, gradient_max_tol=1e-10, relative_loss_tol=1e-14)

    def test_analytic_gradient_matches_all_finite_difference_components(self):
        x, tags, ids = self.inputs(); x, tags, mask, target = p.problem(x, tags, ids, .05)
        w = np.eye(3)+np.arange(9).reshape(3, 3)*.01
        _, gradient, _ = p.loss_gradient(x, tags, mask, target, w, .01)
        numerical = np.zeros_like(w); eps = 1e-6
        for i in range(3):
            for j in range(3):
                plus = w.copy(); minus = w.copy(); plus[i,j] += eps; minus[i,j] -= eps
                numerical[i,j] = (p.loss_gradient(x,tags,mask,target,plus,.01)[0]-p.loss_gradient(x,tags,mask,target,minus,.01)[0])/(2*eps)
        np.testing.assert_allclose(gradient, numerical, atol=2e-9)

    def test_unobserved_prototypes_have_zero_effect(self):
        x, tags, ids = self.inputs(); a = p.problem(x, tags, ids, .05)
        b = p.problem(x, np.vstack([tags, [10., -2., 1.]]), ids, .05)
        loss1, grad1, _ = p.loss_gradient(*a, np.eye(3), .01)
        loss2, grad2, _ = p.loss_gradient(*b, np.eye(3), .01)
        self.assertAlmostEqual(loss1, loss2); np.testing.assert_allclose(grad1, grad2, atol=1e-15)
        self.assertEqual(b[2][:,-1].sum(), 0)

    def test_each_track_weight_is_one_despite_different_positive_counts(self):
        x, tags, ids = self.inputs(); _, _, mask, _ = p.problem(x, tags, ids, .05)
        np.testing.assert_allclose(mask.sum(axis=1), 1)
        self.assertEqual(mask[2, 0], 1/3)

    def test_targets_frozen_to_identity_and_cap_at_one(self):
        x, tags, mask, target = p.problem(np.eye(2), np.eye(2), [[0], [0]], .05)
        self.assertEqual(target[0,0], 1.); self.assertEqual(target[1,0], .05)
        self.assertEqual(mask[0,1], 0.)

    def test_data_loss_cannot_be_reduced_by_only_scaling_audio_norm(self):
        x, tags, ids = self.inputs(); args = p.problem(x,tags,ids,.05); w = np.eye(3)+.1
        _, _, first = p.loss_gradient(*args,w,.01); _, _, scaled = p.loss_gradient(*args,w*3,.01)
        self.assertAlmostEqual(first['data_loss'], scaled['data_loss'])

    def test_fit_monotonic_and_improves_training_objective(self):
        x, tags, ids = self.inputs(); w, diag = p.fit(x,tags,ids,**self.settings())
        self.assertLess(diag['objective_after'], diag['objective_before'])
        self.assertTrue(all(b<=a for a,b in zip(diag['loss_trace'],diag['loss_trace'][1:])))
        self.assertEqual(w.shape,(3,3)); self.assertFalse(diag['validation_used_for_early_stopping'])

    def test_deterministic_and_duplicate_rows_do_not_change_mean_objective(self):
        x, tags, ids = self.inputs(); a, _ = p.fit(x,tags,ids,**self.settings()); b, _ = p.fit(x,tags,ids,**self.settings())
        np.testing.assert_array_equal(a,b)
        c, _ = p.fit(np.repeat(x,2,axis=0),tags,[z for v in ids for z in (v,v)],**self.settings())
        np.testing.assert_allclose(a,c,atol=1e-12)

    def test_invalid_positive_rows_or_nonfinite_inputs_rejected(self):
        x, tags, ids = self.inputs()
        for invalid in ([[],[1],[2],[3]], [[0,0],[1],[2],[3]], [[9],[1],[2],[3]]):
            with self.assertRaises(ValueError): p.problem(x,tags,invalid,.05)
        with self.assertRaises(ValueError): p.problem(x*np.nan,tags,ids,.05)

    def test_zero_mapped_vector_is_refused(self):
        x,tags,ids = self.inputs(); args = p.problem(x,tags,ids,.05)
        with self.assertRaises(ValueError): p.loss_gradient(*args,np.zeros((3,3)),.01)

    def test_backtracking_is_bounded_and_retains_monotonicity(self):
        x,tags,ids = self.inputs(); settings=self.settings();settings.update(alpha=10.,initial_step=100.)
        _, diag=p.fit(x,tags,ids,**settings)
        self.assertLess(max(diag['accepted_step_sizes']),100.)
        self.assertLessEqual(diag['steps'],20);self.assertLess(diag['objective_after'],diag['objective_before'])


if __name__=='__main__':unittest.main()

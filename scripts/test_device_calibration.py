"""Synthetic acceptance/device policy checks; never emulates a GPU run."""
import unittest
import numpy as np
import device_calibration as d


class DeviceCalibrationTest(unittest.TestCase):
    def policy(self):
        return {'audio_windows': 9, 'audio_tracks': 3, 'text_prompts': 2, 'dimension': 3,
                'atol_vector_maxabs': 1e-4, 'atol_cosine_distance': 1e-4,
                'atol_score_maxabs': 1e-4, 'stable_order_score_gap': 2e-4}

    def data(self):
        return np.repeat(np.eye(3), 3, axis=0), np.array([[1., 0., 0.], [0., 1., 0.]])

    def test_identical_features_pass_and_near_ties_are_disclosed(self):
        a, t = self.data(); r = d.compare(a, t, a, t, self.policy())
        self.assertEqual(r['status'], 'passed')
        self.assertEqual(r['modes']['whole']['stable_pairs'], 4)
        self.assertEqual(r['modes']['whole']['near_tie_pairs'], 2)
        self.assertEqual(r['modes']['segment']['stable_pair_flips'], 0)

    def test_changed_unit_vectors_fail_without_widening_tolerance(self):
        a, t = self.data(); z = a.copy(); z[[0, 3]] = z[[3, 0]]
        self.assertEqual(d.compare(a, t, z, t, self.policy())['status'], 'failed')

    def test_nonfinite_wrong_shape_and_nonunit_rejected(self):
        a, t = self.data()
        for bad in (a[:8], a*2, np.full_like(a, np.nan)):
            with self.assertRaises(ValueError): d.compare(a, t, bad, t, self.policy())

    def test_stable_order_flip_fails_even_with_relaxed_vector_threshold(self):
        a, t = self.data(); cfg = self.policy(); cfg['atol_vector_maxabs'] = 2; cfg['atol_cosine_distance'] = 2
        cfg['atol_score_maxabs'] = 2
        z = np.repeat(np.eye(3)[[1, 0, 2]], 3, axis=0)
        r = d.compare(a, t, z, t, cfg)
        self.assertGreater(r['modes']['whole']['stable_pair_flips'], 0)
        self.assertEqual(r['status'], 'failed')

    def test_near_tie_order_is_not_claimed_exact(self):
        a = np.repeat(np.array([[1., 0., 0.]]), 9, axis=0); t = np.array([[1., 0., 0.], [0., 1., 0.]])
        r = d.compare(a, t, a, t, self.policy())
        self.assertEqual(r['modes']['whole']['stable_pairs'], 0)
        self.assertEqual(r['modes']['whole']['near_tie_pairs'], 6)

    def test_explicit_device_required(self):
        for name in ('auto', 'cuda', 'mps:1'):
            with self.assertRaises(ValueError): d.device_status(name, {'torch_available': True})

    def test_missing_cuda_or_torch_is_blocked_not_cpu_fallback(self):
        self.assertEqual(d.device_status('cpu', {})['status'], 'blocked')
        r = d.device_status('cuda:0', {'torch_available': True, 'cuda_build': None, 'cuda_available': False, 'cuda_count': 0})
        self.assertEqual(r['device'], 'cuda:0'); self.assertEqual(r['status'], 'blocked')
        self.assertEqual(d.device_status('cpu', {'torch_available': True})['status'], 'ready')

    def test_mps_cpu_fallback_is_rejected(self):
        with self.assertRaises(ValueError): d.device_status('mps', {'torch_available': True, 'mps_available': True}, mps_fallback=True)
        self.assertEqual(d.device_status('mps', {'torch_available': True, 'mps_available': True})['status'], 'ready')

    def test_device_environment_and_source_separate_cache_keys(self):
        args = {'device': 'cpu', 'environment': {'torch': '2.6'}, 'model_sha256': 'a'*64,
                'input_sha256': 'b'*64, 'recipe_sha256': 'c'*64, 'source_sha256': {'driver': 'd'*64}}
        cpu = d.cache_key(**args)
        self.assertNotEqual(cpu, d.cache_key(**{**args, 'device': 'mps'}))
        self.assertNotEqual(cpu, d.cache_key(**{**args, 'environment': {'torch': 'other'}}))
        self.assertNotEqual(cpu, d.cache_key(**{**args, 'source_sha256': {'driver': 'e'*64}}))
        self.assertEqual(cpu, d.cache_key(**args))


    def test_binary_bundle_streams_above_old_json_ceiling(self):
        from calibrate_encoder_device import check_bound_files
        from pathlib import Path
        import tempfile, hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve()/'inputs.npz'; raw = b'x'*(17*1024*1024); p.write_bytes(raw)
            check_bound_files({p: hashlib.sha256(raw).hexdigest()})
            with self.assertRaises(ValueError): check_bound_files({p: '0'*64})

    def test_bundle_symlink_is_not_followed(self):
        from calibrate_encoder_device import check_bound_files
        from pathlib import Path
        import tempfile, hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); p = root/'data.npz'; p.write_bytes(b'fixture')
            link = root/'link.npz'; link.symlink_to(p)
            with self.assertRaises(ValueError): check_bound_files({link: hashlib.sha256(b'fixture').hexdigest()})

    def test_cache_rejects_unpinned_input(self):
        with self.assertRaises(ValueError):
            d.cache_key(device='cpu', environment={}, model_sha256='a'*64, input_sha256='bad',
                        recipe_sha256='c'*64, source_sha256={})


if __name__ == '__main__': unittest.main()

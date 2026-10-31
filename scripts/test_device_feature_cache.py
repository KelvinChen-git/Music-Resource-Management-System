"""Synthetic typed-cache consumer and full-pool numerical acceptance boundaries."""
from pathlib import Path
import tempfile
import json
import hashlib
import unittest
import numpy as np
import device_feature_cache as d
import device_calibration as calibration
from build_device_feature_cache import compare_retrieval


class FeatureCacheTest(unittest.TestCase):
    def policy(self):
        return {'atol_vector_maxabs': 1e-4, 'atol_cosine_distance': 1e-4,
                'atol_score_maxabs': 1e-4, 'stable_order_score_gap': 2e-4, 'metric_atol': 1e-12}

    def test_vector_and_score_identity(self):
        a = np.eye(3); self.assertEqual(d.vector_parity(a, a, self.policy())['status'], 'passed')
        r = d.score_parity([[.8, .4, .2]], [[.8, .4, .2]], self.policy())
        self.assertEqual(r['stable_pairs'], 3); self.assertEqual(r['stable_pair_flips'], 0)

    def test_stable_flip_fails_near_tie_is_disclosed(self):
        r = d.score_parity([[.8, .4, .400001]], [[.8, .400001, .4]], self.policy())
        self.assertEqual(r['status'], 'passed'); self.assertEqual(r['near_tie_pairs'], 1)
        self.assertEqual(r['queries_with_any_rank_change'], 1)
        self.assertEqual(d.score_parity([[.8, .4]], [[.4, .8]], self.policy())['status'], 'failed')

    def test_bad_vectors_scores_rejected(self):
        for x in (np.zeros((2, 3)), np.full((2, 3), np.nan)):
            with self.assertRaises(ValueError): d.vector_parity(x, x, self.policy())
        with self.assertRaises(ValueError): d.score_parity([[np.nan]], [[0]], self.policy())

    def fixture(self, root):
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        unit = lambda n: np.tile(np.eye(512)[0], (n, 1))
        np.savez(root/'features.npz', train_fullsong=unit(100), validation_fullsong=unit(20),
                 retrieval_first120=unit(140), prototypes=unit(183), texts=unit(24))
        rows = [{'source_track_id': f'{i:07}', 'split': 'train' if i < 100 else 'validation' if i < 120 else 'caption_dev',
                 'positive_indices': [0]} for i in range(140)]
        context = {'device': 'mps', 'environment': {'device': 'mps'}, 'model_sha256': 'a'*64,
                   'input_sha256': 'b'*64, 'recipe_sha256': 'c'*64, 'source_sha256': {'driver': 'd'*64}}
        key = calibration.cache_key(**context)
        result = {'status': 'passed', 'ready_cache_written': True, 'cache_key_sha256': key}
        (root/'result.json').write_text(json.dumps(result))
        views = {name: {'npz_key': k, 'recipe': recipe, 'row_indices': [i for i, r in enumerate(rows) if split is None or r['split'] == split]}
                 for name, (k, recipe, split, count) in d.VIEWS.items()}
        meta = {'schema': 'sonora-typed-device-feature-cache-v1', 'status': 'ready_after_parity', 'device': 'mps',
                'model_sha256': 'a'*64, 'key_context': context, 'cache_key_sha256': key, 'feature_sha256': sha(root/'features.npz'),
                'parity_report_sha256': sha(root/'result.json'), 'views': views, 'rows': rows,
                'query_tracks': [f'{i:07}' for i in range(120, 140)]+['0000120']*4}
        return meta

    def load(self, root, meta, view='tag_training', device='mps', model='a'*64):
        path = root/'cache.json'; path.write_text(json.dumps(meta))
        return d.ready_view(path, hashlib.sha256(path.read_bytes()).hexdigest(), expected_device=device,
                            expected_model_sha256=model, view=view)

    def test_three_views_return_separate_rows_no_dev_text_in_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root)
            for view, count in [('tag_training', 100), ('tag_validation', 20), ('caption_retrieval', 140)]:
                r = self.load(root, meta, view); self.assertEqual(r['features'].shape, (count, 512))
                self.assertEqual('texts' in r, view == 'caption_retrieval')
            self.assertEqual(self.load(root, meta)['source_track_ids'][-1], '0000099')

    def test_wrong_device_model_or_implicit_view_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root)
            for kwargs in ({'device': 'cpu'}, {'model': 'f'*64}, {'view': 'auto'}):
                with self.assertRaises(ValueError): self.load(root, meta, **kwargs)

    def test_partial_cache_or_failed_report_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root); meta['status'] = 'partial'
            with self.assertRaises(ValueError): self.load(root, meta)
            meta['status'] = 'ready_after_parity'; (root/'result.json').write_text('{}')
            with self.assertRaises(ValueError): self.load(root, meta)

    def test_view_recipe_or_cross_split_row_swap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root)
            meta['views']['tag_training']['recipe'] = 'first120_first_mid_last10s'
            with self.assertRaises(ValueError): self.load(root, meta)
            meta = self.fixture(root); meta['views']['tag_training']['row_indices'][0] = 120
            with self.assertRaises(ValueError): self.load(root, meta)

    def test_changed_feature_hash_or_tag_index_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root); meta['feature_sha256'] = '0'*64
            with self.assertRaises(ValueError): self.load(root, meta)
            meta = self.fixture(root); meta['rows'][0]['positive_indices'] = [183]
            with self.assertRaises(ValueError): self.load(root, meta)

    def test_manifest_hash_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); meta = self.fixture(root); path = root/'cache.json'; path.write_text(json.dumps(meta))
            with self.assertRaises(ValueError): d.ready_view(path, '0'*64, expected_device='mps', expected_model_sha256='a'*64, view='tag_training')

    def test_two_pools_modes_metric_parity(self):
        x = np.eye(3); rows = [{'source_track_id': str(i), 'split': 'caption_dev' if i == 0 else 'train'} for i in range(3)]
        r = compare_retrieval(x, x, x, x, x[:1], x[:1], [[0], [1], [2]], [[0], [1], [2]],
                              rows, ['0'], {'identity': np.eye(3)}, self.policy())
        for pool in r.values():
            for value in pool['identity'].values(): self.assertEqual(value['status'], 'passed')


if __name__ == '__main__': unittest.main()

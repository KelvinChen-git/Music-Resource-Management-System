"""Synthetic expanded-pool metrics and source binding; no model/audio/network."""
import copy
import unittest
import numpy as np
import expanded_caption_metrics as m
from diagnose_expanded_caption import validate_rows, evaluate


class ExpandedMetricsTest(unittest.TestCase):
    def test_distractors_need_no_queries_and_change_known_pair_rank(self):
        r = m.paired([[6, 5, 4, 3, 2, 1]], ['f'], list('abcdef'))
        self.assertEqual(r['recordings'], 1)
        self.assertEqual(r['unqueried_candidates'], 5)
        self.assertEqual(r['recording_macro'], {'R1': 0., 'R5': 0., 'MRR': 1/6})

    def test_multiple_captions_weight_recordings_equally(self):
        r = m.paired([[2, 1, 0]]*3 + [[2, 1, 0]], list('aaab'), list('abc'))
        self.assertEqual(r['recording_macro']['MRR'], .75)
        self.assertEqual(r['query_macro']['MRR'], .875)

    def test_tie_order_is_id_based_and_independent_of_candidate_order(self):
        a = m.paired([[0, 0, 0]], ['b'], list('abc'))
        b = m.paired([[0, 0, 0]], ['b'], list('cba'))
        self.assertEqual(a, b)
        self.assertEqual(a['recording_macro']['MRR'], .5)

    def test_nonfinite_duplicates_and_absent_positives_rejected(self):
        for scores, query, ids in [([[np.nan]], ['a'], ['a']), ([[1, 0]], ['a'], ['a', 'a']),
                                    ([[1, 0]], ['c'], ['a', 'b']), ([], [], [])]:
            with self.assertRaises(ValueError): m.paired(scores, query, ids)

    def test_bootstrap_groups_recordings_and_all_three_metrics(self):
        baseline = m.paired([[3, 2, 1], [2, 3, 1]], ['a', 'b'], list('abc'))
        candidate = m.paired([[2, 3, 1], [2, 3, 1]], ['a', 'b'], list('abc'))
        d = m.deltas(candidate, baseline, 2000, 7)
        self.assertEqual(d, m.deltas(candidate, baseline, 2000, 7))
        self.assertEqual(d['MRR']['mean_delta'], -.25)
        self.assertEqual(d['R1']['losses'], 1)
        self.assertEqual(d['R5']['ties'], 2)

    def test_bootstrap_rejects_changed_positive_set(self):
        a = m.paired([[1]], ['a'], ['a']); b = m.paired([[1]], ['b'], ['b'])
        with self.assertRaises(ValueError): m.deltas(a, b, 10, 3)

    def test_geometry_formula_matches_explicit_off_diagonal_cosines(self):
        x = np.random.default_rng(6).normal(size=(8, 3))
        z = x/np.linalg.norm(x, axis=1, keepdims=True)
        direct = np.mean((z @ z.T)[~np.eye(8, dtype=bool)])
        self.assertAlmostEqual(m.mean_pair_cosine(x), direct)
        self.assertAlmostEqual(m.mean_pair_cosine(np.ones((8, 3))), 1)

    def test_caption_cosine_averages_inside_recording_first(self):
        value = m.paired_cosine_mean([[1, 0]]*3 + [[0, 1]], [[1, 0], [1, 0]], list('aaab'), list('ab'))
        self.assertEqual(value, .5)
        with self.assertRaises(ValueError): m.paired_cosine_mean([[1, 0]], [[1, 0]], ['a'], ['b'])

    def test_evaluate_pools_and_segment_map_order(self):
        whole = np.array([[1, 0], [0, 1], [1, 1]], dtype=float)
        whole /= np.linalg.norm(whole, axis=1, keepdims=True)
        windows = np.array([[1, 0], [0, 1], [0, 1], [1, 0], [1, 1]], dtype=float)
        text = np.array([[1., 0.]])
        models = {'identity': np.eye(2), 'adapter': np.array([[1, .3], [.1, 1]])}
        r, d = evaluate(whole, windows, [[0, 1], [2, 3], [4]], text, list('abc'),
                        ['caption_dev', 'train', 'validation'], ['a'], models,
                        {'bootstrap_iterations': 20, 'bootstrap_seed': 3})
        self.assertEqual(r['dev20']['identity']['whole']['candidates'], 1)
        self.assertEqual(r['expanded140']['identity']['whole']['candidates'], 3)
        np.testing.assert_equal(r['expanded140']['identity']['segment']['recording_macro']['MRR'], 1)
        self.assertEqual(set(d['expanded140']['adapter']), {'whole', 'segment'})


class BoundRowsTest(unittest.TestCase):
    def fixture(self):
        rows = [{'split': 'train' if i < 100 else 'validation' if i < 120 else 'caption_dev',
                 'source_track_id': str(i), 'audio_sha256': 'audio'+str(i), 'pcm_sha256': 'pcm'+str(i)}
                for i in range(140)]
        corpus = {'tracks': [{**r, 'decode': {'pcm_sha256': r['pcm_sha256']}} for r in rows]}
        meta = {'rows': rows, 'query_tracks': [str(i) for i in range(120, 140)]+['120']*4,
                'query_text_sha256': ['p']*24}
        return meta, corpus

    def test_all_sources_match_and_only_original_dev_is_queried(self):
        meta, corpus = self.fixture()
        self.assertEqual(len(validate_rows(meta, corpus)), 140)
        meta['query_tracks'][0] = '0'
        with self.assertRaises(ValueError): validate_rows(meta, corpus)

    def test_cross_split_or_content_swap_is_rejected(self):
        meta, corpus = self.fixture()
        corpus['tracks'][0]['split'] = 'caption_dev'
        with self.assertRaises(ValueError): validate_rows(meta, corpus)
        meta, corpus = self.fixture(); corpus['tracks'][0]['decode']['pcm_sha256'] = 'changed'
        with self.assertRaises(ValueError): validate_rows(meta, corpus)

    def test_duplicate_recording_cannot_preserve_row_count(self):
        meta, corpus = self.fixture(); meta['rows'][1] = copy.deepcopy(meta['rows'][0])
        with self.assertRaises(ValueError): validate_rows(meta, corpus)


if __name__ == '__main__': unittest.main()

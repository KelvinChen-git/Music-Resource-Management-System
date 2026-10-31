"""Synthetic metrics and custody gates; no real qrels, models or audio."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import holdout_evaluate as ev


class EvaluationTest(unittest.TestCase):
    def fixture(self, grade=0):
        labels = {q: {str(t): grade for t in range(1, 21)} for q in ev.QUERIES}
        rankings = {c: {q: list(labels[q]) for q in ev.QUERIES} for c in ev.CONFIGS}
        return labels, rankings

    def test_zero_IDCG_excluded_only_from_ndcg_all8_precision_retained(self):
        labels, runs = self.fixture()
        out = ev.compare(labels, runs)
        self.assertEqual(out['zero_positive_queries'], list(ev.QUERIES))
        for s in out['macro'].values():
            self.assertEqual(s, {'P_at_5': 0, 'P_query_denominator': 8, 'nDCG_at_5': None, 'nDCG_query_denominator': 0})
        self.assertEqual(out['contrasts'][0]['nDCG_at_5']['query_denominator'], 0)

    def test_all_grade1_not_binary_positive_but_ndcg_one(self):
        labels, runs = self.fixture(1)
        out = ev.compare(labels, runs)
        self.assertEqual(out['zero_IDCG_queries'], [])
        for s in out['macro'].values():
            self.assertEqual(s['P_at_5'], 0)
            self.assertAlmostEqual(s['nDCG_at_5'], 1)

    def test_full20_IDCG_uses_relevant_track_outside_top5(self):
        labels, runs = self.fixture()
        labels[ev.QUERIES[0]]['20'] = 3
        out = ev.compare(labels, runs)
        self.assertEqual(out['per_query'][0]['IDCG_at_5'], 7)
        self.assertEqual(out['per_query'][0]['P_at_5_ceiling'], .2)
        self.assertEqual(out['macro']['A-whole']['nDCG_at_5'], 0)
        self.assertEqual(out['macro']['A-whole']['nDCG_query_denominator'], 1)

    def test_fixed_denominator_macro_all8_and_preregistered_deltas(self):
        labels, runs = self.fixture()
        labels[ev.QUERIES[0]]['20'] = 3
        runs['B-whole'][ev.QUERIES[0]] = ['20'] + [str(t) for t in range(1, 20)]
        out = ev.compare(labels, runs)
        self.assertEqual(out['macro']['B-whole']['P_at_5'], .025)
        self.assertEqual(out['macro']['B-whole']['nDCG_at_5'], 1)
        c = out['contrasts'][0]
        self.assertEqual((c['candidate'], c['anchor'], c['role']), ('B-whole', 'A-whole', 'primary'))
        self.assertEqual(c['P_at_5']['absolute_percentage_point_delta'], 2.5)
        self.assertEqual((c['P_at_5']['wins'], c['P_at_5']['ties'], c['P_at_5']['losses']), (1, 7, 0))
        self.assertEqual(len(out['contrasts']), 4)

    def test_exponential_gain_and_log2_discount_hand_calculated(self):
        labels, runs = self.fixture()
        for q in ev.QUERIES:
            labels[q]['1'] = 1; labels[q]['2'] = 3; labels[q]['3'] = 2
        expected = (1 + 7 / 1.584962500721156 + 3 / 2) / (7 + 3 / 1.584962500721156 + 1 / 2)
        self.assertAlmostEqual(ev.compare(labels, runs)['macro']['A-whole']['nDCG_at_5'], expected)

    def test_unknown_float_bool_or_out_of_range_grades_rejected(self):
        for bad in (None, True, 2.0, -1, 4):
            with self.subTest(bad=bad):
                labels, runs = self.fixture(); labels[ev.QUERIES[0]]['1'] = bad
                with self.assertRaises(ValueError): ev.compare(labels, runs)

    def test_missing_query_or_track_or_duplicate_short_rank_rejected(self):
        changes = [lambda l, r: l.pop(ev.QUERIES[0]),
                   lambda l, r: l[ev.QUERIES[0]].pop('1'),
                   lambda l, r: r.pop('title-tfidf'),
                   lambda l, r: r['A-whole'][ev.QUERIES[0]].pop(),
                   lambda l, r: r['A-whole'][ev.QUERIES[0]].__setitem__(0, '2')]
        for change in changes:
            labels, runs = self.fixture(); change(labels, runs)
            with self.assertRaises(ValueError): ev.compare(labels, runs)

    def archive(self, extra=False, wrong_fourth=False, duplicate=False):
        payloads = [b'not JSON; commitment phase must not parse ' + bytes([i]) for i in range(1, 5)]
        exports = [{'batch': i, 'dataset_sha256': str(i) * 64,
                    'payload_sha256': hashlib.sha256(payloads[i - 1]).hexdigest()} for i in range(1, 5)]
        target = Path(self.temp.name).resolve() / 'input.zip'
        with zipfile.ZipFile(target, 'w') as z:
            for i, raw in enumerate(payloads, 1):
                z.writestr('folder/sonora-judgments-' + str(i) * 12 + '-2.json', raw + (b'!' if wrong_fourth and i == 4 else b''))
            z.writestr('__MACOSX/folder/._metadata', b'ignored metadata')
            if extra: z.writestr('unexpected.json', b'{}')
            if duplicate: z.writestr('other/sonora-judgments-' + '1' * 12 + '.json', payloads[0])
        return target, exports, payloads

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)

    def test_all4_commitments_accept_suffixes_ignore_macos_without_JSON_parse(self):
        target, exports, payloads = self.archive()
        with patch.object(ev.hc.assets.source, 'strict_json', side_effect=AssertionError('must not parse')):
            raw, result = ev.committed_bytes(target, exports)
        self.assertEqual(result, payloads)
        self.assertEqual(raw, target.read_bytes())

    def test_fourth_hash_failure_rejects_before_any_JSON_parse(self):
        target, exports, _ = self.archive(wrong_fourth=True)
        with patch.object(ev.hc.assets.source, 'strict_json', side_effect=AssertionError('must not parse')):
            with self.assertRaisesRegex(ValueError, 'commitment'): ev.committed_bytes(target, exports)

    def test_extra_or_duplicate_file_rejected(self):
        for args in ({'extra': True}, {'duplicate': True}):
            target, exports, _ = self.archive(**args)
            with self.assertRaises(ValueError): ev.committed_bytes(target, exports)

    def test_all20_track_sets_must_be_identical(self):
        labels, runs = self.fixture()
        labels[ev.QUERIES[1]]['999'] = labels[ev.QUERIES[1]].pop('20')
        with self.assertRaises(ValueError): ev.compare(labels, runs)


if __name__ == '__main__': unittest.main()

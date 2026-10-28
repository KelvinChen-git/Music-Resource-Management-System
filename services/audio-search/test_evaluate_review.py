"""Independent arithmetic/integrity checks using synthetic judgments only."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

import evaluate_review as evaluation
import review_pack as rp
import test_review_pack as fixtures


def dcg(grades):
    """The expected arithmetic is deliberately independent of the evaluator."""
    return sum((2 ** grade - 1) / math.log2(rank + 1)
               for rank, grade in enumerate(grades, start=1))


class RankingMetricTest(unittest.TestCase):
    def test_hand_calculated_grades_and_pool_ideal_include_sixth_track(self):
        pool = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 1, '6': 3}
        ranking = list('54321')
        before = deepcopy((ranking, pool))
        result = evaluation.score_ranking(ranking, pool)
        expected_dcg = 1 + 7 / math.log2(3) + 3 / 2 + 1 / math.log2(5)
        expected_ideal = 7 + 7 / math.log2(3) + 3 / 2 + 1 / math.log2(5) + 1 / math.log2(6)
        self.assertEqual(result['precision_at_5'], 2 / 5)
        self.assertEqual(result['positive_count'], 2)
        self.assertEqual(result['low_relevance_ranks'], [1, 4, 5])
        self.assertAlmostEqual(result['dcg_at_5'], expected_dcg)
        self.assertAlmostEqual(result['pool_idcg_at_5'], expected_ideal)
        self.assertAlmostEqual(result['pooled_ndcg_at_5'], expected_dcg / expected_ideal)
        self.assertEqual((ranking, pool), before)

    def test_rank_order_changes_dcg_without_changing_precision(self):
        pool = {'1': 3, '2': 2, '3': 1, '4': 0, '5': 0}
        ideal = evaluation.score_ranking(list('12345'), pool)
        reversed_order = evaluation.score_ranking(list('54321'), pool)
        self.assertEqual(ideal['precision_at_5'], 0.4)
        self.assertEqual(reversed_order['precision_at_5'], 0.4)
        self.assertAlmostEqual(ideal['pooled_ndcg_at_5'], 1)
        self.assertAlmostEqual(reversed_order['dcg_at_5'], 1 / 2 + 3 / math.log2(5) + 7 / math.log2(6))
        self.assertLess(reversed_order['pooled_ndcg_at_5'], ideal['pooled_ndcg_at_5'])

    def test_weak_relevance_contributes_gain_but_never_precision(self):
        result = evaluation.score_ranking(list('12345'), dict.fromkeys(list('12345'), 1))
        self.assertEqual(result['precision_at_5'], 0)
        self.assertEqual(result['positive_count'], 0)
        self.assertEqual(result['low_relevance_ranks'], [1, 2, 3, 4, 5])
        self.assertGreater(result['dcg_at_5'], 0)
        self.assertAlmostEqual(result['pooled_ndcg_at_5'], 1)

    def test_zero_ideal_is_null_instead_of_zero_or_one(self):
        result = evaluation.score_ranking(list('12345'), dict.fromkeys(list('123456'), 0))
        self.assertEqual(result['precision_at_5'], 0)
        self.assertEqual(result['dcg_at_5'], 0)
        self.assertEqual(result['pool_idcg_at_5'], 0)
        self.assertIsNone(result['pooled_ndcg_at_5'])

    def test_ranking_must_be_five_distinct_known_ids(self):
        pool = dict.fromkeys(list('123456'), 2)
        for ranking in (list('1234'), list('123456'), list('12344'), list('12349'),
                        ['1', '2', '3', '4', 5], ['1', '2', '3', '4', True]):
            with self.subTest(ranking=ranking), self.assertRaises(ValueError):
                evaluation.score_ranking(ranking, pool)

    def test_all_pool_labels_must_be_real_integers_even_outside_current_ranking(self):
        for rating in (None, False, True, -1, 4, 2.0, '2'):
            pool = dict.fromkeys(list('123456'), 2)
            pool['6'] = rating
            with self.subTest(rating=rating), self.assertRaises(ValueError):
                evaluation.score_ranking(list('12345'), pool)
        with self.assertRaises(ValueError):
            evaluation.score_ranking(list('12345'), {'1': 2, '2': 2, '3': 2, '4': 2})


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        # Composition avoids discovering/running the existing 17 tests a second time.
        self.fixture = fixtures.ReviewPackTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.path = self.root / 'judged.json'
        self.ratings = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 1, '6': 3}
        self.make_pack()

    def make_pack(self):
        self.pack = self.fixture.build()
        for query in self.pack['queries']:
            for row in query['candidates']:
                row.update(relevance=self.ratings[row['track_id']] if query['query_id'] == 'q2' else 0,
                           annotator='synthetic-evaluation', judged_at='2026-10-28T10:00:00Z')
        self.save_pack()

    def save_pack(self):
        self.fixture.put(self.path, self.pack)
        self.pack_hash = rp.digest(self.path.read_bytes())

    def evaluate(self, report_hash=None, pack_hash=None):
        return evaluation.evaluate(self.fixture.run, self.fixture.catalog,
                                   self.fixture.expected_hash if report_hash is None else report_hash,
                                   self.path, self.pack_hash if pack_hash is None else pack_hash)

    def test_original_rankings_not_id_sorted_pack_and_equal_query_macro_weight(self):
        before = {path: path.read_bytes() for path in [self.path, self.fixture.catalog,
                                                       *self.fixture.run.iterdir()]}
        self.assertEqual([row['track_id'] for row in self.pack['queries'][0]['candidates']], list('123456'))
        result = self.evaluate()
        by_id = {query['query_id']: query for query in result['queries']}
        q2, q1 = by_id['q2'], by_id['q1']
        self.assertEqual(q2['text'], 'Calm synthetic query.')
        self.assertEqual(q2['pool_size'], 6)
        self.assertEqual(q2['relevance_counts'], {'0': 1, '1': 2, '2': 1, '3': 2})
        self.assertEqual(q2['pool_positive_count'], 3)
        self.assertEqual(q2['modes']['whole_track']['track_ids'], list('54321'))
        self.assertEqual(q2['modes']['segment']['track_ids'], list('65432'))
        self.assertEqual(q2['modes']['whole_track']['relevance'], [1, 3, 2, 1, 0])
        self.assertEqual(q2['modes']['segment']['relevance'], [3, 1, 3, 2, 1])
        ideal = dcg([3, 3, 2, 1, 1])
        for mode, grades, precision in (('whole_track', [1, 3, 2, 1, 0], 0.4),
                                        ('segment', [3, 1, 3, 2, 1], 0.6)):
            summary = result['summary'][mode]
            self.assertAlmostEqual(summary['macro_precision_at_5'], precision / 2)
            self.assertAlmostEqual(summary['macro_pooled_ndcg_at_5'], dcg(grades) / ideal)
            self.assertEqual(summary['ndcg_valid_queries'], 1)
            self.assertEqual(summary['zero_idcg_queries'], 1)
            self.assertIsNone(q1['modes'][mode]['pooled_ndcg_at_5'])
        self.assertEqual(result['paired']['precision_at_5'], {
            'segment_wins': 1, 'ties': 1, 'whole_track_wins': 0, 'compared_queries': 2})
        self.assertEqual(result['paired']['pooled_ndcg_at_5'], {
            'segment_wins': 1, 'ties': 0, 'whole_track_wins': 0, 'compared_queries': 1})
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_result_binds_original_bytes_model_pipeline_and_evaluator(self):
        result = self.evaluate()
        self.assertEqual(result['input_sha256'], {
            'source_report': self.fixture.expected_hash,
            'catalog': rp.digest(self.fixture.catalog.read_bytes()),
            'judgments': self.pack_hash,
            'rankings': rp.digest((self.fixture.run / 'rankings.json').read_bytes())})
        self.assertEqual(result['retrieval_provenance'], self.pack['provenance'])
        self.assertEqual(result['evaluator_sha256'], rp.digest(Path(evaluation.__file__).read_bytes()))
        self.assertEqual(result['validator_sha256'], rp.digest(Path(rp.__file__).read_bytes()))

    def test_equal_model_scores_preserve_frozen_order(self):
        for query in self.fixture.artifacts['rankings.json']['queries']:
            for mode in ('whole_track', 'segment'):
                for row in query[mode]:
                    row['score'] = 0.5
        self.fixture.refresh()
        self.make_pack()
        for query in self.evaluate()['queries']:
            self.assertEqual(query['modes']['whole_track']['track_ids'], list('54321'))
            self.assertEqual(query['modes']['segment']['track_ids'], list('65432'))

    def test_all_zero_queries_have_no_ndcg_macro_or_paired_comparisons(self):
        for query in self.pack['queries']:
            for row in query['candidates']:
                row['relevance'] = 0
        self.save_pack()
        result = self.evaluate()
        for mode in ('whole_track', 'segment'):
            self.assertEqual(result['summary'][mode]['macro_precision_at_5'], 0)
            self.assertIsNone(result['summary'][mode]['macro_pooled_ndcg_at_5'])
            self.assertEqual(result['summary'][mode]['ndcg_valid_queries'], 0)
            self.assertEqual(result['summary'][mode]['zero_idcg_queries'], 2)
        self.assertEqual(result['paired']['pooled_ndcg_at_5'], {
            'segment_wins': 0, 'ties': 0, 'whole_track_wins': 0, 'compared_queries': 0})

    def test_paired_counts_can_favor_whole_track(self):
        self.ratings = {'1': 3, '2': 2, '3': 1, '4': 0, '5': 0, '6': 0}
        self.make_pack()
        result = self.evaluate()
        self.assertEqual(result['paired']['precision_at_5'], {
            'segment_wins': 0, 'ties': 1, 'whole_track_wins': 1, 'compared_queries': 2})
        self.assertEqual(result['paired']['pooled_ndcg_at_5'], {
            'segment_wins': 0, 'ties': 0, 'whole_track_wins': 1, 'compared_queries': 1})

    def test_missing_judgment_is_not_silently_treated_as_zero(self):
        row = self.pack['queries'][0]['candidates'][0]
        row.update(dict.fromkeys(rp.HUMAN_FIELDS))
        self.save_pack()
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_invalid_labels_or_immutable_candidate_edits_are_rejected(self):
        original = deepcopy(self.pack)
        for key, value in (('relevance', False), ('relevance', 4), ('track_id', '99'),
                           ('title', 'Changed candidate'), ('content_sha256', 'f' * 64)):
            self.pack = deepcopy(original)
            self.pack['queries'][0]['candidates'][0][key] = value
            self.save_pack()
            with self.subTest(field=key, value=value), self.assertRaises(ValueError):
                self.evaluate()

    def test_pack_and_report_sha_are_explicit_byte_pins(self):
        for report_hash, pack_hash in (('f' * 64, self.pack_hash),
                                       (self.fixture.expected_hash, 'f' * 64),
                                       (self.fixture.expected_hash, None), (None, self.pack_hash)):
            with self.subTest(report=report_hash, pack=pack_hash), self.assertRaises(ValueError):
                evaluation.evaluate(self.fixture.run, self.fixture.catalog, report_hash,
                                    self.path, pack_hash)
        self.path.write_bytes(self.path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_hashed_artifact_and_catalog_drift_are_rejected(self):
        for path in [self.fixture.catalog, *(self.fixture.run / name for name in rp.ARTIFACTS)]:
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                self.evaluate()
            path.write_bytes(raw)

    def test_rehashed_rankings_cannot_reuse_original_candidate_provenance(self):
        self.fixture.artifacts['rankings.json']['queries'][0]['whole_track'].reverse()
        self.fixture.refresh()
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_duplicate_unknown_or_short_rankings_are_rejected(self):
        original = deepcopy(self.fixture.artifacts)
        for mutation in ('duplicate', 'unknown', 'short'):
            self.fixture.artifacts = deepcopy(original)
            rows = self.fixture.artifacts['rankings.json']['queries'][0]['whole_track']
            if mutation == 'duplicate':
                rows[0] = deepcopy(rows[1])
            elif mutation == 'unknown':
                rows[0]['track_id'] = '99'
            else:
                rows.pop()
            self.fixture.refresh()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.evaluate()

    def test_valid_pack_from_four_track_corpus_still_cannot_claim_at_five(self):
        catalog = json.loads(self.fixture.catalog.read_text())
        catalog['audioTracks'] = catalog['audioTracks'][:4]
        self.fixture.put(self.fixture.catalog, catalog)
        self.fixture.artifacts['corpus-manifest.json']['tracks'] = self.fixture.artifacts['corpus-manifest.json']['tracks'][:4]
        self.fixture.artifacts['segments.json'] = self.fixture.artifacts['segments.json'][:4]
        for query in self.fixture.artifacts['rankings.json']['queries']:
            for mode in ('whole_track', 'segment'):
                query[mode] = [row for row in query[mode] if int(row['track_id']) <= 4]
        self.fixture.report['counts'].update(tracks=4, segments=4)
        self.fixture.refresh()
        # Rebuild each mode to four entries; this is valid for rp.prepare, not E4.
        segments = self.fixture.artifacts['segments.json']
        for query in self.fixture.artifacts['rankings.json']['queries']:
            query['whole_track'] = [{'track_id': str(i), 'score': 1 - i / 10} for i in (4, 3, 2, 1)]
            query['segment'] = [{'track_id': str(i), 'score': 1 - i / 10,
                                 'segments': [{**segments[i - 1], 'score': 1 - i / 10}]}
                                for i in (4, 3, 2, 1)]
        self.fixture.refresh()
        self.make_pack()
        self.assertEqual(rp.validate(self.pack, self.fixture.build())['unjudged'], 0)
        with self.assertRaises(ValueError):
            self.evaluate()

    def run_cli(self, output):
        command = ['evaluate_review.py', '--run-dir', str(self.fixture.run),
                   '--catalog', str(self.fixture.catalog), '--report-sha256', self.fixture.expected_hash,
                   '--pack', str(self.path), '--pack-sha256', self.pack_hash, '--output', str(output)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', command), patch.object(rp, 'REPO', self.root), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                evaluation.main()
                code = 0
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_creates_private_result_exclusively_and_prints_only_summary(self):
        output = self.root / '.local' / 'evaluation.json'
        code, stdout, stderr = self.run_cli(output)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        result = json.loads(output.read_text())
        self.assertEqual(len(result['queries']), 2)
        self.assertIsInstance(json.loads(stdout), dict)
        for private_value in ('Calm synthetic query.', 'synthetic-evaluation', 'track_ids', 'candidates'):
            self.assertNotIn(private_value, stdout)
        raw = output.read_bytes()
        code, stdout, _ = self.run_cli(output)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, '')
        self.assertEqual(output.read_bytes(), raw)
        outside = self.root / 'public.json'
        code, _, _ = self.run_cli(outside)
        self.assertEqual(code, 1)
        self.assertFalse(outside.exists())

    def test_cli_rejects_output_parent_symlink_escape(self):
        private = self.root / '.local'
        private.mkdir()
        (private / 'escape').symlink_to(self.fixture.run, target_is_directory=True)
        code, stdout, _ = self.run_cli(private / 'escape' / 'evaluation.json')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, '')
        self.assertFalse((self.fixture.run / 'evaluation.json').exists())

    def test_cli_rejected_judgments_create_no_result_or_stdout(self):
        self.pack['queries'][0]['candidates'][0].update(dict.fromkeys(rp.HUMAN_FIELDS))
        self.save_pack()
        output = self.root / '.local' / 'rejected.json'
        code, stdout, stderr = self.run_cli(output)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, '')
        self.assertTrue(stderr)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

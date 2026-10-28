"""Synthetic complement integrity/CLI checks; never read real judgments or audio."""
from copy import deepcopy
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

import diagnostic_pack as dp
import review_pack as rp
import test_review_pack as fixtures


class DiagnosticPackTest(unittest.TestCase):
    def setUp(self):
        # Compose its fixture without inheriting or rerunning the original E1 tests.
        self.fixture = fixtures.ReviewPackTest()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.root, self.run, self.catalog = self.fixture.root, self.fixture.run, self.fixture.catalog
        catalog = json.loads(self.catalog.read_text())
        tracks = self.fixture.artifacts['corpus-manifest.json']['tracks']
        segments = self.fixture.artifacts['segments.json']
        for number in (10, 7):
            tid, sid = str(number), str(number + 100)
            track = deepcopy(tracks[0])
            track.update(track_id=tid, source_id=sid, title='Title ' + tid,
                         source_url='https://www.jamendo.com/track/' + sid,
                         content_sha256=rp.digest(('synthetic-' + tid).encode()), bytes=1234 + number)
            tracks.append(track)
            catalog['audioTracks'].append({
                'musicId': number, 'sourceId': sid, 'sourceUrl': track['source_url'],
                'licenseUrl': track['license_url'], 'sha256': track['content_sha256'],
                'title': track['title'], 'artist': track['artist']})
            segments.append({**deepcopy(segments[0]), 'track_id': tid, 'segment_id': tid + ':0:480000'})
        self.fixture.put(self.catalog, catalog)
        # q1 excludes 6, q2 excludes 7, and neither original union ever returns 10.
        q1 = next(q for q in self.fixture.artifacts['rankings.json']['queries'] if q['query_id'] == 'q1')
        q1['segment'][0] = {'track_id': '7', 'score': .3,
                            'segments': [{**deepcopy(segments[-1]), 'score': .3}]}
        self.fixture.report['counts'].update(tracks=8, segments=8)
        self.fixture.refresh()
        self.base_path = self.root / 'completed-base.json'
        self.make_base()

    def make_base(self):
        self.base = self.fixture.build()
        for index, row in enumerate(c for q in self.base['queries'] for c in q['candidates']):
            row.update(relevance=index % 4, annotator='synthetic-private-alias',
                       judged_at='2026-10-28T12:00:00Z')
            if row['relevance'] > 0:
                row['human_intervals_ms'] = [[1000, 2000]]
        self.save_base()

    def save_base(self):
        self.fixture.put(self.base_path, self.base)
        self.base_hash = rp.digest(self.base_path.read_bytes())

    def build(self, query_ids=('q1', 'q2'), report_hash=True, base_hash=True):
        return dp.prepare(self.run, self.catalog,
                          self.fixture.expected_hash if report_hash is True else report_hash,
                          self.base_path, self.base_hash if base_hash is True else base_hash, query_ids)

    def command(self, command, path, query_ids=('q1', 'q2')):
        return [sys.executable, str(Path(dp.__file__)), command, '--run-dir', str(self.run),
                '--catalog', str(self.catalog), '--report-sha256', self.fixture.expected_hash,
                '--base-pack', str(self.base_path), '--base-pack-sha256', self.base_hash,
                '--query-ids', *query_ids, '--output' if command == 'build' else '--pack', str(path)]

    @staticmethod
    def rehash(pack):
        pack['dataset_sha256'] = rp.digest(rp.canonical({k: v for k, v in pack.items()
                                                       if k != 'dataset_sha256'}))

    def assert_summary_only(self, raw):
        summary = json.loads(raw)
        self.assertEqual(summary['schema'], dp.SCHEMA)
        for private in ('synthetic-private-alias', 'Title ', 'Calm synthetic query.',
                        'Fast synthetic query.', '"candidates"', '"annotator"', '"judged_at"'):
            self.assertNotIn(private, raw)
        return summary

    def test_complete_complement_includes_never_retrieved_tracks_in_numeric_order(self):
        pack = self.build()
        self.assertEqual([q['query_id'] for q in pack['queries']], ['q2', 'q1'])
        self.assertEqual([[c['track_id'] for c in q['candidates']] for q in pack['queries']],
                         [['7', '10'], ['6', '10']])
        for query in pack['queries']:
            old = next(q for q in self.base['queries'] if q['query_id'] == query['query_id'])
            self.assertEqual(query['text'], old['text'])
            self.assertFalse({c['track_id'] for c in query['candidates']} &
                             {c['track_id'] for c in old['candidates']})
        self.assertTrue(all(c['track_id'] != '10' for q in self.base['queries'] for c in q['candidates']))
        manifest = {t['track_id']: t for t in self.fixture.artifacts['corpus-manifest.json']['tracks']}
        for query in pack['queries']:
            for row in query['candidates']:
                asset = manifest[row['track_id']]
                for field in ('source_id', 'source_url', 'license_url', 'title', 'artist',
                              'duration_ms', 'content_sha256'):
                    self.assertEqual(row[field], asset[field])
                self.assertEqual(row['content_bytes'], asset['bytes'])
                self.assertEqual(row['model_suggested_intervals_ms'], [])
                self.assertTrue(all(row[field] is None for field in rp.HUMAN_FIELDS))
                self.assertNotIn('score', row)
        summary = dp.validate(pack, self.build())
        self.assertEqual((summary['judged'], summary['unjudged'], summary['candidate_pairs']), (0, 4, 4))
        self.assertEqual(summary['schema'], dp.SCHEMA)
        self.assertFalse(summary['identity_or_listening_verified'])

    def test_provenance_binds_both_original_fingerprints_and_ordered_query_subset(self):
        pack = self.build(['q1'])
        original = self.fixture.build()
        self.assertEqual(pack['schema'], 'sonora-diagnostic-pack-v1')
        self.assertEqual(pack['split'], rp.SPLIT)
        self.assertEqual(pack['owner_user_id'], original['owner_user_id'])
        provenance = pack['provenance']
        self.assertEqual(provenance['base_judgments_sha256'], self.base_hash)
        self.assertEqual(provenance['base_dataset_sha256'], self.base['dataset_sha256'])
        self.assertEqual(provenance['diagnostic_query_ids'], ['q1'])
        self.assertEqual(provenance['selection'], 'unjudged_complement_for_selected_queries')
        self.assertEqual(provenance['labeling_aid'], 'no_model_intervals_for_diagnostic_complement')
        for field in ('source_report_sha256', 'run_code_sha', 'input_catalog_sha256',
                      'checkpoint_sha256', 'pipeline_version', 'artifact_sha256', 'ordering'):
            self.assertEqual(provenance[field], original['provenance'][field])
        self.assertEqual([q['query_id'] for q in pack['queries']], ['q1'])
        self.assertNotEqual(pack['dataset_sha256'], original['dataset_sha256'])
        self.assertNotEqual(pack['dataset_sha256'], self.build()['dataset_sha256'])
        self.assertEqual(pack['dataset_sha256'], rp.digest(rp.canonical({k: v for k, v in pack.items()
                                                                        if k != 'dataset_sha256'})))

    def test_original_run_catalog_and_completed_labels_are_read_only(self):
        paths = [self.catalog, self.base_path, *self.run.iterdir()]
        before = {p: p.read_bytes() for p in paths}
        expected = self.build()
        dp.validate(deepcopy(expected), expected)
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(self.base, json.loads(self.base_path.read_text()))

    def test_both_external_pins_are_mandatory_and_exact(self):
        for field in ('report_hash', 'base_hash'):
            for bad in (None, '', 'f' * 64, 'F' * 64, 'bad'):
                with self.subTest(field=field, pin=bad), self.assertRaises(ValueError):
                    self.build(**{field: bad})
        self.base_path.write_bytes(self.base_path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.build()

    def test_incomplete_or_invalid_original_judgments_are_not_reused(self):
        original = deepcopy(self.base)
        for mutation in ('unjudged', 'invalid_alias', 'invalid_rating', 'changed_title'):
            self.base = deepcopy(original)
            row = self.base['queries'][0]['candidates'][0]
            if mutation == 'unjudged':
                row.update(dict.fromkeys(rp.HUMAN_FIELDS))
            elif mutation == 'invalid_alias':
                row['annotator'] = 'Personal Name'
            elif mutation == 'invalid_rating':
                row['relevance'] = True
            else:
                row['title'] = 'Changed title'
            self.save_base()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build()

    def test_changed_run_rejected_even_with_a_new_report_pin(self):
        self.fixture.report['pipeline_version'] = 'different-pipeline'
        self.fixture.artifacts['corpus-manifest.json']['pipeline_version'] = 'different-pipeline'
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            self.build()

    def test_missing_unknown_duplicate_or_malformed_query_selection_rejected(self):
        for query_ids in ([], (), ['unknown'], ['q1', 'q1'], ['q1', 'unknown'],
                          [''], [None], 'q1', ['q1'] * 21):
            with self.subTest(query_ids=query_ids), self.assertRaises(ValueError):
                self.build(query_ids)

    def test_request_order_never_replaces_fixture_order(self):
        self.assertEqual(self.build(['q1', 'q2']), self.build(['q2', 'q1']))

    def test_a_query_with_no_complement_is_rejected(self):
        q2 = next(q for q in self.fixture.artifacts['rankings.json']['queries'] if q['query_id'] == 'q2')
        segments = {s['track_id']: s for s in self.fixture.artifacts['segments.json']}
        q2['segment'] = [{'track_id': tid, 'score': .3,
                          'segments': [{**deepcopy(segments[tid]), 'score': .3}]}
                         for tid in ('4', '5', '6', '7', '10')]
        self.fixture.refresh()
        self.make_base()
        with self.assertRaisesRegex(ValueError, 'complement'):
            self.build(['q2'])
        self.assertEqual(len(self.build(['q1'])['queries']), 1)

    def test_partial_zero_and_positive_labels_are_distinct_and_validate_without_mutation(self):
        expected = self.build()
        pack = deepcopy(expected)
        zero, positive = pack['queries'][0]['candidates']
        for row, rating in ((zero, 0), (positive, 3)):
            row.update(relevance=rating, annotator='synthetic-private-alias',
                       judged_at='2026-10-28T12:00:00Z')
        positive['human_intervals_ms'] = [[0, 1000], [1000, 12000]]
        before = deepcopy(pack)
        result = dp.validate(pack, expected)
        self.assertEqual((result['judged'], result['unjudged'], result['human_intervals']), (2, 2, 2))
        self.assertEqual(result['relevance_counts'], {'0': 1, '1': 0, '2': 0, '3': 1})
        self.assertEqual(result['schema'], dp.SCHEMA)
        self.assertEqual(before, pack)
        self.assertIsNone(zero['human_intervals_ms'])

    def test_existing_human_validation_applies_to_diagnostic_labels(self):
        expected = self.build()
        for field, bad in (('relevance', False), ('relevance', 1.0), ('relevance', 4),
                           ('annotator', 'not anonymous'), ('judged_at', '2026-02-30T00:00:00Z'),
                           ('human_intervals_ms', [[0, 12001]]), ('human_intervals_ms', [[0, 1.5]]),
                           ('human_intervals_ms', [[5000, 7000], [6000, 8000]])):
            pack = deepcopy(expected)
            row = pack['queries'][0]['candidates'][0]
            row.update(relevance=2, annotator='synthetic-private-alias', judged_at='2026-10-28T12:00:00Z')
            row[field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                dp.validate(pack, expected)
        for rating in (None, 0):
            pack = deepcopy(expected)
            row = pack['queries'][0]['candidates'][0]
            row.update(relevance=rating, human_intervals_ms=[[0, 1000]],
                       annotator='synthetic-private-alias', judged_at='2026-10-28T12:00:00Z')
            with self.subTest(rating=rating), self.assertRaises(ValueError):
                dp.validate(pack, expected)

    def test_old_pair_insertions_missing_pairs_and_immutable_drift_rejected(self):
        expected = self.build()
        for mutation in ('old_pair', 'drop', 'duplicate', 'reorder', 'title', 'model_interval',
                         'owner', 'base_hash', 'query_ids', 'query_text', 'unknown_field', 'schema'):
            pack = deepcopy(expected)
            query = pack['queries'][0]
            if mutation == 'old_pair':
                old = deepcopy(self.base['queries'][0]['candidates'][0])
                old.update(dict.fromkeys(rp.HUMAN_FIELDS))
                query['candidates'].append(old)
            elif mutation == 'drop': query['candidates'].pop()
            elif mutation == 'duplicate': query['candidates'][1] = deepcopy(query['candidates'][0])
            elif mutation == 'reorder': query['candidates'].reverse()
            elif mutation == 'title': query['candidates'][0]['title'] = 'Changed title'
            elif mutation == 'model_interval': query['candidates'][0]['model_suggested_intervals_ms'] = [[0, 1000]]
            elif mutation == 'owner': pack['owner_user_id'] = '43'
            elif mutation == 'base_hash': pack['provenance']['base_judgments_sha256'] = 'f' * 64
            elif mutation == 'query_ids': pack['provenance']['diagnostic_query_ids'].reverse()
            elif mutation == 'query_text': query['text'] = 'Changed query.'
            elif mutation == 'unknown_field': query['candidates'][0]['extra'] = True
            else: pack['schema'] = rp.SCHEMA
            self.rehash(pack)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'Immutable'):
                dp.validate(pack, expected)

    def test_cli_build_private_exclusive_and_validation_outputs_only_summary(self):
        with tempfile.TemporaryDirectory(prefix='mus030-synthetic-test-', dir=rp.REPO / '.local') as directory:
            output = Path(directory) / 'new.json'
            result = subprocess.run(self.command('build', output), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = self.assert_summary_only(result.stdout)
            self.assertEqual((summary['candidate_pairs'], summary['judged'], summary['unjudged']), (4, 0, 4))
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            original = output.read_bytes()
            result = subprocess.run(self.command('build', output), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertEqual(output.read_bytes(), original)
            pack = json.loads(original)
            pack['queries'][0]['candidates'][0].update(
                relevance=0, annotator='synthetic-private-alias', judged_at='2026-10-28T12:00:00Z')
            self.fixture.put(output, pack)
            result = subprocess.run(self.command('validate', output), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = self.assert_summary_only(result.stdout)
            self.assertEqual((summary['judged'], summary['unjudged']), (1, 3))
            pack['queries'][0]['candidates'].pop()
            self.fixture.put(output, pack)
            result = subprocess.run(self.command('validate', output), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertIn('Immutable', result.stderr)

    def test_cli_output_cannot_escape_private_storage_even_through_symlink(self):
        output = self.root / 'public.json'
        result = subprocess.run(self.command('build', output), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertFalse(output.exists())
        with tempfile.TemporaryDirectory(prefix='mus030-synthetic-test-', dir=rp.REPO / '.local') as directory:
            link = Path(directory) / 'escape'
            link.symlink_to(self.root, target_is_directory=True)
            result = subprocess.run(self.command('build', link / 'escaped.json'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertFalse((self.root / 'escaped.json').exists())

    def test_cli_requires_report_base_and_query_pins(self):
        path = self.root / 'submitted.json'
        self.fixture.put(path, self.build())
        command = self.command('validate', path, ['q1'])
        for option in ('--run-dir', '--catalog', '--report-sha256', '--base-pack',
                       '--base-pack-sha256', '--query-ids'):
            args = command[:]
            index = args.index(option)
            del args[index:index + 2]
            with self.subTest(option=option):
                result = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(option, result.stderr)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()

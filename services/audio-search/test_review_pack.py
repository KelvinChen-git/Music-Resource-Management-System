"""Synthetic integrity/label regressions; no model, audio, account or HTTP access."""
from copy import deepcopy
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import review_pack as rp


class ReviewPackTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'run'
        self.run.mkdir()
        self.catalog = self.root / 'catalog.json'
        catalog_tracks, tracks, segments = [], [], []
        for number in range(1, 7):
            tid, sid = str(number), str(number + 100)
            source = 'https://www.jamendo.com/track/' + sid
            license_url = 'https://creativecommons.org/licenses/by/4.0/'
            content = rp.digest(('synthetic-' + tid).encode())
            catalog_tracks.append({'musicId': number, 'sourceId': sid, 'sourceUrl': source,
                                   'licenseUrl': license_url, 'sha256': content,
                                   'title': 'Title ' + tid, 'artist': 'Synthetic artist'})
            tracks.append({'track_id': tid, 'source_id': sid, 'source_url': source,
                           'license_url': license_url, 'content_sha256': content,
                           'bytes': 1234 + number, 'title': 'Title ' + tid, 'artist': 'Synthetic artist',
                           'duration_ms': 12000, 'sample_rate_hz': 48000, 'decoded_samples': 576000})
            start, end = (240000, 576000) if number == 6 else (0, 480000)
            segments.append({'segment_id': f'{tid}:{start}:{end}', 'track_id': tid,
                             'start_sample': start, 'end_sample': end,
                             'start_ms': start // 48, 'end_ms': end // 48,
                             'padded_samples': 480000 - (end - start)})
        self.put(self.catalog, {'ownerId': 42, 'audioTracks': catalog_tracks})
        self.artifacts = {
            'corpus-manifest.json': {'pipeline_version': 'synthetic-pipeline', 'tracks': tracks},
            'segments.json': segments,
            'queries.json': {'split': 'exploratory_unjudged', 'queries': [
                {'query_id': 'q2', 'text': 'Calm synthetic query.'},
                {'query_id': 'q1', 'text': 'Fast synthetic query.'}]},
            'rankings.json': {'judgments': 'unjudged', 'queries': []}}
        for query in reversed(self.artifacts['queries.json']['queries']):
            self.artifacts['rankings.json']['queries'].append({'kind': 'text', **query,
                'whole_track': [{'track_id': str(i), 'score': 1 - i / 10} for i in (5, 4, 3, 2, 1)],
                'segment': [{'track_id': str(i), 'score': 1 - i / 10,
                             'segments': [{**segments[i - 1], 'score': 1 - i / 10}]} for i in (6, 5, 4, 3, 2)]})
        self.report = {'status': 'passed_offline_pipeline_only', 'working_tree_dirty': False,
                       'code_sha': 'a' * 40, 'pipeline_version': 'synthetic-pipeline',
                       'model': {'dimension': 512, 'strict_missing': [], 'strict_unexpected': [],
                                 'checkpoint_sha256': 'b' * 64},
                       'counts': {'tracks': 6, 'segments': 6, 'text_queries': 2, 'reference_queries': 0}}
        self.refresh()

    def put(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False) + '\n')

    def refresh(self):
        for name, value in self.artifacts.items():
            self.put(self.run / name, value)
        self.report['artifact_sha256'] = {n: rp.digest((self.run / n).read_bytes()) for n in rp.ARTIFACTS}
        self.report['input_catalog_sha256'] = rp.digest(self.catalog.read_bytes())
        self.put(self.run / 'report.json', self.report)
        self.expected_hash = rp.digest((self.run / 'report.json').read_bytes())

    def build(self):
        return rp.prepare(self.run, self.catalog, self.expected_hash)

    def judged(self, rating=2):
        pack = self.build()
        row = pack['queries'][0]['candidates'][0]
        row.update(relevance=rating, annotator='synthetic-test', judged_at='2026-10-21T10:00:00Z')
        return pack, row

    def test_union_sorted_without_scores_or_automatic_judgments(self):
        before = {p: p.read_bytes() for p in [self.catalog, *self.run.iterdir()]}
        pack = self.build()
        self.assertEqual([q['query_id'] for q in pack['queries']], ['q2', 'q1'])
        for query in pack['queries']:
            self.assertEqual([c['track_id'] for c in query['candidates']], list('123456'))
            self.assertEqual(query['candidates'][0]['model_suggested_intervals_ms'], [])
            self.assertEqual(query['candidates'][-1]['model_suggested_intervals_ms'], [[5000, 12000]])
            for row in query['candidates']:
                self.assertTrue(all(row[k] is None for k in rp.HUMAN_FIELDS))
                self.assertNotIn('score', row)
                self.assertNotIn('asset_filename', row)
                self.assertEqual(len(row['content_sha256']), 64)
                self.assertGreater(row['content_bytes'], 0)
        summary = rp.validate(pack, self.build())
        self.assertEqual((summary['judged'], summary['unjudged'], summary['candidate_pairs']), (0, 12, 12))
        self.assertFalse(summary['identity_or_listening_verified'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_external_report_hash_required_and_artifacts_cannot_drift(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            rp.prepare(self.run, self.catalog, 'f' * 64)
        for name in rp.ARTIFACTS:
            path = self.run / name
            before = path.read_bytes()
            path.write_bytes(before + b' ')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'hash mismatch'):
                self.build()
            path.write_bytes(before)
        self.catalog.write_bytes(self.catalog.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.build()

    def test_failed_dirty_or_different_model_run_rejected(self):
        original = deepcopy(self.report)
        variants = [('status', 'failed'), ('working_tree_dirty', True), ('code_sha', 'bad'),
                    ('counts', {**self.report['counts'], 'tracks': 7}),
                    ('model', {**self.report['model'], 'strict_missing': ['weight']}),
                    ('model', {**self.report['model'], 'dimension': 768})]
        for key, value in variants:
            self.report = deepcopy(original)
            self.report[key] = value
            self.refresh()
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.build()

    def test_catalog_manifest_identity_metadata_and_content_must_match(self):
        original = deepcopy(self.artifacts)
        for key, value in [('track_id', '99'), ('track_id', '01'), ('track_id', True),
                           ('source_id', '999'), ('title', 'Changed'), ('content_sha256', 'c' * 64),
                           ('bytes', True), ('duration_ms', 600001), ('decoded_samples', 1)]:
            self.artifacts = deepcopy(original)
            self.artifacts['corpus-manifest.json']['tracks'][0][key] = value
            self.refresh()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()

    def test_source_and_license_cannot_carry_secrets_or_wrong_identity(self):
        original = deepcopy(self.artifacts)
        variants = [('source_url', 'https://www.jamendo.com/track/101?client_id=canary'),
                    ('source_url', 'https://www.jamendo.com/track/999'),
                    ('source_url', 'https://www.jamendo.com.evil/track/101'),
                    ('source_url', 'https://user@www.jamendo.com/track/101'),
                    ('source_url', 'https://www.jamendo.com:443/track/101'),
                    ('license_url', 'https://creativecommons.org/licenses/by/3.0/'),
                    ('license_url', 'https://creativecommons.org/licenses/by/4.0/?canary=1')]
        for key, value in variants:
            self.artifacts = deepcopy(original)
            self.artifacts['corpus-manifest.json']['tracks'][0][key] = value
            self.refresh()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build()

    def test_duplicate_manifest_catalog_content_and_query_rejected(self):
        mutations = [lambda: self.artifacts['corpus-manifest.json']['tracks'].__setitem__(1, deepcopy(self.artifacts['corpus-manifest.json']['tracks'][0])),
                     lambda: self.artifacts['queries.json']['queries'].append(deepcopy(self.artifacts['queries.json']['queries'][0])),
                     lambda: self.artifacts['rankings.json']['queries'].append(deepcopy(self.artifacts['rankings.json']['queries'][0])),
                     lambda: self.artifacts['segments.json'].append(deepcopy(self.artifacts['segments.json'][0]))]
        original = deepcopy(self.artifacts)
        for index, mutate in enumerate(mutations):
            self.artifacts = deepcopy(original)
            mutate()
            self.refresh()
            with self.subTest(case=index), self.assertRaises(ValueError):
                self.build()
        c = json.loads(self.catalog.read_text())
        c['audioTracks'][1] = c['audioTracks'][0]
        self.put(self.catalog, c)
        self.refresh()
        with self.assertRaises(ValueError):
            self.build()

    def test_rankings_require_exact_queries_candidates_and_known_segments(self):
        original = deepcopy(self.artifacts)
        for mutation in ('missing_query', 'wrong_text', 'duplicate_track', 'unknown_segment', 'wrong_segment', 'short_top5'):
            self.artifacts = deepcopy(original)
            rows = self.artifacts['rankings.json']['queries']
            if mutation == 'missing_query':
                rows.pop()
            elif mutation == 'wrong_text':
                rows[0]['text'] = 'Different query.'
            elif mutation == 'duplicate_track':
                rows[0]['whole_track'][0] = deepcopy(rows[0]['whole_track'][1])
            elif mutation == 'unknown_segment':
                rows[0]['segment'][0]['segments'][0]['segment_id'] = 'unknown'
            elif mutation == 'wrong_segment':
                rows[0]['segment'][0]['segments'][0]['end_ms'] = 12001
            else:
                rows[0]['whole_track'].pop()
            self.refresh()
            with self.subTest(case=mutation), self.assertRaises(ValueError):
                self.build()

    def test_invalid_segment_bounds_padding_and_identity_rejected(self):
        original = deepcopy(self.artifacts)
        for key, value in [('start_sample', -1), ('end_sample', 576001), ('start_ms', False),
                           ('end_ms', 13000), ('padded_samples', 1), ('segment_id', 'changed')]:
            self.artifacts = deepcopy(original)
            self.artifacts['segments.json'][0][key] = value
            self.refresh()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()

    def test_zero_and_null_remain_distinct_without_mutating_pack(self):
        pack, row = self.judged(0)
        original = deepcopy(pack)
        summary = rp.validate(pack, self.build())
        self.assertEqual((summary['judged'], summary['unjudged']), (1, 11))
        self.assertEqual(summary['relevance_counts'], {'0': 1, '1': 0, '2': 0, '3': 0})
        self.assertEqual(pack, original)
        self.assertEqual(summary['dataset_sha256'], self.build()['dataset_sha256'])
        self.assertIsNone(row['human_intervals_ms'])

    def test_judgments_require_real_integer_alias_and_valid_timestamp(self):
        variants = [('relevance', False), ('relevance', 1.0), ('relevance', -1), ('relevance', 4),
                    ('relevance', '2'), ('annotator', None), ('annotator', 'Personal Name'),
                    ('judged_at', None), ('judged_at', '2026-02-30T00:00:00Z'),
                    ('judged_at', '2026-10-21T00:00:00+00:00')]
        for key, value in variants:
            pack, row = self.judged()
            row[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                rp.validate(pack, self.build())
        for rating in range(4):
            pack, _ = self.judged(rating)
            self.assertEqual(rp.validate(pack, self.build())['judged'], 1)

    def test_human_ranges_are_optional_integer_sorted_nonoverlapping_and_bounded(self):
        pack, row = self.judged()
        row['human_intervals_ms'] = [[0, 5000], [5000, 12000]]
        self.assertEqual(rp.validate(pack, self.build())['human_intervals'], 2)
        for value in ([], [[0, 0]], [[-1, 100]], [[0, 12001]], [[0, 1.5]], [[False, 100]],
                      [[5000, 6000], [0, 1000]], [[0, 6000], [5000, 10000]],
                      [[0, 100]] * 21, 'not a range'):
            row['human_intervals_ms'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                rp.validate(pack, self.build())
        row.update(relevance=0, human_intervals_ms=[[0, 1000]])
        with self.assertRaises(ValueError):
            rp.validate(pack, self.build())

    def test_unjudged_annotations_may_not_exist(self):
        for field, value in [('annotator', 'synthetic-test'), ('judged_at', '2026-10-21T00:00:00Z'),
                             ('human_intervals_ms', [[0, 1000]])]:
            pack = self.build()
            pack['queries'][0]['candidates'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rp.validate(pack, self.build())

    def test_immutable_fields_and_unknown_fields_cannot_be_edited_even_with_fingerprint(self):
        expected = self.build()
        for field, value in [('owner_user_id', '43'), ('split', 'test'), ('dataset_sha256', 'f' * 64),
                             ('provenance', {}), ('unexpected', True)]:
            pack = deepcopy(expected)
            pack[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rp.validate(pack, expected)
        for field, value in [('track_id', '2'), ('content_sha256', 'f' * 64), ('content_bytes', 1),
                             ('duration_ms', 12000.0), ('source_url', 'https://evil.test'),
                             ('model_suggested_intervals_ms', [[0, 1]]), ('unknown', 1)]:
            pack = deepcopy(expected)
            pack['queries'][0]['candidates'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rp.validate(pack, expected)
        for mutation in ('drop', 'duplicate', 'reorder', 'text', 'missing_label'):
            pack = deepcopy(expected)
            query = pack['queries'][0]
            if mutation == 'drop': query['candidates'].pop()
            elif mutation == 'duplicate': query['candidates'][1] = deepcopy(query['candidates'][0])
            elif mutation == 'reorder': query['candidates'].reverse()
            elif mutation == 'text': query['text'] = 'Changed query.'
            else: del query['candidates'][0]['relevance']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                rp.validate(pack, expected)

    def test_json_rejects_duplicates_nonfinite_and_oversize(self):
        path = self.root / 'invalid.json'
        for value in ('{"relevance":null,"relevance":0}', '{"score":NaN}', '{"score":Infinity}'):
            path.write_text(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                rp.read_json(path)
        path.write_text(' ' * 100)
        with self.assertRaisesRegex(ValueError, 'size'):
            rp.read_json(path, limit=99)

    def test_ids_support_long_strings_without_boolean_or_float_coercion(self):
        self.assertEqual(rp.identity('9223372036854775807'), '9223372036854775807')
        for value in ('9223372036854775808', '01', '0', '-1', 1, True, 1.0, '1e3'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rp.identity(value)

    def test_private_exclusive_output_and_symlink_escape_guard(self):
        pack = self.build()
        with patch.object(rp, 'REPO', self.root):
            output = self.root / '.local' / 'pack.json'
            rp.write_new(output, pack)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            raw = output.read_bytes()
            with self.assertRaises(FileExistsError): rp.write_new(output, pack)
            self.assertEqual(output.read_bytes(), raw)
            with self.assertRaises(ValueError): rp.write_new(self.root / 'public.json', pack)
            link = self.root / '.local' / 'link'
            link.symlink_to(self.run, target_is_directory=True)
            with self.assertRaises(ValueError): rp.write_new(link / 'escaped.json', pack)
            self.assertFalse((self.run / 'escaped.json').exists())
            dangling = self.root / '.local' / 'dangling.json'
            dangling.symlink_to(output.parent / 'new.json')
            with self.assertRaises(FileExistsError): rp.write_new(dangling, pack)
            self.assertFalse((output.parent / 'new.json').exists())

    def test_cli_validates_synthetic_partial_pack_and_rejects_drift(self):
        pack, row = self.judged(3)
        row['human_intervals_ms'] = [[1000, 2000]]
        path = self.root / 'submitted.json'
        self.put(path, pack)
        command = [sys.executable, str(Path(rp.__file__)), 'validate', '--run-dir', str(self.run),
                   '--catalog', str(self.catalog), '--report-sha256', self.expected_hash, '--pack', str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual((summary['judged'], summary['human_intervals'], summary['unjudged']), (1, 1, 11))
        pack['split'] = 'test'
        self.put(path, pack)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Immutable', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()

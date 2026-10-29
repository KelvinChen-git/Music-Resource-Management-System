"""Independent supplement selection checks using synthetic frozen runs and labels."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

import research_evaluate as ev
import review_pack as rp
import supplement_pack as supplement
from test_research_evaluate import Fixture, put, windows


class SupplementPackTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.f = Fixture(self.root)
        for item in (patch.object(ev, 'SOURCE_ROOT', self.f.code), patch.object(supplement, 'ROOT', self.root),
                     patch.object(supplement.subprocess, 'run', return_value=SimpleNamespace(returncode=0))):
            item.start()
            self.addCleanup(item.stop)
        self.private = self.root / '.local/a/mus036'
        self.private.mkdir(parents=True, mode=0o700)
        self.evaluation = self.root / 'evaluation.json'
        self.capture_evaluation()

    def capture_evaluation(self):
        self.evaluated = ev.evaluate(**self.f.arguments())
        put(self.evaluation, self.evaluated)
        self.evaluation_sha = ev.file_hash(self.evaluation)

    def arguments(self):
        return {**self.f.arguments(), 'evaluation': self.evaluation, 'evaluation_sha256': self.evaluation_sha}

    def prepare(self, **changes):
        args = self.arguments()
        args.update(changes)
        return supplement.prepare(**args)

    def cli(self, command, target, **changes):
        args = self.arguments()
        args.update(changes)
        argv = ['supplement_pack.py', command]
        for name, value in args.items():
            argv.extend(['--' + name.replace('_', '-'), str(value)])
        argv.extend(['--output' if command == 'build' else '--pack', str(target)])
        stdout, stderr = io.StringIO(), io.StringIO()
        status = 0
        with patch.object(sys, 'argv', argv), redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                supplement.main()
            except SystemExit as exc:
                status = exc.code
        return status, stdout.getvalue(), stderr.getvalue()

    def test_unknown_union_omits_known_pairs_and_has_fixed_query_numeric_order(self):
        pack = self.prepare()
        self.assertEqual((pack['schema'], pack['split']), (supplement.SCHEMA, supplement.SPLIT))
        self.assertEqual([q['query_id'] for q in pack['queries']], list(ev.TARGETS))
        known = {(q['query_id'], r['track_id']) for path in self.f.package_paths.values()
                 for q in json.loads(path.read_text())['queries'] for r in q['candidates']}
        actual = {(q['query_id'], r['track_id']) for q in pack['queries'] for r in q['candidates']}
        expected = set()
        for query in self.evaluated['queries']:
            for mode in ('whole_track', 'segment'):
                row = query['new_modes'][mode]
                expected.update((query['query_id'], tid) for tid, grade in zip(row['track_ids'], row['relevance'])
                                if grade is None)
        self.assertEqual(len(actual), 10)
        self.assertEqual(actual, expected)
        self.assertFalse(actual & known)
        for query in pack['queries']:
            ids = [r['track_id'] for r in query['candidates']]
            self.assertEqual(ids, sorted(set(ids), key=int))
            for row in query['candidates']:
                self.assertEqual(row['model_suggested_intervals_ms'], [])
                self.assertTrue(all(row[key] is None for key in rp.HUMAN_FIELDS))
        unsigned = {k: v for k, v in pack.items() if k != 'dataset_sha256'}
        self.assertEqual(pack['dataset_sha256'], rp.digest(rp.canonical(unsigned)))

    def test_union_deduplicates_overlap_between_modes(self):
        for query in self.f.new_artifacts['rankings.json']['queries']:
            query['segment'] = Fixture.ranking([r['track_id'] for r in query['whole_track']],
                                               self.f.new_artifacts['segments.json'], True)
        self.f.refresh_runs()
        self.capture_evaluation()
        pack = self.prepare()
        self.assertEqual(sum(len(q['candidates']) for q in pack['queries']), 10)
        self.assertTrue(all(len(q['candidates']) == 2 for q in pack['queries']))

    def test_fully_known_queries_are_omitted_without_reordering_remaining(self):
        first = next(q for q in self.f.new_artifacts['rankings.json']['queries'] if q['query_id'] == ev.TARGETS[0])
        first['whole_track'] = [{k: v for k, v in r.items() if k != 'segments'} for r in first['segment']]
        self.f.refresh_runs()
        self.capture_evaluation()
        pack = self.prepare()
        self.assertEqual([q['query_id'] for q in pack['queries']], list(ev.TARGETS[1:]))
        self.assertEqual(pack['provenance']['supplement_query_ids'], list(ev.TARGETS[1:]))

    def test_no_unknown_query_cannot_produce_empty_pack(self):
        for query in self.f.new_artifacts['rankings.json']['queries']:
            query['whole_track'] = [{k: v for k, v in r.items() if k != 'segments'} for r in query['segment']]
        self.f.refresh_runs()
        self.capture_evaluation()
        with self.assertRaisesRegex(ValueError, 'No unknown'):
            self.prepare()

    def test_actual_eof_duration_is_used_instead_of_catalog_header_duration(self):
        for row in self.f.new_tracks:
            if row['source_provider'] == 'incompetech':
                row['source_frames'] -= 1024
                row['decoded_samples'] = row['source_frames']
                row['duration_ms'] = row['decoded_samples'] * 1000 // 48000
        self.f.new_artifacts['segments.json'] = windows(self.f.new_tracks)
        self.f.refresh_runs()
        self.capture_evaluation()
        pack = self.prepare()
        self.assertTrue(all(r['duration_ms'] == 59978 for q in pack['queries'] for r in q['candidates']))
        self.assertTrue(all(r['decodedDurationMs'] == 60000 for r in self.f.source.catalog['audioTracks'][20:]))

    def test_both_provider_identities_are_canonical_and_unsafe_sources_fail(self):
        old = supplement.candidate(self.f.new_tracks[0])
        new_asset = next(a for a in self.f.new_tracks if a['source_provider'] == 'incompetech')
        new = supplement.candidate(new_asset)
        self.assertEqual(old['source_provider'], 'jamendo')
        self.assertTrue(old['source_id'].isdigit())
        self.assertEqual(old['source_url'], 'https://www.jamendo.com/track/' + old['source_id'])
        self.assertEqual(new['source_provider'], 'incompetech')
        self.assertEqual(new['source_url'], supplement.sp.BASE + 'index.html?isrc=' + new['source_id'])
        for field, value in (('source_provider', 'other'), ('source_id', '123'),
                             ('source_url', 'https://example.invalid/music'),
                             ('license_url', 'https://creativecommons.org/licenses/by/3.0/')):
            asset = {**new_asset, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                supplement.candidate(asset)

    def test_exact_provenance_has_all_five_artifacts_and_three_label_pins(self):
        pack = self.prepare()
        p = pack['provenance']
        self.assertEqual(set(p), {'source_report_sha256', 'run_code_sha', 'input_catalog_sha256',
            'checkpoint_sha256', 'pipeline_version', 'source_decoder_version', 'artifact_sha256',
            'evaluation_sha256', 'known_judgments_sha256', 'supplement_query_ids',
            'selection', 'ordering', 'labeling_aid'})
        self.assertEqual(set(p['artifact_sha256']), set(ev.ARTIFACTS))
        self.assertEqual(p['known_judgments_sha256'], {name: ev.file_hash(path) for name, path in self.f.package_paths.items()})
        self.assertEqual(p['run_code_sha'], self.f.new_report['code_sha'])
        self.assertEqual(p['selection'], supplement.SELECTION)
        self.assertEqual(p['labeling_aid'], 'no_model_intervals_retrieval_supplement')

    def test_repeated_tracks_have_identical_metadata_but_independent_human_fields(self):
        pack = self.prepare()
        seen = {}
        repeats = 0
        for query in pack['queries']:
            for row in query['candidates']:
                if row['track_id'] in seen:
                    self.assertEqual(row, seen[row['track_id']])
                    self.assertIsNot(row, seen[row['track_id']])
                    repeats += 1
                seen[row['track_id']] = row
        self.assertGreater(repeats, 0)

    def test_wrong_or_missing_evaluation_pin_rejected_before_full_evaluator(self):
        for value in (None, '0' * 64):
            with self.subTest(pin=value), patch.object(ev, 'evaluate') as rebuild, self.assertRaises(ValueError):
                self.prepare(evaluation_sha256=value)
            rebuild.assert_not_called()

    def test_rehashed_evaluation_cannot_change_archived_unknown_or_metrics(self):
        for mutate in (lambda e: e['queries'][0]['new_modes']['whole_track']['relevance'].__setitem__(1, 0),
                       lambda e: e['summary']['whole_track'].update(new_macro_precision_at_5_lower=1.0)):
            value = deepcopy(self.evaluated)
            mutate(value)
            put(self.evaluation, value)
            with self.assertRaisesRegex(ValueError, 'complete pinned-input'):
                self.prepare(evaluation_sha256=ev.file_hash(self.evaluation))

    def test_all_eleven_evaluation_pins_are_still_required(self):
        for key in self.f.arguments():
            if not key.endswith('_sha256'):
                continue
            with self.subTest(pin=key), self.assertRaises(ValueError):
                self.prepare(**{key: None})

    def test_missing_old_human_judgment_cannot_become_supplement_candidate(self):
        path = self.f.package_paths['diagnostic']
        value = json.loads(path.read_text())
        value['queries'][0]['candidates'][0].update(dict.fromkeys(rp.HUMAN_FIELDS))
        put(path, value)
        with self.assertRaisesRegex(ValueError, 'fully judged'):
            self.prepare()

    def test_only_valid_human_fields_may_change(self):
        expected = self.prepare()
        pack = deepcopy(expected)
        row = pack['queries'][0]['candidates'][0]
        row.update(relevance=2, annotator='SYNTHETIC_ONLY', judged_at='2026-10-29T10:00:00Z',
                   human_intervals_ms=[[1000, 2000]])
        result = supplement.validate(pack, expected)
        self.assertEqual((result['judged'], result['human_intervals']), (1, 1))
        self.assertEqual((result['schema'], result['split']), (supplement.SCHEMA, supplement.SPLIT))
        for changes in ({'relevance': True}, {'relevance': 4}, {'annotator': ''},
                        {'judged_at': 'bad'}, {'human_intervals_ms': [[0, row['duration_ms'] + 1]]}):
            invalid = deepcopy(pack)
            invalid['queries'][0]['candidates'][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                supplement.validate(invalid, expected)

    def test_unjudged_candidate_cannot_carry_alias_or_intervals(self):
        expected = self.prepare()
        for changes in ({'annotator': 'SYNTHETIC_ONLY'}, {'human_intervals_ms': [[1, 2]]}):
            value = deepcopy(expected)
            value['queries'][0]['candidates'][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                supplement.validate(value, expected)

    def test_immutable_metadata_provenance_order_and_membership_cannot_change(self):
        expected = self.prepare()
        mutations = [lambda p: p['queries'][0]['candidates'][0].update(duration_ms=60000.0),
            lambda p: p['queries'][0]['candidates'][0].update(title='Changed'),
            lambda p: p['queries'][0]['candidates'][0].update(source_provider='jamendo'),
            lambda p: p['queries'][0]['candidates'][0].update(model_suggested_intervals_ms=[[1, 2]]),
            lambda p: p['provenance'].update(evaluation_sha256='0' * 64),
            lambda p: p['provenance'].update(run_code_sha='0' * 40),
            lambda p: p['queries'][0]['candidates'].reverse(),
            lambda p: p['queries'][0]['candidates'].pop(),
            lambda p: p['queries'][0]['candidates'].append(deepcopy(p['queries'][0]['candidates'][0]))]
        for mutate in mutations:
            value = deepcopy(expected)
            mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                supplement.validate(value, expected)

    def test_validate_requires_this_reconstructed_schema(self):
        pack = self.prepare()
        wrong = {**pack, 'schema': rp.SCHEMA}
        with self.assertRaisesRegex(ValueError, 'reconstructed retrieval'):
            supplement.validate(pack, wrong)

    def test_cli_build_validate_permissions_and_aggregate_only_output(self):
        target = self.private / 'nested/pack.json'
        status, stdout, stderr = self.cli('build', target)
        self.assertEqual((status, stderr), (0, ''))
        value = json.loads(stdout)
        self.assertEqual((value['candidate_pairs'], value['unjudged']), (10, 10))
        self.assertNotIn('track_id', stdout)
        self.assertNotIn('query_id', stdout)
        self.assertNotIn('SYNTHETIC_ONLY', stdout)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        status, stdout, stderr = self.cli('validate', target)
        self.assertEqual((status, stderr), (0, ''))
        self.assertEqual(json.loads(stdout)['split'], supplement.SPLIT)

    def test_output_rejects_overwrite_symlink_escape_and_unignored_path(self):
        pack = self.prepare()
        target = self.private / 'pack.json'
        supplement.write_new(target, pack)
        before = target.read_bytes()
        with self.assertRaises(FileExistsError):
            supplement.write_new(target, pack)
        self.assertEqual(target.read_bytes(), before)
        link = self.private / 'linked'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            supplement.write_new(link / 'escape.json', pack)
        outside = self.root / 'outside.json'
        with self.assertRaisesRegex(ValueError, 'below this checkout'):
            supplement.write_new(outside, pack)
        self.assertFalse(outside.exists())
        supplement.subprocess.run.return_value = SimpleNamespace(returncode=1)
        with self.assertRaisesRegex(ValueError, 'ignored by Git'):
            supplement.write_new(self.private / 'unignored.json', pack)

    def test_private_file_remains_readable_with_restrictive_umask(self):
        pack = self.prepare()
        target = self.private / 'restricted-umask.json'
        previous = os.umask(0o777)
        try:
            supplement.write_new(target, pack)
        finally:
            os.umask(previous)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(target.read_bytes()), pack)

    def test_readonly_inputs_remain_exact_after_prepare_and_cli_failure(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.prepare()
        status, stdout, _ = self.cli('build', self.private / 'rejected.json', evaluation_sha256='0' * 64)
        self.assertEqual((status, stdout), (1, ''))
        self.assertFalse((self.private / 'rejected.json').exists())
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == '__main__':
    unittest.main()

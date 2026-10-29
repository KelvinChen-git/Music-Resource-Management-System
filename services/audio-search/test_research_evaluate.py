"""Synthetic unknown-aware evaluation; no HTTP, model, real audio or human labels."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

import diagnostic_pack as dp
import research_evaluate as ev
import review_pack as rp
import source_review_pack as sp
from test_source_review_pack import Fixture as SourceFixture


def put(path, value):
    Path(path).write_bytes(rp.canonical(value))


def windows(tracks):
    """Fixture construction independent of the evaluator's window checker."""
    result = []
    for track in tracks:
        total = track['decoded_samples']
        start = 0
        while True:
            end = min(start + 480000, total)
            tid = track['track_id']
            result.append({'segment_id': f'{tid}:{start}:{end}', 'track_id': tid,
                           'start_sample': start, 'end_sample': end,
                           'start_ms': start // 48, 'end_ms': end // 48,
                           'padded_samples': 480000 - (end - start)})
            if end == total:
                break
            start += 240000
    return result


class Fixture:
    def __init__(self, root):
        self.root = root
        self.source = SourceFixture(root)
        self.code = root / 'synthetic-source'
        self.code.mkdir()
        for name in ev.SOURCE_NAMES:
            (self.code / name).write_text('Synthetic fixed source bytes: ' + name)
        self.old_run, self.new_run = root / 'old-run', root / 'new-run'
        self.old_run.mkdir(); self.new_run.mkdir()
        self.package_paths = {name: root / (name + '-judged.json') for name in ('base', 'diagnostic', 'source')}
        self.source.queries['queries'] = [{'query_id': qid, 'text': 'Synthetic query ' + qid}
                                         for qid in ev.QUERY_IDS]
        self.old_tracks = []
        for row in self.source.baseline['audioTracks']:
            sid, tid = row['sourceId'], str(row['musicId'])
            row.update(artist='Synthetic old author', durationSeconds=60,
                       sourceUrl='https://www.jamendo.com/track/' + sid,
                       licenseUrl='https://creativecommons.org/licenses/by/4.0/')
            self.old_tracks.append({'track_id': tid, 'source_id': sid, 'asset_filename': sid + '.mp3',
                'content_sha256': row['sha256'], 'bytes': 1234 + int(tid),
                'download_proof_sha256': rp.digest(('synthetic-proof-' + sid).encode()),
                'source_url': row['sourceUrl'], 'license_url': row['licenseUrl'],
                'title': row['title'], 'artist': row['artist'], 'provider_duration_seconds': 60,
                'format': 'MP3', 'source_frames': 60 * 48000, 'source_sample_rate_hz': 48000,
                'source_channels': 2, 'sample_rate_hz': 48000, 'decoded_samples': 60 * 48000,
                'duration_ms': 60000})
        self.source.catalog['audioTracks'][:20] = [dict(row, sourceProvider='jamendo')
                                                   for row in self.source.baseline['audioTracks']]
        self.source.save()
        self.old_artifacts = {'corpus-manifest.json': {'pipeline_version': ev.PIPELINE, 'tracks': self.old_tracks},
                              'segments.json': windows(self.old_tracks), 'queries.json': deepcopy(self.source.queries)}
        pool_orders = ([6, 5, 4, 3, 2], [7, 6, 5, 4, 3], [7, 6, 5, 4, 3], [1, 2, 3, 4, 5],
                       [7, 6, 5, 4, 3], [1, 2, 3, 4, 5], [6, 5, 4, 3, 2], [8, 7, 6, 5, 4])
        self.old_artifacts['rankings.json'] = {'judgments': 'unjudged', 'queries': []}
        for query, segment_order in zip(self.source.queries['queries'], pool_orders):
            self.old_artifacts['rankings.json']['queries'].append({'kind': 'text', **query,
                'whole_track': self.ranking([5, 4, 3, 2, 1], self.old_artifacts['segments.json']),
                'segment': self.ranking(segment_order, self.old_artifacts['segments.json'], True)})
        self.old_report = {'status': 'passed_offline_pipeline_only', 'working_tree_dirty': False,
            'code_sha': 'a' * 40, 'pipeline_version': ev.PIPELINE, 'model': deepcopy(ev.MODEL),
            'preprocessing': deepcopy(ev.PREPROCESSING), 'environment': {'device': 'cpu'},
            'source_hashes': self.hash_sources(),
            'counts': {'tracks': 20, 'segments': len(self.old_artifacts['segments.json']),
                       'text_queries': 8, 'reference_queries': 0}}
        self.new_tracks = [dict(row, source_provider='jamendo', asset_filename='jamendo-' + row['source_id'] + '.mp3')
                           for row in self.old_tracks]
        decoded = {row['source_id']: row for row in self.source.decoded}
        for entry in self.source.catalog['audioTracks'][20:]:
            sid = entry['sourceId']; raw = decoded[sid]
            self.new_tracks.append({'track_id': str(entry['musicId']), 'source_id': sid, 'source_provider': 'incompetech',
                'asset_filename': 'incompetech-' + sid + '.mp3', 'content_sha256': entry['sha256'],
                'bytes': entry['contentBytes'], 'download_proof_sha256': ev.file_hash(root / (sid + '.download.json')),
                'source_url': entry['sourceUrl'], 'license_url': entry['licenseUrl'],
                'title': entry['title'], 'artist': entry['artist'], 'provider_duration_seconds': entry['durationSeconds'],
                'recorded_decode': {key: raw[key] for key in ('frames', 'sample_rate_hz', 'channels', 'format', 'duration_ms')},
                'format': 'MP3', 'source_frames': raw['frames'], 'source_sample_rate_hz': raw['sample_rate_hz'],
                'source_channels': raw['channels'], 'sample_rate_hz': 48000,
                'decoded_samples': 60 * 48000, 'duration_ms': 60000})
        self.new_tracks.sort(key=lambda row: int(row['track_id']))
        self.new_artifacts = {'corpus-manifest.json': {'schema': 'sonora-research-corpus-v1',
            'pipeline_version': ev.PIPELINE, 'tracks': self.new_tracks},
            'segments.json': windows(self.new_tracks), 'queries.json': deepcopy(self.source.queries),
            'rankings.json': {'judgments': 'unjudged', 'queries': []}}
        sources_by_query = {qid: sorted((str(row['musicId']) for row in self.source.catalog['audioTracks'][20:]
            if next(choice for choice in self.source.selection['tracks'] if choice['isrc'] == row['sourceId'])['bucket_id'] == qid), key=int)
            for qid in ev.TARGETS}
        new_ids = {str(row['musicId']) for row in self.source.catalog['audioTracks'][20:]}
        for query in self.source.queries['queries']:
            own = sources_by_query.get(query['query_id'], sorted(new_ids, key=int)[:4])
            others = sorted(new_ids - set(own), key=int)
            self.new_artifacts['rankings.json']['queries'].append({'kind': 'text', **query,
                'whole_track': self.ranking([own[-1], others[0], '3', others[1], '1'], self.new_artifacts['segments.json']),
                'segment': self.ranking([*own, '20'], self.new_artifacts['segments.json'], True)})
        self.new_report = {'schema': 'sonora-research-probe-v1', 'status': 'passed_private_research_pipeline_only',
            'working_tree_dirty': False, 'code_sha': 'b' * 40, 'pipeline_version': ev.PIPELINE,
            'model': deepcopy(ev.MODEL), 'preprocessing': deepcopy(ev.PREPROCESSING), 'environment': {'device': 'cpu'},
            'source_hashes': self.hash_sources(), 'counts': {}}
        self.refresh_runs()
        self.rebuild_packages()

    def hash_sources(self):
        return {name: ev.file_hash(self.code / name) for name in ev.SOURCE_NAMES}

    @staticmethod
    def ranking(ids, segments, segment=False):
        result = []
        for index, value in enumerate(ids):
            tid = str(value); score = 1 - index / 10
            row = {'track_id': tid, 'score': score}
            if segment:
                row['segments'] = [dict(next(item for item in segments if item['track_id'] == tid), score=score)]
            result.append(row)
        return result

    def refresh_runs(self):
        self.source.save()
        for run, artifacts, report in ((self.old_run, self.old_artifacts, self.old_report),
                                       (self.new_run, self.new_artifacts, self.new_report)):
            for name, value in artifacts.items(): put(run / name, value)
            (run / 'vectors.npz').write_bytes(b'Synthetic vector artifact; never model evidence')
            report['artifact_sha256'] = {name: ev.file_hash(run / name) for name in ev.ARTIFACTS}
        self.old_report['input_catalog_sha256'] = ev.file_hash(self.source.paths['baseline'])
        self.new_report['input_catalog_sha256'] = self.source.catalog_hash
        self.new_report['input_sha256'] = {name: ev.file_hash(self.source.paths[key]) for name, key in
            (('catalog', 'catalog'), ('source_manifest', 'manifest'), ('decode_report', 'decode'),
             ('baseline_catalog', 'baseline'), ('selection', 'selection'), ('queries', 'queries'))}
        segments = self.new_artifacts['segments.json']
        self.new_report['counts'] = {'tracks': 40, 'segments': len(segments), 'text_queries': 8, 'reference_queries': 0,
            'padded_tail_segments': sum(row['padded_samples'] > 0 for row in segments),
            'decoded_duration_ms': sum(row['duration_ms'] for row in self.new_tracks)}
        put(self.old_run / 'report.json', self.old_report); put(self.new_run / 'report.json', self.new_report)

    def rebuild_packages(self):
        base = rp.prepare(self.old_run, self.source.paths['baseline'], ev.file_hash(self.old_run / 'report.json'))
        self.judge(base, source=False); put(self.package_paths['base'], base)
        diagnostic = dp.prepare(self.old_run, self.source.paths['baseline'], ev.file_hash(self.old_run / 'report.json'),
            self.package_paths['base'], ev.file_hash(self.package_paths['base']), ev.TARGETS)
        self.judge(diagnostic, source=False); put(self.package_paths['diagnostic'], diagnostic)
        source = self.source.build(); self.judge(source, source=True); put(self.package_paths['source'], source)

    @staticmethod
    def judge(pack, source):
        for query in pack['queries']:
            for row in query['candidates']:
                row.update(relevance=3 if source else (2 if row['track_id'] == '3' else 0),
                           annotator='SYNTHETIC_ONLY', judged_at='2026-10-29T10:00:00Z')

    def arguments(self):
        result = {'old_run_dir': self.old_run, 'old_report_sha256': ev.file_hash(self.old_run / 'report.json'),
                  'new_run_dir': self.new_run, 'new_report_sha256': ev.file_hash(self.new_run / 'report.json')}
        for name, key in (('baseline_catalog', 'baseline'), ('import_catalog', 'catalog'),
                          ('source_manifest', 'manifest'), ('decode_report', 'decode'),
                          ('selection', 'selection'), ('query_fixture', 'queries')):
            result[name] = self.source.paths[key]; result[name + '_sha256'] = ev.file_hash(self.source.paths[key])
        for name, path in self.package_paths.items():
            result[name + '_pack'] = path; result[name + '_pack_sha256'] = ev.file_hash(path)
        return result


class ResearchEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.f = Fixture(self.root)
        self.patcher = patch.object(ev, 'SOURCE_ROOT', self.f.code)
        self.patcher.start(); self.addCleanup(self.patcher.stop)

    def evaluate(self, **changes):
        args = self.f.arguments(); args.update(changes)
        return ev.evaluate(**args)

    def test_unknown_preserved_bounds_and_known_source_hits(self):
        before = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        result = self.evaluate()
        self.assertEqual(result['target_query_ids'], list(ev.TARGETS))
        self.assertEqual((result['known_pairs_in_targets'], result['unknown_pairs_in_targets']), (120, 80))
        for query in result['queries']:
            self.assertEqual((query['known_pairs'], query['unknown_pairs']), (24, 16))
            whole, segment = [query['new_modes'][mode] for mode in ev.MODES]
            self.assertEqual((whole['known_relevant'], whole['known_nonrelevant'], whole['unknown']), (2, 1, 2))
            self.assertEqual((whole['precision_at_5_lower'], whole['precision_at_5_upper']), (0.4, 0.8))
            self.assertIsNone(whole['exact_precision_at_5'])
            self.assertEqual(whole['relevance'].count(None), 2)
            self.assertEqual(whole['confirmed_new_source_relevant_hits'], 1)
            self.assertEqual(segment['exact_precision_at_5'], 0.8)
            self.assertEqual(segment['confirmed_new_source_relevant_hits'], 4)
        whole, segment = [result['summary'][mode] for mode in ev.MODES]
        self.assertEqual((whole['new_unknown_returned_positions'], whole['new_fully_judged_queries']), (10, 0))
        self.assertIsNone(whole['new_macro_exact_precision_at_5'])
        self.assertEqual(segment['new_macro_exact_precision_at_5'], 0.8)
        self.assertAlmostEqual(whole['old_macro_exact_precision_at_5'], 0.2)
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_macro_never_excludes_unknown_queries(self):
        q = next(q for q in self.f.new_artifacts['rankings.json']['queries'] if q['query_id'] == ev.TARGETS[0])
        q['whole_track'] = [{k: v for k, v in row.items() if k != 'segments'} for row in q['segment']]
        self.f.refresh_runs(); result = self.evaluate()['summary']['whole_track']
        self.assertEqual(result['new_fully_judged_queries'], 1)
        self.assertEqual(result['new_unknown_returned_positions'], 8)
        self.assertAlmostEqual(result['new_macro_precision_at_5_lower'], 0.48)
        self.assertAlmostEqual(result['new_macro_precision_at_5_upper'], 0.8)
        self.assertIsNone(result['new_macro_exact_precision_at_5'])

    def test_frozen_arrays_are_not_sorted_by_id_or_label(self):
        result = self.evaluate()
        q = result['queries'][0]
        original = next(row for row in self.f.new_artifacts['rankings.json']['queries'] if row['query_id'] == q['query_id'])
        self.assertEqual(q['new_modes']['whole_track']['track_ids'], [r['track_id'] for r in original['whole_track']])
        self.assertEqual(q['old_modes']['whole_track']['track_ids'], list('54321'))
        self.assertNotEqual(q['new_modes']['whole_track']['track_ids'], sorted(q['new_modes']['whole_track']['track_ids'], key=int))
        original['whole_track'].reverse(); self.f.refresh_runs()
        self.assertEqual(self.evaluate()['queries'][0]['new_modes']['whole_track']['track_ids'],
                         [r['track_id'] for r in original['whole_track']])

    def test_all_eleven_explicit_hashes_reject_none_and_wrong(self):
        for name in self.f.arguments():
            if not name.endswith('_sha256'): continue
            for value in (None, '0' * 64):
                with self.subTest(pin=name, value=value), self.assertRaises(ValueError):
                    self.evaluate(**{name: value})

    def test_rebound_package_content_cannot_change_immutable_identity(self):
        for name in ('base', 'diagnostic', 'source'):
            path = self.f.package_paths[name]; raw = path.read_bytes(); pack = json.loads(raw)
            pack['queries'][0]['candidates'][0]['content_sha256'] = '0' * 64
            put(path, pack)
            with self.subTest(package=name), self.assertRaises(ValueError): self.evaluate()
            path.write_bytes(raw)

    def test_missing_human_judgment_in_any_package_rejected(self):
        for name in ('base', 'diagnostic', 'source'):
            path = self.f.package_paths[name]; raw = path.read_bytes(); pack = json.loads(raw)
            pack['queries'][0]['candidates'][0].update(dict.fromkeys(rp.HUMAN_FIELDS)); put(path, pack)
            with self.subTest(package=name), self.assertRaises(ValueError): self.evaluate()
            path.write_bytes(raw)

    def test_all_artifact_raw_hashes_checked_including_vectors(self):
        for name in ev.ARTIFACTS:
            path = self.f.new_run / name; raw = path.read_bytes(); path.write_bytes(raw + b' ')
            with self.subTest(artifact=name), self.assertRaises(ValueError): self.evaluate()
            path.write_bytes(raw)

    def test_changed_old_decode_content_and_proof_rejected_after_rehash(self):
        original = deepcopy(self.f.new_tracks[0])
        for name, value in (('source_frames', original['source_frames'] + 1), ('download_proof_sha256', '0' * 64),
                            ('content_sha256', '0' * 64), ('title', 'Changed old track')):
            self.f.new_tracks[0].update({name: value}); self.f.refresh_runs()
            with self.subTest(field=name), self.assertRaises(ValueError): self.evaluate()
            self.f.new_tracks[0].clear(); self.f.new_tracks[0].update(original)
        self.f.refresh_runs()

    def test_duplicate_or_missing_corpus_track_rejected_after_rehash(self):
        for mutation in ('duplicate', 'missing'):
            old = deepcopy(self.f.new_tracks)
            if mutation == 'duplicate': self.f.new_tracks[1] = deepcopy(self.f.new_tracks[0])
            else: self.f.new_tracks.pop()
            self.f.refresh_runs()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.evaluate()
            self.f.new_tracks[:] = old
        self.f.refresh_runs()

    def test_model_preprocessing_dirty_or_input_binding_mismatch(self):
        mutations = [lambda r: r['model'].update(checkpoint_sha256='0' * 64),
            lambda r: r['model'].update(checkpoint_revision='0' * 40),
            lambda r: r['model'].update(roberta_revision='0' * 40),
            lambda r: r['model'].update(dimension=768), lambda r: r['model'].update(fusion=True),
            lambda r: r['model'].update(strict_missing=['bad']), lambda r: r.update(working_tree_dirty=True),
            lambda r: r['preprocessing'].update(hop_samples=480000), lambda r: r.update(pipeline_version='other'),
            lambda r: r['environment'].update(device='cuda'),
            lambda r: r['input_sha256'].update(selection='0' * 64)]
        original = deepcopy(self.f.new_report)
        for index, mutate in enumerate(mutations):
            self.f.new_report = deepcopy(original); mutate(self.f.new_report)
            put(self.f.new_run / 'report.json', self.f.new_report)
            with self.subTest(index=index), self.assertRaises(ValueError): self.evaluate()
        self.f.new_report = original; self.f.refresh_runs()

    def test_source_hash_cannot_drift_or_old_dependency_change(self):
        path = self.f.code / 'corpus.py'; raw = path.read_bytes(); path.write_bytes(raw + b'changed')
        with self.assertRaises(ValueError): self.evaluate()
        self.f.new_report['source_hashes'] = self.f.hash_sources(); self.f.refresh_runs()
        with self.assertRaisesRegex(ValueError, 'original retrieval dependency'): self.evaluate()

    def test_illegal_or_missing_windows_and_ranked_segment_rejected(self):
        original = deepcopy(self.f.new_artifacts)
        for mutation in ('missing-window', 'wrong-time', 'unknown-ranked-segment'):
            self.f.new_artifacts = deepcopy(original)
            if mutation == 'missing-window': self.f.new_artifacts['segments.json'].pop()
            elif mutation == 'wrong-time': self.f.new_artifacts['segments.json'][0]['end_ms'] += 1
            else: self.f.new_artifacts['rankings.json']['queries'][0]['segment'][0]['segments'][0]['segment_id'] = 'bad'
            self.f.refresh_runs()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.evaluate()
        self.f.new_artifacts = original; self.f.refresh_runs()

    def test_short_duplicate_unknown_rank_or_query_text_change_rejected(self):
        original = deepcopy(self.f.new_artifacts['rankings.json'])
        for mutation in ('short', 'duplicate', 'unknown', 'query-text', 'duplicate-query'):
            ranks = deepcopy(original); query = ranks['queries'][0]
            if mutation == 'short': query['whole_track'].pop()
            elif mutation == 'duplicate': query['whole_track'][1] = deepcopy(query['whole_track'][0])
            elif mutation == 'unknown': query['whole_track'][0]['track_id'] = '9999'
            elif mutation == 'query-text': query['text'] = 'Changed synthetic query'
            else: ranks['queries'].append(deepcopy(query))
            self.f.new_artifacts['rankings.json'] = ranks; self.f.refresh_runs()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.evaluate()
        self.f.new_artifacts['rankings.json'] = original; self.f.refresh_runs()

    def test_semantically_identical_queries_allow_distinct_raw_serializations(self):
        for run, report in ((self.f.old_run, self.f.old_report), (self.f.new_run, self.f.new_report)):
            (run / 'queries.json').write_text(json.dumps(self.f.source.queries, indent=3) + '\n')
            report['artifact_sha256']['queries.json'] = ev.file_hash(run / 'queries.json')
            put(run / 'report.json', report)
        # Baseline package provenance must be rebound to the newly explicitly fixed old report.
        self.f.rebuild_packages()
        self.assertEqual(self.evaluate()['query_count'], 5)
        self.f.new_artifacts['queries.json']['queries'][0]['text'] = 'Changed synthetic query'
        self.f.refresh_runs()
        with self.assertRaises(ValueError): self.evaluate()

    def test_exact_source_resampling_allows_only_derived_one_ms_difference(self):
        row = self.f.source.decoded[0]
        row.update(frames=60 * 44100 + 44, sample_rate_hz=44100)
        tid = str(self.f.source.catalog['audioTracks'][20]['musicId'])
        track = next(row for row in self.f.new_tracks if row['track_id'] == tid)
        track['recorded_decode'].update(frames=60 * 44100 + 44, sample_rate_hz=44100)
        track.update(source_frames=60 * 44100 + 44, source_sample_rate_hz=44100,
                     decoded_samples=2880048, duration_ms=60001)
        self.f.new_artifacts['segments.json'] = windows(self.f.new_tracks)
        self.f.refresh_runs(); self.f.rebuild_packages()
        self.assertEqual(self.evaluate()['query_count'], 5)
        track['duration_ms'] = 60002
        self.f.refresh_runs()
        with self.assertRaisesRegex(ValueError, 'integer-ceiling'): self.evaluate()

    def test_new_source_proof_or_recorded_decode_cannot_change_after_rehash(self):
        track = next(row for row in self.f.new_tracks if row['source_provider'] == 'incompetech')
        original = deepcopy(track)
        for mutation in ('proof', 'recorded'):
            if mutation == 'proof': track['download_proof_sha256'] = '0' * 64
            else: track['recorded_decode']['duration_ms'] += 1
            self.f.refresh_runs()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.evaluate()
            track.clear(); track.update(deepcopy(original))

    def run_cli(self, output):
        arguments = ['research_evaluate.py']
        for key, value in self.f.arguments().items(): arguments.extend(['--' + key.replace('_', '-'), str(value)])
        arguments.extend(['--output', str(output)])
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(rp, 'REPO', self.root), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            try: ev.main(); code = 0
            except SystemExit as exc: code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_private_exclusive_output_and_aggregate_stdout(self):
        output = self.root / '.local' / 'result.json'
        code, stdout, stderr = self.run_cli(output)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        for secret in ('SYNTHETIC_ONLY', 'Synthetic query', 'track_ids', 'relevance', 'judged_at'):
            self.assertNotIn(secret, stdout)
        self.assertIsNone(json.loads(stdout)['summary']['whole_track']['new_macro_exact_precision_at_5'])
        raw = output.read_bytes(); code, stdout, _ = self.run_cli(output)
        self.assertEqual((code, stdout), (1, '')); self.assertEqual(output.read_bytes(), raw)
        code, _, _ = self.run_cli(self.root / 'public.json')
        self.assertEqual(code, 1); self.assertFalse((self.root / 'public.json').exists())

    def test_cli_output_parent_symlink_escape_rejected(self):
        private = self.root / '.local'; private.mkdir()
        (private / 'escape').symlink_to(self.f.old_run, target_is_directory=True)
        code, stdout, _ = self.run_cli(private / 'escape' / 'result.json')
        self.assertEqual((code, stdout), (1, ''))
        self.assertFalse((self.f.old_run / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()

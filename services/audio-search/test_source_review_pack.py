"""Synthetic source-proof/identity tests. No HTTP, model, listening or real judgments."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import review_pack as rp
import source_review_pack as sp


class Fixture:
    def __init__(self, root):
        self.root = root
        self.paths = {name: root / (name + '.json') for name in ('manifest', 'decode', 'catalog', 'queries', 'selection', 'baseline')}
        self.selection = {'schema': 'sonora-source-selection-v1', 'split': sp.SPLIT, 'tracks': []}
        self.baseline = {'ownerId': 42, 'slot': 'a', 'audioTracks': [
            {'source': 'Jamendo', 'sourceId': str(1000 + i), 'musicId': i, 'fileId': i,
             'title': 'Old synthetic ' + str(i), 'sha256': rp.digest(('old' + str(i)).encode())}
            for i in range(1, 21)]}
        self.official, self.tracks, self.decoded, new = [], [], [], []
        for i in range(20):
            sid, bucket = 'USABC' + str(1000000 + i), sp.BUCKETS[i // 4]
            title = 'Synthetic recording ' + str(i)
            record = {'isrc': sid, 'title': title, 'filename': title + '.mp3', 'length': '00:01:00', 'instruments': 'Synthetic'}
            self.official.append(record)
            self.selection['tracks'].append({'bucket_id': bucket, 'isrc': sid, 'title': title})
            raw = ('Synthetic bytes, not real MP3 or listening evidence: ' + str(i)).encode()
            (root / (sid + '.mp3')).write_bytes(raw)
            track = {'provider': 'incompetech', 'source_id': sid, 'bucket_id': bucket, 'title': title,
                     'artist': 'Kevin MacLeod', 'duration_seconds': 60,
                     'source_url': sp.BASE + 'index.html?isrc=' + sid, 'license_url': sp.LICENSE,
                     'download_url': sp.BASE + 'mp3-royaltyfree/Synthetic%20recording%20' + str(i) + '.mp3',
                     'audio_filename': sid + '.mp3', 'metadata_record_sha256': rp.digest(rp.canonical(record)),
                     'provider_instruments': 'Synthetic', 'provider_feel': '', 'provider_bpm': '',
                     'attribution': title + ' — Kevin MacLeod (incompetech.com), CC BY 4.0',
                     'changes': 'Audio file unchanged', 'human_relevance': None, 'sha256': rp.digest(raw), 'bytes': len(raw)}
            self.tracks.append(track)
            self.decoded.append({'source_id': sid, 'bucket_id': bucket, 'frames': 48000 * 60, 'sample_rate_hz': 48000,
                                 'channels': 2, 'format': 'MP3', 'duration_ms': 60000, 'finite_samples': True,
                                 'provider_duration_delta_ms': 0, 'metadata_within_2000ms': True})
            new.append({'sourceProvider': 'incompetech', 'source': 'Incompetech', 'sourceId': sid,
                        'musicId': 120 - i, 'fileId': 220 - i, 'title': title, 'artist': 'Kevin MacLeod', 'album': '',
                        'durationSeconds': 60, 'decodedDurationMs': 60000, 'contentBytes': len(raw),
                        'sourceUrl': track['source_url'], 'licenseUrl': sp.LICENSE, 'license': 'CC BY 4.0',
                        'changes': 'Audio file unchanged', 'sha256': track['sha256'], 'rangeVerified': True, 'fullBytesVerified': True})
        snapshot_raw = {'official-catalog.json': rp.canonical(self.official),
                        'official-track-template.html': b'Licensed under Creative Commons: By Attribution 4.0 License creativecommons.org/licenses/by/4.0/ encodeURIComponent(p.filename)',
                        'official-license.html': b'Creative Commons Requires that you credit'}
        self.snapshots = {}
        for name, raw in snapshot_raw.items():
            (root / name).write_bytes(raw)
            url = sp.BASE + {'official-catalog.json': 'pieces.json',
                             'official-track-template.html': 'index.html?isrc=' + self.tracks[0]['source_id'],
                             'official-license.html': 'licenses/'}[name]
            self.snapshots[name] = {'url': url, 'sha256': rp.digest(raw)}
        self.manifest = {'schema': 'sonora-source-candidates-v1', 'split': sp.SPLIT, 'created_at': 'synthetic-only',
                         'selection_sha256': '', 'baseline_catalog_sha256': '', 'collector_sha256': 'a' * 64,
                         'snapshots': self.snapshots, 'tracks': self.tracks, 'limits': ['Synthetic proof fixtures only']}
        self.decode = {'status': 'passed_full_source_decode_with_metadata_differences', 'manifest_sha256': '',
                       'verification_script_sha256': 'b' * 64, 'tracks': self.decoded,
                       'counts': {'decoded': 20, 'finite': 20, 'hash_and_proof_matched': 20,
                                  'duration_metadata_within_2000ms': 20, 'duration_metadata_outside_2000ms': 0,
                                  'human_judged': 0, 'java_imported': 0},
                       'total_duration_ms': 1200000, 'min_duration_ms': 60000, 'max_duration_ms': 60000}
        self.catalog = {'schema': 'sonora-research-catalog-v1', 'ownerId': 42, 'slot': 'a',
                        'baseline_catalog_sha256': '', 'source_manifest_sha256': '', 'decode_report_sha256': '',
                        'importer_sha256': 'c' * 64,
                        'audioTracks': [{**row, 'sourceProvider': 'jamendo'} for row in self.baseline['audioTracks']] + new}
        self.queries = {'split': 'exploratory_unjudged', 'queries': [
            {'query_id': qid, 'text': 'Synthetic query ' + qid} for qid in sp.BUCKETS]}
        self.save()

    def save(self):
        def write(name, obj):
            raw = rp.canonical(obj)
            self.paths[name].write_bytes(raw)
            return rp.digest(raw)
        self.manifest['selection_sha256'] = write('selection', self.selection)
        self.manifest['baseline_catalog_sha256'] = write('baseline', self.baseline)
        self.manifest_hash = write('manifest', self.manifest)
        self.decode['manifest_sha256'] = self.manifest_hash
        self.decode_hash = write('decode', self.decode)
        self.catalog.update(baseline_catalog_sha256=self.manifest['baseline_catalog_sha256'],
                            source_manifest_sha256=self.manifest_hash, decode_report_sha256=self.decode_hash)
        self.catalog_hash = write('catalog', self.catalog)
        self.query_hash = write('queries', self.queries)
        for track in self.tracks:
            proof = {'sha256': track['sha256'], 'size': track['bytes'], 'source': track['source_url'],
                     'license': track['license_url'], 'download_url': track['download_url'],
                     'metadata_record_sha256': track['metadata_record_sha256'], 'snapshots': self.snapshots}
            (self.root / (track['source_id'] + '.download.json')).write_bytes(rp.canonical(proof))

    def build(self, **changes):
        args = dict(source_manifest_path=self.paths['manifest'], decode_report_path=self.paths['decode'],
                    import_catalog_path=self.paths['catalog'], query_fixture_path=self.paths['queries'],
                    expected_manifest_sha256=self.manifest_hash, expected_decode_sha256=self.decode_hash,
                    expected_catalog_sha256=self.catalog_hash, expected_query_sha256=self.query_hash,
                    selection_path=self.paths['selection'], baseline_catalog_path=self.paths['baseline'])
        args.update(changes)
        return sp.prepare(**args)


class SourcePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))

    def test_complete_null_source_pack_and_fixture_order(self):
        pack = self.f.build()
        self.assertEqual(pack['schema'], sp.SCHEMA)
        self.assertEqual(pack['split'], sp.SPLIT)
        self.assertEqual([q['query_id'] for q in pack['queries']], list(sp.BUCKETS))
        self.assertEqual(set(pack['provenance']), {'source_manifest_sha256', 'decode_report_sha256',
            'import_catalog_sha256', 'source_selection_sha256', 'query_fixture_sha256', 'selection', 'ordering', 'labeling_aid'})
        rows = [row for q in pack['queries'] for row in q['candidates']]
        self.assertEqual(len({row['track_id'] for row in rows}), 20)
        for q in pack['queries']:
            self.assertEqual(len(q['candidates']), 4)
            self.assertEqual([int(r['track_id']) for r in q['candidates']], sorted(int(r['track_id']) for r in q['candidates']))
        for row in rows:
            self.assertTrue(all(row[k] is None for k in rp.HUMAN_FIELDS))
            self.assertEqual(row['model_suggested_intervals_ms'], [])
        result = sp.validate(pack, pack)
        self.assertEqual((result['candidate_pairs'], result['unjudged']), (20, 20))
        self.assertFalse(result['identity_or_listening_verified'])

    def test_all_explicit_pins_reject_none_and_wrong(self):
        for key in ('expected_manifest_sha256', 'expected_decode_sha256', 'expected_catalog_sha256', 'expected_query_sha256'):
            for wrong in (None, '0' * 64, 'bad'):
                with self.subTest(key=key, wrong=wrong), self.assertRaises(ValueError):
                    self.f.build(**{key: wrong})

    def test_selection_and_baseline_pins_are_enforced(self):
        for name in ('selection', 'baseline'):
            before = self.f.paths[name].read_bytes()
            self.f.paths[name].write_bytes(before + b' ')
            with self.subTest(name=name), self.assertRaises(ValueError): self.f.build()
            self.f.paths[name].write_bytes(before)

    def test_duplicate_json_keys_rejected_even_with_matching_explicit_sha(self):
        raw = self.f.paths['catalog'].read_bytes().replace(b'"ownerId":42', b'"ownerId":42,"ownerId":42')
        self.f.paths['catalog'].write_bytes(raw)
        with self.assertRaises(ValueError): self.f.build(expected_catalog_sha256=rp.digest(raw))

    def test_input_change_after_initial_read_is_rejected(self):
        original = rp.read_json
        path = self.f.root / self.f.tracks[0]['audio_filename']
        def read_then_change(target, *args, **kwargs):
            result = original(target, *args, **kwargs)
            if Path(target) == self.f.paths['queries']:
                path.write_bytes(b'Changed after initial content check')
            return result
        with patch.object(rp, 'read_json', side_effect=read_then_change):
            with self.assertRaisesRegex(ValueError, 'Input changed'):
                self.f.build()

    def test_source_audio_and_proof_and_snapshots_must_match(self):
        names = [self.f.tracks[0]['audio_filename'], self.f.tracks[0]['source_id'] + '.download.json', *self.f.snapshots]
        for name in names:
            path = self.f.root / name
            before = path.read_bytes()
            if name.endswith('.download.json'):
                proof = json.loads(before); proof['sha256'] = '0' * 64
                path.write_bytes(rp.canonical(proof))
            else:
                path.write_bytes(before + b' ')
            with self.subTest(name=name), self.assertRaises(ValueError): self.f.build()
            path.write_bytes(before)

    def test_symlink_evidence_escape_rejected(self):
        path = self.f.root / self.f.tracks[0]['audio_filename']
        other = self.f.root / 'outside.mp3'; path.rename(other); path.symlink_to(other)
        with self.assertRaises(ValueError): self.f.build()

    def test_imported_owner_source_content_duration_and_verification(self):
        original = deepcopy(self.f.catalog)
        mutations = [lambda c: c.update(ownerId=43), lambda c: c.update(ownerId=True),
            lambda c: c['audioTracks'][20].update(sourceUrl=sp.BASE + 'index.html?isrc=USABC9999999'),
            lambda c: c['audioTracks'][20].update(sourceProvider='jamendo'),
            lambda c: c['audioTracks'][20].update(sourceId='usabc1000000'),
            lambda c: c['audioTracks'][20].update(licenseUrl='https://evil.invalid/'),
            lambda c: c['audioTracks'][20].update(sha256='d' * 64),
            lambda c: c['audioTracks'][20].update(decodedDurationMs=60001),
            lambda c: c['audioTracks'][20].update(durationSeconds=61),
            lambda c: c['audioTracks'][20].update(contentBytes=1),
            lambda c: c['audioTracks'][20].update(album='Invented album'),
            lambda c: c['audioTracks'][20].update(rangeVerified=False),
            lambda c: c['audioTracks'][20].update(fullBytesVerified=False),
            lambda c: c['audioTracks'][20].update(musicId='120'),
            lambda c: c['audioTracks'][20].update(fileId=True),
            lambda c: c['audioTracks'][20].update(musicId=9223372036854775808)]
        for index, change in enumerate(mutations):
            self.f.catalog = deepcopy(original); change(self.f.catalog); self.f.save()
            with self.subTest(index=index), self.assertRaises(ValueError): self.f.build()

    def test_original_tracks_are_exact_copies_and_no_missing_duplicate(self):
        original = deepcopy(self.f.catalog)
        mutations = [lambda c: c['audioTracks'][0].update(title='Changed old'),
            lambda c: c['audioTracks'][20].update(musicId=1),
            lambda c: c['audioTracks'][20].update(fileId=1),
            lambda c: c['audioTracks'][21].update(sourceId=c['audioTracks'][20]['sourceId']),
            lambda c: c['audioTracks'].pop(),
            lambda c: c['audioTracks'].__setitem__(20, deepcopy(c['audioTracks'][0]))]
        for index, change in enumerate(mutations):
            self.f.catalog = deepcopy(original); change(self.f.catalog); self.f.save()
            with self.subTest(index=index), self.assertRaises(ValueError): self.f.build()

    def test_selection_groups_and_duplicates_are_rejected(self):
        original = deepcopy(self.f.selection)
        for change in (lambda p: p['tracks'].pop(), lambda p: p['tracks'][0].update(bucket_id='exp-03'),
                       lambda p: p['tracks'][0].update(isrc=p['tracks'][1]['isrc'])):
            self.f.selection = deepcopy(original); change(self.f.selection); self.f.save()
            with self.assertRaises(ValueError): self.f.build()

    def test_decode_frames_duration_finite_and_counts(self):
        original = deepcopy(self.f.decode)
        mutations = [lambda d: d['tracks'][0].update(frames=1), lambda d: d['tracks'][0].update(finite_samples=False),
            lambda d: d['tracks'][0].update(provider_duration_delta_ms=1),
            lambda d: d['tracks'][0].update(source_id=d['tracks'][1]['source_id']),
            lambda d: d['counts'].update(finite=19), lambda d: d.update(total_duration_ms=1)]
        for change in mutations:
            self.f.decode = deepcopy(original); change(self.f.decode); self.f.save()
            with self.assertRaises(ValueError): self.f.build()

    def test_official_record_manifest_identity_and_filename(self):
        original = deepcopy(self.f.manifest)
        for field, wrong in (('source_url', 'javascript:alert(1)'), ('audio_filename', '../outside.mp3'),
                             ('metadata_record_sha256', '0' * 64), ('title', 'Changed'), ('human_relevance', 2)):
            self.f.manifest = deepcopy(original); self.f.manifest['tracks'][0][field] = wrong; self.f.save()
            with self.subTest(field=field), self.assertRaises(ValueError): self.f.build()

    def test_missing_and_duplicate_fixture_queries(self):
        original = deepcopy(self.f.queries)
        for change in (lambda q: q['queries'].pop(), lambda q: q['queries'][0].update(query_id=q['queries'][1]['query_id'])):
            self.f.queries = deepcopy(original); change(self.f.queries); self.f.save()
            with self.assertRaises(ValueError): self.f.build()

    def test_out_of_order_target_fixture_rejected_without_reordering(self):
        self.f.queries['queries'].reverse()
        self.f.save()
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            self.f.build()

    def test_short_decode_rejected_even_with_consistent_rebound_evidence(self):
        row = self.f.decode['tracks'][0]
        row.update(frames=48000, duration_ms=1000, provider_duration_delta_ms=-59000,
                   metadata_within_2000ms=False)
        self.f.decode['counts'].update(duration_metadata_within_2000ms=19,
                                       duration_metadata_outside_2000ms=1)
        self.f.decode.update(total_duration_ms=1141000, min_duration_ms=1000)
        self.f.catalog['audioTracks'][20]['decodedDurationMs'] = 1000
        self.f.save()
        with self.assertRaisesRegex(ValueError, 'Integer outside allowed range'):
            self.f.build()

    def test_only_four_human_fields_may_change(self):
        expected = self.f.build(); pack = deepcopy(expected)
        row = pack['queries'][0]['candidates'][0]
        row.update(relevance=2, annotator='SYNTHETIC_ONLY', judged_at='2026-01-01T00:00:00Z', human_intervals_ms=[[0, 1000]])
        result = sp.validate(pack, expected)
        self.assertEqual((result['judged'], result['human_intervals']), (1, 1))
        for wrong in (False, 4, -1, 1.0):
            row['relevance'] = wrong
            with self.assertRaises(ValueError): sp.validate(pack, expected)
        row['relevance'] = None
        with self.assertRaises(ValueError): sp.validate(pack, expected)

    def test_immutable_schema_provenance_and_suggestions(self):
        expected = self.f.build()
        mutations = [lambda p: p.update(schema=rp.SCHEMA), lambda p: p.update(split=rp.SPLIT),
            lambda p: p['provenance'].update(checkpoint_sha256='a' * 64),
            lambda p: p['queries'][0]['candidates'][0].update(model_suggested_intervals_ms=[[0, 1000]]),
            lambda p: p['queries'][0]['candidates'][0].update(extra='unexpected'),
            lambda p: p['queries'][0]['candidates'].pop(), lambda p: p.update(owner_user_id='43')]
        for change in mutations:
            pack = deepcopy(expected); change(pack)
            with self.assertRaises(ValueError): sp.validate(pack, expected)

    def test_output_exclusive_and_private(self):
        (rp.REPO / '.local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=rp.REPO / '.local') as directory:
            path = Path(directory) / 'synthetic.json'
            pack = self.f.build(); rp.write_new(path, pack)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): rp.write_new(path, pack)
            self.assertEqual(before, path.read_bytes())
        with self.assertRaises(ValueError): rp.write_new(self.f.root / 'outside.json', pack)

    def test_cli_build_validate_and_reject_missing_pin(self):
        script = Path(sp.__file__)
        arguments = []
        for name, key, digest in [('source-manifest', 'manifest', self.f.manifest_hash),
                                 ('decode-report', 'decode', self.f.decode_hash),
                                 ('import-catalog', 'catalog', self.f.catalog_hash),
                                 ('query-fixture', 'queries', self.f.query_hash)]:
            arguments += ['--' + name, str(self.f.paths[key]), '--' + name + '-sha256', digest]
        arguments += ['--selection', str(self.f.paths['selection']), '--baseline-catalog', str(self.f.paths['baseline'])]
        with tempfile.TemporaryDirectory(dir=rp.REPO / '.local') as directory:
            path = Path(directory) / 'synthetic.json'
            result = subprocess.run([sys.executable, str(script), 'build', *arguments, '--output', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['unjudged'], 20)
            result = subprocess.run([sys.executable, str(script), 'validate', *arguments, '--pack', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['split'], sp.SPLIT)
            result = subprocess.run([sys.executable, str(script), 'build', '--output', str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()

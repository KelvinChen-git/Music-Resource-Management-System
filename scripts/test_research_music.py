"""Offline collection guards; synthetic bytes are not evidence of decodable music."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

import collect_research_music as collector


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


class ResearchMusicCollectionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.private = self.root / '.local' / 'a'
        self.private.mkdir(parents=True, mode=0o700)
        self.output = self.private / 'new-batch'
        root_patch = patch.object(collector, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.rows, self.catalog = [], []
        for index in range(20):
            sid = 'USABC' + str(2400001 + index)
            title = 'Synthetic piece ' + str(index)
            self.rows.append({'bucket_id': collector.BUCKETS[index // 4],
                              'isrc': sid, 'title': title})
            self.catalog.append({'isrc': sid, 'title': title, 'filename': title + '.mp3',
                                 'length': '00:02:00', 'instruments': 'Synthetic instrument',
                                 'feel': 'Synthetic mood', 'bpm': '80'})
        self.plan = {'schema': collector.SCHEMA, 'split': collector.SPLIT,
                     'tracks': self.rows}
        self.selection = self.root / 'selection.json'
        self.baseline = self.root / 'baseline.json'
        self.selection.write_bytes(encoded(self.plan))
        self.old_audio = b'ID3 prior synthetic content'
        self.baseline.write_bytes(encoded({'audioTracks': [{'sha256': sha(self.old_audio)}]}))
        self.selection_sha = sha(self.selection.read_bytes())
        self.baseline_sha = sha(self.baseline.read_bytes())
        self.template = (
            b'Licensed under Creative Commons: By Attribution 4.0 License '
            b'https://creativecommons.org/licenses/by/4.0/ '
            b'encodeURIComponent(p.filename)')
        self.license = b'Creative Commons: Requires that you credit the composer.'
        self.audio = {
            collector.BASE + 'mp3-royaltyfree/' + row['title'].replace(' ', '%20') + '.mp3':
            b'ID3 synthetic fixture ' + row['isrc'].encode()
            for row in self.rows
        }
        self.calls = []

    def fetch(self, url, limit):
        self.calls.append((url, limit))
        if url == collector.BASE + 'pieces.json':
            return encoded(self.catalog)
        if url == collector.BASE + 'index.html?isrc=' + self.rows[0]['isrc']:
            return self.template
        if url == collector.BASE + 'licenses/':
            return self.license
        return self.audio[url]

    def run_batch(self, **overrides):
        arguments = {'output': self.output, 'selection': self.selection,
                     'selection_sha256': self.selection_sha,
                     'baseline_catalog': self.baseline,
                     'baseline_sha256': self.baseline_sha, 'fetch': self.fetch}
        arguments.update(overrides)
        return collector.run(**arguments)

    def replace_plan(self, plan):
        self.selection.write_bytes(encoded(plan))
        self.selection_sha = sha(self.selection.read_bytes())

    def rejected_before_network(self, **overrides):
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            self.run_batch(**overrides)
        self.assertEqual([], self.calls)
        self.assertFalse(self.output.exists())

    def test_selected_source_identity_and_four_per_bucket(self):
        tracks = collector.select_tracks(self.catalog, self.plan)
        self.assertEqual([row['isrc'] for row in self.rows],
                         [track['source_id'] for track in tracks])
        self.assertEqual(20, len({track['source_id'] for track in tracks}))
        self.assertEqual({bucket: 4 for bucket in collector.BUCKETS},
                         {bucket: sum(track['bucket_id'] == bucket for track in tracks)
                          for bucket in collector.BUCKETS})
        self.assertTrue(all(track['human_relevance'] is None for track in tracks))
        self.assertTrue(all(track['duration_seconds'] == 120 for track in tracks))

    def test_plan_shape_ids_and_quota_are_rejected_before_network(self):
        changes = []
        for key, value in [('schema', 'other'), ('split', 'held_out')]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            changes.append(plan)
        plan = copy.deepcopy(self.plan)
        plan['unexpected'] = True
        changes.append(plan)
        for change in [{'bucket_id': 'unknown'}, {'isrc': '../../other'},
                       {'isrc': self.rows[0]['isrc']}, {'musicId': '42'}]:
            plan = copy.deepcopy(self.plan)
            plan['tracks'][1].update(change)
            changes.append(plan)
        plan = copy.deepcopy(self.plan)
        plan['tracks'][-1]['bucket_id'] = 'exp-02'
        changes.append(plan)
        plan = copy.deepcopy(self.plan)
        plan['tracks'].pop()
        changes.append(plan)
        for plan in changes:
            with self.subTest(plan=plan):
                self.replace_plan(plan)
                self.rejected_before_network()

    def test_missing_ambiguous_or_changed_official_record_is_rejected(self):
        catalogs = [self.catalog[1:], self.catalog + [self.catalog[0]]]
        changed = copy.deepcopy(self.catalog)
        changed[0]['title'] += ' changed'
        catalogs.append(changed)
        for catalog in catalogs:
            with self.subTest(catalog=catalog):
                with self.assertRaises(ValueError):
                    collector.select_tracks(catalog, self.plan)

    def test_duration_is_formatted_bounded_and_not_a_synthetic_long_track(self):
        for length, seconds in [('00:00:30', 30), ('00:10:00', 600)]:
            catalog = copy.deepcopy(self.catalog)
            catalog[0]['length'] = length
            self.assertEqual(seconds, collector.select_tracks(catalog, self.plan)[0]['duration_seconds'])
        for length in ['00:00:29', '00:10:01', '01:00:00', '00:60:00',
                       '0:02:00', '120', 120, None]:
            catalog = copy.deepcopy(self.catalog)
            catalog[0]['length'] = length
            with self.subTest(length=length), self.assertRaises(ValueError):
                collector.select_tracks(catalog, self.plan)

    def test_filename_must_be_a_safe_mp3_basename(self):
        for filename in ['../piece.mp3', 'sub/piece.mp3', r'sub\piece.mp3',
                         'piece..mp3', 'piece.mp3?x=1', 'piece.mp3#fragment',
                         '%2e%2e.mp3', 'piece\n.mp3', 'piece\x7f.mp3', 'piece.wav', None]:
            catalog = copy.deepcopy(self.catalog)
            catalog[0]['filename'] = filename
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                collector.select_tracks(catalog, self.plan)

    def test_official_https_urls_allow_only_known_paths_and_exact_queries(self):
        valid = [collector.BASE + 'pieces.json', collector.BASE + 'licenses/',
                 collector.BASE + 'index.html?isrc=' + self.rows[0]['isrc'],
                 collector.BASE + 'mp3-royaltyfree/Valid%20piece.mp3',
                 'https://www.incompetech.com:443/music/royalty-free/pieces.json']
        for url in valid:
            self.assertEqual(url, collector.safe_url(url))
        invalid = [url.replace('https:', 'http:') for url in valid[:1]] + [
            'https://incompetech.com.evil.example/music/royalty-free/pieces.json',
            'https://user:secret@incompetech.com/music/royalty-free/pieces.json',
            'https://incompetech.com:8443/music/royalty-free/pieces.json',
            collector.BASE + '../private.json', collector.BASE + 'pieces.json?x=1',
            collector.BASE + 'licenses/#x', collector.BASE + 'index.html',
            collector.BASE + 'index.html?isrc=' + self.rows[0]['isrc'] + '&extra=1',
            collector.BASE + 'mp3-royaltyfree/%2e%2e%2fsecret.mp3',
            collector.BASE + 'mp3-royaltyfree/one%5ctwo.mp3',
            'file:///music/royalty-free/pieces.json']
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                collector.safe_url(url)

    def test_redirects_cannot_escape_origin_or_change_recording(self):
        original = collector.BASE + 'index.html?isrc=' + self.rows[0]['isrc']
        request = Request(original)
        handler = collector.OfficialRedirects()
        for destination in ['https://evil.example/track.mp3',
                            collector.BASE + 'index.html?isrc=' + self.rows[1]['isrc'],
                            collector.BASE + 'pieces.json']:
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, 'Found', {}, destination)
        destination = original.replace('https://incompetech.com/', 'https://www.incompetech.com/')
        redirected = handler.redirect_request(request, None, 302, 'Found', {}, destination)
        self.assertEqual(destination, redirected.full_url)

    def test_explicit_selection_and_baseline_sha_are_required_before_network(self):
        for name in ['selection_sha256', 'baseline_sha256']:
            for pin in [None, '', 'A' * 64, '0' * 64, '0' * 63]:
                with self.subTest(name=name, pin=pin):
                    self.rejected_before_network(**{name: pin})

    def test_malformed_duplicate_key_or_missing_original_hash_is_rejected_before_network(self):
        for raw in [b'{"audioTracks":[],"audioTracks":[]}', b'{}',
                    encoded({'audioTracks': []}), encoded({'audioTracks': [{}]}),
                    encoded({'audioTracks': [{'sha256': 'not-a-sha'}]})]:
            self.baseline.write_bytes(raw)
            with self.subTest(raw=raw):
                self.rejected_before_network(baseline_sha256=sha(raw))

    def test_existing_output_is_preserved_without_network(self):
        self.output.mkdir()
        marker = self.output / 'partial-evidence'
        marker.write_bytes(b'preserve existing partial or complete batch')
        with self.assertRaises(FileExistsError):
            self.run_batch()
        self.assertEqual([], self.calls)
        self.assertEqual(b'preserve existing partial or complete batch', marker.read_bytes())

    def test_output_outside_private_tree_or_through_symlink_is_rejected(self):
        link = self.private / 'linked'
        link.symlink_to(self.private, target_is_directory=True)
        for output in [self.root / 'public-batch', self.root / '.local', link / 'batch']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.run_batch(output=output)
            self.assertEqual([], self.calls)
        self.assertFalse((self.root / 'public-batch').exists())

    def test_success_preserves_sources_proofs_permissions_and_inputs(self):
        original_inputs = [self.selection.read_bytes(), self.baseline.read_bytes()]
        summary = self.run_batch()
        self.assertEqual('collected_source_candidates', summary['status'])
        self.assertEqual((20, 0, 0), (summary['tracks'], summary['human_judged'], summary['java_imported']))
        self.assertEqual({bucket: 4 for bucket in collector.BUCKETS}, summary['buckets'])
        manifest_bytes = (self.output / 'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertEqual('sonora-source-candidates-v1', manifest['schema'])
        self.assertEqual(collector.SPLIT, manifest['split'])
        self.assertEqual(self.selection_sha, manifest['selection_sha256'])
        self.assertEqual(self.baseline_sha, manifest['baseline_catalog_sha256'])
        self.assertEqual(sha(manifest_bytes), summary['manifest_sha256'])
        self.assertEqual(0o700, stat.S_IMODE(self.output.stat().st_mode))
        self.assertEqual(23, len(self.calls))
        self.assertEqual([collector.BASE + 'pieces.json',
                          collector.BASE + 'index.html?isrc=' + self.rows[0]['isrc'],
                          collector.BASE + 'licenses/'], [url for url, _ in self.calls[:3]])
        self.assertTrue(all(limit == collector.MAX_METADATA for _, limit in self.calls[:3]))
        self.assertTrue(all(limit == collector.MAX_AUDIO for _, limit in self.calls[3:]))
        for path in self.output.iterdir():
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        forbidden = {'musicId', 'music_id', 'owner', 'owner_id', 'annotator', 'judged_at',
                     'relevance', 'human_intervals_ms'}
        for track in manifest['tracks']:
            self.assertFalse(forbidden.intersection(track))
            self.assertIsNone(track['human_relevance'])
            audio = (self.output / track['audio_filename']).read_bytes()
            self.assertEqual(self.audio[track['download_url']], audio)
            self.assertEqual((sha(audio), len(audio)), (track['sha256'], track['bytes']))
            proof = json.loads((self.output / (track['source_id'] + '.download.json')).read_bytes())
            self.assertEqual(track['sha256'], proof['sha256'])
            self.assertEqual(track['metadata_record_sha256'], proof['metadata_record_sha256'])
            self.assertEqual(manifest['snapshots'], proof['snapshots'])
        self.assertEqual(sum(len(value) for value in self.audio.values()), summary['bytes'])
        self.assertEqual(original_inputs, [self.selection.read_bytes(), self.baseline.read_bytes()])

    def test_changed_license_or_download_template_stops_before_audio(self):
        template, license_page = self.template, self.license
        for attribute in ['template', 'license']:
            with self.subTest(attribute=attribute):
                self.template, self.license = template, license_page
                setattr(self, attribute, b'Changed source page without attribution evidence')
                output = self.private / ('bad-' + attribute)
                with self.assertRaises(ValueError):
                    self.run_batch(output=output)
                self.assertFalse((output / 'manifest.json').exists())
                self.assertEqual(3, len(self.calls))
                self.calls.clear()

    def test_invalid_metadata_response_never_produces_manifest(self):
        for index, invalid in enumerate([b'', 'not bytes', b'x' * (collector.MAX_METADATA + 1)]):
            def invalid_fetch(url, limit):
                self.calls.append((url, limit))
                return invalid

            with self.subTest(case=index):
                output = self.private / ('bad-metadata-' + str(index))
                with self.assertRaises(ValueError):
                    self.run_batch(output=output, fetch=invalid_fetch)
                self.assertEqual(1, len(self.calls))
                self.assertFalse((output / 'manifest.json').exists())
                self.calls.clear()

    def test_empty_html_and_oversized_audio_leave_no_final_manifest(self):
        first = next(iter(self.audio))
        for index, invalid in enumerate([b'', b' \n<html>not audio</html>', b'x' * 9]):
            with self.subTest(invalid=invalid):
                self.audio[first] = invalid
                output = self.private / ('bad-audio-' + str(index))
                with patch.object(collector, 'MAX_AUDIO', 8 if index == 2 else 1024):
                    with self.assertRaises(ValueError):
                        self.run_batch(output=output)
                self.assertFalse((output / 'manifest.json').exists())
                self.assertEqual(4, len(self.calls))
                self.calls.clear()

    def test_duplicate_new_audio_and_original_content_are_rejected(self):
        urls = list(self.audio)
        cases = [(urls[1], self.audio[urls[0]]), (urls[0], self.old_audio)]
        for index, (url, content) in enumerate(cases):
            with self.subTest(case=index):
                self.audio[url] = content
                output = self.private / ('duplicate-' + str(index))
                with self.assertRaises(ValueError):
                    self.run_batch(output=output)
                self.assertFalse((output / 'manifest.json').exists())

    def test_fetch_failure_preserves_partial_evidence_but_never_completes(self):
        normal_fetch = self.fetch

        def failing_fetch(url, limit):
            if len(self.calls) == 4:
                raise OSError('synthetic interruption')
            return normal_fetch(url, limit)

        with self.assertRaises(OSError):
            self.run_batch(fetch=failing_fetch)
        self.assertTrue((self.output / 'official-catalog.json').is_file())
        self.assertTrue((self.output / (self.rows[0]['isrc'] + '.mp3')).is_file())
        self.assertFalse((self.output / 'manifest.json').exists())

    def test_input_change_during_acquisition_prevents_final_manifest(self):
        normal_fetch = self.fetch

        def changing_fetch(url, limit):
            raw = normal_fetch(url, limit)
            if len(self.calls) == 23:
                self.selection.write_bytes(self.selection.read_bytes() + b'\n')
            return raw

        with self.assertRaises(ValueError):
            self.run_batch(fetch=changing_fetch)
        self.assertEqual(23, len(self.calls))
        self.assertFalse((self.output / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()

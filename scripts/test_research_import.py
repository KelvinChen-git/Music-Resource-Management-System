"""Synthetic local-transport tests; no real credentials, HTTP, decoder or database."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import collect_research_music as collector
import import_research_music as importer


def raw(value):
    return json.dumps(value).encode()


class FakeLocal:
    def __init__(self, owner, old_tracks, audio):
        self.owner, self.role, self.token = owner, 'USER', None
        self.files, self.resources, self.calls = {}, [], []
        self.uploads = self.metadata = 0
        self.lose_upload = self.lose_metadata = False
        self.bad_media = None
        self.login_fails = False
        for track in old_tracks:
            body = audio[track['sourceId']]
            path = 'old/' + track['sourceId'] + '.mp3'
            self.files[track['fileId']] = {'id': track['fileId'], 'ownerUserId': owner,
                'fileSize': len(body), 'fileMd5': hashlib.md5(body).hexdigest(), 'filePath': path,
                'status': 1, 'audio': body}
            self.resources.append({'musicid': track['musicId'], 'userid': owner, 'filePath': path,
                'fileSize': len(body), 'format': 'mp3', 'isDeleted': False,
                'title': track['title'], 'artist': track['artist'], 'album': track['album']})

    def api(self, method, url, body=None, binary=None, headers=None):
        self.calls.append((method, url))
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        if parsed.path == '/auth/login':
            if self.login_fails:
                raise RuntimeError('Synthetic rejected credentials; no registration fallback')
            return {'token': 'synthetic-secret-token'}
        if parsed.path == '/auth/profile':
            return {'userid': self.owner, 'role': self.role}
        if parsed.path == '/file/check':
            found = [f for f in self.files.values() if f['fileMd5'] == params['fileMd5'][0]]
            if not found:
                return {'exists': False}
            return {'exists': True, 'fileId': found[0]['id'], 'filePath': found[0]['filePath']}
        if parsed.path == '/file/upload':
            boundary = headers['Content-Type'].split('boundary=')[1].encode()
            content = binary.split(b'\r\n\r\n', 1)[1].rsplit(b'\r\n--' + boundary, 1)[0]
            fid = 1000 + self.uploads
            self.uploads += 1
            uploaded = {'id': fid, 'ownerUserId': self.owner, 'fileSize': len(content),
                'fileMd5': hashlib.md5(content).hexdigest(), 'filePath': 'new/' + str(fid) + '.mp3',
                'status': 1, 'audio': content}
            self.files[fid] = uploaded
            if self.lose_upload:
                self.lose_upload = False
                raise RuntimeError('Synthetic response lost after upload commit')
            return {k: v for k, v in uploaded.items() if k != 'audio'}
        if parsed.path == '/music-resources/list':
            assert params['onlyMine'] == ['true']
            found = [r for r in self.resources if params['title'][0] in r['title']]
            current, size = int(params['current'][0]), int(params['pageSize'][0])
            return {'records': found[(current - 1) * size:current * size], 'total': len(found)}
        if parsed.path == '/music-resources/metadata':
            upload = self.files[int(params['fileId'][0])]
            self.resources.append({**body, 'musicid': 2000 + self.metadata, 'userid': self.owner,
                'filePath': upload['filePath'], 'fileSize': upload['fileSize'], 'format': 'mp3', 'isDeleted': False})
            self.metadata += 1
            if self.lose_metadata:
                self.lose_metadata = False
                raise RuntimeError('Synthetic response lost after metadata commit')
            return {}
        raise AssertionError('Unexpected or mutating API: ' + parsed.path)

    def media(self, path, headers=None):
        music = int(path.split('/')[2])
        record = next(r for r in self.resources if r['musicid'] == music)
        body = next(f['audio'] for f in self.files.values() if f['filePath'] == record['filePath'])
        if headers:
            return 206, {'Content-Range': 'bytes 0-63/' + str(len(body))}, b'bad' if self.bad_media == 'range' else body[:64]
        return 200, {}, body[:-1] + b'x' if self.bad_media == 'full' else body


class ResearchImportTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.checkout = self.root / 'backend'
        self.state = self.checkout / '.local/a'
        self.cache = self.state / 'music-catalog'
        self.cache.mkdir(parents=True, mode=0o700)
        self.private = self.root / 'sonora/.local/a'
        self.private.mkdir(parents=True, mode=0o700)
        self.sonora = self.private.parents[1]
        self.output = self.private / 'import'
        self.batch = self.private / 'source-batch'
        self.owner = 62
        self.plan_path = self.sonora / 'services/audio-search/targeted_sources.json'
        self.plan_path.parent.mkdir(parents=True)
        self.catalog_path = self.sonora / 'baseline.json'
        self.old_audio, self.old_tracks = {}, []
        for index in range(20):
            sid = str(10000 + index)
            audio = b'ID3 baseline synthetic recording ' + str(index).encode() + b'Z' * 100
            self.old_audio[sid] = audio
            track = {'source': 'Jamendo', 'sourceId': sid, 'title': 'Old title ' + str(index),
                'artist': 'Old artist ' + str(index), 'album': 'Old album', 'durationSeconds': 120,
                'sourceUrl': 'https://www.jamendo.com/track/' + sid,
                'licenseUrl': 'https://creativecommons.org/licenses/by/4.0/', 'license': 'CC BY 4.0',
                'changes': 'Audio file unchanged', 'sha256': importer.sha(audio),
                'fileId': 100 + index, 'musicId': 200 + index, 'rangeVerified': True, 'fullBytesVerified': True}
            self.old_tracks.append(track)
            (self.cache / (sid + '.mp3')).write_bytes(audio)
            (self.cache / (sid + '.download.json')).write_bytes(raw({'sha256': track['sha256'],
                'size': len(audio), 'source': track['sourceUrl'],
                'license': track['licenseUrl'].replace('https:', 'http:')}))
        self.catalog_path.write_bytes(raw({'ownerId': self.owner, 'slot': 'a', 'audioTracks': self.old_tracks}))
        self.catalog_sha = importer.sha(self.catalog_path.read_bytes())
        self.plan = {'schema': collector.SCHEMA, 'split': collector.SPLIT, 'tracks': []}
        official = []
        for index in range(20):
            sid = 'USABC' + str(2400001 + index)
            title = 'Synthetic source ' + str(index)
            self.plan['tracks'].append({'bucket_id': collector.BUCKETS[index // 4], 'isrc': sid, 'title': title})
            official.append({'isrc': sid, 'title': title, 'filename': title + '.mp3', 'length': '00:02:00'})
        self.plan_path.write_bytes(raw(self.plan))
        template = b'Licensed under Creative Commons: By Attribution 4.0 License creativecommons.org/licenses/by/4.0/ encodeURIComponent(p.filename)'
        def fetch(url, limit):
            if url == collector.BASE + 'pieces.json':
                return raw(official)
            if 'index.html?' in url:
                return template
            if url.endswith('licenses/'):
                return b'Creative Commons Requires that you credit'
            return b'ID3 synthetic new source ' + url.encode() + b'A' * 100
        self.root_patches = [patch.object(importer, 'ROOT', self.sonora), patch.object(collector, 'ROOT', self.sonora)]
        for item in self.root_patches:
            item.start()
            self.addCleanup(item.stop)
        collector.run(self.batch, self.plan_path, importer.sha(self.plan_path.read_bytes()), self.catalog_path, self.catalog_sha, fetch)
        self.manifest_path = self.batch / 'manifest.json'
        self.manifest_sha = importer.sha(self.manifest_path.read_bytes())
        self.manifest = json.loads(self.manifest_path.read_bytes())
        self.decode_path = self.private / 'decode-results.json'
        script = self.private / 'verify_audio.py'
        script.write_bytes(b'Synthetic fixed decoder evidence; not a real decoder.')
        self.decode = {'status': 'passed_full_source_decode_with_metadata_differences',
            'manifest_sha256': self.manifest_sha, 'verification_script_sha256': importer.sha(script.read_bytes()),
            'tracks': [{'source_id': t['source_id'], 'bucket_id': t['bucket_id'], 'frames': 5292000,
                'sample_rate_hz': 44100, 'channels': 2, 'format': 'MP3', 'duration_ms': 120000,
                'finite_samples': True, 'provider_duration_delta_ms': 0, 'metadata_within_2000ms': True}
                for t in self.manifest['tracks']],
            'counts': {'decoded': 20, 'finite': 20, 'hash_and_proof_matched': 20,
                'duration_metadata_within_2000ms': 20, 'duration_metadata_outside_2000ms': 0, 'human_judged': 0, 'java_imported': 0},
            'total_duration_ms': 2400000, 'min_duration_ms': 120000, 'max_duration_ms': 120000}
        self.save_decode()
        self.env = {'MUSIC_DB_HOST': '127.0.0.1', 'SPRING_PROFILES_ACTIVE': 'local',
            'MUSIC_DB_NAME': 'music_dev_a', 'MUSIC_DB_USER': 'music_dev_a', 'MUSIC_DB_PORT': '3307',
            'MUSIC_SERVER_PORT': '8080', 'VITE_DEV_PORT': '5173', 'VITE_PROXY_TARGET': 'http://127.0.0.1:8080',
            'MUSIC_UPLOAD_PATH': str(self.state / 'uploads'), 'MUSIC_UPLOAD_TEMP_PATH': str(self.state / 'chunks')}
        (self.state / 'config.json').write_bytes(raw(self.env))
        credentials = {'email': 'fixture@example.invalid', 'password': 'synthetic-password', 'name': 'Fixture'}
        (self.cache / 'demo-account.json').write_bytes(raw(credentials))
        (self.cache / 'demo-account-state.json').write_bytes(raw({'status': 'confirmed',
            'credential_sha256': importer.account_fingerprint(credentials), 'user_id': str(self.owner)}))
        self.client = FakeLocal(self.owner, self.old_tracks, self.old_audio)
        self.old_snapshot = {p: p.read_bytes() for p in self.cache.iterdir()}

    def save_decode(self):
        self.decode_path.write_bytes(raw(self.decode))
        self.decode_sha = importer.sha(self.decode_path.read_bytes())

    def run_import(self, **overrides):
        args = dict(source_manifest=self.manifest_path, source_manifest_sha256=self.manifest_sha,
            decode_report=self.decode_path, decode_report_sha256=self.decode_sha,
            baseline_catalog=self.catalog_path, baseline_catalog_sha256=self.catalog_sha,
            backend_checkout=self.checkout, baseline_audio_root=self.cache, output_state=self.output,
            slot='a', transport=self.client)
        args.update(overrides)
        return importer.run(**args)

    def test_full_import_copies_and_catalog_are_private_and_preserve_originals(self):
        result = self.run_import()
        catalog = json.loads((self.output / 'catalog.json').read_bytes())
        self.assertEqual(result['tracks'], 40)
        self.assertEqual(set(catalog), {'schema', 'ownerId', 'slot', 'baseline_catalog_sha256',
            'source_manifest_sha256', 'decode_report_sha256', 'importer_sha256', 'audioTracks'})
        self.assertEqual(catalog['audioTracks'][:20], [{**t, 'sourceProvider': 'jamendo'} for t in self.old_tracks])
        self.assertEqual(len({t['musicId'] for t in catalog['audioTracks']}), 40)
        self.assertEqual(len(list((self.output / 'audio').iterdir())), 80)
        for path in (self.output / 'audio').iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.old_snapshot, {p: p.read_bytes() for p in self.cache.iterdir()})
        self.assertIsNone(self.client.token)
        persisted = b''.join(p.read_bytes() for p in self.output.rglob('*.json'))
        self.assertNotIn(b'synthetic-password', persisted)
        self.assertNotIn(b'synthetic-secret-token', persisted)
        self.assertNotIn(b'fixture@example.invalid', persisted)

    def test_rerun_is_stable_and_reverifies_without_creating_resources(self):
        first = self.run_import()
        catalog = (self.output / 'catalog.json').read_bytes()
        second = self.run_import()
        self.assertEqual(first, second)
        self.assertEqual(catalog, (self.output / 'catalog.json').read_bytes())
        self.assertEqual((self.client.uploads, self.client.metadata), (20, 20))
        self.client.bad_media = 'full'
        with self.assertRaisesRegex(ValueError, 'Full media'):
            self.run_import()
        self.assertEqual(catalog, (self.output / 'catalog.json').read_bytes())

    def test_response_lost_after_upload_recovers_by_md5(self):
        self.client.lose_upload = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        self.assertFalse((self.output / 'import.lock').exists())
        self.run_import()
        self.assertEqual((self.client.uploads, self.client.metadata), (20, 20))

    def test_response_lost_after_metadata_recovers_exact_record(self):
        self.client.lose_metadata = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        self.run_import()
        self.assertEqual((self.client.uploads, self.client.metadata), (20, 20))

    def test_all_three_pins_are_required_before_network(self):
        for key in ('source_manifest_sha256', 'decode_report_sha256', 'baseline_catalog_sha256'):
            with self.subTest(pin=key), self.assertRaises(ValueError):
                self.run_import(**{key: None})
        self.assertEqual(self.client.calls, [])

    def test_corrupt_audio_or_proof_stops_before_login(self):
        path = self.batch / self.manifest['tracks'][0]['audio_filename']
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'audio hash'):
            self.run_import()
        self.assertEqual(self.client.calls, [])

    def test_corrupt_original_proof_stops_before_login(self):
        path = self.cache / (self.old_tracks[0]['sourceId'] + '.download.json')
        proof = json.loads(path.read_bytes())
        proof['source'] = 'https://www.jamendo.com/track/1'
        path.write_bytes(raw(proof))
        with self.assertRaisesRegex(ValueError, 'Original audio/proof'):
            self.run_import()
        self.assertEqual(self.client.calls, [])

    def test_decode_wrong_frames_or_source_is_not_accepted(self):
        self.decode['tracks'][0]['frames'] += 1
        self.decode['tracks'][0]['duration_ms'] += 10
        self.save_decode()
        with self.assertRaisesRegex(ValueError, 'Decode frames'):
            self.run_import()
        self.assertEqual(self.client.calls, [])

    def test_source_human_label_is_not_copied_into_import(self):
        self.manifest['tracks'][0]['human_relevance'] = 3
        self.manifest_path.write_bytes(raw(self.manifest))
        self.manifest_sha = importer.sha(self.manifest_path.read_bytes())
        self.decode['manifest_sha256'] = self.manifest_sha
        self.save_decode()
        with self.assertRaisesRegex(ValueError, 'human field'):
            self.run_import()
        self.assertEqual(self.client.calls, [])

    def test_only_original_confirmed_ordinary_owner_can_write(self):
        for owner, role in [(self.owner, 'ADMIN'), (999, 'USER')]:
            self.client.owner, self.client.role = owner, role
            with self.subTest(owner=owner, role=role), self.assertRaisesRegex(ValueError, 'ordinary owner'):
                self.run_import()
            self.assertEqual((self.client.uploads, self.client.metadata), (0, 0))
        self.assertIsNone(self.client.token)

    def test_login_failure_never_registers_or_modifies_original_account(self):
        self.client.login_fails = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        self.assertEqual(self.client.calls, [('POST', '/auth/login')])
        self.assertEqual(self.old_snapshot, {p: p.read_bytes() for p in self.cache.iterdir()})

    def test_legacy_missing_confirmation_uses_login_and_preserves_account_files(self):
        confirmed = self.cache / 'demo-account-state.json'
        confirmed.unlink()
        before = {p: p.read_bytes() for p in self.cache.iterdir()}
        result = self.run_import()
        self.assertEqual(result['tracks'], 40)
        self.assertFalse(confirmed.exists())
        self.assertEqual(before, {p: p.read_bytes() for p in self.cache.iterdir()})
        profile_index = self.client.calls.index(('GET', '/auth/profile'))
        upload_index = self.client.calls.index(('POST', '/file/upload'))
        self.assertLess(profile_index, upload_index)
        self.assertFalse(any('register' in url for _, url in self.client.calls))

    def test_legacy_missing_confirmation_rejects_wrong_profile_before_upload(self):
        confirmed = self.cache / 'demo-account-state.json'
        confirmed.unlink()
        before = {p: p.read_bytes() for p in self.cache.iterdir()}
        for owner, role in [(999, 'USER'), (self.owner, 'ADMIN')]:
            self.client.owner, self.client.role = owner, role
            with self.subTest(owner=owner, role=role), self.assertRaisesRegex(ValueError, 'ordinary owner'):
                self.run_import()
            self.assertEqual((self.client.uploads, self.client.metadata), (0, 0))
            self.assertFalse(confirmed.exists())
            self.assertIsNone(self.client.token)
        self.assertEqual(before, {p: p.read_bytes() for p in self.cache.iterdir()})

    def test_existing_bad_confirmation_cannot_fall_back_to_legacy(self):
        confirmed = self.cache / 'demo-account-state.json'
        original = json.loads(confirmed.read_bytes())
        for value in ({**original, 'status': 'pending'},
                      {**original, 'credential_sha256': '0' * 64},
                      {**original, 'user_id': '999'}, [], {'status': 'confirmed'}):
            confirmed.write_bytes(raw(value))
            before = confirmed.read_bytes()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_import()
            self.assertEqual(confirmed.read_bytes(), before)
            self.assertEqual(self.client.calls, [])

    def test_dangling_confirmation_symlink_is_not_a_legacy_missing_file(self):
        confirmed = self.cache / 'demo-account-state.json'
        confirmed.unlink()
        confirmed.symlink_to(self.cache / 'missing-state.json')
        with self.assertRaisesRegex(ValueError, 'regular input'):
            self.run_import()
        self.assertTrue(confirmed.is_symlink())
        self.assertEqual(self.client.calls, [])

    def test_config_upload_paths_cannot_use_sonora_slot(self):
        self.env['MUSIC_UPLOAD_PATH'] = str(self.sonora / '.local/a/uploads')
        (self.state / 'config.json').write_bytes(raw(self.env))
        with self.assertRaisesRegex(ValueError, 'another checkout'):
            self.run_import()
        self.assertEqual(self.client.calls, [])

    def test_changed_ledger_owner_and_private_cache_are_preserved(self):
        self.run_import()
        ledger = self.output / 'import-ledger.json'
        value = json.loads(ledger.read_bytes())
        value['binding']['ownerId'] += 1
        ledger.write_bytes(raw(value))
        before = ledger.read_bytes()
        self.client.calls.clear()
        with self.assertRaisesRegex(ValueError, 'binding mismatch'):
            self.run_import()
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(self.client.calls, [])

    def test_ledger_recovery_rejects_changed_file_identity(self):
        self.client.lose_metadata = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        next(f for fid, f in self.client.files.items() if fid == 1000)['filePath'] = 'changed/path.mp3'
        with self.assertRaisesRegex(ValueError, 'Upload identity'):
            self.run_import()
        self.assertEqual(self.client.metadata, 1)

    def test_matching_title_with_wrong_file_is_never_reused(self):
        track = self.manifest['tracks'][0]
        self.client.resources.append({'musicid': 5000, 'userid': self.owner, 'filePath': 'unrelated/file.mp3',
            'title': track['title'], 'artist': track['artist'], 'album': '', 'isDeleted': False,
            'fileSize': track['bytes'], 'format': 'mp3'})
        with self.assertRaisesRegex(ValueError, 'unrelated bytes'):
            self.run_import()
        self.assertEqual(self.client.uploads, 0)
        self.assertEqual(self.client.metadata, 0)

    def test_legacy_http_license_equivalence_is_version_and_origin_specific(self):
        path = self.cache / (self.old_tracks[0]['sourceId'] + '.download.json')
        original = json.loads(path.read_bytes())
        for url in ('http://creativecommons.org/licenses/by/3.0/',
                    'https://creativecommons.org.evil.invalid/licenses/by/4.0/',
                    'https://user:secret@creativecommons.org/licenses/by/4.0/'):
            proof = {**original, 'license': url}
            path.write_bytes(raw(proof))
            before = path.read_bytes()
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.run_import()
            self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.client.calls, [])

    def test_tampered_private_catalog_stops_before_http(self):
        self.run_import()
        path = self.output / 'catalog.json'
        value = json.loads(path.read_bytes())
        value['audioTracks'][-1]['musicId'] += 1000
        path.write_bytes(raw(value))
        before = path.read_bytes()
        self.client.calls.clear()
        with self.assertRaisesRegex(ValueError, 'catalog changed'):
            self.run_import()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.client.calls, [])

    def test_tampered_ledger_md5_stops_before_http(self):
        self.client.lose_metadata = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        path = self.output / 'import-ledger.json'
        value = json.loads(path.read_bytes())
        value['tracks'][self.manifest['tracks'][0]['source_id']]['md5'] = '0' * 32
        path.write_bytes(raw(value))
        before = path.read_bytes()
        self.client.calls.clear()
        with self.assertRaisesRegex(ValueError, 'MD5 changed'):
            self.run_import()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.client.calls, [])

    def test_ambiguous_metadata_is_not_silently_selected(self):
        self.client.resources.append(copy.deepcopy(self.client.resources[0]))
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            self.run_import()
        self.assertEqual(self.client.uploads, 0)

    def test_range_failure_keeps_catalog_unpublished(self):
        self.client.bad_media = 'range'
        with self.assertRaisesRegex(ValueError, 'Range verification'):
            self.run_import()
        self.assertFalse((self.output / 'catalog.json').exists())
        self.assertEqual(self.client.uploads, 0)

    def test_lock_refuses_concurrent_import_and_is_not_deleted(self):
        self.output.mkdir(mode=0o700)
        lock = self.output / 'import.lock'
        lock.write_bytes(b'existing worker')
        with self.assertRaises(FileExistsError):
            self.run_import()
        self.assertEqual(lock.read_bytes(), b'existing worker')
        self.assertEqual(self.client.calls, [])

    def test_existing_bad_audio_copy_is_not_repaired(self):
        self.client.login_fails = True
        with self.assertRaises(RuntimeError):
            self.run_import()
        path = self.output / 'audio' / ('jamendo-' + self.old_tracks[0]['sourceId'] + '.mp3')
        path.write_bytes(b'changed')
        self.client.calls.clear()
        with self.assertRaisesRegex(ValueError, 'private copy changed'):
            self.run_import()
        self.assertEqual(path.read_bytes(), b'changed')
        self.assertEqual(self.client.calls, [])

    def test_redirect_is_rejected_before_any_forwarding(self):
        request = Request('http://127.0.0.1:8080/api/auth/login', headers={'Authorization': 'Bearer synthetic-secret'})
        with self.assertRaisesRegex(RuntimeError, 'redirect refused'):
            importer.NoRedirects().redirect_request(request, None, 302, 'redirect', {}, 'https://example.invalid/steal')


if __name__ == '__main__':
    unittest.main()

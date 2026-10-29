#!/usr/bin/env python3
"""Import a pinned, decoded development batch using an existing local ordinary owner.

No registration, privilege changes, provider requests, SQL, or public-catalog writes.
The original account/cache remain read-only; recovery state is private and separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import collect_research_music as source
from import_demo_music import account_fingerprint, license_page, source_page

ROOT = Path(__file__).resolve().parents[1]
MAX_AUDIO = source.MAX_AUDIO
MAX_JSON = source.MAX_METADATA
SCHEMA = 'sonora-research-catalog-v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode() + b'\n'


def regular(path):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            'Expected a regular input file without symlinks')
    return path


def read(path, limit=MAX_JSON):
    raw = regular(path).read_bytes()
    require(0 < len(raw) <= limit, 'Input size outside allowed bounds')
    return raw


def document(path, expected=None):
    raw = read(path)
    if expected is not None:
        require(isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected)
                and sha(raw) == expected, 'Explicit input SHA256 mismatch')
    return source.strict_json(raw)


def positive(value):
    require(type(value) is int and 0 < value <= 9223372036854775807, 'Expected positive Java Long identity')
    return value


def identity(value):
    require(type(value) in (int, str) and re.fullmatch(r'[1-9][0-9]*', str(value)), 'Invalid owner identity')
    return positive(int(value))


def file_path(value):
    require(isinstance(value, str) and value and not value.startswith('/')
            and '\\' not in value and not any(p in ('', '.', '..') for p in value.split('/'))
            and not any(ord(c) < 32 for c in value), 'Invalid server file path')
    return value


def private_target(output):
    target, local = Path(output), ROOT / '.local'
    require(local.is_dir() and not local.is_symlink(), 'Expected checkout private root')
    require(not any(p.is_symlink() for p in (target, *target.parents)), 'Output cannot traverse symlinks')
    target = target.resolve()
    require(target.is_relative_to(local.resolve()) and target != local.resolve(), 'Output must be below checkout .local')
    require(target.parent.is_dir(), 'Private output parent must already exist')
    if not target.exists():
        target.mkdir(mode=0o700)
    require(target.is_dir() and (target.stat().st_mode & 0o777) == 0o700,
            'Private output directory must have mode 0700')
    return target


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)


def preserve_copy(path, raw):
    if path.exists():
        require(read(path, max(MAX_AUDIO, MAX_JSON)) == raw and (path.stat().st_mode & 0o777) == 0o600,
                'Existing private copy changed; preserved for review')
    else:
        write_new(path, raw)


def checkpoint(path, value):
    if path.exists():
        regular(path)
        require((path.stat().st_mode & 0o777) == 0o600, 'Ledger permissions changed')
    temporary = path.parent / ('.checkpoint-' + secrets.token_hex(12))
    write_new(temporary, encoded(value))
    os.replace(temporary, path)


def validate_inputs(manifest_path, manifest_sha, decode_path, decode_sha, catalog_path, catalog_sha,
                    baseline_audio_root):
    for pin in (manifest_sha, decode_sha, catalog_sha):
        require(isinstance(pin, str) and re.fullmatch(r'[a-f0-9]{64}', pin), 'Three explicit SHA256 pins required')
    manifest = document(manifest_path, manifest_sha)
    report = document(decode_path, decode_sha)
    baseline = document(catalog_path, catalog_sha)
    require(all(isinstance(v, dict) for v in (manifest, report, baseline)), 'Expected pinned JSON objects')
    require(manifest.get('schema') == 'sonora-source-candidates-v1'
            and manifest.get('split') == source.SPLIT and manifest.get('baseline_catalog_sha256') == catalog_sha,
            'Source manifest schema/split/baseline mismatch')
    batch = regular(manifest_path).parent
    plan_path = ROOT / 'services/audio-search/targeted_sources.json'
    plan = document(plan_path, manifest.get('selection_sha256'))
    source.validate_plan(plan)
    snapshots = manifest.get('snapshots')
    urls = {'official-catalog.json': source.BASE + 'pieces.json',
            'official-track-template.html': source.BASE + 'index.html?isrc=' + plan['tracks'][0]['isrc'],
            'official-license.html': source.BASE + 'licenses/'}
    require(isinstance(snapshots, dict) and set(snapshots) == set(urls), 'Missing source snapshots')
    for name, url in urls.items():
        evidence = snapshots[name]
        require(isinstance(evidence, dict) and set(evidence) == {'url', 'sha256'}
                and evidence['url'] == url, 'Source snapshot identity mismatch')
        require(sha(read(batch / name)) == evidence['sha256'], 'Source snapshot hash mismatch')
    template, license_text = read(batch / 'official-track-template.html'), read(batch / 'official-license.html')
    require(b'Licensed under Creative Commons: By Attribution 4.0 License' in template
            and b'creativecommons.org/licenses/by/4.0/' in template and b'encodeURIComponent(p.filename)' in template
            and b'Creative Commons' in license_text and b'Requires that you credit' in license_text,
            'Source attribution/license evidence mismatch')
    selected = source.select_tracks(document(batch / 'official-catalog.json'), plan)
    tracks = manifest.get('tracks')
    require(isinstance(tracks, list) and len(tracks) == 20, 'Expected twenty source candidates')
    require(report.get('status') == 'passed_full_source_decode_with_metadata_differences'
            and report.get('manifest_sha256') == manifest_sha,
            'Decode report is not bound to the source manifest')
    require(sha(read(Path(decode_path).parent / 'verify_audio.py')) == report.get('verification_script_sha256'),
            'Decode verification script changed')
    decoded = report.get('tracks')
    require(isinstance(decoded, list) and len(decoded) == 20 and all(isinstance(r, dict) for r in decoded)
            and len({r.get('source_id') for r in decoded}) == 20, 'Incomplete or duplicate decode report')
    decoded = {row['source_id']: row for row in decoded}
    old_tracks = baseline.get('audioTracks')
    require(baseline.get('slot') == 'a' and isinstance(old_tracks, list) and len(old_tracks) == 20,
            'Expected original twenty-track slot-a catalog')
    positive(baseline.get('ownerId'))
    seen, ids, files, copies = set(), set(), set(), []
    for track in old_tracks:
        require(isinstance(track, dict) and track.get('source') == 'Jamendo'
                and track.get('rangeVerified') is True and track.get('fullBytesVerified') is True,
                'Original catalog is not a verified Jamendo import')
        sid = track.get('sourceId')
        require(isinstance(sid, str) and re.fullmatch(r'[1-9][0-9]*', sid), 'Invalid original source ID')
        require(source_page(track.get('sourceUrl'), sid) == track['sourceUrl']
                and license_page(track.get('licenseUrl')) == track['licenseUrl'], 'Original source/license mismatch')
        mid, fid = positive(track.get('musicId')), positive(track.get('fileId'))
        require(mid not in ids and fid not in files, 'Duplicate original Java identity')
        ids.add(mid)
        files.add(fid)
        audio_path, proof_path = Path(baseline_audio_root) / (sid + '.mp3'), Path(baseline_audio_root) / (sid + '.download.json')
        raw, proof_raw = read(audio_path, MAX_AUDIO), read(proof_path)
        proof = source.strict_json(proof_raw)
        require(isinstance(proof, dict) and set(proof) == {'sha256', 'size', 'source', 'license'}
                and proof['sha256'] == track['sha256'] and type(proof['size']) is int and proof['size'] == len(raw)
                and proof['source'] == track['sourceUrl']
                and license_page(proof['license']) == track['licenseUrl'] and sha(raw) == track['sha256']
                and track['sha256'] not in seen, 'Original audio/proof/catalog mismatch')
        seen.add(track['sha256'])
        copies.extend([('jamendo-' + sid + '.mp3', raw), ('jamendo-' + sid + '.download.json', proof_raw)])
    for actual, expected in zip(tracks, selected):
        require(isinstance(actual, dict) and actual == {**expected, 'sha256': actual.get('sha256'), 'bytes': actual.get('bytes')}
                and actual['human_relevance'] is None, 'Source candidate metadata or human field changed')
        require(len(actual['title']) <= 100 and len(actual['artist']) <= 50, 'Source metadata exceeds existing API limits')
        sid = actual['source_id']
        raw, proof_raw = read(batch / actual['audio_filename'], MAX_AUDIO), read(batch / (sid + '.download.json'))
        require(type(actual['bytes']) is int and len(raw) == actual['bytes'] and sha(raw) == actual['sha256']
                and actual['sha256'] not in seen, 'Source audio hash/size mismatch or duplicate content')
        proof = source.strict_json(proof_raw)
        require(proof == {'sha256': actual['sha256'], 'size': actual['bytes'], 'source': actual['source_url'],
                'license': actual['license_url'], 'download_url': actual['download_url'],
                'metadata_record_sha256': actual['metadata_record_sha256'], 'snapshots': snapshots}, 'Source download proof mismatch')
        row = decoded.get(sid, {})
        frames, rate, duration = row.get('frames'), row.get('sample_rate_hz'), row.get('duration_ms')
        require(type(frames) is int and frames > 0 and type(rate) is int and 8000 <= rate <= 192000
                and type(duration) is int and duration == frames * 1000 // rate and 30000 <= duration <= 600000
                and type(row.get('channels')) is int and row['channels'] in (1, 2) and row.get('format') == 'MP3'
                and row.get('finite_samples') is True and row.get('bucket_id') == actual['bucket_id']
                and row.get('provider_duration_delta_ms') == duration - actual['duration_seconds'] * 1000
                and row.get('metadata_within_2000ms') is (abs(duration - actual['duration_seconds'] * 1000) <= 2000),
                'Decode frames/duration/source binding mismatch')
        seen.add(actual['sha256'])
        copies.extend([('incompetech-' + sid + '.mp3', raw), ('incompetech-' + sid + '.download.json', proof_raw)])
    require(report.get('total_duration_ms') == sum(row['duration_ms'] for row in decoded.values())
            and report.get('min_duration_ms') == min(row['duration_ms'] for row in decoded.values())
            and report.get('max_duration_ms') == max(row['duration_ms'] for row in decoded.values()), 'Decode aggregate mismatch')
    counts = report.get('counts', {})
    require(isinstance(counts, dict), 'Invalid decode count object')
    within = sum(row['metadata_within_2000ms'] for row in decoded.values())
    require(all(counts.get(key) == 20 for key in ('decoded', 'finite', 'hash_and_proof_matched'))
            and counts.get('duration_metadata_within_2000ms') == within
            and counts.get('duration_metadata_outside_2000ms') == 20 - within
            and counts.get('human_judged') == 0 and counts.get('java_imported') == 0, 'Decode counts mismatch')
    return manifest, report, baseline, decoded, copies


def backend_settings(checkout, slot, audio_root, expected_owner):
    require(slot == 'a', 'Only the explicit existing slot a is supported')
    checkout = Path(checkout)
    require(checkout.is_dir() and not any(p.is_symlink() for p in (checkout, *checkout.parents)), 'Invalid backend checkout')
    require(checkout.resolve() != ROOT.resolve(), 'Backend and private importer checkouts must be independent')
    state = checkout.resolve() / '.local' / slot
    require(Path(audio_root).resolve() == state / 'music-catalog'
            and not any(p.is_symlink() for p in (Path(audio_root), *Path(audio_root).parents)), 'Original audio root belongs to another checkout')
    env = document(state / 'config.json')
    require(isinstance(env, dict), 'Invalid backend configuration')
    expected = {'MUSIC_DB_HOST': '127.0.0.1', 'SPRING_PROFILES_ACTIVE': 'local',
                'MUSIC_DB_NAME': 'music_dev_a', 'MUSIC_DB_USER': 'music_dev_a',
                'MUSIC_DB_PORT': '3307', 'MUSIC_SERVER_PORT': '8080', 'VITE_DEV_PORT': '5173',
                'VITE_PROXY_TARGET': 'http://127.0.0.1:8080'}
    require(all(str(env.get(k)) == v for k, v in expected.items()), 'Backend configuration is outside isolated slot a')
    for key, child in [('MUSIC_UPLOAD_PATH', 'uploads'), ('MUSIC_UPLOAD_TEMP_PATH', 'chunks')]:
        require(Path(env.get(key, '')).resolve() == state / child, 'Backend upload path belongs to another checkout')
    credentials = document(state / 'music-catalog/demo-account.json')
    require(isinstance(credentials, dict)
            and all(isinstance(credentials.get(k), str) and credentials[k] for k in ('email', 'password')),
            'Existing ordinary account credentials are invalid')
    owner = positive(expected_owner)
    confirmed_path = state / 'music-catalog/demo-account-state.json'
    if confirmed_path.exists() or confirmed_path.is_symlink():
        confirmed = document(confirmed_path)
        require(isinstance(confirmed, dict) and confirmed.get('status') == 'confirmed'
                and confirmed.get('credential_sha256') == account_fingerprint(credentials)
                and identity(confirmed.get('user_id')) == owner, 'Existing ordinary account is not confirmed')
    # Legacy imports predate the confirmation file. The pinned catalog supplies
    # only the expected identity; successful login + ordinary profile must still
    # establish that identity before any backend upload or metadata operation.
    # Neither this path nor the confirmed-state path ever writes account files.
    return credentials, owner


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Local API redirect refused')


class HttpTransport:
    def __init__(self):
        self.token = None
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def response(self, method, path, body=None, binary=None, headers=None, limit=MAX_JSON):
        require(isinstance(path, str) and path.startswith('/') and not path.startswith('//')
                and '\\' not in path and not any(ord(c) < 32 for c in path), 'Invalid local API path')
        headers = dict(headers or {})
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if body is not None:
            binary, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        try:
            request = Request('http://127.0.0.1:8080/api' + path, data=binary, method=method, headers=headers)
            with self.opener.open(request, timeout=120) as response:
                raw = response.read(limit + 1)
                require(len(raw) <= limit, 'Oversized local API response')
                return response.status, dict(response.headers), raw
        except Exception:
            raise RuntimeError('Local HTTP operation failed; checkpoint preserved for retry') from None

    def api(self, method, path, body=None, binary=None, headers=None):
        status, _, raw = self.response(method, path, body, binary, headers)
        try:
            value = source.strict_json(raw)
            require(status == 200 and isinstance(value, dict) and value.get('code') == 200,
                    'Local API rejected the operation; checkpoint preserved')
            return value.get('data')
        except (ValueError, TypeError):
            raise RuntimeError('Local API rejected the operation; checkpoint preserved') from None

    def media(self, path, headers=None):
        return self.response('GET', path, headers=headers, limit=MAX_AUDIO)


def matching(client, title, artist, album):
    records, current, total = [], 1, None
    while True:
        data = client.api('GET', '/music-resources/list?' + urlencode(
            {'title': title, 'onlyMine': 'true', 'current': current, 'pageSize': 100}))
        require(isinstance(data, dict) and isinstance(data.get('records'), list)
                and type(data.get('total')) is int and 0 <= data['total'] <= 10000, 'Invalid metadata lookup page')
        if total is None:
            total = data['total']
        require(data['total'] == total and len(data['records']) <= 100, 'Metadata lookup changed during pagination')
        records.extend(data['records'])
        if len(records) >= total:
            require(len(records) == total, 'Metadata lookup total mismatch')
            break
        require(data['records'] and current < 101, 'Incomplete metadata lookup')
        current += 1
    found = [r for r in records if isinstance(r, dict) and r.get('title') == title
             and r.get('artist') == artist and (r.get('album') or '') == album]
    require(len(found) <= 1, 'Ambiguous existing resources; refusing metadata import')
    return found


def verify_resource(row, owner, path, size, expected_music=None):
    music = positive(row.get('musicid'))
    require(identity(row.get('userid')) == owner and row.get('filePath') == path
            and type(row.get('fileSize')) is int and row['fileSize'] == size
            and str(row.get('format')).lower() == 'mp3' and row.get('isDeleted') is False
            and (expected_music is None or music == expected_music), 'Resource owner/file/identity mismatch')
    return music


def verify_media(client, music, audio):
    path = '/music-resources/' + str(music) + '/file'
    status, headers, raw = client.media(path, {'Range': 'bytes=0-63'})
    headers = {k.lower(): v for k, v in headers.items()}
    require(status == 206 and raw == audio[:64]
            and headers.get('content-range') == 'bytes 0-63/' + str(len(audio)), 'Media Range verification failed')
    status, _, raw = client.media(path)
    require(status == 200 and len(raw) == len(audio) and sha(raw) == sha(audio), 'Full media SHA256 verification failed')


def imported_track(track, decoded, saved):
    sid = track['source_id']
    return {'source': 'Incompetech', 'sourceProvider': 'incompetech', 'sourceId': sid,
        'title': track['title'], 'artist': track['artist'], 'album': '',
        'durationSeconds': track['duration_seconds'], 'decodedDurationMs': decoded[sid]['duration_ms'],
        'contentBytes': track['bytes'], 'sourceUrl': track['source_url'], 'licenseUrl': track['license_url'],
        'license': 'CC BY 4.0', 'changes': track['changes'], 'sha256': track['sha256'],
        'fileId': saved['fileId'], 'musicId': saved['musicId'], 'rangeVerified': True, 'fullBytesVerified': True}


def final_catalog(binding, tracks):
    return {'schema': SCHEMA, 'ownerId': binding['ownerId'], 'slot': binding['slot'],
            'baseline_catalog_sha256': binding['baseline_catalog_sha256'],
            'source_manifest_sha256': binding['source_manifest_sha256'],
            'decode_report_sha256': binding['decode_report_sha256'],
            'importer_sha256': binding['importer_sha256'], 'audioTracks': tracks}


def run(source_manifest, source_manifest_sha256, decode_report, decode_report_sha256,
        baseline_catalog, baseline_catalog_sha256, backend_checkout, baseline_audio_root,
        output_state, slot='a', transport=None):
    manifest, _, baseline, decoded, copies = validate_inputs(source_manifest, source_manifest_sha256,
        decode_report, decode_report_sha256, baseline_catalog, baseline_catalog_sha256, baseline_audio_root)
    credentials, owner = backend_settings(backend_checkout, slot, baseline_audio_root, baseline['ownerId'])
    require(owner == baseline['ownerId'], 'Original account/catalog owner mismatch')
    target = private_target(output_state)
    protected = (Path(baseline_audio_root).resolve(), Path(source_manifest).resolve().parent)
    require(all(not target.is_relative_to(path) and not path.is_relative_to(target) for path in protected),
            'Output must be independent of original inputs')
    lock = target / 'import.lock'
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(encoded({'pid': os.getpid(), 'slot': slot}))
        binding = {'source_manifest_sha256': source_manifest_sha256, 'decode_report_sha256': decode_report_sha256,
                   'baseline_catalog_sha256': baseline_catalog_sha256, 'importer_sha256': sha(Path(__file__).read_bytes()),
                   'ownerId': owner, 'slot': slot, 'backend_checkout': str(Path(backend_checkout).resolve())}
        ledger_path = target / 'import-ledger.json'
        if ledger_path.exists():
            ledger = document(ledger_path)
            require(isinstance(ledger, dict) and set(ledger) == {'binding', 'tracks'} and ledger['binding'] == binding
                    and isinstance(ledger['tracks'], dict), 'Import ledger binding mismatch; preserved for review')
        else:
            require(not any(target.iterdir()) or set(p.name for p in target.iterdir()) == {'import.lock'},
                    'Output has artifacts without a ledger; preserved for review')
            ledger = {'binding': binding, 'tracks': {}}
            checkpoint(ledger_path, ledger)
        source_ids = {t['source_id'] for t in manifest['tracks']}
        require(set(ledger['tracks']).issubset(source_ids), 'Unexpected ledger source identity')
        require(set(p.name for p in target.iterdir()).issubset({'import.lock', 'import-ledger.json', 'audio', 'catalog.json'}),
                'Unexpected private output artifact; preserved for review')
        source_audio = {name: raw for name, raw in copies if name.startswith('incompetech-') and name.endswith('.mp3')}
        saved_files, saved_music = set(), set()
        for sid, saved in ledger['tracks'].items():
            require(isinstance(saved, dict) and set(saved).issubset({'sha256', 'md5', 'fileId', 'filePath', 'musicId', 'verified'})
                    and all(k in saved for k in ('sha256', 'md5', 'fileId', 'filePath')), 'Invalid import checkpoint')
            track = next(t for t in manifest['tracks'] if t['source_id'] == sid)
            require(saved['sha256'] == track['sha256']
                    and saved['md5'] == hashlib.md5(source_audio['incompetech-' + sid + '.mp3']).hexdigest(),
                    'Ledger source bytes or MD5 changed')
            positive(saved['fileId'])
            require(saved['fileId'] not in saved_files and saved['fileId'] not in {t['fileId'] for t in baseline['audioTracks']},
                    'Duplicate ledger file identity')
            saved_files.add(saved['fileId'])
            file_path(saved['filePath'])
            if 'musicId' in saved:
                positive(saved['musicId'])
                require(saved['musicId'] not in saved_music and saved['musicId'] not in {t['musicId'] for t in baseline['audioTracks']},
                        'Duplicate ledger music identity')
                saved_music.add(saved['musicId'])
            if 'verified' in saved:
                require(saved['verified'] is True and 'musicId' in saved, 'Invalid verified checkpoint')
        audio_dir = target / 'audio'
        if not audio_dir.exists():
            audio_dir.mkdir(mode=0o700)
        require(not audio_dir.is_symlink() and audio_dir.is_dir() and (audio_dir.stat().st_mode & 0o777) == 0o700,
                'Invalid private audio directory')
        require(set(p.name for p in audio_dir.iterdir()).issubset({name for name, _ in copies}), 'Unexpected private audio artifact')
        for name, raw in copies:
            preserve_copy(audio_dir / name, raw)
        catalog_path = target / 'catalog.json'
        if catalog_path.exists():
            require(set(ledger['tracks']) == source_ids and all(t.get('verified') is True for t in ledger['tracks'].values()),
                    'Existing catalog has an incomplete ledger')
            expected_tracks = [{**old, 'sourceProvider': 'jamendo'} for old in baseline['audioTracks']]
            expected_tracks.extend(imported_track(t, decoded, ledger['tracks'][t['source_id']]) for t in manifest['tracks'])
            require(read(catalog_path) == encoded(final_catalog(binding, expected_tracks)),
                    'Existing private catalog changed; preserved for review')
        client = transport or HttpTransport()
        token = client.api('POST', '/auth/login', {'email': credentials['email'], 'password': credentials['password']})
        require(isinstance(token, dict) and isinstance(token.get('token'), str) and token['token'], 'Existing account login failed')
        client.token = token['token']
        viewer = client.api('GET', '/auth/profile')
        require(isinstance(viewer, dict) and viewer.get('role') == 'USER' and identity(viewer.get('userid')) == owner,
                'Logged-in profile is not the confirmed ordinary owner')
        result_tracks = []
        # Recheck every original resource/media while preserving the catalog record byte values.
        for old in baseline['audioTracks']:
            raw = read(audio_dir / ('jamendo-' + old['sourceId'] + '.mp3'), MAX_AUDIO)
            existing = matching(client, old['title'], old['artist'], old['album'])
            require(len(existing) == 1, 'Original resource is missing')
            check = client.api('GET', '/file/check?' + urlencode({'fileMd5': hashlib.md5(raw).hexdigest()}))
            require(isinstance(check, dict) and check.get('exists') is True and positive(check.get('fileId')) == old['fileId'],
                    'Original upload identity changed')
            path = file_path(check.get('filePath'))
            verify_resource(existing[0], owner, path, len(raw), old['musicId'])
            verify_media(client, old['musicId'], raw)
            result_tracks.append({**old, 'sourceProvider': 'jamendo'})
        used_music = {t['musicId'] for t in result_tracks}
        used_files = {t['fileId'] for t in result_tracks}
        for track in manifest['tracks']:
            sid = track['source_id']
            audio = read(audio_dir / ('incompetech-' + sid + '.mp3'), MAX_AUDIO)
            md5 = hashlib.md5(audio).hexdigest()
            saved = ledger['tracks'].get(sid)
            if saved:
                require(saved['md5'] == md5, 'Ledger MD5/content mismatch')
            matches = matching(client, track['title'], track['artist'], '')
            check = client.api('GET', '/file/check?' + urlencode({'fileMd5': md5}))
            require(isinstance(check, dict) and type(check.get('exists')) is bool, 'Invalid upload lookup')
            if check['exists']:
                fid, path = positive(check.get('fileId')), file_path(check.get('filePath'))
            else:
                require(saved is None and check.get('fileId') is None, 'Incomplete or missing prior upload; preserved for review')
                require(not matches, 'Same metadata references unrelated bytes; preserved for review')
                boundary = 'sonora-' + secrets.token_hex(12)
                binary = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="incompetech-{sid}.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                          + audio + f'\r\n--{boundary}--\r\n'.encode())
                uploaded = client.api('POST', '/file/upload', binary=binary,
                    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
                require(isinstance(uploaded, dict) and identity(uploaded.get('ownerUserId')) == owner
                        and uploaded.get('fileMd5') == md5 and uploaded.get('fileSize') == len(audio)
                        and uploaded.get('status') == 1, 'Upload response owner/content mismatch')
                fid, path = positive(uploaded.get('id')), file_path(uploaded.get('filePath'))
            require(fid not in used_files and (saved is None or (saved['fileId'], saved['filePath']) == (fid, path)),
                    'Upload identity changed or duplicated')
            saved = saved or {'sha256': track['sha256'], 'md5': md5, 'fileId': fid, 'filePath': path}
            ledger['tracks'][sid] = saved
            checkpoint(ledger_path, ledger)
            if not matches:
                require('musicId' not in saved, 'Previously imported metadata is missing; preserved for review')
                client.api('POST', '/music-resources/metadata?fileId=' + str(fid),
                           {'title': track['title'], 'artist': track['artist'], 'album': ''})
                matches = matching(client, track['title'], track['artist'], '')
            require(len(matches) == 1, 'Imported metadata lookup failed')
            mid = verify_resource(matches[0], owner, path, len(audio), saved.get('musicId'))
            require(mid not in used_music, 'Duplicate Java music identity')
            saved['musicId'] = mid
            checkpoint(ledger_path, ledger)
            verify_media(client, mid, audio)
            saved['verified'] = True
            checkpoint(ledger_path, ledger)
            used_music.add(mid)
            used_files.add(fid)
            result_tracks.append(imported_track(track, decoded, saved))
        # Pin the source bytes again before publishing a stable, private catalog.
        require(all(sha(read(path)) == expected for path, expected in (
            (source_manifest, source_manifest_sha256), (decode_report, decode_report_sha256),
            (baseline_catalog, baseline_catalog_sha256))), 'Pinned input changed during import')
        catalog = final_catalog(binding, result_tracks)
        preserve_copy(catalog_path, encoded(catalog))
        return {'status': 'imported_and_verified_private_catalog', 'tracks': 40, 'new_tracks': 20,
                'range_verified': 40, 'full_bytes_verified': 40, 'catalog_sha256': sha(read(catalog_path)),
                'catalog': str(catalog_path), 'human_judged': 0, 'vectors_built': 0}
    finally:
        if 'client' in locals():
            client.token = None
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-manifest', 'decode-report', 'baseline-catalog', 'backend-checkout', 'baseline-audio-root', 'output-state'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('source-manifest-sha256', 'decode-report-sha256', 'baseline-catalog-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--slot', choices=['a'], required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(**vars(args)), ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, AttributeError):
        # Input JSON/server bodies may contain secrets. Do not echo exception text.
        parser.exit(1, 'Research import stopped; inputs/account/checkpoint preserved for review.\n')


if __name__ == '__main__':
    main()

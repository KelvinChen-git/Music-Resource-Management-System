#!/usr/bin/env python3
"""Import CC BY Jamendo demo audio through existing local-slot HTTP APIs.

Credentials, downloaded bytes and resumable import ledger stay in ignored .local.
Only sanitized catalog metadata is written under web/public. No direct DB writes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from baseline import validate
from dev import ROOT, read_env


MAX_AUDIO = 30 * 1024 * 1024


def source_page(value, track_id):
    parsed = urlparse(value)
    if (not re.fullmatch(r'[1-9][0-9]*', track_id)
            or parsed.scheme != 'https' or parsed.hostname != 'www.jamendo.com'
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)
            or not re.fullmatch(r'/track/' + track_id + r'(?:/[^?#]*)?', parsed.path)):
        raise ValueError('Invalid Jamendo source page')
    # Do not copy provider-controlled query, fragment or slug into public output.
    return 'https://www.jamendo.com/track/' + track_id


def license_page(value):
    parsed = urlparse(value)
    if (parsed.scheme not in ('https', 'http') or parsed.hostname != 'creativecommons.org'
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443 if parsed.scheme == 'https' else 80)
            or parsed.query or parsed.fragment
            or not re.fullmatch(r'/licenses/by/(2\.0|2\.5|3\.0|4\.0)/', parsed.path)):
        raise ValueError('Invalid recorded CC BY license')
    return 'https://creativecommons.org' + parsed.path


def eligible(track):
    try:
        duration = int(track.get('duration', 0))
        license_page(track.get('license_ccurl', ''))
        source_page(track.get('shareurl', ''), track.get('id', ''))
        download = urlparse(track.get('audiodownload', ''))
        return (track.get('audiodownload_allowed') is True
                and download.scheme == 'https'
                and download.username is None and download.password is None
                and download.port in (None, 443)
                and (download.hostname or '').endswith('.jamendo.com')
                and 60 <= duration <= 420)
    except (ValueError, TypeError, AttributeError):
        return False


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')
    os.replace(temp, path)


class LocalApiError(RuntimeError):
    def __init__(self, path, code, message):
        self.path, self.code, self.server_message = path, code, message
        super().__init__('Local import API rejected ' + path + ' (business code ' + str(code) + ')')


def account_fingerprint(credentials):
    return hashlib.sha256(json.dumps(credentials, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def recover_login(api, credentials, state_path):
    """Same saved credentials across retries; a file alone is not registration ACK."""
    fingerprint = account_fingerprint(credentials)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if (not isinstance(state, dict) or state.get('status') not in ('pending', 'confirmed')
                or state.get('credential_sha256') != fingerprint):
            raise RuntimeError('Demo account state/credentials mismatch; preserved for review.')
    else:
        state = {'status': 'pending', 'credential_sha256': fingerprint}
        atomic_json(state_path, state)
    login_body = {'email': credentials['email'], 'password': credentials['password']}
    try:
        return api('POST', '/auth/login', login_body)['token']
    except LocalApiError as exc:
        if (state['status'] != 'pending' or exc.path != '/auth/login'
                or exc.code != 500 or exc.server_message != 'Invalid email or password'):
            raise RuntimeError('Demo account login unconfirmed; credentials/state preserved.') from exc
    # Only the existing endpoint's explicit identity rejection permits this retry.
    try:
        api('POST', '/auth/register', credentials)
    except Exception as exc:
        try:
            return api('POST', '/auth/login', login_body)['token']
        except Exception:
            raise RuntimeError('Demo registration pending; retry with the same saved credentials.') from exc
    return api('POST', '/auth/login', login_body)['token']


def confirm_account(credentials, viewer, state_path):
    state = json.loads(state_path.read_text())
    identity = str(viewer.get('userid', ''))
    if (viewer.get('role') != 'USER' or not re.fullmatch(r'[1-9][0-9]*', identity)
            or state.get('credential_sha256') != account_fingerprint(credentials)
            or (state['status'] == 'confirmed' and str(state.get('user_id')) != identity)):
        raise RuntimeError('Demo account identity/role mismatch; state preserved.')
    atomic_json(state_path, {**state, 'status': 'confirmed', 'user_id': identity})


def verify_download(path, proof, track):
    """Bind cached bytes to the recorded selection; never repair a bad proof silently."""
    try:
        evidence = json.loads(proof.read_text())
        size = path.stat().st_size
        if not 0 < size <= MAX_AUDIO:
            raise ValueError('Invalid cached audio size')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if (not isinstance(evidence, dict)
                or type(evidence.get('size')) is not int or evidence['size'] != size
                or not isinstance(evidence.get('sha256'), str)
                or not re.fullmatch(r'[a-f0-9]{64}', evidence['sha256'])
                or evidence['sha256'] != digest
                or source_page(evidence['source'], track['id']) != source_page(track['shareurl'], track['id'])
                or license_page(evidence['license']) != license_page(track['license_ccurl'])):
            raise ValueError('Proof does not match cached selection/bytes')
    except (ValueError, TypeError, KeyError, AttributeError):
        raise RuntimeError('Existing download proof/bytes mismatch; preserved for review.') from None


def _run(slot, count):
    env = read_env(slot)
    validate(slot, env)
    state = ROOT / '.local' / slot / 'music-catalog'
    state.mkdir(mode=0o700, exist_ok=True)
    client_id = os.environ.get('JAMENDO_CLIENT_ID') or (state / 'jamendo-client-id').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9]+', client_id):
        raise RuntimeError('Invalid Jamendo client ID.')
    ca = os.environ.get('SSL_CERT_FILE')
    if not ca and Path('/etc/ssl/cert.pem').is_file():
        ca = '/etc/ssl/cert.pem'
    context = ssl.create_default_context(cafile=ca)

    def external_json(url):
        request = Request(url)
        with urlopen(request, timeout=40, context=context) as response:
            return json.load(response)

    params = dict(client_id=client_id, format='json', limit=200, audioformat='mp32',
                  audiodlformat='mp32', ccnc='false', ccnd='false', include='musicinfo',
                  order='downloads_total')
    saved_selection = state / 'selection.json'
    if saved_selection.exists():
        saved = json.loads(saved_selection.read_text())
        # A completed import can be checked again without new provider downloads.
        # Original license/download evidence stays beside the unchanged bytes.
        all_cached = all((state / (t['id'] + '.mp3')).is_file()
                         and (state / (t['id'] + '.download.json')).is_file() for t in saved)
        if all_cached:
            data = {'headers': {'code': 0}, 'results': saved}
        else:
            fresh = []
            for track in saved:
                lookup = dict(client_id=client_id, format='json', id=track['id'],
                              audioformat='mp32', audiodlformat='mp32', include='musicinfo')
                response = external_json('https://api.jamendo.com/v3.0/tracks/?' + urlencode(lookup))
                if response.get('headers', {}).get('code') != 0:
                    raise RuntimeError('Could not revalidate pending source download.')
                fresh.extend(response.get('results', []))
            data = {'headers': {'code': 0}, 'results': fresh}
    else:
        data = external_json('https://api.jamendo.com/v3.0/tracks/?' + urlencode(params))
    if data.get('headers', {}).get('code') != 0:
        raise RuntimeError('Jamendo catalog request failed: ' + data.get('headers', {}).get('error_message', 'unknown'))
    selection = []
    seen = set()
    artists = set()
    for track in data.get('results', []):
        if (eligible(track) and track['id'] not in seen and track.get('artist_id') not in artists
                and 'remix' not in track['name'].lower()):
            selection.append(track)
            seen.add(track['id'])
            artists.add(track.get('artist_id'))
        if len(selection) == count:
            break
    if not saved_selection.exists() and len(selection) < count:
        raise RuntimeError('Not enough eligible CC BY tracks; no account or uploads created.')
    selection_path = state / 'selection.json'
    if selection_path.exists():
        prior = json.loads(selection_path.read_text())
        indexed = {t['id']: t for t in data['results'] if eligible(t)}
        if len(prior) != count or any(t['id'] not in indexed for t in prior):
            raise RuntimeError('Saved selection changed eligibility; preserved for review.')
        selection = [indexed[t['id']] for t in prior]
    else:
        atomic_json(selection_path, selection)

    def download(track):
        path = state / (track['id'] + '.mp3')
        proof = state / (track['id'] + '.download.json')
        if path.exists() and proof.exists():
            verify_download(path, proof, track)
            return track['id'], path
        request = Request(track['audiodownload'])
        # No tokens or local credentials are sent to the music provider.
        with urlopen(request, timeout=120, context=context) as response:
            body = response.read(MAX_AUDIO + 1)
            final = urlparse(response.url)
            if (final.scheme != 'https' or final.username is not None or final.password is not None
                    or final.port not in (None, 443) or not (final.hostname or '').endswith('.jamendo.com')):
                raise RuntimeError('Unexpected download origin.')
            if not body or len(body) > MAX_AUDIO or body[:1] == b'<':
                raise RuntimeError('Invalid or oversized audio download.')
        temp = path.with_suffix('.part')
        temp.write_bytes(body)
        temp.chmod(0o600)
        os.replace(temp, path)
        atomic_json(proof, {'sha256': hashlib.sha256(body).hexdigest(), 'size': len(body),
                            'source': source_page(track['shareurl'], track['id']),
                            'license': license_page(track['license_ccurl'])})
        return track['id'], path

    with ThreadPoolExecutor(max_workers=3) as pool:
        audio_paths = dict(pool.map(download, selection))
    base = 'http://127.0.0.1:' + env['MUSIC_SERVER_PORT'] + '/api'
    token = None

    def api(method, path, body=None, binary=None, headers=None):
        headers = dict(headers or {})
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if body is not None:
            binary = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        with urlopen(Request(base + path, method=method, data=binary, headers=headers), timeout=120) as response:
            value = json.load(response)
            if value.get('code') != 200:
                raise LocalApiError(path.split('?')[0], value.get('code'), value.get('message'))
            return value.get('data')

    credential_path = state / 'demo-account.json'
    if credential_path.exists():
        credentials = json.loads(credential_path.read_text())
    else:
        credentials = {'email': 'library-demo-' + secrets.token_hex(3) + '@example.invalid',
                       'password': secrets.token_urlsafe(9) + 'Aa1!', 'name': 'Music Demo'}
        # Persist before registration so an ambiguous response cannot lose credentials.
        atomic_json(credential_path, credentials)
    account_state_path = state / 'demo-account-state.json'
    token = recover_login(api, credentials, account_state_path)
    viewer = api('GET', '/auth/profile')
    confirm_account(credentials, viewer, account_state_path)
    ledger_path = state / 'import-ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    manifest = []
    for track in selection:
        key = track['id']
        checkpoint = ledger.setdefault(key, {})
        path = audio_paths[key]
        audio = path.read_bytes()
        md5 = hashlib.md5(audio).hexdigest()
        if not checkpoint.get('file_id'):
            existing = api('GET', '/file/check?' + urlencode({'fileMd5': md5}))
            if existing.get('exists'):
                checkpoint['file_id'] = existing['fileId']
            else:
                boundary = 'demo-' + secrets.token_hex(10)
                binary = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="jamendo-{key}.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                          + audio + f'\r\n--{boundary}--\r\n'.encode())
                checkpoint['file_id'] = api('POST', '/file/upload', binary=binary,
                    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})['id']
            atomic_json(ledger_path, ledger)
        fid = int(checkpoint['file_id'])
        title, artist, album = track['name'][:100], track['artist_name'][:50], track.get('album_name', '')[:50]
        lookup = '/music-resources/list?' + urlencode({'title': title, 'onlyMine': 'true', 'pageSize': 100})
        existing = [r for r in api('GET', lookup)['records'] if r['title'] == title and r.get('artist') == artist and (r.get('album') or '') == album]
        if len(existing) > 1:
            raise RuntimeError('Ambiguous existing demo resources; refusing duplicate metadata import.')
        if not existing:
            genre = next(iter(track.get('musicinfo', {}).get('tags', {}).get('genres', [])), 'other')[:30]
            api('POST', '/music-resources/metadata?fileId=' + str(fid),
                {'title': title, 'artist': artist, 'album': album, 'genre': genre})
            existing = [r for r in api('GET', lookup)['records'] if r['title'] == title and r.get('artist') == artist and (r.get('album') or '') == album]
        if len(existing) != 1:
            raise RuntimeError('Imported resource lookup failed.')
        music_id = int(existing[0]['musicid'])
        checkpoint['music_id'] = music_id
        atomic_json(ledger_path, ledger)
        headers = {'Authorization': 'Bearer ' + token, 'Range': 'bytes=0-63'}
        with urlopen(Request(base + f'/music-resources/{music_id}/file', headers=headers), timeout=30) as response:
            if response.status != 206 or response.read() != audio[:64]:
                raise RuntimeError('Imported media Range verification failed.')
        with urlopen(Request(base + f'/music-resources/{music_id}/file',
                             headers={'Authorization': 'Bearer ' + token}), timeout=60) as response:
            if response.status != 200 or hashlib.sha256(response.read(MAX_AUDIO + 1)).hexdigest() != hashlib.sha256(audio).hexdigest():
                raise RuntimeError('Imported full audio checksum verification failed.')
        manifest.append({'source': 'Jamendo', 'sourceId': key, 'title': title, 'artist': artist,
                         'album': album, 'durationSeconds': track['duration'],
                         'sourceUrl': source_page(track['shareurl'], key), 'licenseUrl': license_page(track['license_ccurl']),
                         'license': 'CC BY ' + license_page(track['license_ccurl']).strip('/').split('/')[-1],
                         'changes': 'Audio file unchanged', 'sha256': hashlib.sha256(audio).hexdigest(),
                         'fileId': fid, 'musicId': music_id, 'rangeVerified': True, 'fullBytesVerified': True})
        print('Imported and verified ' + str(len(manifest)) + '/' + str(count), flush=True)
    public = ROOT / 'web/public/demo-catalog.json'
    # Never publish credentials, tokens, signed download URLs or provider client IDs.
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(json.dumps({'importedAtUnix': int(time.time()), 'slot': slot,
        'ownerId': viewer['userid'], 'audioTracks': manifest,
        'note': 'Full audio from Jamendo, unchanged. Attribution and license shown per track.'}, ensure_ascii=False, indent=2) + '\n')
    atomic_json(state / 'result.json', {'status': 'passed', 'slot': slot, 'count': len(manifest),
        'owner_id': viewer['userid'], 'checks': ['CC BY and download flag checked', 'local API upload and metadata save',
        'exactly one matching resource per selection', 'authenticated 206 Range bytes match for every track'],
        'limits': ['No moderation approval or administrator promotion.', 'No retrieval quality benchmark.']})
    return {'status': 'passed', 'slot': slot, 'count': len(manifest), 'catalog': str(public)}


def run(slot, count):
    validate(slot, read_env(slot))
    state = ROOT / '.local' / slot / 'music-catalog'
    state.mkdir(mode=0o700, exist_ok=True)
    lock = state / 'import.lock'
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump({'pid': os.getpid(), 'slot': slot}, output)
        return _run(slot, count)
    finally:
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], default='a')
    parser.add_argument('--count', type=int, choices=range(1, 21), default=20)
    args = parser.parse_args()
    print(json.dumps(run(args.slot, args.count), ensure_ascii=False))

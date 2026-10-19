#!/usr/bin/env python3
"""Exercise legacy API on a generated local dev slot; leaves synthetic fixtures."""
import argparse
import hashlib
import json
import secrets
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dev import read_env


def synthetic_mp3(title):
    # ID3v2.3 title + complete 128 kbps / 44.1 kHz MPEG frames (silent payload).
    body = b'\x00' + title.encode('ascii')
    tag = b'TIT2' + len(body).to_bytes(4, 'big') + b'\x00\x00' + body
    size = len(tag)
    syncsafe = bytes((size >> shift) & 127 for shift in (21, 14, 7, 0))
    return b'ID3\x03\x00\x00' + syncsafe + tag + (b'\xff\xfb\x90\x00' + bytes(413)) * 40


def run(slot, via_proxy):
    env = read_env(slot)
    port = env['VITE_DEV_PORT'] if via_proxy else env['MUSIC_SERVER_PORT']
    base = f'http://127.0.0.1:{port}/api'
    token = None
    checks = []

    def request(method, path, body=None, binary=None, headers=None, authenticated=True):
        outgoing = dict(headers or {})
        if authenticated and token:
            outgoing['Authorization'] = 'Bearer ' + token
        if body is not None:
            binary = json.dumps(body).encode()
            outgoing['Content-Type'] = 'application/json'
        req = Request(base + path, data=binary, headers=outgoing, method=method)
        try:
            response = urlopen(req, timeout=20)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()

    def api(method, path, body=None, **kwargs):
        status, _, data = request(method, path, body, **kwargs)
        result = json.loads(data)
        if status != 200 or result.get('code') != 200:
            raise RuntimeError(f'{method} {path}: HTTP {status}, {result}')
        return result.get('data')

    def check(name, condition):
        if not condition:
            raise RuntimeError('Failed: ' + name)
        checks.append(name)

    prefix = 'smoke-' + secrets.token_hex(5)
    email = prefix + '@example.invalid'
    password = secrets.token_urlsafe(12)
    check('anonymous profile requires login', request('GET', '/auth/profile')[0] == 401)
    user = api('POST', '/auth/register', {'email': email, 'password': password, 'name': prefix})
    token = api('POST', '/auth/login', {'email': email, 'password': password})['token']
    check('register, login, JWT profile', api('GET', '/auth/profile')['userid'] == user['userid'])
    tag_id = api('POST', '/tags', {'tagName': prefix})['tagId']
    audio = synthetic_mp3(prefix)
    file_md5 = hashlib.md5(audio).hexdigest()
    created = api('POST', '/file/create', {'fileName': prefix + '.mp3', 'fileSize': len(audio),
                                         'fileMd5': file_md5, 'chunkCount': 2})
    file_id = created['id']
    check('new upload reports both missing chunks',
          api('GET', f'/file/missing-chunks?fileId={file_id}') == [0, 1])

    midpoint = len(audio) // 2
    for index, chunk in enumerate([audio[:midpoint], audio[midpoint:]]):
        boundary = 'music-' + secrets.token_hex(10)
        parts = []
        for key, value in [('fileId', file_id), ('chunkIndex', index),
                           ('chunkMd5', hashlib.md5(chunk).hexdigest())]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="chunk"; filename="{index}.bin"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + chunk + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        api('POST', '/file/chunk', binary=b''.join(parts),
            headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        if index == 0:
            resumed = api('GET', '/file/check?' + urlencode({'fileMd5': file_md5}))
            check('partial upload is resumable with original file ID',
                  resumed['fileId'] == file_id and not resumed['exists'] and
                  api('GET', f'/file/missing-chunks?fileId={file_id}') == [1])
    merged = api('POST', f'/file/merge?fileId={file_id}')
    check('merged upload is reusable by MD5', api('GET', '/file/check?fileMd5=' + file_md5)['exists'])
    parsed = api('POST', f'/music-resources/metadata?fileId={file_id}')
    check('MP3 parser reads synthetic ID3 title', parsed['title'] == prefix)
    api('POST', f'/music-resources/metadata?fileId={file_id}', {
        'title': prefix, 'artist': 'Synthetic', 'album': 'Baseline',
        'categoryId': 1, 'tagIds': [tag_id],
    })
    page = api('GET', '/music-resources/list?' + urlencode({
        'title': prefix, 'categoryId': 1, 'tagIds': tag_id, 'onlyMine': 'true'}))
    check('metadata, category and tag filter returns new track', len(page['records']) == 1 and page['total'] == 1)
    track = page['records'][0]
    track_id = track['musicid']
    metadata = track.get('additionalMetadata') or {}
    check('MP3 duration and sample rate retained',
          metadata.get('duration', 0) >= 1 and metadata.get('sampleRate') == 44100)
    status, _, media = request('GET', f'/music-resources/{track_id}/file')
    check('media response matches merged bytes', status == 200 and media == audio)
    status, headers, media = request('GET', f'/music-resources/{track_id}/file',
                                     headers={'Range': 'bytes=0-31'})
    check('media seek uses actual 206 Range response',
          status == 206 and headers.get('content-range', '').startswith('bytes 0-31/') and
          media == audio[:32])
    # Existing exposure is measured and reported separately from functional checks.
    exposure = {'pending_media_anonymous': request('GET', f'/music-resources/{track_id}/file',
                                                   authenticated=False)[0],
                'static_upload_anonymous': request('GET', '/uploads/' + merged['filePath'],
                                                   authenticated=False)[0]}
    api('DELETE', f'/music-resources/{track_id}')
    page = api('GET', '/music-resources/list?' + urlencode({'title': prefix}))
    check('soft delete removes track from normal list', len(page['records']) == 0)
    exposure['deleted_media_anonymous'] = request('GET', f'/music-resources/{track_id}/file',
                                                   authenticated=False)[0]
    recycle = api('GET', '/recycle-bin/list?' + urlencode({'title': prefix}))
    check('recycle bin contains deleted track', len(recycle['records']) == 1)
    api('POST', f'/recycle-bin/{recycle["records"][0]["recycleid"]}/restore')
    restored = api('GET', '/music-resources/list?' + urlencode({'title': prefix}))
    check('recycle restore returns track to list', len(restored['records']) == 1)
    return {'slot': slot, 'base_url': base, 'completed_at_unix': int(time.time()),
            'functional_checks': checks, 'track_id': str(track_id), 'file_id': str(file_id),
            'synthetic_audio_sha256': hashlib.sha256(audio).hexdigest(),
            'legacy_exposure_http_status': exposure,
            'limits': ['Synthetic fixture, no search quality or perceptual audio assessment.',
                       'Resume request only; restart recovery is not exercised.',
                       'Fixtures remain in this isolated slot. No external email is sent.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], required=True)
    parser.add_argument('--via-proxy', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.slot, args.via_proxy), indent=2))
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)

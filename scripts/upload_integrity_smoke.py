#!/usr/bin/env python3
"""Two-phase upload regression; restart the backend between prepare and resume.

Run only against an isolated local development slot. Leaves synthetic fixtures.
State contains a login token and is saved privately under .local/<slot>/.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dev import read_env
from smoke import synthetic_mp3


def run(slot, phase):
    env = read_env(slot)
    base = f'http://127.0.0.1:{env["MUSIC_SERVER_PORT"]}/api'
    state_path = Path(__file__).resolve().parents[1] / '.local' / slot / 'upload-integrity-state.json'
    checks = []
    token = None

    def check(name, condition):
        if not condition:
            raise RuntimeError('Failed: ' + name)
        checks.append(name)

    def request(method, path, body=None, data=None, content_type=None, success=True):
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        if body is not None:
            data = json.dumps(body).encode()
            content_type = 'application/json'
        if content_type:
            headers['Content-Type'] = content_type
        req = Request(base + path, data=data, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            result = json.loads(response.read())
            if response.status != 200 or (result.get('code') == 200) != success:
                raise RuntimeError(f'{method} {path}: HTTP {response.status}, code={result.get("code")}')
            return result.get('data')

    def create(payload, count=12, md5=None, size=None):
        return request('POST', '/file/create', body={
            'fileName': seed + '.mp3', 'fileSize': len(payload) if size is None else size,
            'fileMd5': md5 or hashlib.md5(payload).hexdigest(), 'chunkCount': count})['id']

    def send(file_id, index, payload, md5=None, success=True):
        boundary = 'music-' + secrets.token_hex(10)
        parts = []
        for key, value in [('fileId', file_id), ('chunkIndex', index),
                           ('chunkMd5', md5 or hashlib.md5(payload).hexdigest())]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="chunk"; filename="chunk.bin"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + payload + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return request('POST', '/file/chunk', data=b''.join(parts),
                       content_type='multipart/form-data; boundary=' + boundary, success=success)

    def status(file_id):
        return request('GET', f'/file/status/{file_id}')

    if phase == 'prepare':
        if state_path.exists():
            raise RuntimeError('Existing state preserved; run resume or choose another isolated slot.')
        seed = 'integrity-' + secrets.token_hex(6)
        password = secrets.token_urlsafe(12)
        email = seed + '@example.invalid'
        request('POST', '/auth/register', body={'email': email, 'password': password, 'name': seed})
        token = request('POST', '/auth/login', body={'email': email, 'password': password})['token']
    else:
        state = json.loads(state_path.read_text())
        seed, token = state['seed'], state['token']
        if state['base_url'] != base:
            raise RuntimeError('State belongs to a different local endpoint.')

    payload = synthetic_mp3(seed)
    parts = [payload[i * len(payload) // 12:(i + 1) * len(payload) // 12] for i in range(12)]
    if phase == 'prepare':
        file_id = create(payload)
        send(file_id, 0, parts[0], md5='0' * 32, success=False)
        check('bad chunk hash is rejected without progress', status(file_id)['uploadedChunks'] == 0)
        send(file_id, 12, parts[0], success=False)
        check('out of range index is rejected', status(file_id)['uploadedChunks'] == 0)
        send(file_id, 0, parts[0])
        send(file_id, 0, parts[0])
        check('duplicate chunk is counted once', status(file_id)['uploadedChunks'] == 1)
        send(file_id, 0, b'x' * len(parts[0]), success=False)
        check('conflicting retry preserves progress', status(file_id)['uploadedChunkIndexes'] == [0])
        request('POST', f'/file/merge?fileId={file_id}', success=False)
        check('incomplete merge remains unfinished', status(file_id)['status'] == 0)
        # Exclusive creation keeps a prior run's evidence and credentials intact.
        fd = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump({'seed': seed, 'token': token, 'base_url': base, 'file_id': file_id}, out)
        return {'phase': phase, 'checks': checks, 'next': 'Restart backend, then run --phase resume.'}

    file_id = state['file_id']
    check('persisted partial upload is available in resume phase',
          status(file_id)['uploadedChunkIndexes'] == [0])
    send(file_id, 0, parts[0])
    check('retry after restart is not recounted', status(file_id)['uploadedChunks'] == 1)
    # Same-index races and distinct-index uploads must serialize under the upload row lock.
    jobs = [(1, parts[1]), (1, parts[1])] + list(enumerate(parts[2:], 2))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: send(file_id, item[0], item[1]), jobs))
    check('concurrent uploads past old batch threshold have exact progress',
          status(file_id)['uploadedChunks'] == 12 and status(file_id)['missingChunkIndexes'] == [])
    result = request('POST', f'/file/merge?fileId={file_id}')
    check('merge publishes a complete file', status(file_id)['status'] == 1)
    repeated = request('POST', f'/file/merge?fileId={file_id}')
    check('repeated merge returns original path', repeated['filePath'] == result['filePath'])
    # Inspect only our own local synthetic output; no need to rely on anonymous media routes.
    target = Path(env['MUSIC_UPLOAD_PATH']) / result['filePath']
    check('published bytes exactly match original', target.read_bytes() == payload)
    send(file_id, 0, parts[0], success=False)
    check('completed uploads reject more chunks', status(file_id)['status'] == 1)
    for label, md5, size in [('hash', '0' * 32, len(payload)),
                             ('size', hashlib.md5(payload).hexdigest(), len(payload) + 1)]:
        bad_id = create(payload, count=1, md5=md5, size=size)
        send(bad_id, 0, payload)
        request('POST', f'/file/merge?fileId={bad_id}', success=False)
        check('wrong whole file ' + label + ' never completes', status(bad_id)['status'] == 0)
    # Keep only non-secret results after completion.
    state_path.unlink()
    return {'phase': phase, 'checks': checks, 'file_id': str(file_id)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], required=True)
    parser.add_argument('--phase', choices=['prepare', 'resume'], required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.slot, args.phase), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

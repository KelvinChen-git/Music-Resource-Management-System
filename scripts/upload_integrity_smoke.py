#!/usr/bin/env python3
"""Two-phase upload regression; restart the backend between prepare and resume.

Run only against an isolated local development slot. Leaves synthetic fixtures.
State contains a login token and is saved privately under .local/<slot>/.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dev import ROOT, read_env
from baseline import validate
from smoke import synthetic_mp3


def validate_restart_proof(proof, slot, checkout, state_bytes, prepared_at):
    if (proof.get('schema')!='music-backend-restart-v1' or proof.get('slot')!=slot
            or proof.get('checkout')!=str(checkout.resolve())
            or proof.get('prepared_state_sha256')!=hashlib.sha256(state_bytes).hexdigest()):
        raise RuntimeError('Restart proof does not match this isolated partial upload.')
    old,new=proof.get('old_backend_launcher_pid'),proof.get('new_backend_launcher_pid')
    if type(old) is not int or type(new) is not int or min(old,new)<=0 or old==new:
        raise RuntimeError('Restart requires two distinct owned backend launchers.')
    if any(proof.get(k) is not True for k in ['old_backend_exit_confirmed','backend_port_released','new_backend_ready']):
        raise RuntimeError('Backend stop, port release and new readiness must all be observed.')
    stopped,restarted=proof.get('stopped_at_unix',0),proof.get('restarted_at_unix',0)
    if not prepared_at<=stopped<restarted<=time.time()+5:
        raise RuntimeError('Restart ordering does not follow the partial upload checkpoint.')


def run(slot, phase, mysql=None, restart_proof=None):
    env = read_env(slot)
    validate(slot, env)
    base = f'http://127.0.0.1:{env["MUSIC_SERVER_PORT"]}/api'
    state_path = ROOT / '.local' / slot / 'upload-integrity-state.json'
    checks = []
    token = None
    client=mysql or str(ROOT.parent/'.music-tools/mysql-8.0.41-macos15-arm64/bin/mysql')
    def query(sql):
        result=subprocess.run([client,'--protocol=TCP','--host=127.0.0.1','--port='+env['MUSIC_DB_PORT'],
            '--user='+env['MUSIC_DB_USER'],'--database='+env['MUSIC_DB_NAME'],'--batch','--skip-column-names'],
            input=sql,text=True,capture_output=True,timeout=15,env={**os.environ,'MYSQL_PWD':env['MUSIC_DB_PASSWORD']})
        if result.returncode:raise RuntimeError('Isolated integrity evidence query failed.')
        return result.stdout.strip().splitlines()


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
        seed = 'i-' + secrets.token_hex(5)
        password = secrets.token_urlsafe(12)
        email = seed + '@example.invalid'
        request('POST', '/auth/register', body={'email': email, 'password': password, 'name': seed})
        token = request('POST', '/auth/login', body={'email': email, 'password': password})['token']
    else:
        state_bytes=state_path.read_bytes()
        state = json.loads(state_bytes)
        seed, token = state['seed'], state['token']
        if state['base_url'] != base:
            raise RuntimeError('State belongs to a different local endpoint.')
        if phase=='resume':
            if not restart_proof:raise RuntimeError('Resume requires baseline-owned backend restart proof; same-process exercise uses concurrency phase.')
            proof_path=Path(restart_proof).resolve()
            if not proof_path.is_relative_to((ROOT/'.local'/slot/'logs').resolve()):
                raise RuntimeError('Restart proof must belong to this isolated slot log directory.')
            validate_restart_proof(json.loads(proof_path.read_text()),slot,ROOT,state_bytes,state['prepared_at_unix'])

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
            json.dump({'seed': seed, 'token': token, 'base_url': base, 'file_id': file_id, 'prepared_at_unix':time.time()}, out)
        return {'phase':phase,'checks':checks,'check_count':len(checks),'file_id':str(file_id),'prepared_at_unix':json.loads(state_path.read_text())['prepared_at_unix'],'prepared_state_sha256':hashlib.sha256(state_path.read_bytes()).hexdigest(),'next':'Baseline stops its owned backend and supplies restart proof; concurrency phase does not claim a restart.'}

    file_id = state['file_id']
    check('persisted partial upload is available in '+phase+' phase',
          status(file_id)['uploadedChunkIndexes'] == [0])
    send(file_id, 0, parts[0])
    check('retry after '+phase+' is not recounted', status(file_id)['uploadedChunks'] == 1 and query(f'SELECT uploaded_chunks FROM file_upload WHERE id={int(file_id)};')==['1'])
    # Same-index races and distinct-index uploads must serialize under the upload row lock.
    jobs = [(1, parts[1]), (1, parts[1])] + list(enumerate(parts[2:], 2))
    gate=threading.Barrier(4)
    def concurrent_upload(item):
        job,(index,payload_part)=item
        if job<4:gate.wait(timeout=10)
        return send(file_id,index,payload_part)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(concurrent_upload,enumerate(jobs)))
    check('concurrent uploads past old batch threshold have exact progress',
          status(file_id)['uploadedChunks'] == 12 and status(file_id)['missingChunkIndexes'] == [])
    check('database has twelve unique chunks and matching persisted counter',
          query(f'SELECT COUNT(*), COUNT(DISTINCT chunk_index) FROM file_chunk WHERE file_id={int(file_id)};')==['12\t12']
          and query(f'SELECT uploaded_chunks FROM file_upload WHERE id={int(file_id)};')==['12'])
    merge_gate=threading.Barrier(2)
    def merge_once(_):
        merge_gate.wait(timeout=10)
        return request('POST', f'/file/merge?fileId={file_id}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        merged=list(pool.map(merge_once,range(2)))
    result=merged[0]
    check('concurrent merges publish one common path',merged[0]['filePath']==merged[1]['filePath'])
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
    return {'phase':phase,'status':'passed','checks':checks,'check_count':len(checks),'file_id':str(file_id),
            'restart_verified':phase=='resume','concurrent_upload_requests':len(jobs),'concurrent_merge_requests':2,
            'limits':['Concurrency phase alone does not demonstrate a restarted JVM.','No database outage or transaction-commit acknowledgement loss simulated.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], required=True)
    parser.add_argument('--phase', choices=['prepare','resume','concurrency'], required=True)
    parser.add_argument('--mysql')
    parser.add_argument('--restart-proof')
    args = parser.parse_args()
    print(json.dumps(run(args.slot,args.phase,args.mysql,args.restart_proof), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

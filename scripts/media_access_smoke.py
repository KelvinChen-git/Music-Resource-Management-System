#!/usr/bin/env python3
"""Real HTTP/media regression on an isolated development slot. Leaves synthetic fixtures.

Only a newly registered synthetic fixture account is briefly promoted through the
slot's native MySQL client. Existing users are never modified. It is demoted in
finally. No credentials/tokens enter logs, command arguments or result JSON.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from baseline import validate
from dev import ROOT, read_env
from smoke import synthetic_mp3


def run(slot, mysql=None, via_proxy=False):
    env = read_env(slot)
    validate(slot, env)
    port = env['VITE_DEV_PORT'] if via_proxy else env['MUSIC_SERVER_PORT']
    base = 'http://127.0.0.1:' + port + '/api'
    client = mysql or shutil.which('mysql') or str(ROOT.parent / '.music-tools/mysql-8.0.41-macos15-arm64/bin/mysql')
    prefix = 'm-' + secrets.token_hex(5)
    rows, checks = [], []

    def request(method, path, token=None, body=None, data=None, headers=None):
        outgoing = dict(headers or {})
        if token:
            outgoing['Authorization'] = 'Bearer ' + token
        if body is not None:
            data = json.dumps(body).encode()
            outgoing['Content-Type'] = 'application/json'
        req = Request(base + path, data=data, headers=outgoing, method=method)
        try:
            response = urlopen(req, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            return response.status, {k.lower(): v for k,v in response.headers.items()}, response.read()

    def api(method, path, token=None, body=None, **kwargs):
        status, _, payload = request(method, path, token, body, **kwargs)
        value = json.loads(payload)
        if status != 200 or value.get('code') != 200:
            raise RuntimeError(f'{method} {path}: HTTP {status}, code={value.get("code")}')
        return value.get('data')

    def check(name, condition):
        if not condition:
            raise RuntimeError('Failed: ' + name)
        checks.append(name)

    def user(suffix):
        email = prefix + '-' + suffix + '@example.invalid'
        password = secrets.token_urlsafe(12)
        created = api('POST', '/auth/register', body={'email': email, 'password': password, 'name': prefix + suffix})
        token = api('POST', '/auth/login', body={'email': email, 'password': password})['token']
        return {'id': int(created['userid']), 'email': email, 'token': token}

    def fixture_update(account, assignment):
        # Account/email come solely from this invocation's synthetic registrations.
        assert account['email'].startswith(prefix) and "'" not in account['email']
        sql = f"UPDATE users SET {assignment} WHERE userid={account['id']} AND email='{account['email']}';"
        command = [client, '--protocol=TCP', '--host=127.0.0.1', '--port=' + env['MUSIC_DB_PORT'],
                   '--user=' + env['MUSIC_DB_USER'], '--database=' + env['MUSIC_DB_NAME'], '--batch']
        result = subprocess.run(command, input=sql, text=True, capture_output=True, timeout=15,
                                env={**os.environ, 'MYSQL_PWD': env['MUSIC_DB_PASSWORD']})
        if result.returncode:
            raise RuntimeError('Synthetic fixture role/lock setup failed; inspect native MySQL access.')

    def multipart(fields, payload, filename, field='chunk'):
        boundary = 'music-' + secrets.token_hex(10)
        parts = []
        for key,value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + payload + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return {'data': b''.join(parts), 'headers': {'Content-Type': 'multipart/form-data; boundary=' + boundary}}

    owner, other, admin = user('owner'), user('other'), user('reviewer')
    promoted = False
    try:
        fixture_update(admin, "role='ADMIN'")
        promoted = True
        check('fresh fixture administrator role', api('GET', '/auth/profile', admin['token'])['role'] == 'ADMIN')
        audio = synthetic_mp3(prefix)
        file_id = api('POST', '/file/create', owner['token'], {'fileName': prefix+'.mp3', 'fileSize':len(audio),
                        'fileMd5':hashlib.md5(audio).hexdigest(), 'chunkCount':1})['id']
        api('POST', '/file/chunk', owner['token'], **multipart({'fileId':file_id,'chunkIndex':0,
            'chunkMd5':hashlib.md5(audio).hexdigest()}, audio, 'chunk.bin'))
        relative = api('POST', f'/file/merge?fileId={file_id}', owner['token'])['filePath']
        api('POST', f'/music-resources/metadata?fileId={file_id}', owner['token'],
            {'title':prefix, 'artist':'Synthetic', 'album':'Media regression', 'categoryId':1, 'tagIds':[]})
        page = api('GET', '/music-resources/list?title='+prefix, owner['token'])
        check('fixture metadata creates exactly one pending resource',
              len(page['records'])==1 and page['records'][0]['approvalStatus']=='pending')
        music_id = page['records'][0]['musicid']
        route = f'/music-resources/{music_id}/file'
        before = api('GET', f'/music-resources/{music_id}', owner['token']).get('playCount', 0)
        request('GET', route+'?pay=1')
        request('HEAD', route+'?pay=1', owner['token'])
        request('GET', route+'?pay=1', owner['token'], headers={'Range':'bytes=0-7'})
        after = api('GET', f'/music-resources/{music_id}', owner['token']).get('playCount', 0)
        check('anonymous, HEAD and Range cannot increment playback', before == after)
        paths=[route, f'/file/download/{file_id}', '/uploads/'+relative]
        viewers=[('anonymous',None),('owner',owner['token']),('other',other['token']),('admin',admin['token'])]
        for state in ['pending','approved','rejected','deleted']:
            if state == 'approved': api('POST', f'/music-resources/{music_id}/approve', admin['token'])
            if state == 'rejected': api('POST', f'/music-resources/{music_id}/reject', admin['token'])
            if state == 'deleted': api('DELETE', f'/music-resources/{music_id}', owner['token'])
            if state in ['pending','rejected','deleted']:
                candidate = other if state=='pending' else owner if state=='rejected' else admin
                code,_,data = request('POST',f'/music-resources/metadata?fileId={file_id}',candidate['token'],
                    {'title':prefix+'-copy','artist':'Synthetic','album':'Clone','categoryId':1,'tagIds':[]})
                check(state+' resource cannot be rebound to bypass media policy',
                      code!=200 or json.loads(data).get('code')!=200)
            for viewer,token in viewers:
                for path in paths:
                    for method in ['GET','HEAD','RANGE']:
                        allowed = token and not path.startswith('/uploads/') and state!='deleted' and (
                            state=='approved' or viewer=='admin' or (state=='pending' and viewer=='owner'))
                        expected = 401 if not token else (206 if method=='RANGE' else 200) if allowed else 404
                        status,headers,body=request('GET' if method=='RANGE' else method, path, token,
                            headers={'Range':'bytes=0-7'} if method=='RANGE' else {})
                        if status != expected or 'no-store' not in headers.get('cache-control',''):
                            raise RuntimeError(f'Matrix {state}/{viewer}/{method}/{path}: HTTP {status}, expected {expected}')
                        if 'authorization' not in headers.get('vary','').lower() or headers.get('x-content-type-options')!='nosniff':
                            raise RuntimeError('Media cache/security headers missing')
                        if method=='HEAD' and body: raise RuntimeError('HEAD response contains a body')
                        if allowed and method=='RANGE' and body != audio[:8]: raise RuntimeError('Incorrect range bytes')
                        if allowed and method=='GET' and body != audio: raise RuntimeError('Incorrect complete bytes')
                        rows.append({'state':state,'viewer':viewer,'method':method,'route':path,'status':status})
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ9sAAAAASUVORK5CYII=')
        avatar=api('POST','/file/upload',owner['token'],**multipart({},png,'avatar.png',field='file'))['filePath']
        api('PUT','/auth/profile',owner['token'],{'avatar':avatar})
        status,headers,body=request('GET','/uploads/'+avatar)
        check('registered PNG avatar remains public',status==200 and body==png and headers.get('content-type','').startswith('image/png'))
        api('PUT','/auth/profile',owner['token'],{'avatar':relative})
        check('avatar field cannot expose music',request('GET','/uploads/'+relative)[0]==401)
        api('PUT','/auth/profile',owner['token'],{'avatar':avatar})
        return {'slot':slot,'base_url':base,'matrix_cases':len(rows),'checks':checks,'matrix':rows,
                'synthetic_track_id':str(music_id),'limits':['Local synthetic fixtures only; not search quality.',
                'Existing cached/downloaded copies cannot be revoked.']}
    finally:
        if promoted: fixture_update(admin,"role='USER'")


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot',choices=['a','b'],required=True)
    parser.add_argument('--mysql',help='Native mysql client executable')
    parser.add_argument('--via-proxy',action='store_true')
    args=parser.parse_args()
    try: print(json.dumps(run(args.slot,args.mysql,args.via_proxy),ensure_ascii=False,indent=2))
    except Exception as error:
        print('ERROR: '+str(error),file=sys.stderr)
        sys.exit(1)

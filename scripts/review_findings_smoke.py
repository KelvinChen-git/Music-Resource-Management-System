#!/usr/bin/env python3
"""Synthetic HTTP regressions for B R1/R2. observe records old behavior; verify asserts fixes."""
import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from baseline import validate
from dev import ROOT, read_env
from smoke import synthetic_mp3


def run(slot, mode='verify', mysql=None):
    env=read_env(slot);validate(slot,env)
    base='http://127.0.0.1:'+env['MUSIC_SERVER_PORT']+'/api'
    client=mysql or str(ROOT.parent/'.music-tools/mysql-8.0.41-macos15-arm64/bin/mysql')
    prefix='r-'+secrets.token_hex(5);checks=[];observations={}
    def request(method,path,token=None,body=None,data=None,headers=None):
        headers=dict(headers or {})
        if token:headers['Authorization']='Bearer '+token
        if body is not None:data=json.dumps(body).encode();headers['Content-Type']='application/json'
        try:response=urlopen(Request(base+path,data=data,headers=headers,method=method),timeout=20)
        except HTTPError as error:response=error
        with response:return response.status,response.read()
    def api(method,path,token=None,body=None,**kwargs):
        status,data=request(method,path,token,body,**kwargs);value=json.loads(data)
        if status!=200 or value.get('code')!=200:raise RuntimeError(f'{method} {path}: HTTP {status}, code={value.get("code")}')
        return value.get('data')
    def check(name,condition):
        if not condition:raise RuntimeError('Failed: '+name)
        checks.append(name)
    def user(suffix):
        email=prefix+'-'+suffix+'@example.invalid';password=secrets.token_urlsafe(12)
        created=api('POST','/auth/register',body={'email':email,'name':prefix+suffix,'password':password})
        return {'id':int(created['userid']),'email':email,'token':api('POST','/auth/login',body={'email':email,'password':password})['token']}
    def query(sql):
        result=subprocess.run([client,'--protocol=TCP','--host=127.0.0.1','--port='+env['MUSIC_DB_PORT'],
            '--user='+env['MUSIC_DB_USER'],'--database='+env['MUSIC_DB_NAME'],'--batch','--skip-column-names'],
            input=sql,text=True,capture_output=True,env={**os.environ,'MYSQL_PWD':env['MUSIC_DB_PASSWORD']},timeout=15)
        if result.returncode:raise RuntimeError('Synthetic fixture SQL failed.')
        return result.stdout.strip().splitlines()
    def multipart(payload,filename):
        boundary='music-'+secrets.token_hex(10)
        data=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+payload+f'\r\n--{boundary}--\r\n'.encode())
        return {'data':data,'headers':{'Content-Type':'multipart/form-data; boundary='+boundary}}
    owner,other,admin=user('owner'),user('other'),user('admin')
    assert admin['email'].startswith(prefix)
    injected_email=prefix+'-created@example.invalid'
    primary_error = None
    try:
        # Protect even an ambiguous promotion failure: the SQL may already have committed.
        query(f"UPDATE users SET role='ADMIN' WHERE userid={admin['id']} AND email='{admin['email']}';")
        audio=synthetic_mp3(prefix)
        uploaded=api('POST','/file/upload',owner['token'],**multipart(audio,prefix+'.mp3'));fid=int(uploaded['id'])
        api('POST',f'/music-resources/metadata?fileId={fid}',owner['token'],{'title':prefix,'artist':'Synthetic','categoryId':1,'tagIds':[]})
        music_id=int(api('GET','/music-resources/list?title='+prefix,owner['token'])['records'][0]['musicid'])
        api('POST',f'/music-resources/{music_id}/reject',admin['token'])
        check('rejected original raw bytes unavailable',request('GET',f'/file/download/{fid}',owner['token'])[0]==404)
        code,_=request('DELETE',f'/music/{music_id}',other['token'])
        remaining=int(query(f'SELECT COUNT(*) FROM music_resources WHERE musicid={music_id};')[0])
        raw_code,_=request('GET',f'/file/download/{fid}',owner['token'])
        observations['R1']={'legacy_delete_http':code,'resource_rows_after_delete':remaining,'raw_http_after_delete':raw_code}
        if mode=='verify':
            check('foreign legacy delete is gone and moderation reference retained',code==410 and remaining==1 and raw_code==404)
            for label,token,expected in [('anonymous',None,401),('owner',owner['token'],410),('admin',admin['token'],410)]:
                check(label+' cannot use legacy deletion',request('DELETE',f'/music/{music_id}',token)[0]==expected)
            api('DELETE',f'/music-resources/{music_id}',owner['token'])
            check('standard soft delete retains reference and raw denial',query(f'SELECT is_deleted FROM music_resources WHERE musicid={music_id};')==['1'] and request('GET',f'/file/download/{fid}',owner['token'])[0]==404)
            check('legacy delete cannot erase soft-deleted reference',request('DELETE',f'/music/{music_id}',owner['token'])[0]==410)
            code,body=request('POST',f'/music-resources/metadata?fileId={fid}',owner['token'],{'title':prefix+'copy','categoryId':1,'tagIds':[]})
            check('soft-deleted bytes cannot be rebound',code!=200 or json.loads(body).get('code')!=200)
        elif remaining==0:
            # Recover a moderation reference for only this synthetic upload, then soft delete.
            api('POST',f'/music-resources/metadata?fileId={fid}',owner['token'],{'title':prefix+'copy','categoryId':1,'tagIds':[]})
            new_id=int(api('GET','/music-resources/list?title='+prefix+'copy',owner['token'])['records'][0]['musicid'])
            api('DELETE',f'/music-resources/{new_id}',owner['token'])
            observations['R1']['rebind_succeeded']=True
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ9sAAAAASUVORK5CYII=')
        image=api('POST','/file/upload',owner['token'],**multipart(png,prefix+'.png'))
        check('unregistered image is private before createUser',request('GET','/uploads/'+image['filePath'])[0]==401)
        code,body=request('POST','/users',admin['token'],{'name':prefix+'new','email':injected_email,'avatar':image['filePath'],'role':'USER'})
        public_code,_=request('GET','/uploads/'+image['filePath'])
        rows=int(query(f"SELECT COUNT(*) FROM users WHERE email='{injected_email}';")[0])
        observations['R2']={'create_user_http':code,'created_rows':rows,'anonymous_image_http':public_code}
        if mode=='verify':check('createUser rejects new avatar before insert and image stays private',code==400 and rows==0 and public_code==401)
        # Remove only this synthetic bypass account if old code created it.
        query(f"DELETE FROM users WHERE email='{injected_email}';")
        check('fixture cleanup leaves image private',request('GET','/uploads/'+image['filePath'])[0]==401)
        return {'slot':slot,'mode':mode,'status':'passed' if mode=='verify' else 'observed','check_count':len(checks),
            'checks':checks,'observations':observations,'limits':['Synthetic fixtures; mode observe is old-runtime evidence, not fixed-runtime acceptance.','No fault rollback, concurrency or restart recovery claim.']}
    except BaseException as error:
        primary_error = error
        raise
    finally:
        cleanup_errors = []
        try:
            try:
                query(f"DELETE FROM users WHERE email='{injected_email}';")
            except Exception as error:
                cleanup_errors.append(('bypass account deletion', error))
        finally:
            # Independent of deletion, including cancellation during that operation.
            try:
                query(f"UPDATE users SET role='USER' WHERE userid={admin['id']} AND email='{admin['email']}';")
            except Exception as error:
                cleanup_errors.append(('administrator demotion', error))
        if cleanup_errors:
            details = '; '.join(f'{stage}: {type(error).__name__}: {error}'
                                for stage, error in cleanup_errors)
            message = (f'Synthetic fixture cleanup incomplete (prefix={prefix}, '
                       f'administrator id={admin["id"]}): {details}')
            if primary_error is not None:
                # Keep the original exception/traceback; report every cleanup failure separately.
                print('ERROR: ' + message, file=sys.stderr)
            else:
                # A pending successful return must not escape after incomplete cleanup.
                raise RuntimeError(message) from cleanup_errors[0][1]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--slot',choices=['a','b'],required=True)
    parser.add_argument('--mode',choices=['observe','verify'],default='verify');parser.add_argument('--mysql')
    args=parser.parse_args()
    try:print(json.dumps(run(args.slot,args.mode,args.mysql),ensure_ascii=False,indent=2))
    except Exception as error:print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

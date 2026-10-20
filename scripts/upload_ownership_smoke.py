#!/usr/bin/env python3
"""Real isolated upload management/first-binding regressions, using synthetic accounts only."""
import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from baseline import validate
from dev import ROOT, read_env
from smoke import synthetic_mp3


def run(slot, mysql=None, candidate_port=None):
    env=read_env(slot);validate(slot,env)
    if candidate_port is not None and candidate_port != 18080+(slot=='b'):
        raise RuntimeError('Candidate port must match the isolated slot (18080/18081).')
    base='http://127.0.0.1:'+str(candidate_port or env['MUSIC_SERVER_PORT'])+'/api'
    client=mysql or shutil.which('mysql') or str(ROOT.parent/'.music-tools/mysql-8.0.41-macos15-arm64/bin/mysql')
    prefix='u-'+secrets.token_hex(5);checks=[];denials=[]

    def request(method,path,token=None,body=None,data=None,headers=None):
        outgoing=dict(headers or {})
        if token:outgoing['Authorization']='Bearer '+token
        if body is not None:data=json.dumps(body).encode();outgoing['Content-Type']='application/json'
        try:response=urlopen(Request(base+path,data=data,headers=outgoing,method=method),timeout=20)
        except HTTPError as error:response=error
        with response:return response.status,response.read()

    def api(method,path,token=None,body=None,**kwargs):
        status,payload=request(method,path,token,body,**kwargs);value=json.loads(payload)
        if status!=200 or value.get('code')!=200:
            raise RuntimeError(f'{method} {path}: HTTP {status}, envelope code={value.get("code")}')
        return value.get('data')

    def check(name,ok):
        if not ok:raise RuntimeError('Failed: '+name)
        checks.append(name)

    def user(suffix):
        email=prefix+'-'+suffix+'@example.invalid';password=secrets.token_urlsafe(12)
        created=api('POST','/auth/register',body={'email':email,'password':password,'name':prefix+suffix})
        token=api('POST','/auth/login',body={'email':email,'password':password})['token']
        return {'id':int(created['userid']),'email':email,'token':token}

    def query(sql):
        result=subprocess.run([client,'--protocol=TCP','--host=127.0.0.1','--port='+env['MUSIC_DB_PORT'],
            '--user='+env['MUSIC_DB_USER'],'--database='+env['MUSIC_DB_NAME'],'--batch','--skip-column-names'],
            input=sql,text=True,capture_output=True,timeout=15,env={**os.environ,'MYSQL_PWD':env['MUSIC_DB_PASSWORD']})
        if result.returncode:raise RuntimeError('Synthetic ownership fixture query failed.')
        return result.stdout.strip().splitlines()

    def update_user(account,assignment):
        assert account['email'].startswith(prefix) and "'" not in account['email']
        query(f"UPDATE users SET {assignment} WHERE userid={account['id']} AND email='{account['email']}';")

    def multipart(fields,payload,filename='chunk.bin',field='chunk'):
        boundary='music-'+secrets.token_hex(10);parts=[]
        for key,value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+payload+b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return {'data':b''.join(parts),'headers':{'Content-Type':'multipart/form-data; boundary='+boundary}}

    owner,other,admin=user('owner'),user('other'),user('admin');promoted=False;locked=False
    try:
        update_user(admin,"role='ADMIN'");promoted=True
        audio=synthetic_mp3(prefix);md5=hashlib.md5(audio).hexdigest()
        def create(token,content=audio):
            return api('POST','/file/create',token,{'fileName':prefix+'.mp3','fileSize':len(content),
                'fileMd5':hashlib.md5(content).hexdigest(),'chunkCount':2,'ownerUserId':other['id']})
        record=create(owner['token']);fid=int(record['id'])
        check('create persists server owner and ignores forged owner',record['ownerUserId']==owner['id'])
        check('owner persisted in real database',query(f'SELECT owner_user_id FROM file_upload WHERE id={fid};')==[str(owner['id'])])
        check('foreign MD5 check reveals no ID or path',api('GET','/file/check?fileMd5='+md5,other['token']).get('fileId') is None)
        check('administrator MD5 check also private',api('GET','/file/check?fileMd5='+md5,admin['token']).get('fileId') is None)
        first,second=audio[:len(audio)//2],audio[len(audio)//2:]
        chunk_request=multipart({'fileId':fid,'chunkIndex':0,'chunkMd5':hashlib.md5(first).hexdigest()},first)

        def operations(file_id):
            return [('GET',f'/file/{file_id}',{}),('GET',f'/file/status/{file_id}',{}),
                ('GET',f'/file/missing-chunks?fileId={file_id}',{}),('POST',f'/file/merge?fileId={file_id}',{}),
                ('DELETE',f'/file/{file_id}',{}),('POST',f'/music-resources/metadata?fileId={file_id}',{'body':{'title':prefix}}),
                ('POST','/file/chunk',multipart({'fileId':file_id,'chunkIndex':0,'chunkMd5':hashlib.md5(first).hexdigest()},first))]

        def reject_all(file_id,viewer,token,expected):
            for method,path,args in operations(file_id):
                code,_=request(method,path,token,**args)
                check(viewer+' denied '+method+' '+path,code==expected)
                denials.append({'viewer':viewer,'operation':method+' '+path,'status':code})
        for viewer,token in [('anonymous',None),('other',other['token']),('administrator',admin['token'])]:
            reject_all(fid,viewer,token,401 if token is None else 404)
        check('denied requests leave zero chunks and unchanged upload status',query(f'SELECT status, uploaded_chunks FROM file_upload WHERE id={fid};')==['0\t0'] and query(f'SELECT COUNT(*) FROM file_chunk WHERE file_id={fid};')==['0'])
        api('POST','/file/chunk',owner['token'],**chunk_request)
        check('owner sees persisted resumable first chunk',api('GET',f'/file/status/{fid}',owner['token'])['uploadedChunkIndexes']==[0])
        api('POST','/file/chunk',owner['token'],**multipart({'fileId':fid,'chunkIndex':1,'chunkMd5':hashlib.md5(second).hexdigest()},second))
        relative=api('POST',f'/file/merge?fileId={fid}',owner['token'])['filePath']
        check('owner can download own unbound complete upload',request('GET',f'/file/download/{fid}',owner['token'])==(200,audio))
        check('other cannot download unbound complete upload',request('GET',f'/file/download/{fid}',other['token'])[0]==404)
        check('administrator cannot download foreign unbound upload',request('GET',f'/file/download/{fid}',admin['token'])[0]==404)
        check('owner MD5 reuse stays within owner',int(api('GET','/file/check?fileMd5='+md5,owner['token'])['fileId'])==fid)
        for person in [other,admin]:
            check('completed file cannot be claimed by '+str(person['id']),request('POST',f'/music-resources/metadata?fileId={fid}',person['token'],{'title':prefix+'-claim'})[0]==404)
        duplicate=api('POST','/file/upload',other['token'],**multipart({},audio,prefix+'.mp3','file'))
        check('same bytes uploaded by second account get independent owner ID and path',duplicate['ownerUserId']==other['id'] and int(duplicate['id'])!=fid and duplicate['filePath']!=relative)
        check('each account MD5 lookup resolves own record',int(api('GET','/file/check?fileMd5='+md5,other['token'])['fileId'])==int(duplicate['id']))
        own_page=api('GET','/file/list?fileName='+prefix,owner['token'])['records']
        other_page=api('GET','/file/list?fileName='+prefix,other['token'])['records']
        check('lists isolate owners even with matching content',len(own_page)==1 and int(own_page[0]['id'])==fid and len(other_page)==1 and int(other_page[0]['id'])==int(duplicate['id']))
        check('owner metadata preview works before binding',api('POST',f'/music-resources/metadata?fileId={fid}',owner['token'])['title']==prefix)
        api('POST',f'/music-resources/metadata?fileId={fid}',owner['token'],{'title':prefix,'artist':'Synthetic','categoryId':1,'tagIds':[]})
        check('linked upload cannot be deleted',request('DELETE',f'/file/{fid}',owner['token'])[0]==409)
        orphan_id=int(duplicate['id']);orphan_path=env['MUSIC_UPLOAD_PATH']+'/'+duplicate['filePath']
        api('DELETE',f'/file/{orphan_id}',other['token'])
        check('unbound deletion tombstones upload while retaining bytes',query(f'SELECT deleted FROM file_upload WHERE id={orphan_id};')==['1'] and os.path.isfile(orphan_path))
        check('deleted upload management and download unavailable',request('GET',f'/file/{orphan_id}',other['token'])[0]==404 and request('GET',f'/file/download/{orphan_id}',other['token'])[0]==404)
        legacy=create(owner['token'],synthetic_mp3(prefix+'-legacy'));legacy_id=int(legacy['id'])
        query(f"UPDATE file_upload SET owner_user_id=NULL WHERE id={legacy_id} AND owner_user_id={owner['id']};")
        reject_all(legacy_id,'legacy former owner',owner['token'],404)
        check('legacy record remains unclaimed',query(f'SELECT owner_user_id IS NULL FROM file_upload WHERE id={legacy_id};')==['1'])
        update_user(owner,'is_locked=1');locked=True
        reject_all(fid,'locked owner',owner['token'],403)
        for method,path,args in [('GET','/file/list',{}),('GET','/file/check?fileMd5='+md5,{}),
            ('POST','/file/create',{'body':{'fileName':'f.mp3'}}),('POST','/file/upload',multipart({},audio,prefix+'.mp3','file'))]:
            check('locked owner cannot '+path,request(method,path,owner['token'],**args)[0]==403)
        update_user(owner,'is_locked=0');locked=False
        check('owner access restored after unlock',request('GET',f'/file/{fid}',owner['token'])[0]==200)
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ9sAAAAASUVORK5CYII=')
        image=api('POST','/file/upload',owner['token'],**multipart({},png,prefix+'.png','file'))
        check('foreign image cannot be registered as avatar',request('PUT','/auth/profile',other['token'],{'avatar':image['filePath']})[0]==404)
        check('foreign image remains nonpublic before owner registers it',request('GET','/uploads/'+image['filePath'])[0]==401)
        api('PUT','/auth/profile',owner['token'],{'avatar':image['filePath']})
        check('own uploaded avatar remains public',request('GET','/uploads/'+image['filePath'])==(200,png))
        check('registered avatar upload cannot be deleted',request('DELETE',f"/file/{image['id']}",owner['token'])[0]==409)
        removed=user('removed')
        assert removed['email'].startswith(prefix)
        query(f"DELETE FROM users WHERE userid={removed['id']} AND email='{removed['email']}';")
        check('deleted account stale JWT denied',request('GET','/file/list',removed['token'])[0]==401)
        return {'slot':slot,'base_url':base,'checks':checks,'check_count':len(checks),'denials':denials,
            'limits':['Synthetic isolated fixtures, not independent account B review.','No fault rollback, concurrent requests, or process restart recovery tested here.','Legacy uploads quarantined; no inferred owner backfill.','Physical garbage collection deferred.']}
    finally:
        if locked:update_user(owner,'is_locked=0')
        if promoted:update_user(admin,"role='USER'")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot',choices=['a','b'],required=True)
    parser.add_argument('--mysql')
    parser.add_argument('--candidate-port',type=int,help='Optional separate candidate backend: 18080 for A / 18081 for B')
    args=parser.parse_args()
    try:print(json.dumps(run(args.slot,args.mysql,args.candidate_port),ensure_ascii=False,indent=2))
    except Exception as error:print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

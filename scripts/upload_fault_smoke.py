#!/usr/bin/env python3
"""Real SQL rollback and filesystem failures on new synthetic uploads in one isolated slot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from baseline import validate
from dev import ROOT, read_env
from smoke import synthetic_mp3


def cleanup_constraints(query, names):
    """Try every exact owned CHECK; no global settings or trigger privileges required."""
    failures=[]
    for name in reversed(names):
        match=re.fullmatch(r'music_fault_[a-f0-9]{12}_(insert|count|merge)',name)
        if not match:
            failures.append(name+': invalid owned constraint name');continue
        table='file_chunk' if match.group(1)=='insert' else 'file_upload'
        lookup=("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() "
                f"AND table_name='{table}' AND constraint_name='{name}' AND constraint_type='CHECK';")
        try:
            existing=query(lookup)
            if existing==['1']:query(f'ALTER TABLE `{table}` DROP CHECK `{name}`;')
            elif existing!=['0']:raise RuntimeError('unexpected constraint metadata')
            if query(lookup)!=['0']:raise RuntimeError('constraint still exists')
        except Exception as error:failures.append(name+': '+type(error).__name__)
    return failures


def run(slot,mysql=None):
    env=read_env(slot);validate(slot,env)
    base='http://127.0.0.1:'+env['MUSIC_SERVER_PORT']+'/api'
    client=mysql or str(ROOT.parent/'.music-tools/mysql-8.0.41-macos15-arm64/bin/mysql')
    nonce=secrets.token_hex(6);prefix='f-'+nonce;checks=[];constraints=[];token=None;owner_id=None;primary=None;file_names={}
    state=ROOT/'.local'/slot/'upload-fault-constraints.json'
    if state.exists():raise RuntimeError('Prior fault constraint registry preserved; inspect and clean that run before retrying.')
    def query(sql):
        result=subprocess.run([client,'--protocol=TCP','--host=127.0.0.1','--port='+env['MUSIC_DB_PORT'],
            '--user='+env['MUSIC_DB_USER'],'--database='+env['MUSIC_DB_NAME'],'--batch','--skip-column-names'],
            input=sql,text=True,capture_output=True,timeout=15,env={**os.environ,'MYSQL_PWD':env['MUSIC_DB_PASSWORD']})
        if result.returncode:
            error_path=ROOT/'.local'/slot/'logs'/'MUS-014-fault-query-error.log'
            error_path.write_text(result.stderr);error_path.chmod(0o600)
            diagnostic=re.search(r'ERROR (\d+) \(([^)]+)\)',result.stderr)
            detail=diagnostic.group(0) if diagnostic else 'exit '+str(result.returncode)
            raise RuntimeError('Isolated upload fault fixture query failed: '+sql.split()[0]+' '+detail)
        return result.stdout.strip().splitlines()
    def api(method,path,body=None,data=None,headers=None,success=True):
        headers=dict(headers or {})
        if token:headers['Authorization']='Bearer '+token
        if body is not None:data=json.dumps(body).encode();headers['Content-Type']='application/json'
        try:response=urlopen(Request(base+path,data=data,headers=headers,method=method),timeout=30)
        except HTTPError as error:response=error
        with response:
            value=json.loads(response.read());ok=value.get('code')==200
            if response.status!=200 or ok!=success:raise RuntimeError(f'{method} {path}: HTTP {response.status}, code={value.get("code")}')
            return value.get('data')
    def check(name,ok):
        if not ok:raise RuntimeError('Failed: '+name)
        checks.append(name)
    def create():
        filename=prefix+'-'+str(len(file_names)+1)+'.mp3'
        record=api('POST','/file/create',{'fileName':filename,'fileSize':len(payload),
            'fileMd5':hashlib.md5(payload).hexdigest(),'chunkCount':1})
        fid=int(record['id']);file_names[fid]=filename
        if query(f'SELECT COUNT(*) FROM file_upload WHERE id={fid} AND owner_user_id={owner_id} AND deleted=0;')!=['1']:
            raise RuntimeError('Fault injection refused: synthetic owner does not match persisted upload.')
        return fid
    def send(fid,success=True):
        boundary='fault-'+nonce
        parts=[]
        for key,value in [('fileId',fid),('chunkIndex',0),('chunkMd5',hashlib.md5(payload).hexdigest())]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="chunk"; filename="chunk.bin"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+payload+b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return api('POST','/file/chunk',data=b''.join(parts),headers={'Content-Type':'multipart/form-data; boundary='+boundary},success=success)
    def progress(fid):
        return query(f'SELECT status,uploaded_chunks FROM file_upload WHERE id={fid};'),query(f'SELECT COUNT(*) FROM file_chunk WHERE file_id={fid};')
    def directory(fid):
        root=Path(env['MUSIC_UPLOAD_TEMP_PATH']).resolve();path=root/str(fid)
        if path.resolve()!=path:raise RuntimeError('Unexpected synthetic temporary directory alias.')
        return path
    def file_count(fid):
        p=directory(fid)
        if not p.exists():return 0
        return sum(x.is_file() for x in p.iterdir())
    def registry():
        # No token/password. Durable names allow exact manual cleanup after an uncatchable process death.
        state.write_text(json.dumps({'slot':slot,'nonce':nonce,'owned_constraints':constraints})+'\n');state.chmod(0o600)
    def inject(kind,fid):
        name='music_fault_'+nonce+'_'+kind
        table='file_chunk' if kind=='insert' else 'file_upload'
        if query("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='"+name+"';")!=['0']:
            raise RuntimeError('Existing constraint name preserved; injection refused.')
        constraints.append(name);registry()  # Include ambiguous DDL responses in cleanup.
        filename=file_names[fid]
        if query(f"SELECT COUNT(*) FROM file_upload WHERE file_name='{filename}' AND owner_user_id={owner_id};")!=['1']:
            raise RuntimeError('Fault fixture name is not unique within its owner; injection refused.')
        # MySQL forbids CHECK references to auto-increment id. A freshly generated,
        # verified-unique filename plus owner selects exactly this known file_id.
        guard=f"file_name<>'{filename}' OR owner_user_id<>{owner_id}"
        condition=(f'file_id<>{fid}' if kind=='insert' else
                   guard+' OR uploaded_chunks=0' if kind=='count' else guard+' OR status<>1')
        query(f'ALTER TABLE `{table}` ADD CONSTRAINT `{name}` CHECK ({condition});')
        return name
    def release(name):
        errors=cleanup_constraints(query,[name])
        if errors:raise RuntimeError('Fault cleanup incomplete: '+'; '.join(errors))
        constraints.remove(name);registry()
    payload=synthetic_mp3(prefix)
    email=prefix+'@example.invalid';password=secrets.token_urlsafe(12)
    owner_id=int(api('POST','/auth/register',{'name':prefix,'email':email,'password':password})['userid'])
    token=api('POST','/auth/login',{'email':email,'password':password})['token']
    fd=os.open(state,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as output:json.dump({'slot':slot,'nonce':nonce,'owned_constraints':[]},output)
    try:
        fid=create();name=inject('insert',fid);send(fid,False)
        check('insert failure leaves no chunk row and zero persisted progress',progress(fid)==(['0\t0'],['0']))
        check('insert failure removes candidate bytes',file_count(fid)==0)
        release(name);send(fid)
        check('same upload succeeds once after insert fault removal',progress(fid)==(['0\t1'],['1']))
        send(fid);check('duplicate retry still has one row one count one file',progress(fid)==(['0\t1'],['1']) and file_count(fid)==1)
        fid=create();name=inject('count',fid);send(fid,False)
        check('counter update failure rolls back earlier chunk INSERT',progress(fid)==(['0\t0'],['0']))
        check('counter failure removes candidate bytes',file_count(fid)==0)
        release(name);send(fid);check('counter rollback can retry without stale rows',progress(fid)==(['0\t1'],['1']))
        fid=create();path=directory(fid);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as block:block.write(b'synthetic exclusive directory blocker')
        try:
            send(fid,False)
            check('filesystem write failure has no successful ACK or persisted progress',progress(fid)==(['0\t0'],['0']))
        finally:path.unlink()
        send(fid);check('filesystem failure retries on the same upload',progress(fid)==(['0\t1'],['1']))
        fid=create();send(fid);name=inject('merge',fid)
        root=Path(env['MUSIC_UPLOAD_PATH']).resolve();before={p.resolve() for p in root.rglob('*') if p.is_file()}
        api('POST',f'/file/merge?fileId={fid}',success=False)
        after={p.resolve() for p in root.rglob('*') if p.is_file()}
        check('merge publication failure rolls back status path and count',progress(fid)==(['0\t1'],['1']) and query(f'SELECT file_path FROM file_upload WHERE id={fid};')==['temp/'+hashlib.md5(payload).hexdigest()])
        check('merge rollback preserves valid source chunk bytes',file_count(fid)==1 and next(directory(fid).iterdir()).read_bytes()==payload)
        check('merge rollback removes unpublished target file',before==after)
        release(name);result=api('POST',f'/file/merge?fileId={fid}')
        target=(root/result['filePath']).resolve()
        check('merge retries and publishes exact original bytes',target.is_relative_to(root) and target.read_bytes()==payload and progress(fid)==(['1\t1'],['1']))
        check('successful merge removes its chunk source after commit',file_count(fid)==0)
        fid=create();send(fid);source=next(directory(fid).iterdir());source.write_bytes(b'x'*len(payload))
        api('POST',f'/file/merge?fileId={fid}',success=False)
        check('corrupt persisted chunk cannot complete merge',progress(fid)==(['0\t1'],['1']))
        send(fid);check('corrupt chunk repaired without duplicate row or count',progress(fid)==(['0\t1'],['1']) and file_count(fid)==1 and next(directory(fid).iterdir()).read_bytes()==payload)
        result=api('POST',f'/file/merge?fileId={fid}')
        check('repaired upload merges to original bytes',(root/result['filePath']).read_bytes()==payload)
        check('all created fault constraints removed before success',not constraints)
        return {'slot':slot,'status':'passed','checks':checks,'check_count':len(checks),
            'scope':'real HTTP + MySQL statement faults + filesystem failures; new synthetic owner only',
            'limits':['No transaction-commit acknowledgement loss or database outage simulated.','No restart evidence from this probe.','No claim about concurrent human writes to the same isolated slot.']}
    except BaseException as error:primary=error;raise
    finally:
        errors=cleanup_constraints(query,constraints)
        if errors:
            message='Fault constraint cleanup incomplete; retained registry '+str(state)+': '+'; '.join(errors)
            if primary is not None:print(message,file=sys.stderr)
            else:raise RuntimeError(message)
        else:state.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--slot',choices=['a','b'],required=True);parser.add_argument('--mysql')
    args=parser.parse_args()
    try:print(json.dumps(run(args.slot,args.mysql),indent=2))
    except Exception as error:print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

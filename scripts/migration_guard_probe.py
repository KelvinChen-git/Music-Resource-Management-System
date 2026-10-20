#!/usr/bin/env python3
"""Exercise guards in a disposable native MySQL instance; never connects to existing servers."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from dev import ROOT, SQL
from upload_ownership_migration import migrate, SQL as OWNERSHIP_SQL


def run(mysql_base, slot="a"):
    base=Path(mysql_base).resolve();checks=[]
    for name in ['mysql','mysqld']:
        if not (base/'bin'/name).is_file():raise RuntimeError('Native mysql and mysqld required.')
    logs=ROOT/'.local'/slot/'logs';logs.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='music-migration-probe-',dir='/tmp') as temporary:
        folder=Path(temporary);data=folder/'data';socket=folder/'mysql.sock';database='music_probe_'+secrets.token_hex(5)
        server=None
        with (logs/'MUS-013-migration-native.log').open('w') as log:
            try:
                common=[str(base/'bin/mysqld'),'--no-defaults','--basedir='+str(base),'--datadir='+str(data)]
                result=subprocess.run(common+['--initialize-insecure'],stdout=log,stderr=subprocess.STDOUT,timeout=90)
                if result.returncode:raise RuntimeError('Disposable MySQL initialization failed; see private native log.')
                server=subprocess.Popen(common+['--skip-networking','--mysqlx=0','--socket='+str(socket),
                    '--pid-file='+str(folder/'mysqld.pid')],stdout=log,stderr=subprocess.STDOUT)
                client=[str(base/'bin/mysql'),'--no-defaults','--protocol=SOCKET','--socket='+str(socket),
                    '--user=root','--batch','--skip-column-names','--connect-timeout=2']
                environment={k:v for k,v in os.environ.items() if k not in ['MYSQL_PWD','MYSQL_UNIX_PORT','MYSQL_HOST']}
                def query(sql,selected=True):
                    command=client+(['--database='+database] if selected else [])
                    result=subprocess.run(command,input=sql,text=True,capture_output=True,env=environment,timeout=15)
                    if result.returncode:raise RuntimeError('Disposable MySQL query failed; no existing server was targeted.')
                    return result.stdout.strip().splitlines()
                deadline=time.monotonic()+45
                while True:
                    if server.poll() is not None:raise RuntimeError('Disposable mysqld exited; see private native log.')
                    try:query('SELECT 1;',False);break
                    except RuntimeError:
                        if time.monotonic()>deadline:raise RuntimeError('Disposable MySQL readiness timed out.')
                        time.sleep(0.25)
                query(f'CREATE DATABASE `{database}`;',False)
                def reset():
                    assert database.startswith('music_probe_') and socket.parent==folder
                    query(f'DROP DATABASE `{database}`; CREATE DATABASE `{database}`;',False)
                    query(SQL.read_text())
                def check(name,condition):
                    if not condition:raise RuntimeError('Failed: '+name)
                    checks.append(name)
                def rejected(name):
                    statements=[]
                    def observed(sql):statements.append(sql);return query(sql)
                    try:migrate(observed)
                    except RuntimeError:
                        check(name,all(s.startswith('SELECT') for s in statements));return
                    raise RuntimeError('Unexpected migration accepted: '+name)
                reset()
                query("INSERT INTO file_upload(file_name,file_size,file_md5,file_path,file_type,chunk_size,chunk_count) VALUES ('probe.mp3',1,REPEAT('0',32),'temp/probe','mp3',1,1);")
                check('recognized V001 upgrades and legacy owner remains NULL',migrate(query)['legacy_rows']==1)
                check('completed migration is repeatable',migrate(query)['version']==2)
                reset();query('RENAME TABLE file_chunk TO file_chunk_unexpected;')
                rejected('same-count substituted table rejected without DDL or version write')
                check('substituted schema remains V001 without owner column',query('SELECT version FROM development_schema_version;')==['1'] and query("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='owner_user_id';")==['0'])
                reset();query('ALTER TABLE file_upload DROP COLUMN file_md5;')
                rejected('missing upload column rejected before writes')
                reset();query(OWNERSHIP_SQL.read_text())
                check('DDL committed before marker can be resumed',migrate(query)['version']==2)
                query('ALTER TABLE file_upload ALTER COLUMN owner_user_id SET DEFAULT 1;')
                rejected('non-NULL owner default rejected without writes')
                reset();query(OWNERSHIP_SQL.read_text())
                query('ALTER TABLE file_upload DROP INDEX idx_upload_owner_md5, ADD UNIQUE INDEX idx_upload_owner_md5(owner_user_id,file_md5,deleted);')
                rejected('unique owner index rejected without marker write')
                return {'status':'passed','checks':checks,'check_count':len(checks),'isolation':'new private datadir, unique schema, Unix socket, networking disabled; no existing DB connection','cleanup':'owned mysqld stopped and temporary directory removed in finally'}
            finally:
                if server and server.poll() is None:
                    server.terminate()
                    try:server.wait(timeout=15)
                    except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql-base',required=True)
    parser.add_argument('--slot',choices=['a','b'],default='a')
    args=parser.parse_args()
    try:print(json.dumps(run(args.mysql_base,args.slot),indent=2))
    except Exception as error:print(json.dumps({'status':'blocked','error':str(error)}));raise SystemExit(1)

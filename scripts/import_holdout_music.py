#!/usr/bin/env python3
"""Import frozen G1 recordings through the existing ordinary-owner HTTP API.

Independent private copies/catalog; never edits G1, old40, credentials or privileges.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlencode

import holdout_assets as assets
import import_research_music as legacy

ROOT=Path(__file__).resolve().parents[1]
require=assets.require


def encoded(value):
    return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode()+b'\n'


def write_new(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        os.fchmod(f.fileno(),0o600);f.write(raw)


def preserve(path,raw):
    if path.exists() or path.is_symlink():
        require(assets.read(path,max(assets.MAX_JSON,assets.source.MAX_AUDIO))==raw
                and path.stat().st_mode&0o777==0o600,'Private copy changed; preserved for review')
    else:write_new(path,raw)


def checkpoint(path,value):
    if path.exists() or path.is_symlink():
        assets.regular(path);require(path.stat().st_mode&0o777==0o600,'Ledger mode changed')
    temporary=path.parent/('.checkpoint-'+secrets.token_hex(12))
    write_new(temporary,encoded(value));os.replace(temporary,path)


def private_target(path):
    path=Path(path).absolute();local=ROOT/'.local'
    require(local.is_dir() and not any(p.is_symlink() for p in (path,*path.parents))
            and path.resolve().is_relative_to(local.resolve()) and path.resolve()!=local.resolve()
            and path.parent.is_dir(),'Output must stay in existing private checkout root')
    if not path.exists():path.mkdir(mode=0o700);path.chmod(0o700)
    require(path.is_dir() and path.stat().st_mode&0o777==0o700,'Private output must be0700')
    return path


def verify_old(client,owner,old):
    for row,path in old:
        audio=assets.read(path,assets.source.MAX_AUDIO)
        matches=legacy.matching(client,row['title'],row['artist'],row['album'])
        require(len(matches)==1,'Original40 metadata missing or ambiguous')
        check=client.api('GET','/file/check?'+urlencode({'fileMd5':hashlib.md5(audio).hexdigest()}))
        require(check.get('exists') is True and assets.integer_id(check.get('fileId'))==assets.integer_id(row['fileId']), 'Original40 upload identity changed')
        legacy.verify_resource(matches[0],int(owner),legacy.file_path(check.get('filePath')),len(audio),int(row['musicId']))
        legacy.verify_media(client,int(row['musicId']),audio)


def catalog_value(context,owner,ledger):
    return {'schema':assets.IMPORT_SCHEMA,'split':'independent_test_imported_assets','owner_user_id':owner,
        'source_binding_sha256':context['binding_sha256'],'source_dataset_sha256':context['manifest']['dataset_sha256'],
        'development40_catalog_sha256':context['binding']['development40']['sha256'],
        'importer_source_sha256':ledger['binding']['importer_source_sha256'],
        'helper_source_sha256':ledger['binding']['helper_source_sha256'],
        'tracks':[assets.imported_track(t,context['manifest'],ledger['tracks'][t['recording_key']]) for t in context['tracks']]}


def validate_ledger(ledger,binding,context,old):
    require(isinstance(ledger,dict) and set(ledger)=={'binding','tracks'} and ledger['binding']==binding
            and isinstance(ledger['tracks'],dict),'Import ledger binding changed')
    expected={t['recording_key']:t for t in context['tracks']}
    require(set(ledger['tracks'])<=set(expected),'Unknown source ledger entry')
    files={assets.integer_id(t['fileId']) for t,_ in old};music={assets.integer_id(t['musicId']) for t,_ in old}
    for key,saved in ledger['tracks'].items():
        t=expected[key]
        require(isinstance(saved,dict) and {'sha256','md5','fileId','filePath'}<=set(saved)
                and set(saved)<={'sha256','md5','fileId','filePath','musicId','verified'},'Invalid ledger track fields')
        raw=assets.read(context['source_root']/t['audio_filename'],assets.source.MAX_AUDIO)
        require(saved['sha256']==t['content_sha256'] and saved['md5']==hashlib.md5(raw).hexdigest(),'Ledger content changed')
        fid=assets.integer_id(saved['fileId']);require(fid not in files,'Duplicate ledger/old file identity');files.add(fid)
        legacy.file_path(saved['filePath'])
        if 'musicId' in saved:
            mid=assets.integer_id(saved['musicId']);require(mid not in music,'Duplicate ledger/old music identity');music.add(mid)
        require('verified' not in saved or (saved['verified'] is True and 'musicId' in saved),'Invalid verified ledger state')


def run(*,binding,binding_sha256,backend_checkout,output_state,slot='a',transport=None,decode=None):
    context=assets.checked_source(binding,binding_sha256)
    owner,old=assets.baseline40(context)
    backend_checkout=Path(backend_checkout).absolute()
    credentials,_=legacy.backend_settings(backend_checkout,slot,backend_checkout/'.local/a/music-catalog',int(owner))
    target=private_target(output_state)
    protected=[context['source_root'],ROOT/assets.source.relative(context['binding']['development40']['audio_root'])]
    require(all(not target.is_relative_to(p) and not p.is_relative_to(target) for p in protected),'Output overlaps immutable source/audio')
    lock=target/'import.lock';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),0o600);f.write(encoded({'pid':os.getpid(),'slot':slot}))
    lock_inode=lock.stat().st_ino;client=None;prior_cache=os.environ.get('NUMBA_CACHE_DIR');prior_mask=os.umask(0o077)
    try:
        require(set(p.name for p in target.iterdir())<={'import.lock','import-ledger.json','audio','decode-cache','catalog.json'},'Unexpected output artifacts')
        binding_record={'input_binding_sha256':binding_sha256,'source_manifest_sha256':context['binding']['source_manifest']['sha256'],
            'owner_user_id':owner,'slot':slot,'backend_checkout':str(backend_checkout.resolve()),
            'importer_source_sha256':assets.digest(assets.read(Path(__file__))),
            'helper_source_sha256':assets.digest(assets.read(Path(assets.__file__))),
            'HTTP_helper_source_sha256':assets.digest(assets.read(Path(legacy.__file__)))}
        ledger_path=target/'import-ledger.json'
        if ledger_path.exists():ledger=assets.source.strict_json(assets.read(ledger_path))
        else:
            require(set(p.name for p in target.iterdir())=={'import.lock'},'Artifacts without a ledger are preserved for review')
            ledger={'binding':binding_record,'tracks':{}};checkpoint(ledger_path,ledger)
        validate_ledger(ledger,binding_record,context,old)
        for name in ['audio','decode-cache']:
            path=target/name
            if not path.exists():path.mkdir(mode=0o700);path.chmod(0o700)
            require(path.is_dir() and not path.is_symlink() and path.stat().st_mode&0o777==0o700,'Private subdirectory changed')
        os.environ['NUMBA_CACHE_DIR']=str(target/'decode-cache')
        # Complete actual EOF/PCM validation before any HTTP operation or mutation.
        again=assets.checked_source(binding,binding_sha256,decode=decode or assets.source.decode_actual)
        require(again['tracks']==context['tracks'],'Source changed during actual decode')
        assets.recheck(context['hashes'])
        expected_files=set()
        for t in context['tracks']:
            name=assets.filename(t)
            for suffix,original in [('.mp3',t['audio_filename']),('.download.json',t['download_proof_filename'])]:
                expected_files.add(name+suffix)
                preserve(target/'audio'/(name+suffix),assets.read(context['source_root']/original,assets.source.MAX_AUDIO))
        require({f.name for f in (target/'audio').iterdir()}==expected_files,'Unexpected imported audio/proof copy')
        if (target/'catalog.json').exists():
            require(len(ledger['tracks'])==20 and all(t.get('verified') is True for t in ledger['tracks'].values()),'Catalog has incomplete ledger')
            preserve(target/'catalog.json',encoded(catalog_value(context,owner,ledger)))
            assets.validate_catalog(catalog_value(context,owner,ledger),context,target/'audio')
        client=transport or legacy.HttpTransport()
        session=client.api('POST','/auth/login',{'email':credentials['email'],'password':credentials['password']})
        require(isinstance(session,dict) and isinstance(session.get('token'),str) and session['token'],'Existing owner login failed')
        client.token=session['token'];viewer=client.api('GET','/auth/profile')
        require(viewer.get('role')=='USER' and assets.integer_id(viewer.get('userid'))==owner,'Confirmed ordinary owner required')
        verify_old(client,owner,old)
        used_files={assets.integer_id(t['fileId']) for t,_ in old};used_music={assets.integer_id(t['musicId']) for t,_ in old}
        created_uploads=created_metadata=0
        for t in context['tracks']:
            key=t['recording_key'];meta=assets.metadata(t,context['manifest'])
            audio=assets.read(target/'audio'/(assets.filename(t)+'.mp3'),assets.source.MAX_AUDIO);md5=hashlib.md5(audio).hexdigest()
            saved=ledger['tracks'].get(key);matches=legacy.matching(client,**meta)
            check=client.api('GET','/file/check?'+urlencode({'fileMd5':md5}))
            require(isinstance(check,dict) and type(check.get('exists')) is bool,'Invalid upload lookup')
            if check['exists']:fid,path=legacy.positive(int(assets.integer_id(check.get('fileId')))),legacy.file_path(check.get('filePath'))
            else:
                require(saved is None and not matches and check.get('fileId') is None,'Missing previous upload or unrelated metadata')
                boundary='sonora-'+secrets.token_hex(12)
                binary=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{assets.filename(t)}.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()+audio+f'\r\n--{boundary}--\r\n'.encode())
                uploaded=client.api('POST','/file/upload',binary=binary,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
                require(assets.integer_id(uploaded.get('ownerUserId'))==owner and uploaded.get('fileMd5')==md5
                        and uploaded.get('fileSize')==len(audio) and uploaded.get('status')==1,'Upload owner/content mismatch')
                fid,path=int(assets.integer_id(uploaded.get('id'))),legacy.file_path(uploaded.get('filePath'));created_uploads+=1
            require(str(fid) not in used_files and (saved is None or (saved['fileId'],saved['filePath'])==(fid,path)), 'Upload identity changed or reused old file')
            saved=saved or {'sha256':t['content_sha256'],'md5':md5,'fileId':fid,'filePath':path}
            ledger['tracks'][key]=saved;checkpoint(ledger_path,ledger)
            if not matches:
                require('musicId' not in saved,'Previously imported metadata is missing')
                client.api('POST','/music-resources/metadata?fileId='+str(fid),meta);created_metadata+=1
                matches=legacy.matching(client,**meta)
            require(len(matches)==1 and matches[0].get('approvalStatus')=='pending','Pending imported metadata missing or changed')
            mid=legacy.verify_resource(matches[0],int(owner),path,len(audio),saved.get('musicId'))
            require(str(mid) not in used_music,'Duplicate or original music identity')
            saved['musicId']=mid;checkpoint(ledger_path,ledger)
            legacy.verify_media(client,mid,audio)
            saved['verified']=True;checkpoint(ledger_path,ledger)
            used_files.add(str(fid));used_music.add(str(mid))
        verify_old(client,owner,old)
        assets.recheck(context['hashes'])
        require(binding_record['importer_source_sha256']==assets.digest(assets.read(Path(__file__)))
                and binding_record['helper_source_sha256']==assets.digest(assets.read(Path(assets.__file__)))
                and binding_record['HTTP_helper_source_sha256']==assets.digest(assets.read(Path(legacy.__file__))), 'Importer/helper source changed during import')
        catalog=catalog_value(context,owner,ledger)
        assets.validate_catalog(catalog,context,target/'audio')
        preserve(target/'catalog.json',encoded(catalog))
        return {'status':'imported_and_verified_independent20','new_tracks':20,'old_tracks_verified_before_and_after':40,
            'new_range_and_full_SHA_verified':20,'created_uploads':created_uploads,'created_metadata':created_metadata,
            'catalog_sha256':assets.digest(assets.read(target/'catalog.json')),'source_dataset_sha256':context['manifest']['dataset_sha256'],
            'pending_tracks':20,'judgments':0,'vectors_built':0}
    finally:
        if client is not None:client.token=None
        os.umask(prior_mask)
        if prior_cache is None:os.environ.pop('NUMBA_CACHE_DIR',None)
        else:os.environ['NUMBA_CACHE_DIR']=prior_cache
        if lock.exists() and not lock.is_symlink() and lock.stat().st_ino==lock_inode:lock.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['binding','backend-checkout','output-state']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--binding-sha256',required=True)
    try:result=run(**{k.replace('-','_'):v for k,v in vars(parser.parse_args()).items()})
    except Exception:parser.exit(1,'Holdout import stopped; original inputs and private recovery state preserved.\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

"""Shared synthetic fixture construction for holdout unit tests only; never imported by production."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import test_holdout_music as source_fixtures
import test_research_import as HTTP_fixtures
import holdout_assets as assets
import import_holdout_music as importer


class FakeHTTP(HTTP_fixtures.FakeLocal):
    def __init__(self,*args):
        super().__init__(*args);self.bad_new_media=None
    def api(self,method,url,body=None,binary=None,headers=None):
        try:return super().api(method,url,body,binary,headers)
        finally:
            if method=='POST' and url.startswith('/music-resources/metadata') and self.resources:
                self.resources[-1]['approvalStatus']='pending'
    def media(self,path,headers=None):
        result=super().media(path,headers)
        if int(path.split('/')[2])>=2000 and self.bad_new_media:
            status,head,raw=result
            if self.bad_new_media=='full' and not headers:return status,head,raw[:-1]+b'x'
            if self.bad_new_media=='range' and headers:return status,head,b'wrong'
        return result


class HoldoutFixture:
    def prepare_fixture(self):
        f=source_fixtures.HoldoutCollectionTest(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture=f;self.root=f.root;self.owner=62
        self.old_audio={};self.old_tracks=[];oldroot=self.root/'.local/a/development40';oldroot.mkdir(mode=0o700)
        for i in range(40):
            provider='jamendo' if i<20 else 'incompetech';sid=str(10000+i) if i<20 else 'USABC'+str(2400000+i)
            body=b'ID3 old synthetic recording '+str(i).encode()+b'Q'*100;self.old_audio[sid]=body
            source='https://www.jamendo.com/track/'+sid if i<20 else 'https://incompetech.com/music/royalty-free/index.html?isrc='+sid
            t={'sourceProvider':provider,'sourceId':sid,'title':'Old title '+str(i),'artist':'Old artist '+str(i),'album':'Old album',
                'musicId':200+i,'fileId':100+i,'sha256':assets.digest(body),'sourceUrl':source,
                'licenseUrl':'https://creativecommons.org/licenses/by/4.0/','rangeVerified':True,'fullBytesVerified':True}
            self.old_tracks.append(t)
            (oldroot/(provider+'-'+sid+'.mp3')).write_bytes(body)
            (oldroot/(provider+'-'+sid+'.download.json')).write_text(json.dumps({'sha256':t['sha256'],'size':len(body),'source':source,'license':t['licenseUrl'].replace('https:','http:')}))
            f.old['creator_groups'][i]['works'][0]['content_sha256']=t['sha256']
        f.save();f.make_v2()
        # Short synthetic performer names fit the same existing API boundary as the real recordings.
        replacements={b'Synthetic MusicBox performer A':b'MB performer A',b'Synthetic MusicBox performer B':b'MB performer B'}
        for name in f.frame['snapshots']:
            path=f.state/name;raw=path.read_bytes()
            for a,b in replacements.items():raw=raw.replace(a,b)
            path.write_bytes(raw);path.chmod(0o600);f.frame['snapshots'][name]=assets.digest(raw)
        for row in f.rows:
            if row['source_provider']==assets.source.MUSICBOX:
                row['contributors']=['MB performer A','MB performer B']
                row['rights_snapshot_sha256']=f.frame['snapshots'][row['rights_snapshot']]
        f.frame['tracks']=f.rows;f.save();f.run_batch()
        self.manifest_path=f.output/'manifest.json';self.manifest=json.loads(self.manifest_path.read_text())
        for relative in ['scripts/collect_holdout_music.py','services/audio-search/research_corpus.py','services/audio-search/preprocess.py']:
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((assets.ROOT/relative).read_bytes())
        for module in [assets,importer]:
            item=patch.object(module,'ROOT',self.root);item.start();self.addCleanup(item.stop)
        self.baseline=self.root/'.local/a/development40.json'
        self.baseline.write_text(json.dumps({'schema':'sonora-research-catalog-v1','slot':'a','ownerId':self.owner,'audioTracks':self.old_tracks}))
        self.freeze_path=f.state/'source-freeze.json'
        groups={t['creator_group'] for t in self.manifest['tracks']}
        self.freeze={'schema':'sonora-holdout-source-dataset-freeze-receipt-v1','version':2,'tracks':20,
            'creator_groups':len(groups),'work_groups':20,'source_manifest_sha256':assets.digest(self.manifest_path.read_bytes()),
            'source_dataset_sha256':self.manifest['dataset_sha256'],'protocol_sha256':assets.source.PROTOCOL_V2_SHA,
            'source_frame_sha256':f.frame_sha,'group_review_sha256':f.groups_sha,'replacement_queue_frozen':True,
            'fixed_complete_priority_queue_sha256':self.manifest['priority_queue_sha256']}
        self.freeze_path.write_text(json.dumps(self.freeze))
        pairs={'protocol':self.root/'docs/evaluation/MUS-039-protocol-v2.json','frame':f.frame_path,'group_review':f.groups_path,
            'old_group_review':f.old_path,'source_manifest':self.manifest_path,'source_freeze':self.freeze_path,'development40':self.baseline}
        self.binding={'schema':'sonora-holdout-input-binding-v1',**{k:{'path':str(path.relative_to(self.root)),'sha256':assets.digest(path.read_bytes())} for k,path in pairs.items()}}
        self.binding['development40']['audio_root']=str(oldroot.relative_to(self.root))
        self.binding_path=self.root/'.local/a/binding.json';self.save_binding()
        self.output=self.root/'.local/a/imported20';self.backend=self.root/'backend'
        state=self.backend/'.local/a';cache=state/'music-catalog';cache.mkdir(parents=True,mode=0o700)
        env={'MUSIC_DB_HOST':'127.0.0.1','SPRING_PROFILES_ACTIVE':'local','MUSIC_DB_NAME':'music_dev_a','MUSIC_DB_USER':'music_dev_a',
            'MUSIC_DB_PORT':'3307','MUSIC_SERVER_PORT':'8080','VITE_DEV_PORT':'5173','VITE_PROXY_TARGET':'http://127.0.0.1:8080',
            'MUSIC_UPLOAD_PATH':str(state/'uploads'),'MUSIC_UPLOAD_TEMP_PATH':str(state/'chunks')}
        (state/'config.json').write_text(json.dumps(env));(cache/'demo-account.json').write_text(json.dumps({'email':'synthetic@example.invalid','password':'synthetic-only-password'}))
        self.client=FakeHTTP(self.owner,self.old_tracks,self.old_audio)

    def save_binding(self):
        self.binding_path.write_text(json.dumps(self.binding));self.binding_sha=assets.digest(self.binding_path.read_bytes())

    def source_context(self,**kwargs):return assets.checked_source(self.binding_path,self.binding_sha,**kwargs)

    def run_import(self,**changes):
        args={'binding':self.binding_path,'binding_sha256':self.binding_sha,'backend_checkout':self.backend,
              'output_state':self.output,'transport':self.client,'decode':self.fixture.decode}
        args.update(changes);return importer.run(**args)

    def resign_manifest(self):
        unsigned=deepcopy(self.manifest);unsigned.pop('dataset_sha256')
        self.manifest['dataset_sha256']=assets.digest(assets.canonical(unsigned))
        self.manifest_path.write_bytes(assets.canonical(self.manifest)+b'\n')
        self.binding['source_manifest']['sha256']=assets.digest(self.manifest_path.read_bytes())
        self.freeze['source_manifest_sha256']=self.binding['source_manifest']['sha256'];self.freeze['source_dataset_sha256']=self.manifest['dataset_sha256']
        self.freeze_path.write_text(json.dumps(self.freeze));self.binding['source_freeze']['sha256']=assets.digest(self.freeze_path.read_bytes());self.save_binding()

#!/usr/bin/env python3
"""Locked, resumable, bounded acquisition; no final test audio or training."""
import argparse,fcntl,json,os,ssl,sys,time,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.request import HTTPSHandler,build_opener
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services/audio-search'))
import holdout_contract as h
import review_pack as rp
from preflight_mtg import fetch_one,Redirects,write_raw


class JournalBudget:
    def __init__(self,path,maximum):
        self.path=Path(path);self.maximum=maximum;self.lock=threading.RLock();self.events=[];self.used=0
        if self.path.exists():
            raw=h.assets.read(self.path,16*1024*1024)
            rp.require(not raw or raw.endswith(b'\n'),'Truncated journal; fail closed')
            self.events=[h.assets.source.strict_json(line)for line in raw.splitlines()]
            self.used=sum(e['bytes']for e in self.events if e['event']=='charge')
        rp.require(self.used<=maximum,'Persisted budget exceeded')
    def append(self,event):
        with self.lock:
            event={'time':h.now(),**event};raw=h.canonical(event)+b'\n'
            fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600);os.fchmod(fd,0o600)
            try:rp.require(os.write(fd,raw)==len(raw),'Journal append incomplete');os.fsync(fd)
            finally:os.close(fd)
            self.events.append(event)
    def read(self,response,size):
        with self.lock:
            rp.require(0<=size<=self.maximum-self.used,'Persistent body budget exhausted')
            self.append({'event':'charge','bytes':size});self.used+=size
        return response.read(size) # Charge full reservation even on timeout/truncation/crash.


def decoded(path):
    import numpy as np
    import soundfile as sf
    from research_corpus import decode_source_mono
    from corpus import window_bounds
    with sf.SoundFile(path)as x:head={'frames':x.frames,'sample_rate_hz':x.samplerate,'channels':x.channels,'format':x.format,'duration_ms':x.frames*1000//x.samplerate}
    audio,info=decode_source_mono(path,head)
    return {**info,'pcm_sha256':h.digest(audio.astype('<f4',copy=False).tobytes()),'segments':len(window_bounds(len(audio)))}


def prior_context(inputs,config,target,prior40_root):
    manifest=h.assets.document(inputs,config['source_inputs_sha256'])
    old=h.assets.document(manifest['files']['prior40']['path'],manifest['files']['prior40']['sha256'])['audioTracks']
    new=h.assets.document(manifest['files']['prior20']['path'],manifest['files']['prior20']['sha256'])['tracks']
    if (target/'prior60.json').exists():
        cached=json.loads((target/'prior60.json').read_text());rp.require(cached['inputs_sha256']==config['source_inputs_sha256'],'Prior context mismatch');return cached
    rows=[]
    for t in old:
        path=Path(prior40_root)/(t['sourceProvider']+'-'+str(t['sourceId'])+'.mp3')
        rp.require(h.file_hash(path)==t['sha256'],'Old audio differs from catalog')
        rows.append({'audio_sha256':t['sha256'],'pcm_sha256':decoded(path)['pcm_sha256']})
    rows.extend({'audio_sha256':t['content_sha256'],'pcm_sha256':t['pcm_sha256']}for t in new)
    result={'inputs_sha256':config['source_inputs_sha256'],'tracks':rows,'count':len(rows),'decoder':'65536_actual_EOF_48k_mono_float32le'}
    h.write_json(target/'prior60.json',result);return result


def acquire(*,config,config_sha256,dataset,dataset_sha256,inputs,prior40_root,output,ca_file=None):
    cfg=h.assets.document(config,config_sha256);data=h.assets.document(dataset,dataset_sha256)
    rp.require(data['config_sha256']==config_sha256 and set(data['selected'])=={'train','validation','caption_dev'},'Fixed non-test source data required')
    root=Path(output).absolute()
    if not root.exists():h.private_output(root)
    rp.require(not any(p.is_symlink()for p in(root,*root.parents))and root.is_relative_to(h.ROOT/'.local'),'Private nonsymlink output required')
    fd=os.open(root/'.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600);os.fchmod(fd,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        context={'schema':'sonora-resumable-source-corpus-v1','config_sha256':config_sha256,'dataset_sha256':dataset_sha256,'decoder_sha256':h.file_hash(ROOT/'services/audio-search/research_corpus.py'),'transport_sha256':h.file_hash(ROOT/'scripts/preflight_mtg.py'),'decoder_dependencies':{n:h.file_hash(ROOT/'services/audio-search'/n)for n in('corpus.py','preprocess.py','review_pack.py')}}
        if(root/'context.json').exists():rp.require(json.loads((root/'context.json').read_text())==context,'Cannot resume different context')
        else:h.write_json(root/'context.json',context)
        journal=JournalBudget(root/'journal.jsonl',cfg['max_total_body_bytes']);journal.append({'event':'run_start','script_sha256':h.file_hash(__file__)})
        prior_existed=(root/'prior60.json').exists()
        prior=prior_context(inputs,cfg,root,prior40_root)
        known_prior=[e['sha256']for e in journal.events if e['event']=='prior_pin']
        if prior_existed:rp.require(known_prior and known_prior[-1]==h.file_hash(root/'prior60.json'),'Unregistered or changed prior PCM context')
        else:journal.append({'event':'prior_pin','sha256':h.file_hash(root/'prior60.json')})
        priorfiles={r['audio_sha256']for r in prior['tracks']};priorpcm={r['pcm_sha256']for r in prior['tracks']}
        started=time.monotonic();deadline=started+cfg['max_acquisition_seconds'];results={};failures=[]
        def worker(split,t):
            rp.require(time.monotonic()<deadline,'Acquisition time budget exceeded')
            parent=root/split/t['source_track_id'];parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            # Parents below root are all task-owned directories; enforce modes explicitly.
            for p in(parent,parent.parent):p.chmod(0o700)
            key=split+'/'+t['source_track_id']
            for attempt in range(1,cfg['max_download_attempts_per_track']+1):
                dest=parent/f'attempt-{attempt}';receipt=dest/'receipt.json'
                if receipt.exists():
                    r=h.assets.source.strict_json(h.assets.read(receipt,128*1024))
                    rp.require(r['key']==key and r['audio_sha256']==t['audio_sha256'] and h.file_hash(dest/'audio.mp3')==t['audio_sha256'],'Resume receipt/audio mismatch')
                    known=[e['receipt_sha256']for e in journal.events if e['event']=='ready'and e['key']==key]
                    if known:rp.require(h.file_hash(receipt)==known[-1],'Registered receipt changed')
                    else:rp.require(decoded(dest/'audio.mp3')['pcm_sha256']==r['decode']['pcm_sha256'],'Unregistered recovery PCM mismatch')
                    return {**r,'receipt_path':str(receipt),'receipt_sha256':h.file_hash(receipt)}
                if dest.exists():continue # Preserve failed/partial attempt; never overwrite it.
                dest.mkdir(mode=0o700);dest.chmod(0o700)
                try:
                    opener=build_opener(Redirects(),HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
                    raw,proof=fetch_one(opener,t,cfg,journal)
                    rp.require(t['audio_sha256']not in priorfiles,'Prior60 exact byte duplicate')
                    write_raw(dest/'audio.mp3',raw);info=decoded(dest/'audio.mp3')
                    rp.require(info['pcm_sha256']not in priorpcm,'Prior60 normalized PCM duplicate')
                    r={'key':key,'split':split,'source_track_id':t['source_track_id'],'audio_sha256':t['audio_sha256'],'bytes':len(raw),'transport':proof,'decode':info}
                    h.write_json(receipt,r);digest=h.file_hash(receipt)
                    journal.append({'event':'ready','key':key,'receipt_sha256':digest})
                    return {**r,'receipt_path':str(receipt),'receipt_sha256':digest}
                except Exception as exc:
                    h.write_json(dest/'failure.json',{'error_type':type(exc).__name__,'error':str(exc)})
                    journal.append({'event':'failure','key':key,'attempt':attempt,'error_type':type(exc).__name__})
            raise ValueError('Technical attempts exhausted: '+key)
        jobs=[(split,t)for split,rows in data['selected'].items()for t in rows]
        with ThreadPoolExecutor(max_workers=cfg['workers'])as pool:
            pending={pool.submit(worker,s,t):(s,t)for s,t in jobs}
            for fut in as_completed(pending):
                s,t=pending[fut]
                try:results[(s,t['source_track_id'])]=fut.result()
                except Exception as exc:failures.append((s,t,str(exc)))
                if len(results)%10==0:print(json.dumps({'ready':len(results),'required':len(jobs),'budget_charged_bytes':journal.used}),flush=True)
        replacements=[];used={k for k in results}
        order={(s,t['source_track_id']):i for i,(s,t)in enumerate(jobs)}
        failures.sort(key=lambda f:order[(f[0],f[1]['source_track_id'])])
        for split,original,error in failures:
            found=False
            for reserve in data['reserves'][split]:
                if(split,reserve['source_track_id'])in used:continue
                used.add((split,reserve['source_track_id']))
                try:
                    results[(split,original['source_track_id'])]=worker(split,reserve)
                    replacements.append({'split':split,'original':original['source_track_id'],'replacement':reserve['source_track_id'],'technical_reason':error});found=True;break
                except Exception:continue
            rp.require(found,'Frozen technical reserve exhausted; no result-based substitution')
        # Pair final receipt with its original fixed slot, retaining the full replacement audit.
        rows=[];seen={}
        for split,t in jobs:
            r=results[(split,t['source_track_id'])];pcm=r['decode']['pcm_sha256']
            rp.require(pcm not in seen,'New corpus PCM collision; explicit quarantine/re-freeze required')
            seen[pcm]=r['key'];rows.append({**r,'original_slot_track_id':t['source_track_id']})
        disk=sum(p.stat().st_size for p in root.rglob('*')if p.is_file())
        rp.require(disk<=cfg['max_disk_bytes'],'Disk budget exceeded')
        result={'schema':'sonora-bounded-caption-gate-corpus-v1','status':'ready_train_validation_caption_dev_only','created_at_utc':h.now(),
                **context,'tracks':rows,'replacements':replacements,'budget_charged_bytes':journal.used,'disk_bytes':disk,'prior60_PCM_pins_verified':60,
                'counts':{s:sum(r['split']==s for r in rows)for s in data['selected']},'caption_test_audio_downloads':0,'reserved_tag_test_audio_downloads':0}
        # Append immutable run snapshots; the context and each track's original receipt stay fixed.
        n=1
        while(root/f'catalog-{n}.json').exists():n+=1
        h.write_json(root/f'catalog-{n}.json',result)
        journal.append({'event':'run_complete','catalog':f'catalog-{n}.json','catalog_sha256':h.file_hash(root/f'catalog-{n}.json')})
        return result
    finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('config','dataset','inputs','prior40-root','output'):p.add_argument('--'+k,type=Path,required=True)
    for k in('config-sha256','dataset-sha256'):p.add_argument('--'+k,required=True)
    p.add_argument('--ca-file');r=acquire(**vars(p.parse_args()));print(json.dumps({'status':r['status'],'counts':r['counts'],'budget_charged_bytes':r['budget_charged_bytes']}))
if __name__=='__main__':main()

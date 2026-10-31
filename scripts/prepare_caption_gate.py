#!/usr/bin/env python3
"""Freeze fixed-prefix tag batches and grouped human-caption dev/test metadata."""
from pathlib import Path
import argparse,csv,json,sys
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services/audio-search'))
import mtg_dataset as m
from mtg_plan import Groups
import holdout_contract as h
import review_pack as rp


def prepare(config,config_sha256,inputs,plan,output):
    cfg=h.assets.document(config,config_sha256);manifest=h.assets.document(inputs,cfg['source_inputs_sha256']);future=h.assets.document(plan,cfg['source_plan_sha256'])
    raw={k:h.assets.read(v['path'],40*1024*1024)for k,v in manifest['files'].items()}
    rp.require(all(h.digest(v)==manifest['files'][k]['sha256']for k,v in raw.items()),'Source metadata changed')
    rp.require(h.digest(raw['sdd'])==cfg['sdd_sha256'],'SDD version changed')
    base=m.table(raw['base']);names,_=m.names(raw['names']);rights=m.licenses(raw['licenses']);hashes=m.checksums(raw['audio_sha256'])
    old=json.loads(raw['prior40'])['audioTracks'];new=json.loads(raw['prior20'])['tracks'];pilot=h.assets.document(ROOT/'.local/a/mus043/metadata-02/selection.json','6a338dc43b57fc7d04785d836254ba1b755e2579875ae0839b5acc283a80a28b')['selected']
    priorIDs={str(int(t['sourceId']))for t in old if t['sourceProvider']=='jamendo'}
    blocked={n['artist_id']for tid,n in names.items()if m.source_id(tid,'track')in priorIDs}
    usednames=set().union(*(m.aliases(t['artist'])for t in old),*(m.aliases(t['imported_metadata']['artist'])for t in new),*(m.aliases(t['artist_name'])for rows in future['selected'].values()for t in rows),*(m.aliases(t['artist_name'])for t in pilot))
    usedworks={m.norm(t['title'])for t in old+new}|{m.norm(t['title'])for rows in future['selected'].values()for t in rows}|{m.norm(t['title'])for t in pilot}
    usedSHA={t['sha256']for t in old}|{t['content_sha256']for t in new}|{t['audio_sha256']for rows in future['selected'].values()for t in rows}|{t['audio_sha256']for t in pilot}
    for n in names.values():
        if n['artist_id']in blocked:usednames.update(m.aliases(n['artist']))
    captions=defaultdict(list)
    for row in csv.DictReader(raw['sdd'].decode('utf8').splitlines()):
        if row['is_valid_subset'].lower()in('true','1'):
            tid='track_'+str(int(row['track_id'].removeprefix('track_'))).zfill(7)
            rp.require(isinstance(row['caption'],str)and row['caption'].strip(),'Empty validated caption')
            captions[tid].append({'caption_id':row['caption_id'],'text':row['caption'].strip()})
    candidates=[];groups=Groups();aliasowner={}
    for tid,cs in captions.items():
        t=base.get(tid);n=names.get(tid)
        if not t or not n:continue
        low=t['path'].removesuffix('.mp3')+'.low.mp3'
        if not 30<=t['duration']<=600 or rights[t['path']]['family']not in('by','by-sa')or low not in hashes:continue
        if t['artist_id']in blocked or m.aliases(n['artist'])&usednames or m.norm(n['title'])in usedworks or hashes[low]in usedSHA:continue
        record={'source_track_id':tid,'official_split':'caption_source_test','artist_id':t['artist_id'],'artist_name':n['artist'],'title':n['title'],**t,'low_path':low,'audio_sha256':hashes[low],'audio_license':rights[t['path']],'caption_count':len(cs)}
        candidates.append(record)
        for alias in m.aliases(n['artist']):
            if alias in aliasowner:groups.union(t['artist_id'],aliasowner[alias])
            else:aliasowner[alias]=t['artist_id']
    ordered=sorted(candidates,key=lambda t:(h.digest((cfg['caption_seed']+'\n'+t['source_track_id']).encode()),t['source_track_id']))
    unique=[];usedgroup=set();usedtitle=set();usedhash=set()
    for t in ordered:
        g=groups.root(t['artist_id']);title=m.norm(t['title'])
        if g in usedgroup or title in usedtitle or t['audio_sha256']in usedhash:continue
        unique.append({**t,'creator_component':g});usedgroup.add(g);usedtitle.add(title);usedhash.add(t['audio_sha256'])
    rp.require(len(unique)>=42,'Need42 independent caption source groups before freeze')
    dev=unique[:20];test=unique[20:40];reserve=unique[40:42]
    for t in dev+reserve:t['captions']=captions[t['source_track_id']]
    selected={'train':future['selected']['train'][:100],'validation':future['selected']['validation'][:20],'caption_dev':dev}
    reserves={'train':future['selected']['train'][100:120],'validation':future['selected']['validation'][20:24],'caption_dev':reserve}
    result={'schema':'sonora-caption-dev-gate-source-freeze-v1','created_at_utc':h.now(),'config_sha256':config_sha256,'source_plan_sha256':cfg['source_plan_sha256'],'selected':selected,'reserves':reserves,'caption_test_reserved':test,
        'summary':{'selected_counts':{k:len(v)for k,v in selected.items()},'reserves':{k:len(v)for k,v in reserves.items()},'caption_eligible_records':len(candidates),'caption_independent_groups':len(unique),'caption_dev_queries':sum(t['caption_count']for t in dev),'caption_test_metadata_records':20,'caption_test_text_exported':False,'caption_test_audio_downloads':0,'new_human_labels':0}}
    target=h.private_output(output);h.write_json(target/'dataset.json',result);return result


def main():
    p=argparse.ArgumentParser();
    for k in ('config','inputs','plan','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--config-sha256',required=True)
    print(json.dumps(prepare(**vars(p.parse_args()))['summary']))
if __name__=='__main__':main()

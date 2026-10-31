#!/usr/bin/env python3
"""Frozen-feature encoding and finite mean-loss adapter comparison on caption-dev only."""
from pathlib import Path
import argparse,json,os,sys,subprocess,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services/audio-search'))
import holdout_contract as h
import review_pack as rp
import tag_adapter as a
import caption_metrics as metrics
from train_tag_adapter import save_npz


def encode(*,config,config_sha256,dataset,dataset_sha256,corpus,corpus_sha256,inputs,freeze,freeze_sha256,output):
    import numpy as np
    cfg=h.assets.document(config,config_sha256);data=h.assets.document(dataset,dataset_sha256);cat=h.assets.document(corpus,corpus_sha256)
    rp.require(cat['config_sha256']==data['config_sha256']==config_sha256 and cat['dataset_sha256']==dataset_sha256,'Fixed cache source context required')
    rp.require(cat['counts']=={'train':100,'validation':20,'caption_dev':20}and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Complete corpus and clean committed encoder required')
    original,_=h.checked_freeze(freeze,freeze_sha256,verify_environment=True)
    manifest=h.assets.document(inputs,cfg['source_inputs_sha256'])
    import mtg_dataset as m
    trainraw=h.assets.read(manifest['files']['train']['path'],40*1024*1024)
    rp.require(h.digest(trainraw)==manifest['files']['train']['sha256'],'Source vocabulary changed')
    vocabulary=sorted({tag for t in m.table(trainraw).values()for tag in t['tags']});rp.require(len(vocabulary)==183,'Vocabulary changed')
    lookup={(split,t['source_track_id']):t for split,rows in data['selected'].items()for t in rows}
    lookup.update({(split,t['source_track_id']):t for split,rows in data['reserves'].items()for t in rows})
    target=h.private_output(output);source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    deps=['scripts/evaluate_caption_gate.py','scripts/train_tag_adapter.py','services/audio-search/tag_adapter.py','services/audio-search/caption_metrics.py','services/audio-search/checkpoint_model.py','services/audio-search/research_corpus.py','services/audio-search/preprocess.py']
    context={'schema':'sonora-caption-feature-cache-binding-v1','source_sha':source,'source_sha256':{p:h.file_hash(ROOT/p)for p in deps},'config_sha256':config_sha256,'dataset_sha256':dataset_sha256,'corpus_sha256':corpus_sha256,'model':original['models']['A']['pin'],'environment':original['environment'],'recipe':'three_unit_window_mean_then_unit;caption_first120s;frozen_text;65536_actual_EOF_48k_mono'}
    context['cache_key_sha256']=h.digest(h.canonical(context));h.write_json(target/'freeze.json',context)
    try:
        import torch
        import soundfile as sf
        from checkpoint_model import load_checkpoint
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        torch.set_num_threads(2);torch.set_num_interop_threads(1);np.random.seed(0);torch.manual_seed(0)
        sdk,strict=load_checkpoint(original['models']['A']['pin']['path'],'A')
        for param in sdk.model.parameters():param.requires_grad_(False)
        whole=[];windows=[];rows=[];queries=[];query_tracks=[];token_lengths=[]
        prompts=['Music tagged with '+t.replace('---',': ',1)+'.'for t in vocabulary]
        with torch.inference_mode():
            prototypes=a.unit(np.concatenate([sdk.get_text_embedding(prompts[i:i+16],use_tensor=False)for i in range(0,len(prompts),16)]))
            for n,r in enumerate(cat['tracks'],1):
                t=lookup[(r['split'],r['source_track_id'])];audio_path=Path(r['receipt_path']).parent/'audio.mp3'
                rp.require(h.file_hash(audio_path)==r['audio_sha256'],'Ready source audio changed')
                with sf.SoundFile(audio_path)as z:head={'frames':z.frames,'sample_rate_hz':z.samplerate,'channels':z.channels,'format':z.format,'duration_ms':z.frames*1000//z.samplerate}
                audio,info=decode_source_mono(audio_path,head)
                rp.require(h.digest(audio.astype('<f4',copy=False).tobytes())==r['decode']['pcm_sha256'],'Ready PCM changed')
                if r['split']=='caption_dev':audio=audio[:120*48000]
                last=max(0,len(audio)-480000);starts=sorted({0,last//2,last})
                v=a.unit(sdk.get_audio_embedding_from_data(np.stack([prepare_window(audio[i:i+480000],48000)[0]for i in starts]),use_tensor=False))
                offset=len(windows);windows.extend(v);whole.append(a.unit(v.mean(axis=0,keepdims=True))[0])
                rows.append({'split':r['split'],'source_track_id':r['source_track_id'],'audio_sha256':r['audio_sha256'],'pcm_sha256':r['decode']['pcm_sha256'],'window_indices':list(range(offset,offset+len(v))),'window_start_samples':starts,'view_samples':len(audio),'positive_indices':[vocabulary.index(tag)for tag in t['tags']]})
                if r['split']=='caption_dev':
                    for q in t['captions']:queries.append(q['text']);query_tracks.append(r['source_track_id'])
                if n%10==0:print(json.dumps({'encoded':n,'total':len(cat['tracks'])}),flush=True)
            token_lengths=[len(sdk.tokenize(q,truncation=False)['input_ids'])for q in queries]
            texts=a.unit(np.concatenate([sdk.get_text_embedding(queries[i:i+8],use_tensor=False)for i in range(0,len(queries),8)]))
        save_npz(target/'features.npz',whole=np.stack(whole),windows=np.stack(windows),prototypes=prototypes,texts=texts)
        binding={**context,'created_at_utc':h.now(),'feature_sha256':h.file_hash(target/'features.npz'),'strict':strict,'rows':rows,'query_tracks':query_tracks,'query_text_sha256':[h.digest(q.encode())for q in queries],'caption_token_lengths':token_lengths,'vocabulary':vocabulary,'counts':{'audio_tracks':len(rows),'audio_windows':len(windows),'caption_dev_queries':len(queries),'caption_queries_over77':sum(n>77 for n in token_lengths),'prototype_tags':len(vocabulary),'reserved_test_model_inputs':0}}
        h.write_json(target/'cache.json',binding);return binding
    except Exception as exc:
        h.write_json(target/'failure.json',{'error_type':type(exc).__name__,'error':str(exc)});raise


def tag_buckets(z,p,positive,vocabulary,support):
    import numpy as np
    scores=a.unit(z)@a.unit(p).T;tops=[set(sorted(range(len(p)),key=lambda i:(-float(row[i]),i))[:5])for row in scores]
    result={}
    for category in('all','genre','instrument','mood/theme'):
        for bucket in('all','seen','rare','unseen'):
            values=[];labels=0
            for hit,ids in zip(tops,positive):
                subset=[i for i in ids if(category=='all'or vocabulary[i].split('---')[0]==category)and(bucket=='all'or bucket=='unseen'and support[i]==0 or bucket=='rare'and 1<=support[i]<=4 or bucket=='seen'and support[i]>=5)]
                if subset:values.append(len(hit&set(subset))/len(subset));labels+=len(subset)
            result[category+':'+bucket]={'eligible_recordings':len(values),'observed_positive_labels':labels,'macro_observed_Recall_at5':float(np.mean(values))if values else None}
    return result


def compare(*,config,config_sha256,cache,cache_sha256,output):
    import numpy as np
    cfg=h.assets.document(config,config_sha256);meta=h.assets.document(cache,cache_sha256)
    rp.require(meta['config_sha256']==config_sha256 and cfg['alphas']==[0.1,1.0,5.0],'Frozen finite candidate menu required')
    feature_path=Path(cache).parent/'features.npz';rp.require(h.file_hash(feature_path)==meta['feature_sha256'],'Feature cache changed')
    rp.require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Committed clean comparison source required')
    rp.require(all(h.file_hash(ROOT/n)==v for n,v in meta['source_sha256'].items()),'Bound feature recipe source changed')
    target=h.private_output(output)
    with np.load(feature_path,allow_pickle=False)as f:x=f['whole'];windows=f['windows'];p=f['prototypes'];texts=f['texts']
    rp.require(x.shape==(140,512)and p.shape==(183,512),'Unexpected bound feature shapes')
    train=[i for i,r in enumerate(meta['rows'])if r['split']=='train'];val=[i for i,r in enumerate(meta['rows'])if r['split']=='validation'];dev=[i for i,r in enumerate(meta['rows'])if r['split']=='caption_dev']
    positives=[meta['rows'][i]['positive_indices']for i in train];y=a.targets(p,positives);trainx=x[train]
    support=np.zeros(len(p),dtype=int)
    for ids in positives:support[ids]+=1
    candidates={'identity':(np.eye(512),None,None)}
    for alpha in cfg['alphas']:
        w,diagnostic=a.fit_mean(trainx,y,alpha);name='alpha-'+str(alpha)
        save_npz(target/(name+'.npz'),W=w,alpha=np.asarray(alpha));candidates[name]=(w,alpha,diagnostic)
    results={};ids=[meta['rows'][i]['source_track_id']for i in dev]
    for name,(w,alpha,diagnostic)in candidates.items():
        mapped=a.unit(x@w);whole=texts@mapped[dev].T
        segment=np.stack([np.max(texts@a.unit(windows[meta['rows'][i]['window_indices']]@w).T,axis=1)for i in dev],axis=1)
        results[name]={'alpha':alpha,'fit_diagnostic':diagnostic,'whole':metrics.paired(whole,meta['query_tracks'],ids),'segment':metrics.paired(segment,meta['query_tracks'],ids),
                       'tag_validation':tag_buckets(mapped[val],p,[meta['rows'][i]['positive_indices']for i in val],meta['vocabulary'],support)}
    deltas={k:metrics.paired_delta(v['whole'],results['identity']['whole'],cfg['bootstrap_iterations'],cfg['bootstrap_seed'])for k,v in results.items()if k!='identity'}
    chosen=metrics.choose(results,deltas)
    result={'schema':'sonora-caption-development-gate-comparison-v1','status':'development_gate_complete','created_at_utc':h.now(),'comparison_source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'config_sha256':config_sha256,'cache_sha256':cache_sha256,'feature_sha256':meta['feature_sha256'],'cache_key_sha256':meta['cache_key_sha256'],'counts':{'train':len(train),'tag_validation':len(val),'caption_dev':len(dev),'caption_queries':len(meta['query_tracks']),'fitted_candidates':3,'identity_candidates':1,'reserved_test_scored':0},
            'results':results,'paired_deltas':deltas,'selected':chosen,'scale_up_gate_passed':chosen!='identity','training_tag_support':{tag:int(count)for tag,count in zip(meta['vocabulary'],support)},
            'unseen_training_tags':[t for t,n in zip(meta['vocabulary'],support)if n==0],
            'adapter_artifact_sha256':{k:h.file_hash(target/(k+'.npz'))for k in candidates if k!='identity'},
            'limits':['Known caption-recording pair retrieval, unpaired recordings are not confirmed semantic negatives; no full relevance P@5.',
                      'SDD nominal first120s from official low-bitrate source, not byte-identical official SDD audio benchmark.',
                      'Twenty-recording development selection and descriptive grouped bootstrap, not final test significance or deployment approval.',
                      'Text unchanged; whole mapping after pooling; segment separately maps only three fixed windows, no localization claim.',
                      'No reference-audio query, all-window sensitivity or automatic index/model switch; reserved tests untouched.']}
    h.write_json(target/'result-private.json',result)
    public=json.loads(json.dumps(result))
    for row in public['results'].values():
        for mode in('whole','segment'):row[mode].pop('per_recording')
    h.write_json(target/'result-public.json',public);return public


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    z=sub.add_parser('encode')
    for k in('config','dataset','corpus','inputs','freeze','output'):z.add_argument('--'+k,type=Path,required=True)
    for k in('config-sha256','dataset-sha256','corpus-sha256','freeze-sha256'):z.add_argument('--'+k,required=True)
    z=sub.add_parser('compare')
    for k in('config','cache','output'):z.add_argument('--'+k,type=Path,required=True)
    for k in('config-sha256','cache-sha256'):z.add_argument('--'+k,required=True)
    args=vars(p.parse_args());command=args.pop('command');r=globals()[command](**args);print(json.dumps({'counts':r['counts'],'selected':r.get('selected')}))
if __name__=='__main__':main()

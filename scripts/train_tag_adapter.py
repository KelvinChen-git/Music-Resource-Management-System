#!/usr/bin/env python3
"""One real20 training-only smoke: frozen CLAP features plus positive-centroid ridge fit."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/audio-search'))
import holdout_contract as hc
import review_pack as rp

SOURCE_FILES=('services/audio-search/mtg_dataset.py','services/audio-search/mtg_plan.py','services/audio-search/tag_adapter.py',
              'scripts/train_tag_adapter.py','docs/evaluation/MUS-044-training-config.json')


def save_npz(path,**values):
    import numpy as np
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.fchmod(fd,0o600)
    with os.fdopen(fd,'wb')as f:np.savez(f,**values)


def run(*,config,config_sha256,selection,fetched,decoded,freeze,freeze_sha256,plan,plan_sha256,output):
    import numpy as np
    cfg=hc.assets.document(config,config_sha256)
    rp.require(cfg['training_smoke_tracks']==20 and cfg['lambda']==100.0 and cfg['dimension']==512
               and cfg['windows_per_track']==3 and cfg['validation_or_test_used_for_fit_or_selection']is False
               and cfg['CLAP_parameter_training']is False,'Fixed training-only smoke policy required')
    rp.require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Committed clean training source required')
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    s=hc.assets.document(selection,cfg['source_selection_sha256']);f=hc.assets.document(fetched,cfg['source_fetch_sha256']);d=hc.assets.document(decoded,cfg['source_decode_sha256'])
    future=hc.assets.document(plan,plan_sha256);rp.require(future['policy_sha256']==config_sha256,'Future metadata plan/config mismatch')
    frozen,_=hc.checked_freeze(freeze,freeze_sha256,verify_environment=True)
    rp.require(len(s['selected'])==len(f['tracks'])==len(d['tracks'])==20 and f['selection_sha256']==cfg['source_selection_sha256'] and d['fetched_sha256']==cfg['source_fetch_sha256'],'Original twenty/fetch/PCM bindings required')
    for t,proof,decoded_row in zip(s['selected'],f['tracks'],d['tracks']):
        rp.require(t['source_track_id']==proof['source_track_id']==decoded_row['source_track_id'] and t['official_split']=='train'
                   and hc.file_hash(Path(fetched).parent/proof['filename'])==t['audio_sha256']==proof['sha256'],'Pilot audio differs from frozen selection')
    target=hc.private_output(output);started=time.perf_counter()
    source_hashes={n:hc.file_hash(ROOT/n)for n in SOURCE_FILES}
    opening={'schema':'sonora-tag-adapter-training-freeze-v1','created_at_utc':hc.now(),'source_sha':source,'source_sha256':source_hashes,
             'config_sha256':config_sha256,'future_plan_sha256':plan_sha256,'selection_sha256':cfg['source_selection_sha256'],
             'fetch_sha256':cfg['source_fetch_sha256'],'decode_sha256':cfg['source_decode_sha256'],
             'model':frozen['models']['A']['pin'],'environment':frozen['environment'],
             'trained_parameter_groups':'positive_centroid_linear_adapter_only','training_tracks':20,'evaluation_tracks':0,'test_qrels_used':False}
    hc.write_json(target/'freeze.json',opening)
    try:
        import torch
        from checkpoint_model import load_checkpoint
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        import tag_adapter as adapter
        np.random.seed(0);torch.manual_seed(0);torch.set_num_threads(2);torch.set_num_interop_threads(1)
        sdk,strict=load_checkpoint(frozen['models']['A']['pin']['path'],'A')
        for parameter in sdk.model.parameters():parameter.requires_grad_(False)
        rp.require(not any(p.requires_grad for p in sdk.model.parameters()),'Frozen encoder must have zero trainable parameters')
        prompts=[cfg['prototype_template'].format(category=t.split('---')[0],tag=t.split('---')[1])for t in s['vocabulary']]
        lengths=[len(sdk.tokenize(t,truncation=False)['input_ids'])for t in prompts]
        rp.require(len(prompts)==183 and all(0<n<=77 for n in lengths),'Prototype text would truncate')
        features=[];positions=[]
        with torch.inference_mode():
            prototypes=np.concatenate([sdk.get_text_embedding(prompts[i:i+16],use_tensor=False)for i in range(0,len(prompts),16)])
            rp.require(prototypes.shape==(183,512)and np.isfinite(prototypes).all(),'Invalid prototype feature shape')
            for i,(t,proof,old)in enumerate(zip(s['selected'],f['tracks'],d['tracks']),1):
                path=Path(fetched).parent/proof['filename']
                import soundfile as sf
                with sf.SoundFile(path)as h:header={'frames':h.frames,'sample_rate_hz':h.samplerate,'channels':h.channels,'format':h.format,'duration_ms':h.frames*1000//h.samplerate}
                audio,info=decode_source_mono(path,header)
                rp.require(hc.digest(audio.astype('<f4',copy=False).tobytes())==old['pcm_sha256'] and all(info[k]==old[k]for k in info),'Training PCM differs from preflight')
                last=max(0,len(audio)-480000);starts=sorted({0,last//2,last})
                windows=np.stack([prepare_window(audio[a:a+480000],48000)[0]for a in starts])
                encoded=sdk.get_audio_embedding_from_data(windows,use_tensor=False)
                rp.require(encoded.shape==(len(starts),512),'Invalid audio feature shape')
                features.append(adapter.unit(adapter.unit(encoded).mean(axis=0,keepdims=True))[0]);positions.append(starts)
                print(f'Encoded training smoke {i}/20',flush=True)
        x=np.stack(features);p=adapter.unit(prototypes)
        positives=[[s['vocabulary'].index(tag)for tag in t['tags']]for t in s['selected']]
        y=adapter.targets(p,positives)
        save_npz(target/'features.npz',audio_features=x,prototype_features=p,positive_targets=y)
        hc.write_json(target/'feature-binding.json',{'source_track_ids':[t['source_track_id']for t in s['selected']],
                        'prototype_tags':s['vocabulary'],'positive_indices':positives,'window_start_samples':positions})
        w,diagnostic=adapter.fit(x,y,cfg['lambda'])
        save_npz(target/'adapter.npz',W=w,regularization=np.asarray(cfg['lambda']))
        before=adapter.observed_recall(x,p,positives);after=adapter.observed_recall(x@w,p,positives)
        rp.require(all(hc.file_hash(ROOT/n)==h for n,h in source_hashes.items()),'Training source changed')
        for t,proof in zip(s['selected'],f['tracks']):rp.require(hc.file_hash(Path(fetched).parent/proof['filename'])==t['audio_sha256'],'Training source audio changed')
        result={'schema':'sonora-positive-centroid-ridge-training-smoke-v1','status':'trained_lightweight_adapter_smoke_only_no_generalization_claim',
                'created_at_utc':hc.now(),'source_sha':source,'config_sha256':config_sha256,'freeze_sha256':hc.file_hash(target/'freeze.json'),
                'future_plan_sha256':plan_sha256,'checkpoint_sha256':frozen['models']['A']['pin']['sha256'],'strict':strict,
                'counts':{'training_tracks':20,'audio_windows':sum(len(a)for a in positions),'prototype_tags':183,'observed_training_tags':len({i for ids in positives for i in ids}),
                'fit_runs':1,'CLAP_parameters_trained':0,'validation_tracks':0,'test_tracks':0,'user_judgments_used':0},
                'training_diagnostics':diagnostic,'training_observed_tag_recall_before':before,'training_observed_tag_recall_after':after,
                'artifact_sha256':{n:hc.file_hash(target/n)for n in ('freeze.json','features.npz','feature-binding.json','adapter.npz')},
                'single_run_seconds':time.perf_counter()-started,
                'limits':['All20 are training smoke only; training objective/observed-tag recall are not validation/test or natural-language retrieval metrics.',
                          'Pretrained CLAP remains frozen and unchanged; trained artifact is a small linear layer, not full backbone fine-tuning.',
                          'No lambda search, new corpus downloads, deployment, model switch or use of141/160 human relevance grades.',
                          'Planned1000/200/200 metadata is not a downloaded/validated training corpus; its future content/group checks remain required.']}
        hc.write_json(target/'result.json',result);return result
    except Exception as exc:
        hc.write_json(target/'failed.json',{'status':'failed_training_smoke','error_type':type(exc).__name__,'error':str(exc)})
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('config','selection','fetched','decoded','freeze','plan','output'):p.add_argument('--'+key,type=Path,required=True)
    for key in ('config-sha256','freeze-sha256','plan-sha256'):p.add_argument('--'+key,required=True)
    r=run(**vars(p.parse_args()));print(__import__('json').dumps({'status':r['status'],'counts':r['counts'],'training_diagnostics':r['training_diagnostics']}))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""G2 synthetic-only freeze; G4 fresh independent five-run generation, never qrels."""
import argparse
import gc
import os
from pathlib import Path
import re
import time
import unicodedata

import holdout_contract as hc


def tokens(text):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKC',text).casefold())


def lexical_scores(titles,queries):
    """Unigram log-TF/smoothed-IDF fitted only on the twenty unlabeled titles."""
    from collections import Counter
    import numpy as np
    docs=[Counter(tokens(t)) for t in titles];words=sorted(set().union(*(set(t) for t in docs)))
    df=np.array([sum(w in d for d in docs) for w in words],dtype=np.float64)
    idf=np.log((1+len(docs))/(1+df))+1
    def matrix(rows):
        x=np.array([[1+np.log(row[w]) if row[w] else 0 for w in words] for row in rows],dtype=np.float64)
        x*=idf
        norm=np.linalg.norm(x,axis=1,keepdims=True)
        return np.divide(x,norm,out=np.zeros_like(x),where=norm>0)
    return matrix([Counter(tokens(q)) for q in queries])@matrix(docs).T


def configure():
    import numpy as np
    import torch
    np.random.seed(0);torch.manual_seed(0)
    torch.set_num_threads(2);torch.set_num_interop_threads(1)


def frozen_preflight(checkpoint,model,queries):
    import numpy as np
    import torch
    from checkpoint_model import load_checkpoint
    from preprocess import prepare_window
    sdk,strict=load_checkpoint(checkpoint,model)
    lengths=[len(sdk.tokenize(q['text_en'],truncation=False)['input_ids']) for q in queries]
    hc.require(all(0<n<=77 for n in lengths),'Frozen query would be truncated')
    waveform=0.1*np.sin(2*np.pi*220*np.arange(96000,dtype=np.float32)/48000)
    window,_=prepare_window(waveform,48000)
    with torch.inference_mode():
        audio=sdk.get_audio_embedding_from_data(np.stack([window]),use_tensor=False)
        text=sdk.get_text_embedding(['A sustained low electronic tone.'],use_tensor=False)
    for value in [audio,text]:
        hc.require(value.shape==(1,512) and value.dtype==np.float32 and np.isfinite(value).all(),
            'Synthetic audio/text embedding must be finite float32 1x512')
        hc.require(np.allclose(np.linalg.norm(value,axis=1),1,atol=1e-5),'Synthetic embedding not unit-normalized')
    del sdk;gc.collect()
    return {'pin':hc.checkpoint_pin(checkpoint,model),'strict':strict,'audio_shape':list(audio.shape),
        'text_shape':list(text.shape),'test_query_token_lengths':lengths,
        'synthetic_audio':'220Hz_2seconds_48000_float32_then_explicit_zero_pad_10seconds',
        'generic_development_text':'A sustained low electronic tone.'}


def freeze(*,output,checkpoint_a,checkpoint_b,**arguments):
    target=hc.private_output(output);started=time.perf_counter()
    try:
        source=hc.source_state();data=hc.snapshot(**arguments);env=hc.environment()
        initial={m:hc.checkpoint_pin(p,m) for m,p in [('A',checkpoint_a),('B',checkpoint_b)]}
        configure()
        models={m:frozen_preflight(pin['path'],m,data['queries']) for m,pin in initial.items()}
        hc.require(all(models[m]['pin']==pin for m,pin in initial.items()),'Model changed during preflight')
        hc.require(hc.source_state()==source and hc.snapshot(**arguments)==data and hc.environment()==env,
            'Inputs, source or environment changed during freeze')
        result={'schema':'sonora-independent-runner-freeze-v1','status':'frozen_before_test_inference',
            'created_at_utc':hc.now(),'arguments':data['arguments'],'source':source,
            'input_sha256':data['input_sha256'],'source_dataset_sha256':data['source_dataset_sha256'],
            'models':models,'environment':env,'counts':{'new_test_audio_encoded':0,'new_test_text_encoded':0,'qrels_opened':0},
            'configurations':data['config']['configurations'],'single_run_seconds':time.perf_counter()-started,
            'qrels_custody':'labeler_keeps_readable_exports_until_G5;hashes_are_not_access_control'}
        hc.write_json(target/'freeze.json',result)
        return result
    except Exception as exc:
        hc.write_json(target/'failure.json',{'status':'failed_G2','error_type':type(exc).__name__,'error':str(exc)})
        raise


def encode_model(model,path,data,audio_root,target):
    import numpy as np
    import torch
    from checkpoint_model import load_checkpoint
    from corpus import window_bounds,unit_vectors,rank_segments
    from preprocess import prepare_window
    from research_corpus import decode_source_mono
    from research_probe import write_vectors
    sdk,_=load_checkpoint(path,model);segments=[];blocks=[];whole=[]
    with torch.inference_mode():
        for t in data['tracks']:
            samples,info=decode_source_mono(Path(audio_root)/t['asset_filename'],t['recorded_decode'])
            hc.require(all(info[k]==t[k] for k in info) and hc.digest(samples.astype('<f4',copy=False).tobytes())==t['pcm_sha256'],
                'Actual EOF/PCM differs from G1 freeze')
            bounds=window_bounds(len(samples));track=[]
            for offset in range(0,len(bounds),4):
                windows=[]
                for start,end in bounds[offset:offset+4]:
                    window,padding=prepare_window(samples[start:end],48000);windows.append(window)
                    segments.append({'segment_id':f"{t['track_id']}:{start}:{end}",'track_id':t['track_id'],
                        'start_sample':start,'end_sample':end,'start_ms':start*1000//48000,
                        'end_ms':end*1000//48000,'padded_samples':padding['padded_samples']})
                vectors=unit_vectors(sdk.get_audio_embedding_from_data(np.stack(windows),use_tensor=False))
                hc.require(vectors.shape==(len(windows),512),'Invalid audio vector dimension')
                track.append(vectors)
            vectors=np.concatenate(track);blocks.append(vectors);whole.append(unit_vectors(vectors.mean(axis=0,keepdims=True))[0])
            print(f'{model}: encoded {len(whole)}/20',flush=True)
        texts=unit_vectors(sdk.get_text_embedding([q['text_en'] for q in data['queries']],use_tensor=False))
        hc.require(texts.shape==(8,512),'Invalid text vector dimension')
    all_segments=np.concatenate(blocks);all_whole=np.stack(whole)
    folder=target/model;folder.mkdir(mode=0o700);folder.chmod(0o700)
    write_vectors(folder/'vectors.npz',segment_vectors=all_segments,whole_vectors=all_whole,text_vectors=texts)
    hc.write_json(folder/'segments.json',segments)
    rankings={'whole':[],'segment':[]}
    for q,vector in zip(data['queries'],texts):
        scores=all_whole@vector
        order=sorted(range(20),key=lambda i:(-float(scores[i]),int(data['tracks'][i]['track_id'])))
        rankings['whole'].append({'query_id':q['query_key'],'ranking':[
            {'track_id':data['tracks'][i]['track_id'],'score':float(scores[i])} for i in order]})
        rankings['segment'].append({'query_id':q['query_key'],
            'ranking':rank_segments(all_segments@vector,segments,top_k=20)})
    del sdk;gc.collect()
    return rankings


def run(*,freeze,freeze_sha256,output):
    target=hc.private_output(output);started=time.perf_counter();prior=os.environ.get('NUMBA_CACHE_DIR');mask=os.umask(0o077)
    cache=target/'decode-cache';cache.mkdir(mode=0o700);cache.chmod(0o700);os.environ['NUMBA_CACHE_DIR']=str(cache)
    try:
        source=hc.source_state();receipt,data=hc.checked_freeze(freeze,freeze_sha256,verify_environment=True)
        configure();files=[]
        for m in ['A','B']:
            ranks=encode_model(m,receipt['models'][m]['pin']['path'],data,data['arguments']['audio_root'],target)
            for mode in ['whole','segment']:
                name=f'{m}-{mode}.json';hc.write_json(target/name,{'schema':'sonora-independent-ranking-v1',
                    'split':'independent_test','configuration':f'{m}-{mode}','runner_freeze_sha256':freeze_sha256,
                    'queries':ranks[mode]});files.append(name)
        scores=lexical_scores([t['title'] for t in data['tracks']],[q['text_en'] for q in data['queries']])
        lexical=[]
        for q,row in zip(data['queries'],scores):
            order=sorted(range(20),key=lambda i:(-float(row[i]),int(data['tracks'][i]['track_id'])))
            lexical.append({'query_id':q['query_key'],'ranking':[
                {'track_id':data['tracks'][i]['track_id'],'score':float(row[i])} for i in order]})
        name='title-tfidf.json';hc.write_json(target/name,{'schema':'sonora-independent-ranking-v1',
            'split':'independent_test','configuration':'title-tfidf','runner_freeze_sha256':freeze_sha256,'queries':lexical});files.append(name)
        hc.checked_freeze(freeze,freeze_sha256,verify_environment=True)
        hc.require(hc.source_state()==source,'Source changed during run')
        hashes={name:hc.file_hash(target/name) for name in files}
        vectors={str(p.relative_to(target)):hc.file_hash(p) for m in ['A','B'] for p in (target/m).iterdir()}
        commitment={'schema':'sonora-independent-all-runs-commitment-v1','status':'all_five_runs_persisted_before_qrels',
            'created_at_utc':hc.now(),'runner_freeze_sha256':freeze_sha256,'run_source':source,
            'ranking_sha256':hashes,'vector_artifact_sha256':vectors,
            'counts':{'tracks':20,'queries':8,'configurations':5,'qrels_opened':0},
            'single_run_seconds':time.perf_counter()-started}
        hc.write_json(target/'all-runs-commitment.json',commitment);return commitment
    except Exception as exc:
        hc.write_json(target/'failure.json',{'status':'failed_G4_partial_outputs_preserved','error_type':type(exc).__name__,'error':str(exc)})
        raise
    finally:
        os.umask(mask)
        if prior is None:os.environ.pop('NUMBA_CACHE_DIR',None)
        else:os.environ['NUMBA_CACHE_DIR']=prior


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    f=s.add_parser('freeze')
    for name in ['binding','catalog','audio-root','checkpoint-a','checkpoint-b','output']:f.add_argument('--'+name,type=Path,required=True)
    for name in ['binding-sha256','catalog-sha256']:f.add_argument('--'+name,required=True)
    r=s.add_parser('run')
    for name in ['freeze','output']:r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--freeze-sha256',required=True)
    args=vars(p.parse_args());command=args.pop('command');result=globals()[command](**args)
    print(result['status'])

if __name__=='__main__':main()

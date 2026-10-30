#!/usr/bin/env python3
"""Build G3 full-grid model-blind packages; validate receipts only on the labeler's machine."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import holdout_contract as hc
import review_pack as rp


def ordered(tracks,query_id,seed):
    return sorted(tracks,key=lambda t:(hc.digest((seed+'\n'+query_id+'\n'+t['recording_key']).encode()),t['recording_key']))


def candidate(t):
    provider=t['source_provider'];collection={'loc-citizen-dj-fma':'loc-fma','loc-citizen-dj-musicbox':'loc-musicbox'}[provider]
    return {'track_id':t['track_id'],'source_provider':provider,'source_id':t['source_id'],
        'title':t['title'],'artist':t['imported_metadata']['artist'],'source_url':t['source_url'],
        'license_url':f'https://citizen-dj.labs.loc.gov/{collection}/use/',
        'content_sha256':t['content_sha256'],'content_bytes':t['content_bytes'],'duration_ms':t['duration_ms'],
        'model_suggested_intervals_ms':[],**dict.fromkeys(rp.HUMAN_FIELDS)}


def packages(data,freeze_sha256):
    config=data['config'];queries=[]
    for q in data['queries']:
        queries.append({'query_id':q['query_key'],'text':q['text_en'],'gloss_zh':q['gloss_zh'],
            'audible_required_cues_zh':q['audible_required_cues_zh'],'grade_rules_zh':q['grade_rules_zh'],
            'possible_no_match_probe':q['possible_no_match_probe'],
            'candidates':[candidate(t) for t in ordered(data['tracks'],q['query_key'],config['presentation_seed'])]})
    pins={'runner_freeze_sha256':freeze_sha256,'source_dataset_sha256':data['source_dataset_sha256'],
        'import_catalog_sha256':data['arguments']['catalog_sha256'],'query_manifest_sha256':hc.QUERY_SHA,
        'runtime_config_sha256':data['input_sha256'][str((hc.ROOT/hc.CONFIG_PATH).absolute())]}
    dataset=hc.digest(hc.canonical({'pins':pins,'owner_user_id':data['catalog']['owner_user_id'],
        'presentation_seed':config['presentation_seed'],'queries':queries}))
    result=[]
    for batch in config['batches']:
        subset=[q for q in queries if q['query_id'] in batch['query_slots']]
        hc.require(len(subset)==2 and len({(q['query_id'],t['track_id']) for q in subset for t in q['candidates']})==40,
            'Each batch must contain two full20 queries')
        pack={'schema':hc.SCHEMA,'split':'independent_test','owner_user_id':data['catalog']['owner_user_id'],
            'provenance':{**pins,'test_dataset_sha256':dataset,'batch':batch['batch'],'batches':4,
                'selection':'full20_per_query_model_blind','ordering':'preregistered_hash_recording_order','labeling_aid':'no_model_hints'},
            'queries':deepcopy(subset)}
        pack['dataset_sha256']=hc.digest(hc.canonical(pack));result.append(pack)
    return result


def build(*,freeze,freeze_sha256,output):
    target=hc.private_output(output)
    try:
        _,data=hc.checked_freeze(freeze,freeze_sha256)
        packs=packages(data,freeze_sha256)
        for i,pack in enumerate(packs,1):
            rp.validate(pack,pack)
            hc.write_json(target/f'sonora-independent-batch-{i}.json',pack)
        hc.checked_freeze(freeze,freeze_sha256)
        result={'schema':'sonora-independent-package-build-v1','created_at_utc':hc.now(),
            'runner_freeze_sha256':freeze_sha256,'test_dataset_sha256':packs[0]['provenance']['test_dataset_sha256'],
            'packages':[{'batch':i,'filename':f'sonora-independent-batch-{i}.json','file_sha256':hc.file_hash(target/f'sonora-independent-batch-{i}.json'),
                'dataset_sha256':pack['dataset_sha256'],'candidate_pairs':40,'judged':0} for i,pack in enumerate(packs,1)],
            'counts':{'unique_recordings':20,'queries':8,'candidate_pairs':160,'judged':0,'model_hints':0},
            'custody':'Keep complete exports locally. Send only completion receipts until G5.'}
        hc.write_json(target/'build-receipt.json',result);return result
    except Exception as exc:
        hc.write_json(target/'failure.json',{'status':'failed_G3','error_type':type(exc).__name__,'error':str(exc)})
        raise


def seal(*,base,base_sha256,judgments):
    """Labeler-side only. Never print grades, identities, timestamps, or readable export paths."""
    expected=hc.assets.document(base,base_sha256)
    hc.require(expected.get('schema')==hc.SCHEMA and expected.get('split')=='independent_test','Independent base required')
    blank=deepcopy(expected);fingerprint=blank.pop('dataset_sha256',None)
    hc.require(hc.digest(hc.canonical(blank))==fingerprint,'Base fingerprint mismatch')
    base_check=rp.validate(expected,expected)
    hc.require(base_check['candidate_pairs']==40 and base_check['judged']==0,'Blank40 base required')
    raw=hc.assets.read(judgments,2*1024*1024);pack=hc.assets.source.strict_json(raw)
    checked=rp.validate(pack,expected)
    hc.require(checked['candidate_pairs']==40 and checked['unjudged']==0,'All40 valid judgments required for a receipt')
    return {'dataset_sha256':fingerprint,'payload_sha256':hc.digest(raw),
        'total_completed_count':40,'validation_status':'valid_complete_batch'}


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    b=s.add_parser('build');b.add_argument('--freeze',type=Path,required=True);b.add_argument('--freeze-sha256',required=True);b.add_argument('--output',type=Path,required=True)
    v=s.add_parser('seal',help='LABELER SIDE ONLY, before G5 do not send readable exports to runner')
    v.add_argument('--base',type=Path,required=True);v.add_argument('--base-sha256',required=True);v.add_argument('--judgments',type=Path,required=True)
    args=vars(p.parse_args());command=args.pop('command');result=globals()[command](**args)
    print(json.dumps(result if command=='seal' else {'status':'four_model_blind_batches_ready','counts':result['counts']},ensure_ascii=False))

if __name__=='__main__':main()

"""Known-pair music caption diagnostics. Unpaired candidates remain semantically unjudged."""
from collections import defaultdict
import numpy as np
import review_pack as rp


def paired(scores,query_tracks,candidate_tracks):
    scores=np.asarray(scores);rp.require(scores.shape==(len(query_tracks),len(candidate_tracks))and np.isfinite(scores).all()and len(set(candidate_tracks))==len(candidate_tracks),'Invalid paired score matrix')
    by=defaultdict(list)
    for row,tid in zip(scores,query_tracks):
        rp.require(tid in candidate_tracks,'Known paired recording absent')
        order=sorted(range(len(row)),key=lambda i:(-float(row[i]),candidate_tracks[i]));rank=order.index(candidate_tracks.index(tid))+1
        by[tid].append({'R1':float(rank<=1),'R5':float(rank<=5),'MRR':1/rank})
    rp.require(set(by)==set(candidate_tracks),'All recordings need validated queries')
    records={tid:{k:sum(r[k]for r in rows)/len(rows)for k in('R1','R5','MRR')}for tid,rows in by.items()}
    return {'recording_macro':{k:sum(r[k]for r in records.values())/len(records)for k in('R1','R5','MRR')},
            'query_macro':{k:sum(r[k]for rows in by.values()for r in rows)/len(query_tracks)for k in('R1','R5','MRR')},
            'per_recording':records,'recordings':len(records),'queries':len(query_tracks),'scope':'known_paired_match_not_complete_semantic_relevance'}


def paired_delta(candidate,identity,iterations,seed):
    rp.require(set(candidate['per_recording'])==set(identity['per_recording']),'Paired source set differs')
    keys=sorted(identity['per_recording']);delta=np.array([candidate['per_recording'][k]['R5']-identity['per_recording'][k]['R5']for k in keys])
    rng=np.random.default_rng(seed);means=delta[rng.integers(0,len(delta),size=(iterations,len(delta)))].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975])
    return {'R5_mean_delta':float(delta.mean()),'paired_bootstrap95_lower':float(lo),'paired_bootstrap95_upper':float(hi),
            'wins':int(np.sum(delta>1e-12)),'ties':int(np.sum(np.abs(delta)<=1e-12)),'losses':int(np.sum(delta< -1e-12)),
            'scope':'descriptive_dev_recording_resampling_not_final_test_significance'}


def choose(results,deltas):
    anchor=results['identity']['whole']['recording_macro'];eligible=[]
    for name,result in results.items():
        if name=='identity':continue
        m=result['whole']['recording_macro'];d=deltas[name]
        if m['R5']-anchor['R5']>=.05-1e-12 and m['R1']>=anchor['R1']-1e-12 and d['paired_bootstrap95_lower']>=-1e-12:
            eligible.append((m['R5'],m['R1'],result['alpha'],name))
    return max(eligible)[-1]if eligible else'identity'

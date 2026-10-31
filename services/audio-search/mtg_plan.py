"""Group-aware source metadata plan only; never load audio, embeddings or human grades."""
from collections import Counter, defaultdict
import mtg_dataset as mtg
import review_pack as rp
import holdout_contract as hc


class Groups:
    def __init__(self): self.parent = {}
    def root(self, key):
        self.parent.setdefault(key, key)
        if self.parent[key] != key: self.parent[key] = self.root(self.parent[key])
        return self.parent[key]
    def union(self, a, b):
        a, b = self.root(a), self.root(b)
        if a != b: self.parent[max(a,b)] = min(a,b)


def group_plan(pools, policy):
    rp.require(set(pools) == {'train','validation','test'}, 'Three official source partitions required')
    groups = Groups(); aliases = {}; id_splits = defaultdict(set)
    for split, rows in pools.items():
        for r in rows:
            rp.require(r['official_split'] == split, 'Source partition changed')
            artist = r['artist_id']; id_splits[artist].add(split)
            for name in mtg.aliases(r['artist_name']):
                if name in aliases: groups.union(artist, aliases[name])
                else: aliases[name] = artist
    split_groups, works, audio = defaultdict(set), defaultdict(set), defaultdict(set)
    for split, rows in pools.items():
        for r in rows:
            split_groups[groups.root(r['artist_id'])].add(split)
            works[mtg.norm(r['title'])].add(split); audio[r['audio_sha256']].add(split)
    quarantine = Counter(); eligible = {}
    for split, rows in pools.items():
        eligible[split] = []
        for r in rows:
            root = groups.root(r['artist_id']); reasons=[]
            if len(split_groups[root]) > 1: reasons.append('creator_component_across_official_splits')
            if len(works[mtg.norm(r['title'])]) > 1: reasons.append('work_name_across_official_splits')
            if len(audio[r['audio_sha256']]) > 1: reasons.append('official_audio_SHA_across_splits')
            if reasons: quarantine.update(split+':'+k for k in reasons); continue
            eligible[split].append({**r,'creator_component':root})
    selected = {}
    for split, rows in eligible.items():
        ordered=sorted(rows,key=lambda r:(hc.digest((policy['plan_seed']+'\n'+split+'\n'+r['source_track_id']).encode()),r['source_track_id']))
        selected[split]=[]; counts=Counter(); used_titles=set()
        for r in ordered:
            title=mtg.norm(r['title']); root=r['creator_component']
            if counts[root] >= policy['per_artist_component_cap'] or title in used_titles: continue
            selected[split].append(r); counts[root]+=1; used_titles.add(title)
            if len(selected[split])==policy['planned_counts'][split]:break
        rp.require(len(selected[split])==policy['planned_counts'][split], 'Insufficient isolated '+split+' metadata; no relaxed fallback')
    return {'schema':'sonora-mtg-grouped-future-corpus-plan-v1','status':'metadata_only_audio_not_downloaded_future_training_not_run',
            'selected':selected,'summary':{'counts':{k:len(v)for k,v in selected.items()},
            'eligible_before_cross_split_quarantine':{k:len(v)for k,v in pools.items()},
            'eligible_after_cross_split_quarantine':{k:len(v)for k,v in eligible.items()},
            'quarantine_reasons_nonexclusive':dict(quarantine),
            'creator_components':{k:len({r['creator_component']for r in v})for k,v in selected.items()},
            'tag_coverage':{k:len({t for r in v for t in r['tags']})for k,v in selected.items()},
            'new_audio_downloads':0,'training_runs_on_planned_data':0},
            'limits':['Official IDs, exact normalized names/credit components, work names and official low-file SHA only; not exhaustive alias/version/acoustic dedup or pretraining-unseen proof.',
                      'All new validation/test are metadata reservations, not downloaded/decoded/encoded or evaluated.',
                      'No selection by model scores, user160 judgments, captions or trained adapter outcomes.']}


def prepare(inputs, inputs_sha256, source_policy, source_policy_sha256, policy, policy_sha256, output):
    m=hc.assets.document(inputs,inputs_sha256); original=hc.assets.document(source_policy,source_policy_sha256); cfg=hc.assets.document(policy,policy_sha256)
    rp.require(cfg['source_inputs_sha256']==inputs_sha256 and cfg['source_policy_sha256']==source_policy_sha256,'Fixed original source bindings required')
    raw={k:hc.assets.read(x['path'],40*1024*1024)for k,x in m['files'].items()}
    rp.require(set(raw)==mtg.ROLES and all(hc.digest(v)==original['input_sha256'][k]==m['files'][k]['sha256']for k,v in raw.items()),'Metadata bytes changed')
    pools={k:mtg.build(raw,original,partition=k,include_pool=True)['eligible_pool']for k in ('train','validation','test')}
    result=group_plan(pools,cfg)
    result.update(created_at_utc=hc.now(),inputs_sha256=inputs_sha256,policy_sha256=policy_sha256,
                  adapter_source_sha256=hc.file_hash(mtg.__file__),planner_source_sha256=hc.file_hash(__file__))
    target=hc.private_output(output);hc.write_json(target/'plan.json',result)
    return result

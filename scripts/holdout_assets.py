"""Pinned G1 source and imported20 assets; no credentials, HTTP, queries or models."""
from collections import Counter
from copy import deepcopy
import hashlib
from pathlib import Path
import re
import stat

import collect_holdout_music as source
from import_demo_music import license_page

ROOT = Path(__file__).resolve().parents[1]
require, canonical, digest = source.require, source.canonical, source.digest
MAX_JSON = 16 * 1024 * 1024
IMPORT_SCHEMA = 'sonora-holdout-import-catalog-v1'
BINDING_FIELDS = {'protocol', 'frame', 'group_review', 'old_group_review', 'source_manifest', 'source_freeze', 'development40'}
ADDED = {'recording_key','creator_group','work_group','audio_filename','content_sha256','content_bytes',
    'download_proof_filename','download_proof_sha256','recorded_decode','format','source_frames',
    'declared_source_frames','source_sample_rate_hz','source_channels','sample_rate_hz','decoded_samples',
    'duration_ms','pcm_sha256','pcm_dtype','source_decoder_version'}


def regular(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Input cannot traverse symlinks')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Independent regular input required')
    return path


def read(path, limit=MAX_JSON):
    path = regular(path)
    require(0 < path.stat().st_size <= limit, 'Input size outside bounds')
    with path.open('rb') as f: raw = f.read(limit + 1)
    require(0 < len(raw) <= limit and len(raw) == path.stat().st_size, 'Input size changed while reading')
    return raw


def document(path, expected):
    raw = read(path)
    require(digest(raw) == source.sha(expected), 'Explicit input SHA256 mismatch')
    return source.strict_json(raw)


def local_path(value):
    path = ROOT / source.relative(value)
    require(path.absolute().is_relative_to(ROOT), 'Binding path outside checkout')
    return regular(path)


def integer_id(value):
    require(type(value) in (str, int) and re.fullmatch(r'[1-9][0-9]{0,18}', str(value))
            and int(value) <= 9223372036854775807, 'Invalid Java identity')
    return str(value)


def filename(track):
    return track['source_provider'] + '-' + track['source_id']


def album(manifest):
    return 'SONORA independent test ' + manifest['dataset_sha256'][:16]


def metadata(track, manifest):
    title, artist = track['title'], ' / '.join(track['contributors'])
    require(0 < len(title) <= 100 and 0 < len(artist) <= 50, 'Source metadata exceeds existing API limits')
    return {'title': title, 'artist': artist, 'album': album(manifest)}


def checked_source(binding_path, binding_sha256, decode=None):
    binding_path = regular(binding_path)
    b = document(binding_path, binding_sha256)
    require(isinstance(b, dict) and set(b) == BINDING_FIELDS | {'schema'}
            and b['schema'] == 'sonora-holdout-input-binding-v1', 'Unknown holdout binding schema')
    paths, hashes, values = {}, {binding_path: binding_sha256}, {}
    for name in BINDING_FIELDS:
        entry = b[name]
        fields = {'path','sha256','audio_root'} if name == 'development40' else {'path','sha256'}
        require(isinstance(entry, dict) and set(entry) == fields, 'Invalid binding entry')
        path = local_path(entry['path']); paths[name] = path
        values[name] = document(path, entry['sha256']); hashes[path] = entry['sha256']
        require(isinstance(values[name], dict), 'Expected bound JSON object')
    require(b['protocol']['sha256'] == source.PROTOCOL_V2_SHA and values['protocol'].get('version') == 2
            and values['frame'].get('schema') == 'sonora-holdout-source-frame-v2', 'Frozen v2 protocol/frame required')
    rows, reviews, old_names, old_titles, old_hashes, evidence = source.checked_inputs(
        paths['frame'], b['frame']['sha256'], paths['group_review'], b['group_review']['sha256'],
        paths['old_group_review'], b['old_group_review']['sha256'])
    hashes.update(evidence)
    m, freeze = values['source_manifest'], values['source_freeze']
    require(m.get('schema') == 'sonora-holdout-corpus-v1' and m.get('split') == 'independent_test_source_only'
            and m.get('protocol_sha256') == b['protocol']['sha256']
            and m.get('source_frame_sha256') == b['frame']['sha256']
            and m.get('group_review_sha256') == b['group_review']['sha256']
            and m.get('old_group_review_sha256') == b['old_group_review']['sha256']
            and m.get('source_decoder_version') == source.DECODER
            and m.get('priority_seed') == source.SEED and m.get('creator_group_cap') == 4, 'Source manifest binding mismatch')
    unsigned = deepcopy(m); expected = unsigned.pop('dataset_sha256', None)
    require(digest(canonical(unsigned)) == source.sha(expected), 'Frozen source dataset hash mismatch')
    require(freeze.get('schema') == 'sonora-holdout-source-dataset-freeze-receipt-v1'
            and freeze.get('version') == 2 and freeze.get('tracks') == 20
            and freeze.get('source_manifest_sha256') == b['source_manifest']['sha256']
            and freeze.get('source_dataset_sha256') == expected
            and freeze.get('protocol_sha256') == b['protocol']['sha256']
            and freeze.get('source_frame_sha256') == b['frame']['sha256']
            and freeze.get('group_review_sha256') == b['group_review']['sha256']
            and freeze.get('replacement_queue_frozen') is True, 'G1 source freeze receipt mismatch')
    root = paths['source_manifest'].parent
    queue = [{'source_provider': r['source_provider'], 'source_id': r['source_id'],
              'priority_sha256': source.priority(r['source_id'],r['source_provider'])} for r in rows]
    require(document(root/'priority-queue.json',m['priority_queue_sha256']) == queue
            and freeze['fixed_complete_priority_queue_sha256'] == m['priority_queue_sha256'], 'Frozen complete source queue changed')
    document(root/'exclusions.json',m['exclusions_sha256'])
    hashes[root/'priority-queue.json'] = m['priority_queue_sha256']; hashes[root/'exclusions.json'] = m['exclusions_sha256']
    by_id = {r['source_id']: r for r in rows}
    tracks = m.get('tracks'); require(isinstance(tracks,list) and len(tracks)==20, 'Exactly20 frozen source recordings required')
    creators, works, contents, identities, priorities = Counter(), set(), set(old_hashes), set(), []
    for t in tracks:
        require(isinstance(t,dict) and t.get('source_id') in by_id, 'Unknown source recording')
        row=by_id[t['source_id']]; review=reviews[t['source_id']]
        require(set(t)==set(row)|ADDED and all(t[k]==v for k,v in row.items()), 'Frozen source metadata fields changed')
        require(review['decision']=='eligible' and t['creator_group']==review['creator_group']
                and t['work_group']==review['work_group'], 'Source creator/work decision mismatch')
        key=t['source_provider']+':'+t['source_id']; require(t['recording_key']==key and key not in identities, 'Duplicate source identity')
        identities.add(key); priorities.append((t['priority_sha256'],t['source_provider'],t['source_id']))
        creator, work=source.key(t['creator_group']),source.key(t['work_group'])
        require(creator not in old_names and not any(source.key(n) in old_names for n in t['contributors'])
                and work not in old_titles and source.key(t['title']) not in old_titles and work not in works, 'Old or duplicate creator/work')
        creators[creator]+=1;works.add(work);require(t['content_sha256'] not in contents,'Duplicate old/new content');contents.add(t['content_sha256'])
        require(t['audio_filename']=='audio/'+t['source_id']+'.mp3'
                and t['download_proof_filename']=='audio/'+t['source_id']+'.download.json', 'Source asset/proof path changed')
        audio_path, proof_path = root/t['audio_filename'],root/t['download_proof_filename']
        audio=read(audio_path,source.MAX_AUDIO);proof=document(proof_path,t['download_proof_sha256'])
        require(type(t['content_bytes']) is int and len(audio)==t['content_bytes'] and digest(audio)==source.sha(t['content_sha256']), 'Source audio bytes mismatch')
        require(proof=={'source_url':t['source_url'],'download_url':t['download_url'],'final_url':t['download_url'],
            'bytes_read':t['content_bytes'],'sha256':t['content_sha256'],'download_within_complete_size_bound':True,
            'rights_id':t['rights_id'],'rights_statement':t.get('rights_statement',source.RIGHTS),
            'rights_snapshot':t['rights_snapshot'],'rights_snapshot_sha256':t['rights_snapshot_sha256']}, 'Source download proof mismatch')
        source.validate_decode(t);metadata(t,m)
        if decode is not None:
            actual=decode(audio_path)
            require(isinstance(actual,dict) and set(actual)=={'recorded_decode','format','source_frames','declared_source_frames',
                'source_sample_rate_hz','source_channels','sample_rate_hz','decoded_samples','duration_ms','pcm_sha256','pcm_dtype','source_decoder_version'}
                and actual=={k:t[k] for k in actual}, 'Actual EOF/PCM differs from G1 freeze')
        hashes[audio_path]=t['content_sha256'];hashes[proof_path]=t['download_proof_sha256']
    require(priorities==sorted(priorities) and len(creators)>=5 and max(creators.values())<=4
            and freeze['creator_groups']==len(creators) and freeze['work_groups']==len(works), 'Creator cap/work count/order changed')
    for name, path in {'collector':ROOT/'scripts/collect_holdout_music.py','actual_eof_decoder':ROOT/'services/audio-search/research_corpus.py',
                       'preprocessing':ROOT/'services/audio-search/preprocess.py'}.items():
        require(digest(read(path))==m['source_hashes'][name], 'G1 collector/DSP source changed')
        hashes[path]=m['source_hashes'][name]
    recheck(hashes)
    return {'binding':b,'binding_sha256':binding_sha256,'manifest':m,'tracks':tracks,'source_root':root,'hashes':hashes,'old_hashes':set(old_hashes)}


def recheck(hashes):
    for path, expected in hashes.items():
        limit=source.MAX_AUDIO if path.suffix=='.mp3' else MAX_JSON
        require(digest(read(path,limit))==expected, 'Pinned holdout input changed during operation')


def baseline40(context):
    entry=context['binding']['development40'];catalog=document(local_path(entry['path']),entry['sha256'])
    require(catalog.get('schema')=='sonora-research-catalog-v1' and catalog.get('slot')=='a'
            and isinstance(catalog.get('audioTracks'),list) and len(catalog['audioTracks'])==40, 'Verified original40 catalog required')
    owner=integer_id(catalog.get('ownerId'));root=ROOT/source.relative(entry['audio_root'])
    require(root.is_dir() and not any(p.is_symlink() for p in (root,*root.parents)), 'Invalid original40 audio root')
    providers=Counter();contents=set();ids=set();files=set();items=[]
    for t in catalog['audioTracks']:
        provider=t.get('sourceProvider');require(provider in ('jamendo','incompetech'),'Unknown development source')
        sid=t['sourceId'];require(isinstance(sid,str) and re.fullmatch(r'[A-Za-z0-9-]+',sid),'Invalid development source ID')
        mid,fid=integer_id(t['musicId']),integer_id(t['fileId'])
        require(mid not in ids and fid not in files and t.get('rangeVerified') is True and t.get('fullBytesVerified') is True,'Duplicate or unverified original40 identity')
        name=provider+'-'+sid;audio_path=root/(name+'.mp3');proof_path=root/(name+'.download.json')
        raw=read(audio_path,source.MAX_AUDIO);proof=source.strict_json(read(proof_path))
        require(digest(raw)==source.sha(t['sha256'])==proof.get('sha256') and len(raw)==proof.get('size')
                and proof.get('source')==t['sourceUrl'] and license_page(proof.get('license',''))==license_page(t['licenseUrl'])
                and t['sha256'] not in contents, 'Original40 audio/proof/catalog mismatch')
        require(t['sha256'] not in {row['content_sha256'] for row in context['tracks']}, 'New source overlaps original40')
        context['hashes'][audio_path]=digest(raw);context['hashes'][proof_path]=digest(read(proof_path))
        providers[provider]+=1;contents.add(t['sha256']);ids.add(mid);files.add(fid);items.append((t,audio_path))
    require(providers=={'jamendo':20,'incompetech':20} and contents==context['old_hashes'], 'Original development providers/content exclusion seed changed')
    return owner,items


def imported_track(t,manifest,saved):
    return {**t,'track_id':integer_id(saved['musicId']),'file_id':integer_id(saved['fileId']),
        'imported_metadata':metadata(t,manifest),'asset_filename':filename(t)+'.mp3',
        'proof_filename':filename(t)+'.download.json','range_verified':True,'full_bytes_verified':True,
        'approval_status_at_import':'pending'}


def validate_catalog(catalog,context,audio_root):
    b=context['binding'];m=context['manifest'];root=Path(audio_root).absolute()
    require(root.is_dir() and not any(p.is_symlink() for p in (root,*root.parents))
            and not root.is_relative_to(context['source_root']) and not context['source_root'].is_relative_to(root), 'Imported copies must be independent')
    require(set(catalog)=={'schema','split','owner_user_id','source_binding_sha256','source_dataset_sha256',
        'development40_catalog_sha256','importer_source_sha256','helper_source_sha256','tracks'}
        and catalog['schema']==IMPORT_SCHEMA and catalog['split']=='independent_test_imported_assets'
        and catalog['source_binding_sha256']==context['binding_sha256'] and catalog['source_dataset_sha256']==m['dataset_sha256']
        and catalog['development40_catalog_sha256']==b['development40']['sha256'], 'Imported catalog binding mismatch')
    owner,old=baseline40(context);require(catalog['owner_user_id']==owner, 'Catalog owner differs from original40')
    source.sha(catalog['importer_source_sha256']);source.sha(catalog['helper_source_sha256'])
    require(isinstance(catalog['tracks'],list) and len(catalog['tracks'])==20,'Expected imported20 only')
    ids={integer_id(t['musicId']) for t,_ in old};files={integer_id(t['fileId']) for t,_ in old}
    for row,t in zip(catalog['tracks'],context['tracks']):
        mid,fid=integer_id(row.get('track_id')),integer_id(row.get('file_id'))
        require(mid not in ids and fid not in files and row==imported_track(t,m,{'musicId':mid,'fileId':fid}), 'Imported track identity/metadata changed')
        ids.add(mid);files.add(fid)
        for name,expected in [(row['asset_filename'],t['content_sha256']),(row['proof_filename'],t['download_proof_sha256'])]:
            path=root/name;require(digest(read(path,source.MAX_AUDIO if name.endswith('.mp3') else MAX_JSON))==expected,'Imported copy differs from source')
    recheck(context['hashes'])
    return sorted(catalog['tracks'],key=lambda t:int(t['track_id']))


def checked_catalog(catalog_path,catalog_sha256,binding_path,binding_sha256,audio_root):
    context=checked_source(binding_path,binding_sha256)
    catalog=document(catalog_path,catalog_sha256)
    tracks=validate_catalog(catalog,context,audio_root)
    require(digest(read(catalog_path))==catalog_sha256,'Imported catalog changed during validation')
    return catalog,tracks

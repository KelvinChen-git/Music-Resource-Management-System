"""Pinned MTG metadata adapter. Present tags are weak positives; absent tags stay unknown."""
from collections import Counter
import csv
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import unicodedata

import holdout_contract as hc
import review_pack as rp

REVISION = 'cafd8e20c265ed84f1e61f1c875327971f43a62f'
ROLES = {'base', 'train', 'validation', 'test', 'licenses', 'names', 'audio_sha256', 'prior40', 'prior20', 'sdd'}
SEED = 'MUS-043-MTG-transport-preflight-v1'


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())


def aliases(value):
    parts = [value, *re.split(r'\s*(?:;|,|&|/|\bfeat\.?\s+|\bfeaturing\s+|\band\b)\s*', value, flags=re.I)]
    return {norm(p) for p in parts if norm(p)}


def source_id(value, prefix):
    rp.require(isinstance(value, str) and re.fullmatch(prefix + r'_[0-9]+', value), 'Invalid source identifier')
    return str(int(value.split('_')[-1]))


def table(raw):
    lines = list(csv.reader(io.StringIO(raw.decode('utf8')), delimiter='\t', quoting=csv.QUOTE_NONE))
    rp.require(lines.pop(0) == ['TRACK_ID', 'ARTIST_ID', 'ALBUM_ID', 'PATH', 'DURATION', 'TAGS'], 'Unexpected tag table header')
    result = {}
    for r in lines:
        rp.require(len(r) >= 6 and r[0] not in result, 'Malformed or duplicate tag row')
        tid = source_id(r[0], 'track'); source_id(r[1], 'artist'); source_id(r[2], 'album')
        rp.require(re.fullmatch(r'[0-9]{2}/[0-9]+\.mp3', r[3]) and str(int(PurePosixPath(r[3]).stem)) == tid
                   and r[3][:2] == str(int(tid) % 100).zfill(2), 'Track/path identity mismatch')
        duration = float(r[4]); tags = r[5:]
        rp.require(math.isfinite(duration) and duration > 0 and len(tags) == len(set(tags))
                   and all(re.fullmatch(r'(?:genre|instrument|mood/theme)---[^\s\x00]+', t) for t in tags), 'Invalid duration/tags')
        result[r[0]] = {'artist_id': r[1], 'album_id': r[2], 'path': r[3], 'duration': duration, 'tags': tags}
    return result


def names(raw):
    # The published file is literal TSV, not CSV-quoted. Preserve quotes in names.
    rows = list(csv.reader(io.StringIO(raw.decode('utf8')), delimiter='\t', quoting=csv.QUOTE_NONE))
    rp.require(rows.pop(0) == ['TRACK_ID', 'ARTIST_ID', 'ALBUM_ID', 'TRACK_NAME', 'ARTIST_NAME', 'ALBUM_NAME', 'RELEASEDATE', 'URL'], 'Unexpected name metadata header')
    valid, bad, seen = {}, [], set()
    for r in rows:
        rp.require(r and r[0] not in seen, 'Duplicate name metadata identity'); seen.add(r[0])
        source_id(r[0], 'track')
        if len(r) != 8:
            bad.append(r[0]); continue  # Quarantine malformed rows; never guess tab repairs.
        source_id(r[1], 'artist'); source_id(r[2], 'album')
        valid[r[0]] = {'artist_id': r[1], 'album_id': r[2], 'title': r[3], 'artist': r[4]}
    return valid, bad


def licenses(raw):
    result = {}
    for block in raw.decode('utf8').strip().split('\n\n'):
        rows = block.splitlines()
        rp.require(len(rows) == 3 and re.fullmatch(r'[0-9]{2}/[0-9]+\.mp3', rows[0]) and rows[0] not in result, 'Invalid license block')
        uri = rows[2].rsplit(' ', 1)[-1]
        match = re.fullmatch(r'https?://creativecommons.org/licenses/(by(?:-nc)?(?:-sa|-nd)?)/(\d\.\d)/(?:[a-z]{2}/)?', uri)
        result[rows[0]] = {'uri': uri, 'family': match.group(1) if match else 'unknown', 'original_notice': '\n'.join(rows[1:])}
    return result


def checksums(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        fields = line.split()
        rp.require(len(fields) == 2 and re.fullmatch(r'[0-9]{2}/[0-9]+\.low\.mp3', fields[1]) and fields[1] not in result, 'Invalid audio checksum row')
        result[fields[1]] = rp.sha(fields[0])
    return result


def build(raws, policy):
    rp.require(set(raws) == ROLES and policy['revision'] == REVISION and policy['seed'] == SEED
               and policy['preflight_tracks'] == 20 and policy['per_artist_cap'] == 1
               and policy['allowed_audio_license_families'] == ['by', 'by-sa'], 'Unexpected fixed metadata policy')
    base = table(raws['base']); splits = {s: table(raws[s]) for s in ('train', 'validation', 'test')}
    for name, rows in splits.items():
        rp.require(len(rows) == policy['expected_split_counts'][name], 'Split size changed')
        for tid, r in rows.items():
            rp.require(tid in base and all(r[k] == base[tid][k] for k in ('artist_id', 'album_id', 'path', 'duration'))
                       and set(r['tags']) <= set(base[tid]['tags']), 'Split/base drift')
    for i, a in enumerate(splits):
        for b in list(splits)[i + 1:]:
            rp.require(not set(splits[a]) & set(splits[b]) and all(not {r[k] for r in splits[a].values()} & {r[k] for r in splits[b].values()} for k in ('artist_id', 'album_id')), 'Official split identity leakage')
    metadata, malformed = names(raws['names']); rights = licenses(raws['licenses']); hashes = checksums(raws['audio_sha256'])
    old40 = hc.assets.source.strict_json(raws['prior40'])['audioTracks']; old20 = hc.assets.source.strict_json(raws['prior20'])['tracks']
    rp.require(len(old40) == 40 and len(old20) == 20, 'All sixty prior recordings required')
    prior_ids = {str(int(t['sourceId'])) for t in old40 if t['sourceProvider'] == 'jamendo'}
    prior_names = set().union(*(aliases(t['artist']) for t in old40), *(aliases(t['imported_metadata']['artist']) for t in old20),
                              *(aliases(c) for t in old20 for c in t['contributors']))
    prior_titles = {norm(t['title']) for t in old40 + old20 if norm(t['title'])}
    prior_hashes = {t['sha256'] for t in old40} | {t['content_sha256'] for t in old20}
    blocked_artists = {r['artist_id'] for tid, r in metadata.items() if source_id(tid, 'track') in prior_ids}
    blocked_albums = {r['album_id'] for tid, r in metadata.items() if source_id(tid, 'track') in prior_ids}
    # Resolve conservative exact-name/credit-component closure across official artist IDs.
    while True:
        new = {r['artist_id'] for r in metadata.values() if aliases(r['artist']) & prior_names}
        expanded = blocked_artists | new
        for r in metadata.values():
            if r['artist_id'] in expanded: prior_names.update(aliases(r['artist']))
        if expanded == blocked_artists: break
        blocked_artists = expanded
    sdd = list(csv.DictReader(io.StringIO(raws['sdd'].decode('utf8'))))
    sdd_ids = {str(int(r['track_id'].removeprefix('track_'))) for r in sdd}
    sdd_artists = {str(int(r['artist_id'].removeprefix('artist_'))) for r in sdd}
    # Do not read/use caption text as a selection feature or model input.
    vocabulary = sorted({t for r in splits['train'].values() for t in r['tags']})
    rp.require(len(vocabulary) == policy['expected_tag_count'], 'Tag vocabulary changed')
    for rows in splits.values(): rp.require({t for r in rows.values() for t in r['tags']} == set(vocabulary), 'Split tag vocabulary mismatch')
    excluded = Counter(); pool = []
    for tid, row in splits['train'].items():
        numeric = source_id(tid, 'track'); meta = metadata.get(tid); low = row['path'].removesuffix('.mp3') + '.low.mp3'
        reasons = []
        if numeric in prior_ids: reasons.append('prior_recording_id')
        if row['artist_id'] in blocked_artists or row['album_id'] in blocked_albums: reasons.append('prior_artist_or_album_id')
        if numeric in sdd_ids or source_id(row['artist_id'], 'artist') in sdd_artists: reasons.append('reserved_SDD_group')
        if not meta: reasons.append('missing_or_malformed_names')
        elif meta['artist_id'] != row['artist_id'] or meta['album_id'] != row['album_id']: reasons.append('name_identity_mismatch')
        else:
            if aliases(meta['artist']) & prior_names: reasons.append('prior_creator_name')
            if norm(meta['title']) in prior_titles: reasons.append('prior_work_name')
            if not norm(meta['artist']) or not norm(meta['title']): reasons.append('unresolved_blank_identity')
        if not 30 <= row['duration'] <= 600: reasons.append('metadata_duration_outside_bounds')
        if rights.get(row['path'], {}).get('family') not in policy['allowed_audio_license_families']: reasons.append('audio_license_outside_policy')
        if low not in hashes: reasons.append('missing_official_audio_hash')
        elif hashes[low] in prior_hashes: reasons.append('prior_exact_audio_hash')
        if reasons:
            excluded.update(reasons); continue
        text = 'Music tagged with ' + '; '.join(t.replace('---', ': ', 1) for t in row['tags']) + '.'
        pool.append({'source_track_id': tid, 'official_split': 'train', **row, 'title': meta['title'], 'artist_name': meta['artist'],
                     'low_path': low, 'audio_sha256': hashes[low], 'audio_license': rights[row['path']],
                     'text_en': text, 'unobserved_tags': 'unknown_not_confirmed_negative',
                     'priority_sha256': hc.digest((SEED + '\n' + tid).encode())})
    pool.sort(key=lambda r: (r['priority_sha256'], r['source_track_id']))
    chosen, used_artists = [], set()
    for r in pool:
        if r['artist_id'] not in used_artists:
            chosen.append(r); used_artists.add(r['artist_id'])
            if len(chosen) == 20: break
    rp.require(len(chosen) == 20, 'Insufficient eligible distinct-artist preflight candidates')
    return {'schema': 'sonora-mtg-train-preflight-selection-v1', 'revision': REVISION, 'seed': SEED,
            'selected': chosen, 'vocabulary': vocabulary,
            'summary': {'base_tracks': len(base), 'split_counts': {k: len(v) for k, v in splits.items()},
                        'tag_count': len(vocabulary), 'eligible_train_tracks': len(pool),
                        'excluded_train_tracks': len(splits['train']) - len(pool), 'exclusion_reasons_nonexclusive': dict(excluded),
                        'raw_name_records_valid': len(metadata), 'raw_name_records_quarantined': len(malformed),
                        'known_prior_source_matches': sum(source_id(t, 'track') in prior_ids for t in metadata),
                        'prior_artist_ids_blocked': len(blocked_artists), 'prior_name_aliases': len(prior_names),
                        'SDD_reserved_recordings': len(sdd_ids), 'SDD_reserved_artists': len(sdd_artists),
                        'selected_tracks': 20, 'selected_artist_ids': len(used_artists),
                        'selected_license_families': dict(Counter(r['audio_license']['family'] for r in chosen)),
                        'selected_tags': len({t for r in chosen for t in r['tags']}),
                        'training_runs': 0, 'model_loads': 0, 'user_grades_used_for_selection': False},
            'limits': ['Uploader track-level weak labels; missing tags unknown; no interval truth or model-generated music description.',
                       'Known ID/exact normalized names/credit components/work names only; unresolved aliases/versions/acoustic near-duplicates and pretraining overlap not proven absent.',
                       'Noncommercial research metadata terms remain; this is not commercial authorization or a ready training corpus.']}


def prepare(*, inputs, inputs_sha256, policy, policy_sha256, output):
    m = hc.assets.document(inputs, inputs_sha256); p = hc.assets.document(policy, policy_sha256)
    rp.require(m['revision'] == REVISION and set(m['files']) == ROLES and set(p['input_sha256']) == ROLES, 'Complete pinned input manifest required')
    raws = {}
    for role, entry in m['files'].items():
        rp.require(entry['sha256'] == p['input_sha256'][role], 'Input differs from committed policy pin')
        raw = hc.assets.read(entry['path'], 40 * 1024 * 1024)
        rp.require(hc.digest(raw) == entry['sha256'], 'Source input bytes changed'); raws[role] = raw
    selection = build(raws, p)
    selection.update(inputs_sha256=inputs_sha256, policy_sha256=policy_sha256,
                     adapter_sha256=hc.file_hash(Path(__file__)), created_at_utc=hc.now())
    target = hc.private_output(output); hc.write_json(target / 'selection.json', selection)
    hc.write_json(target / 'receipt.json', {'selection_sha256': hc.file_hash(target / 'selection.json'), 'summary': selection['summary']})
    return selection

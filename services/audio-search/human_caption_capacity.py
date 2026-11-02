"""Source-only human-caption capacity, never use caption bodies or model outputs."""
from collections import Counter, defaultdict
import csv
import io

import mtg_dataset as m
from mtg_plan import Groups
from review_pack import require


def identity(value, prefix):
    return prefix + '_' + m.source_id(value, prefix).zfill(7 if prefix == 'track' else 6)


def sdd_metadata(raw):
    """CSV framing sees source bytes; immediately project to non-text columns only."""
    result = []
    seen = set()
    for row in csv.DictReader(io.StringIO(raw.decode('utf8'))):
        require(row['caption_id'] not in seen, 'Duplicate caption identifier')
        seen.add(row['caption_id'])
        flag = row['is_valid_subset'].lower()
        require(flag in ('true', 'false', '1', '0'), 'Unknown validation flag')
        result.append({'track_id': identity(row['track_id'], 'track'),
                       'artist_id': identity(row['artist_id'], 'artist'),
                       'validated': flag in ('true', '1')})
    require(bool(result), 'Empty source frame')
    return result


def graph(names):
    """Resolve credit aliases on ALL name metadata, before candidate filtering."""
    groups = Groups()
    owners = {}
    for row in names.values():
        groups.root(row['artist_id'])
        for alias in m.aliases(row['artist']):
            if alias in owners:
                groups.union(row['artist_id'], owners[alias])
            else:
                owners[alias] = row['artist_id']
    return groups, owners


def block_set(rows, groups, owners, names):
    ids, components, titles, hashes = set(), set(), set(), set()
    for row in rows:
        if row.get('source_track_id'):
            ids.add(row['source_track_id'])
            original = names.get(row['source_track_id'])
            if original:
                components.add(groups.root(original['artist_id']))
        if row.get('artist_id'):
            components.add(groups.root(row['artist_id']))
        for credit in row.get('credits', []):
            components.update(groups.root(owners[a]) for a in m.aliases(credit) if a in owners)
        if m.norm(row.get('title', '')):
            titles.add(m.norm(row['title']))
        if row.get('audio_sha256'):
            hashes.add(row['audio_sha256'])
    return ids, components, titles, hashes


def measure(rows, base, names, rights, hashes, splits, blockers):
    groups, owners = graph(names)
    sets = {key: block_set(items, groups, owners, names) for key, items in blockers.items()}
    bytrack = defaultdict(list)
    for row in rows:
        bytrack[row['track_id']].append(row)
    accepted, exclusions = [], {}
    reasons_count = Counter()
    for tid, captions in sorted(bytrack.items()):
        reasons = []
        validated = sum(c['validated'] for c in captions)
        if not validated:
            reasons.append('no_validated_caption')
        t, n = base.get(tid), names.get(tid)
        if t is None or n is None:
            reasons.append('missing_source_metadata')
        else:
            require(t['artist_id'] == n['artist_id'], 'Base/name artist disagreement')
            require({c['artist_id'] for c in captions} == {t['artist_id']}, 'SDD/base artist disagreement')
            low = t['path'].removesuffix('.mp3') + '.low.mp3'
            digest = hashes.get(low)
            component = groups.root(t['artist_id'])
            title = m.norm(n['title'])
            if not 30 <= t['duration'] <= 600:
                reasons.append('duration_outside_policy')
            if rights.get(t['path'], {}).get('family') not in ('by', 'by-sa'):
                reasons.append('audio_license_outside_policy')
            if not digest:
                reasons.append('missing_official_audio_sha')
            if splits.get(tid) != 'test':
                reasons.append('outside_original_SDD_source_test')
            for label, (ids, components, titles, used_hashes) in sets.items():
                for field, overlap in [('id', tid in ids), ('credit_component', component in components),
                                       ('work_name', title in titles), ('official_audio_sha', digest in used_hashes)]:
                    if overlap:
                        reasons.append(label + ':' + field)
        if reasons:
            exclusions[tid] = reasons
            reasons_count.update(reasons)
        else:
            accepted.append({'source_track_id': tid, 'creator_component': component,
                             'work_key': title, 'audio_sha256': digest,
                             'validated_caption_count': validated,
                             'unvalidated_caption_count': len(captions) - validated})
    # Counts are alternatives to a future selection, not an implicit new split.
    components = defaultdict(list)
    for row in accepted:
        components[row['creator_component']].append(row)
    # Each component is represented once; shared works/hashes across components
    # make the simple component count only an upper bound, never a ready batch.
    works, content = defaultdict(set), defaultdict(set)
    for row in accepted:
        works[row['work_key']].add(row['creator_component'])
        content[row['audio_sha256']].add(row['creator_component'])
    valid_tracks = {r['track_id'] for r in rows if r['validated']}
    summary = {
        'source_caption_rows': len(rows), 'source_recordings': len(bytrack),
        'validated_caption_rows': sum(r['validated'] for r in rows),
        'validated_recordings': len(valid_tracks),
        'source_artist_ids': len({r['artist_id'] for r in rows}),
        'all_name_metadata_credit_components': len({groups.root(r['artist_id']) for r in names.values()}),
        'eligible_recordings': len(accepted),
        'eligible_validated_captions': sum(r['validated_caption_count'] for r in accepted),
        'independent_credit_components_upper_bound': len(components),
        'captions_if_one_recording_per_component_min': sum(min(r['validated_caption_count'] for r in v) for v in components.values()),
        'captions_if_one_recording_per_component_max': sum(max(r['validated_caption_count'] for r in v) for v in components.values()),
        'cross_component_shared_work_keys': sum(len(v) > 1 for v in works.values()),
        'cross_component_shared_official_audio_hashes': sum(len(v) > 1 for v in content.values()),
        'excluded_recordings': len(exclusions),
        'exclusion_reasons_nonexclusive': dict(sorted(reasons_count.items())),
        'eligible_caption_count_histogram': dict(sorted(Counter(str(r['validated_caption_count']) for r in accepted).items())),
        'eligible_recordings_per_component_histogram': dict(sorted(Counter(str(len(v)) for v in components.values()).items())),
        'blocked_group_sizes': {label: dict(zip(('recordings', 'credit_components', 'work_keys', 'audio_hashes'), map(len, values)))
                                for label, values in sets.items()},
        'source_only_not_audio_ready': True, 'candidate_selection_performed': False,
        'caption_content_reviewed_or_encoded': False,
    }
    return {'summary': summary, 'eligible': accepted, 'excluded': exclusions}


def blockers_from_documents(documents, raw):
    import json
    old40 = json.loads(raw['prior40'])['audioTracks']
    old20 = json.loads(raw['prior20'])['tracks']
    old = []
    for row in old40:
        old.append({'source_track_id': 'track_' + str(int(row['sourceId'])).zfill(7)
                    if row['sourceProvider'] == 'jamendo' else None,
                    'credits': [row['artist']], 'title': row['title'], 'audio_sha256': row['sha256']})
    for row in old20:
        old.append({'credits': [row['imported_metadata']['artist'], *row['contributors']],
                    'title': row['title'], 'audio_sha256': row['content_sha256']})
    def convert(rows):
        return [{**r, 'credits': [r['artist_name']]} for r in rows]
    dataset = documents['dataset']
    return {
        'prior60': old,
        'pilot_and_planned1400': convert(documents['pilot']['selected'] +
            [r for rows in documents['plan']['selected'].values() for r in rows]),
        'used_or_allocated_development': convert(
            [r for rows in dataset['selected'].values() for r in rows] +
            [r for rows in dataset['reserves'].values() for r in rows] + documents['expanded']['records']),
        'sealed_caption_test': convert(dataset['caption_test_reserved']),
    }

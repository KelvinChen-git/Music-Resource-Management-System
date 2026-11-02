"""Metadata-only Clotho training capacity; uploader/source closure, never model scoring."""
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import re
from urllib.parse import unquote, urlsplit
from review_pack import require

TAGS = ['music', 'musical', 'piano', 'guitar', 'violin', 'cello', 'orchestra', 'orchestral',
        'saxophone', 'trumpet', 'trombone', 'clarinet', 'flute', 'drum', 'drums', 'drumming',
        'percussion', 'accordion', 'ukulele', 'synth', 'synthesizer']
META_FIELDS = ['file_name', 'keywords', 'sound_id', 'sound_link', 'start_end_samples', 'manufacturer', 'license']
CAPTION_FIELDS = ['file_name', *[f'caption_{i}' for i in range(1, 6)]]
SPLITS = ('development', 'validation', 'evaluation')


def decode(raw):
    try: return raw.decode('utf-8-sig'), 'utf-8-sig'
    except UnicodeDecodeError: return raw.decode('iso-8859-1'), 'iso-8859-1'


def table(raw, fields):
    text, encoding = decode(raw); reader = csv.DictReader(io.StringIO(text))
    require(reader.fieldnames == fields, 'Pinned Clotho CSV schema required')
    rows = list(reader)
    require(rows and all(set(row) == set(fields) and all(isinstance(v, str) for v in row.values()) for row in rows),
            'Complete rectangular CSV required')
    return rows, encoding


def normalize(tag): return ' '.join(re.sub('[^a-z0-9]+', ' ', tag.casefold()).split())


def license_family(uri):
    p = urlsplit(uri)
    if p.scheme not in ('http', 'https') or p.netloc not in ('creativecommons.org', 'www.creativecommons.org') or p.query or p.fragment:
        return 'unknown'
    if re.fullmatch(r'/publicdomain/zero/1\.0/?', p.path): return 'cc0'
    match = re.fullmatch(r'/licenses/(by(?:-nc)?(?:-nd|-sa)?)/([1-4]\.0)(?:/[a-z]{2})?/?', p.path)
    return match[1] if match else 'unknown'


def metadata(raw, split):
    require(split in SPLITS, 'Explicit official split required')
    rows, encoding = table(raw, META_FIELDS); result = []
    for row in rows:
        name, sid, user = row['file_name'], row['sound_id'], row['manufacturer']
        require(name and '/' not in name and '\\' not in name and name not in ('.', '..')
                and user.strip(), 'Bound source/name/uploader required')
        unresolved = sid == 'Not found' and row['sound_link'] == 'NA'
        link_user = None
        if not unresolved:
            require(re.fullmatch('[0-9]+', sid) is not None and int(sid) > 0, 'Bound source/name/uploader required')
            sid = str(int(sid)); url = urlsplit(row['sound_link'])
            match = re.fullmatch(r'/people/([^/]+)/sounds/([0-9]+)/?', unquote(url.path))
            require(url.scheme in ('http', 'https') and url.netloc in ('freesound.org', 'www.freesound.org')
                    and match is not None and str(int(match[2])) == sid and not url.query and not url.fragment,
                    'Freesound ID/uploader URL binding differs')
            link_user = match[1].casefold()
        uploader_mismatch = link_user is not None and link_user != user.casefold()
        offsets = None
        if row['start_end_samples']:
            offsets = json.loads(row['start_end_samples'])
            require(isinstance(offsets, list) and len(offsets) == 2 and all(type(n) is int for n in offsets)
                    and 0 <= offsets[0] < offsets[1], 'Two ordered source sample offsets required')
        hits = sorted(set(normalize(t) for t in row['keywords'].split(';')) & set(TAGS))
        result.append({**row, 'split': split, 'sound_id': sid, 'uploader_key': user.casefold(), 'source_sample_offsets': offsets,
                       'source_id_known': not unresolved, 'source_resolved': not unresolved and not uploader_mismatch,
                       'source_binding_reason': 'missing_source_ID_and_URL' if unresolved else 'uploader_field_URL_mismatch' if uploader_mismatch else 'bound',
                       'uploader_keys': sorted({user.casefold()} | ({link_user} if link_user else set())), 'music_tag_hits': hits, 'explicit_music_tag': bool(set(hits) & {'music', 'musical'}),
                       'license_family': license_family(row['license'])})
    require(len({r['file_name'] for r in result}) == len(result), 'Duplicate filename within split')
    return result, encoding


def caption_structure(raw):
    rows, encoding = table(raw, CAPTION_FIELDS)
    require(len({r['file_name'] for r in rows}) == len(rows), 'Duplicate caption file binding')
    require(all(r['file_name'] and all(r[k].strip() for k in CAPTION_FIELDS[1:]) for r in rows),
            'Exactly five original nonempty development captions required')
    # Only count presence; no body returned, selected, rewritten, tokenized or encoded.
    return {r['file_name']: 5 for r in rows}, encoding


def analyze(raw_by_split, captions):
    require(set(raw_by_split) == set(SPLITS), 'All three metadata splits required for closure')
    rows = []; encodings = {}
    for split in SPLITS:
        values, encodings[split] = metadata(raw_by_split[split], split); rows.extend(values)
    counts, encodings['development_captions'] = caption_structure(captions)
    require(set(counts) == {r['file_name'] for r in rows if r['split'] == 'development'},
            'Development metadata/caption filenames differ')
    parent = list(range(len(rows)))
    def find(i):
        while i != parent[i]: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for key in ([('source', row['sound_id'])] if row['source_id_known'] else []) + [('uploader', user) for user in row['uploader_keys']]:
            if key in seen: parent[find(i)] = find(seen[key])
            else: seen[key] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows): groups[find(i)].append(row)
    for values in groups.values():
        identity = '\n'.join(sorted({(r['sound_id'] if r['source_id_known'] else r['split']+'|'+r['file_name'])+'|'+r['uploader_key'] for r in values}))
        key = hashlib.sha256(identity.encode()).hexdigest()
        splits = sorted({r['split'] for r in values})
        for row in values: row.update(component=key, component_splits=splits, cross_split_component=len(splits) > 1)
    summary = {}
    for split in SPLITS:
        allrows = [r for r in rows if r['split'] == split]
        music = [r for r in allrows if r['music_tag_hits']]
        rights = [r for r in music if r['license_family'] in ('by', 'by-sa')]
        bound = [r for r in rights if r['source_resolved']]
        isolated = [r for r in bound if not r['cross_split_component']]
        summary[split] = {'metadata_clips': len(allrows), 'unique_source_recordings': len({r['sound_id'] for r in allrows if r['source_id_known']}),
            'uploader_keys': len({u for r in allrows for u in r['uploader_keys']}),
            'source_binding_reasons': dict(sorted(Counter(r['source_binding_reason'] for r in allrows).items())),
            'all_clips_license_families': dict(sorted(Counter(r['license_family'] for r in allrows).items())),
            'music_tag_clips': len(music), 'explicit_music_tag_clips': sum(r['explicit_music_tag'] for r in music),
            'instrument_tag_only_clips': sum(not r['explicit_music_tag'] for r in music),
            'music_tag_audio_license_families': dict(sorted(Counter(r['license_family'] for r in music).items())),
            'BY_BYSA_music_tag_clips': len(rights), 'missing_source_binding_all_clips': sum(not r['source_resolved'] for r in allrows),
            'missing_source_binding_BY_BYSA_music_clips': len(rights)-len(bound),
            'source_bound_BY_BYSA_music_clips': len(bound), 'cross_split_component_excluded_BY_BYSA_clips': len(bound)-len(isolated),
            'isolated_BY_BYSA_music_tag_clips': len(isolated), 'isolated_unique_sources': len({r['sound_id'] for r in isolated}),
            'isolated_components': len({r['component'] for r in isolated}),
            'isolated_explicit_music_tag_clips': sum(r['explicit_music_tag'] for r in isolated),
            'missing_source_offsets_all': sum(r['source_sample_offsets'] is None for r in allrows)}
    candidates = [{**r, 'caption_count': counts[r['file_name']]} for r in rows if r['split'] == 'development'
                  and r['source_resolved'] and r['music_tag_hits'] and r['license_family'] in ('by', 'by-sa') and not r['cross_split_component']]
    candidates.sort(key=lambda r: (int(r['sound_id']), r['file_name']))
    return {'split_summary': summary, 'csv_encodings': encodings, 'all_metadata_clips': len(rows),
        'all_components': len(groups), 'cross_split_components': sum(len({r['split'] for r in v}) > 1 for v in groups.values()),
        'cross_split_component_clips': sum(r['cross_split_component'] for r in rows),
        'development_caption_pairs': sum(counts.values()), 'training_candidate_caption_pairs': len(candidates)*5,
        'training_candidates': candidates, 'metadata_components': [{k:r[k] for k in ('split','file_name','sound_id','source_resolved','source_id_known','uploader_key','uploader_keys','component','cross_split_component')} for r in rows],
        'training_ready': False, 'audio_ready': False, 'independent_benchmark_ready': False,
        'body_semantics_used': False, 'operations': dict.fromkeys(('audio_downloads','encodes','fits','quality_scores','reserved_test_inputs','new_manual_labels'),0)}

#!/usr/bin/env python3
"""Collect the pinned LOC frame in protocol order; no query, labels, API or model input."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys
import unicodedata
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT
PROVIDER = 'loc-citizen-dj-fma'
MUSICBOX = 'loc-citizen-dj-musicbox'
MUSICBOX_GROUP = 'loc-musicbox-recording-project'
REVISION = '216bda2dc80b4ec53b3d279d67923eea020dcce7'
PROTOCOL_SHA = 'f83a3b456ce51a6dc25b1e4b5c8ae3c77a37168f2b2b11645ccb14a65bebc9e8'
PROTOCOL_V2_SHA = '83bc7bf3f00a91634a56fd269daaf6720192c19507860ddff9df33c3063de63b'
SEED = 'MUS-038-phase1-corpus-v1'
SITE = 'https://citizen-dj.labs.loc.gov'
BUCKET = 'https://s3.amazonaws.com/citizen-dj-assets.labs.loc.gov'
DECODER = 'soundfile-read-out-65536-actual-eof-v1'
RIGHTS = ('This work has been dedicated to the public domain by its creator, thus is free to use and reuse without restriction. '
          'You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission. '
          'Attribution is recommended but not required.')
MUSICBOX_RIGHTS = ('This sound recording is free to use and reuse. You can copy, modify, distribute and perform the work, '
    'even for commercial purposes, all without asking permission. The American Folklife Center at the Library of Congress '
    'asks that artists approach the materials in this collection with respect for the culture and sensibilities of the people '
    'whose lives, ideas, and creativity are documented here. Attribution is recommended but not required.')
MAX_AUDIO = 30 * 1024 * 1024
MAX_INPUT = 16 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value), 'Explicit SHA256 required')
    return value


def text(value):
    require(isinstance(value, str) and 0 < len(value) <= 2000 and value.strip() == value
            and all(ord(c) >= 32 for c in value), 'Invalid bounded metadata text')
    return value


def key(value):
    return ' '.join(unicodedata.normalize('NFKC', text(value)).casefold().split())


def strict_json(raw):
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, 'Duplicate JSON key')
            result[name] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, 'Nonfinite JSON value'))


def relative(value):
    require(isinstance(value, str) and value and '\\' not in value and not Path(value).is_absolute()
            and all(part not in ('', '.', '..') for part in value.split('/')), 'Unsafe evidence path')
    return value


def regular(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Input/output cannot traverse symlinks')
    require(not any(token in path.name.casefold() for token in
                    ('sealed', 'quer', 'qrel', 'judgment', 'ranking', 'label')), 'Sampler cannot open query or label inputs')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Expected independent regular input, not hard link')
    return path


def priority(source_id, provider=PROVIDER):
    require(provider in (PROVIDER, MUSICBOX), 'Unknown official LOC provider')
    return digest((SEED + '\n' + provider + '\n' + source_id).encode())


def source_id(value, provider=PROVIDER):
    pattern = r'fma-[1-9][0-9]*' if provider == PROVIDER else r'(?:DR[0-9]{6}|[0-9]{10}|[0-9]{14})'
    require(provider in (PROVIDER, MUSICBOX) and isinstance(value, str) and re.fullmatch(pattern, value), 'Invalid LOC recording identity')
    return value


def audio_url(value, sid, provider=PROVIDER):
    collection = 'loc-fma' if provider == PROVIDER else 'loc-musicbox'
    expected = BUCKET + '/audio/items/' + collection + '/' + source_id(sid, provider) + '.mp3'
    require(value == expected, 'Only the exact pinned LOC full-recording URL is allowed')
    return expected


def scalar(document, name, frontmatter=False):
    lines = document.decode('utf-8').splitlines()
    if frontmatter:
        require(lines and lines[0] == '---' and '---' in lines[1:], 'Missing item frontmatter')
        lines = lines[1:lines.index('---', 1)]
    values = [line[len(name) + 1:].strip() for line in lines if line.startswith(name + ':')]
    require(len(values) == 1, 'Missing or duplicate official scalar metadata')
    raw = values[0]
    # LOC numeric titles are displayed as strings; do not reinterpret YAML numbers.
    value = json.loads(raw) if raw.startswith('"') else raw
    return text(value)


def _checked_inputs_v1(frame, frame_sha256, group_review, group_review_sha256,
                       old_group_review, old_group_review_sha256):
    bindings = {}
    def read(path, expected):
        path = regular(path)
        data = path.read_bytes()
        require(0 < len(data) <= MAX_INPUT and digest(data) == sha(expected), 'Pinned evidence SHA/size mismatch')
        require(path not in bindings or bindings[path] == expected, 'Conflicting evidence pins')
        bindings[path] = expected
        return data
    f = strict_json(read(frame, frame_sha256))
    groups = strict_json(read(group_review, group_review_sha256))
    old = strict_json(read(old_group_review, old_group_review_sha256))
    protocol = strict_json(read(ROOT / 'docs/evaluation/MUS-038-protocol.json', PROTOCOL_SHA))
    require(protocol['sampling']['corpus_priority_seed'] == SEED
            and protocol['test_design']['planned_tracks'] == 20
            and protocol['test_design']['creator_groups_minimum'] == 5
            and protocol['test_design']['tracks_per_creator_group_maximum'] == 4, 'Frozen protocol mismatch')
    require(isinstance(f, dict) and f.get('schema') == 'sonora-holdout-source-frame-v1'
            and f.get('status') == 'source_frame_frozen_not_final_dataset'
            and f.get('protocol_sha256') == PROTOCOL_SHA and f.get('source_revision') == REVISION
            and f.get('provider') == PROVIDER and f.get('priority_seed') == SEED
            and f.get('expected_item_count') == 132
            and f.get('enumeration') == 'all132items_in_pinned_official_metadata_no_genre_or_query_filter'
            and f.get('selection_uses_query_or_model_or_human_relevance') is False
            and f.get('rights_statement') == RIGHTS and f.get('metadata_file') == 'loc-fma-metadata.json',
            'Unknown or changed frozen source frame')
    root = Path(frame).absolute().parent
    snapshots = f['snapshots']
    require(isinstance(snapshots, dict) and len(snapshots) == 137, 'Expected all137 official snapshots')
    raw = {name: read(root / relative(name), value) for name, value in snapshots.items()}
    fixed = {'loc-fma-metadata.json', 'loc-fma-collection.md', 'loc-fma-data.json',
             'loc-config.yml', 'loc-item-layout.html'}
    require(fixed <= set(raw), 'Missing official metadata/template evidence')
    require(scalar(raw['loc-fma-collection.md'], 'uid', True) == 'loc-fma'
            and scalar(raw['loc-fma-collection.md'], 'item_rights', True) == RIGHTS
            and scalar(raw['loc-config.yml'], 'asset_url') == BUCKET
            and b'{{ site.asset_url }}{{ page.stream_url }}' in raw['loc-item-layout.html']
            and b'{{ page.rights }}' in raw['loc-item-layout.html'], 'Official rights/audio template mismatch')
    meta = strict_json(raw['loc-fma-metadata.json'])
    headings = ['title', 'filename', 'contributors', 'subjects', 'url', 'stream_url']
    require(meta['itemHeadings'] == headings and isinstance(meta['items'], list) and len(meta['items']) == 132,
            'Expected complete official132 metadata rows')
    contributors = meta['groups']['contributors']
    require(isinstance(contributors, list) and contributors and all(isinstance(v, str) for v in contributors),
            'Invalid official contributor enumeration')
    rows, seen = [], set()
    for values in meta['items']:
        require(isinstance(values, list) and len(values) == 6, 'Unexpected official item shape')
        item = dict(zip(headings, values))
        require(isinstance(item['filename'], str) and item['filename'].endswith('.mp3'), 'Expected MP3 recording')
        sid = source_id(item['filename'][:-4])
        require(sid not in seen, 'Duplicate official recording')
        seen.add(sid)
        title = str(item['title']) if type(item['title']) is int else text(item['title'])
        indices = item['contributors']
        require(isinstance(indices, list) and indices and len(set(indices)) == len(indices)
                and all(type(i) is int and 0 <= i < len(contributors) for i in indices), 'Invalid contributor indices')
        names = [text(contributors[i]) for i in indices]
        page, stream = '/items/loc-fma/' + sid + '/', '/audio/items/loc-fma/' + sid + '.mp3'
        require(item['url'] == page and item['stream_url'] == stream, 'Official recording identity/path mismatch')
        rights_file = 'item-rights/' + sid + '.md'
        require(rights_file in raw, 'Missing per-recording rights snapshot')
        item_raw = raw[rights_file]
        require(scalar(item_raw, 'uid', True) == sid and scalar(item_raw, 'title', True) == title
                and scalar(item_raw, 'permalink', True) == page
                and scalar(item_raw, 'stream_url', True) == stream
                and scalar(item_raw, 'contributors', True).split(' | ') == names
                and scalar(item_raw, 'rights', True) == RIGHTS, 'Item frontmatter/rights differs from official metadata')
        rows.append({'source_provider': PROVIDER, 'source_id': sid, 'title': title, 'contributors': names,
            'source_url': SITE + page, 'upstream_source_url': scalar(item_raw, 'source_url', True),
            'download_url': BUCKET + stream, 'rights_id': 'public-domain-dedication',
            'rights_snapshot': rights_file, 'rights_snapshot_sha256': snapshots[rights_file],
            'priority_sha256': priority(sid)})
    require(set(raw) == fixed | {'item-rights/' + sid + '.md' for sid in seen}, 'Unexpected source snapshots')
    data_items = strict_json(raw['loc-fma-data.json'])['items']
    require(isinstance(data_items, list) and len(data_items) == 132
            and len({v['id'] for v in data_items}) == 132, 'Incomplete official collection item data')
    by_id = {r['source_id']: r for r in rows}
    require(all(v['id'] in by_id and str(v['title']) == by_id[v['id']]['title']
                and SITE + v['url'] == by_id[v['id']]['source_url'] for v in data_items), 'Official collection identities changed')
    rows.sort(key=lambda r: (priority(r['source_id']), PROVIDER, r['source_id']))
    require(canonical(f['tracks']) == canonical(rows), 'Frozen frame is not the complete reconstructed priority queue')
    require(old.get('schema') == 'sonora-old-creator-work-exclusion-review-v1'
            and isinstance(old.get('evidence'), list) and old['evidence'], 'Invalid old40 exclusion seed')
    old_evidence = {}
    for evidence in old['evidence']:
        name = relative(evidence['path'])
        require(name not in old_evidence, 'Duplicate old evidence path')
        read(ROOT / name, evidence['sha256'])
        old_evidence[name] = evidence['sha256']
    old_names, old_titles, old_hashes, old_ids = set(), set(), set(), set()
    for creator in old['creator_groups']:
        canonical_name = key(creator['canonical_creator_name'])
        require(creator['creator_comparison_key'] == canonical_name, 'Old creator normalization mismatch')
        old_names.add(canonical_name)
        for field in ('observed_creator_names', 'proven_aliases', 'proven_collaborators'):
            old_names.update(key(v) for v in creator[field])
        for work in creator['works']:
            require(work['title_comparison_key'] == key(work['title'])
                    and work['evidence_paths'] and set(work['evidence_paths']) <= set(old_evidence), 'Old work evidence/normalization mismatch')
            content, identity = sha(work['content_sha256']), (text(work['provider']), text(work['source_id']))
            require(content not in old_hashes and identity not in old_ids, 'Duplicate old40 seed recording')
            old_hashes.add(content); old_ids.add(identity); old_titles.add(work['title_comparison_key'])
    require(len(old_hashes) == len(old_ids) == 40, 'Expected exactly40 old exclusion recordings')
    require(groups.get('schema') == 'sonora-holdout-group-review-v1'
            and groups.get('source_frame_sha256') == frame_sha256
            and groups.get('old_group_review_sha256') == old_group_review_sha256
            and groups.get('acoustic_fingerprinting_performed') is False,
            'Group review input binding or capability mismatch')
    text(groups['method_version'])
    evidence = groups['evidence']
    require(isinstance(evidence, dict) and evidence, 'Group review requires pinned evidence')
    group_root = Path(group_review).absolute().parent
    for name, expected in evidence.items():
        read(group_root / relative(name), expected)
    reviews = {}
    require(isinstance(groups['records'], list) and len(groups['records']) == 132, 'Group review must cover every frame item')
    for row in groups['records']:
        sid = source_id(row['source_id'])
        require(sid in seen and sid not in reviews and row['decision'] in ('eligible', 'quarantined', 'old_overlap'),
                'Unknown/duplicate group decision')
        text(row['reason'])
        paths = row['evidence_paths']
        require(isinstance(paths, list) and paths and len(set(paths)) == len(paths) and set(paths) <= set(evidence),
                'Each group decision requires declared pinned evidence')
        for name in ('creator_group', 'work_group'):
            require(row[name] is None or isinstance(row[name], str), 'Invalid creator/work group')
            if row[name] is not None:
                text(row[name])
            require(row['decision'] != 'eligible' or row[name] is not None, 'Eligible item needs resolved creator/work groups')
        reviews[sid] = row
    return rows, reviews, old_names, old_titles, old_hashes, bindings


def _checked_inputs_v2(frame, frame_sha256, group_review, group_review_sha256,
                       old_group_review, old_group_review_sha256):
    root = Path(frame).absolute().parent
    raw_frame = regular(frame).read_bytes()
    require(digest(raw_frame) == sha(frame_sha256), 'V2 source frame SHA mismatch')
    f = strict_json(raw_frame)
    require(f.get('schema') == 'sonora-holdout-source-frame-v2'
            and f.get('status') == 'source_frame_frozen_not_final_dataset'
            and f.get('protocol_sha256') == PROTOCOL_V2_SHA and f.get('source_revision') == REVISION
            and f.get('provider') == 'loc-citizen-dj-union-v2' and f.get('priority_seed') == SEED
            and f.get('enumeration') == 'all132FMA_union_all89MusicBox_pinned_metadata_no_query_or_genre_filter'
            and f.get('expected_item_counts') == {PROVIDER: 132, MUSICBOX: 89}
            and f.get('selection_uses_query_or_model_or_human_relevance') is False
            and f.get('musicbox_metadata_file') == 'revision02/loc-musicbox-metadata.json'
            and f.get('musicbox_rights_statement') == MUSICBOX_RIGHTS, 'Unknown or changed V2 source frame')
    fma_rows, fma_reviews, old_names, old_titles, old_hashes, bindings = _checked_inputs_v1(
        root / relative(f['fma_frame_file']), f['fma_frame_sha256'],
        root / relative(f['fma_group_review_file']), f['fma_group_review_sha256'], old_group_review, old_group_review_sha256)
    def read(path, expected):
        path = regular(path)
        raw = path.read_bytes()
        require(0 < len(raw) <= MAX_INPUT and digest(raw) == sha(expected), 'V2 evidence SHA/size mismatch')
        require(path not in bindings or bindings[path] == expected, 'Conflicting V2 evidence pins')
        bindings[path] = expected
        return raw
    read(frame, frame_sha256)
    protocol = strict_json(read(ROOT / 'docs/evaluation/MUS-039-protocol-v2.json', PROTOCOL_V2_SHA))
    require(protocol.get('version') == 2 and protocol.get('parent_protocol_sha256') == PROTOCOL_SHA
            and protocol['sampling']['corpus_priority_seed'] == SEED
            and protocol['test_design']['planned_tracks'] == 20
            and protocol['test_design']['tracks_per_creator_group_maximum'] == 4,
            'V2 protocol inheritance/budget mismatch')
    snapshots = f['snapshots']
    require(isinstance(snapshots, dict) and len(snapshots) == 92, 'Expected all92 MusicBox snapshots')
    raw = {name: read(root / relative(name), pin) for name, pin in snapshots.items()}
    fixed = {'revision02/loc-musicbox-metadata.json', 'revision02/loc-musicbox-collection.md', 'revision02/loc-musicbox-data.json'}
    require(fixed <= set(raw), 'Missing MusicBox metadata evidence')
    collection = raw['revision02/loc-musicbox-collection.md']
    require(scalar(collection, 'uid', True) == 'loc-musicbox'
            and scalar(collection, 'item_rights', True) == MUSICBOX_RIGHTS
            and scalar(collection, 'source_url', True) == 'https://lccn.loc.gov/2019655209', 'MusicBox rights/upstream mismatch')
    meta = strict_json(raw[f['musicbox_metadata_file']])
    headings = ['title', 'filename', 'year', 'contributors', 'url', 'stream_url']
    require(meta['itemHeadings'] == headings and isinstance(meta['items'], list) and len(meta['items']) == 89,
            'Expected complete89 MusicBox metadata')
    names = meta['groups']['contributors']
    require(isinstance(names, list) and names and all(isinstance(name, str) for name in names), 'Invalid MusicBox contributor groups')
    rows, extras, seen = list(fma_rows), {}, set()
    for values in meta['items']:
        require(isinstance(values, list) and len(values) == 6, 'Unexpected MusicBox item shape')
        item = dict(zip(headings, values))
        match = re.fullmatch(r'/items/loc-musicbox/([^/]+)/', item['url'])
        require(match is not None, 'Invalid MusicBox canonical URL')
        sid = source_id(match[1], MUSICBOX)
        require(sid not in seen, 'Duplicate MusicBox recording')
        seen.add(sid)
        title = str(item['title']) if type(item['title']) is int else text(item['title'])
        indices = item['contributors']
        require(isinstance(indices, list) and indices and len(set(indices)) == len(indices)
                and all(type(i) is int and 0 <= i < len(names) for i in indices), 'Invalid MusicBox contributor indices')
        contributors = [text(names[i]) for i in indices]
        original = text(item['filename'])
        require(original == Path(original).name and Path(original).stem == sid
                and Path(original).suffix in ('.m2ts', '.mov', '.MTS', '.wav'), 'Unexpected original MusicBox media filename')
        require(type(item['year']) is int and 1900 <= item['year'] <= 2100, 'Invalid MusicBox recording year')
        stream = '/audio/items/loc-musicbox/' + sid + '.mp3'
        require(item['stream_url'] == stream, 'MusicBox full-MP3 stream identity mismatch')
        rights_file = 'revision02/item-rights/' + sid + '.md'
        require(rights_file in raw, 'Missing MusicBox recording rights')
        document = raw[rights_file]
        require(scalar(document, 'uid', True) == sid and scalar(document, 'title', True) == title
                and scalar(document, 'permalink', True) == item['url']
                and scalar(document, 'stream_url', True) == stream
                and scalar(document, 'contributors', True).split(' | ') == contributors
                and scalar(document, 'rights', True) == MUSICBOX_RIGHTS, 'MusicBox item frontmatter/rights mismatch')
        rows.append({'source_provider': MUSICBOX, 'source_id': sid, 'title': title, 'contributors': contributors,
            'source_url': SITE + item['url'], 'upstream_source_url': 'https://lccn.loc.gov/2019655209',
            'download_url': BUCKET + stream, 'rights_id': 'loc-musicbox-free-use-and-reuse',
            'rights_statement': MUSICBOX_RIGHTS, 'rights_snapshot': rights_file,
            'rights_snapshot_sha256': snapshots[rights_file], 'priority_sha256': priority(sid, MUSICBOX),
            'provider_original_filename': original, 'official_MP3_derivative_of_original_media': True})
        extras[sid] = {'provider_summary': scalar(document, 'summary', True),
                      'provider_credit': scalar(document, 'credit', True), 'provider_recorded_year': item['year']}
    require(set(raw) == fixed | {'revision02/item-rights/' + sid + '.md' for sid in seen}, 'Unexpected MusicBox snapshots')
    data = strict_json(raw['revision02/loc-musicbox-data.json'])['items']
    by_id = {r['source_id']: r for r in rows if r['source_provider'] == MUSICBOX}
    require(isinstance(data, list) and len(data) == 89 and len({r['id'] for r in data}) == 89
            and all(r['id'] in by_id and str(r['title']) == by_id[r['id']]['title']
                    and SITE + r['url'] == by_id[r['id']]['source_url'] for r in data), 'MusicBox collection metadata mismatch')
    rows.sort(key=lambda row: (priority(row['source_id'], row['source_provider']), row['source_provider'], row['source_id']))
    require(canonical(f['tracks']) == canonical(rows), 'V2 frame is not the full reconstructed221 priority queue')
    groups = strict_json(read(group_review, group_review_sha256))
    require(groups.get('schema') == 'sonora-holdout-group-review-v2'
            and groups.get('source_frame_sha256') == frame_sha256
            and groups.get('old_group_review_sha256') == old_group_review_sha256
            and groups.get('acoustic_fingerprinting_performed') is False, 'V2 group review binding mismatch')
    text(groups['method_version'])
    evidence = groups['evidence']
    require(isinstance(evidence, dict) and evidence, 'V2 group review requires evidence')
    for name, pin in evidence.items():
        read(Path(group_review).absolute().parent / relative(name), pin)
    require(isinstance(groups['records'], list) and len(groups['records']) == 221, 'Expected all221 group decisions')
    reviews = {}
    for row in groups['records']:
        provider, sid = row['source_provider'], row['source_id']
        source_id(sid, provider)
        require(sid not in reviews and ((provider == PROVIDER and sid in fma_reviews)
                or (provider == MUSICBOX and sid in by_id)), 'Unknown/duplicate V2 group record')
        if provider == PROVIDER:
            require(canonical({k: v for k, v in row.items() if k != 'source_provider'}) == canonical(fma_reviews[sid]),
                    'Original FMA group decisions cannot change in V2')
        else:
            require(row['decision'] in ('eligible', 'quarantined', 'old_overlap'), 'Invalid MusicBox review decision')
            text(row['reason'])
            for name in ('creator_group', 'work_group'):
                require(row[name] is None or isinstance(row[name], str), 'Invalid MusicBox group')
                if row[name] is not None: text(row[name])
                require(row['decision'] != 'eligible' or row[name] is not None, 'Eligible MusicBox groups must be resolved')
            require(row['creator_group'] in (None, MUSICBOX_GROUP)
                    and (row['decision'] != 'eligible' or row['creator_group'] == MUSICBOX_GROUP),
                    'MusicBox must retain the single recording-project creator group')
        paths = row['evidence_paths']
        require(isinstance(paths, list) and paths and len(set(paths)) == len(paths) and set(paths) <= set(evidence),
                'V2 group record lacks pinned evidence')
        reviews[sid] = row
    for row in rows:
        if row['source_provider'] == MUSICBOX:
            row.update(extras[row['source_id']])
    return rows, reviews, old_names, old_titles, old_hashes, bindings


def checked_inputs(frame, frame_sha256, group_review, group_review_sha256, old_group_review, old_group_review_sha256):
    raw = regular(frame).read_bytes()
    require(0 < len(raw) <= MAX_INPUT and digest(raw) == sha(frame_sha256), 'Pinned source frame SHA/size mismatch')
    schema = strict_json(raw).get('schema')
    if schema == 'sonora-holdout-source-frame-v1':
        checker = _checked_inputs_v1
    elif schema == 'sonora-holdout-source-frame-v2':
        checker = _checked_inputs_v2
    else:
        raise ValueError('Unknown holdout source frame schema')
    return checker(frame, frame_sha256, group_review, group_review_sha256, old_group_review, old_group_review_sha256)


class ExactRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(req.full_url == newurl, 'LOC redirect changed source or recording identity')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_audio(url, limit):
    sid = url.rsplit('/', 1)[-1].removesuffix('.mp3')
    provider = MUSICBOX if url.startswith(BUCKET + '/audio/items/loc-musicbox/') else PROVIDER
    audio_url(url, sid, provider)
    context = ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    opener = build_opener(ProxyHandler({}), ExactRedirects(), HTTPSHandler(context=context))
    with opener.open(Request(url, headers={'User-Agent': 'SonoraHoldoutSource/1.0'}), timeout=90) as response:
        require(response.status == 200 and response.url == url, 'Unexpected LOC download response/identity')
        raw = response.read(limit + 1)
        length = response.headers.get('Content-Length')
        if length is not None:
            require(re.fullmatch(r'[0-9]+', length) and len(raw) == min(int(length), limit + 1),
                    'Incomplete LOC HTTP response')
        return raw, response.url


def decode_actual(path):
    import soundfile as sf
    sys.path.insert(0, str(ROOT / 'services/audio-search'))
    from research_corpus import decode_source_mono, SOURCE_DECODE_VERSION
    require(SOURCE_DECODE_VERSION == DECODER, 'Actual EOF decoder version changed')
    with sf.SoundFile(path) as header:
        recorded = {'frames': header.frames, 'sample_rate_hz': header.samplerate, 'channels': header.channels,
                    'format': header.format, 'duration_ms': header.frames * 1000 // header.samplerate}
    pcm, info = decode_source_mono(path, recorded)
    return {'recorded_decode': recorded, **info, 'pcm_sha256': digest(pcm.astype('<f4', copy=False).tobytes()),
            'pcm_dtype': 'float32_le', 'source_decoder_version': DECODER}


def write_new(path, value, raw=False):
    body = value if raw else canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(body)


def validate_decode(info):
    require(isinstance(info, dict) and info.get('source_decoder_version') == DECODER
            and info.get('format') == 'MP3' and info.get('pcm_dtype') == 'float32_le', 'Invalid actual EOF decode result')
    for name in ('source_frames', 'declared_source_frames', 'source_sample_rate_hz', 'source_channels',
                 'sample_rate_hz', 'decoded_samples', 'duration_ms'):
        require(type(info[name]) is int, 'Decode metadata must use integers')
    rate, frames = info['source_sample_rate_hz'], info['source_frames']
    require(8000 <= rate <= 192000, 'Invalid actual EOF sample rate')
    expected = (frames * 48000 + rate - 1) // rate
    require(8000 <= rate <= 192000 and info['source_channels'] in (1, 2) and rate * 30 <= frames <= rate * 600
            and 0 < info['declared_source_frames'] <= rate * 600 and info['sample_rate_hz'] == 48000
            and info['decoded_samples'] == expected and info['duration_ms'] == expected * 1000 // 48000
            and info['recorded_decode'] == {'frames': info['declared_source_frames'], 'sample_rate_hz': rate,
                'channels': info['source_channels'], 'format': 'MP3',
                'duration_ms': info['declared_source_frames'] * 1000 // rate}, 'Actual EOF frame/duration binding mismatch')
    sha(info['pcm_sha256'])
    require(isinstance(info['recorded_decode'], dict)
            and all(type(info['recorded_decode'][name]) is int for name in
                    ('frames', 'sample_rate_hz', 'channels', 'duration_ms')), 'Invalid declared frame metadata types')


def run(frame, frame_sha256, group_review, group_review_sha256, old_group_review, old_group_review_sha256,
        output, fetch=None, decode=None):
    rows, reviews, old_names, old_titles, old_hashes, bindings = checked_inputs(
        frame, frame_sha256, group_review, group_review_sha256, old_group_review, old_group_review_sha256)
    protocol_sha = strict_json(regular(frame).read_bytes())['protocol_sha256']
    source_paths = {'collector': Path(__file__), 'actual_eof_decoder': CODE_ROOT / 'services/audio-search/research_corpus.py',
                    'preprocessing': CODE_ROOT / 'services/audio-search/preprocess.py'}
    source_hashes = {name: digest(regular(path).read_bytes()) for name, path in source_paths.items()}
    bindings.update({path.absolute(): source_hashes[name] for name, path in source_paths.items()})
    target, local = Path(output).absolute(), ROOT / '.local'
    require(local.is_dir() and not any(p.is_symlink() for p in (target, *target.parents))
            and target.resolve().is_relative_to(local.resolve()) and target.resolve() != local.resolve(), 'Output must be private and cannot traverse symlinks')
    target = target.resolve()
    require(target.parent.is_dir(), 'Create the private output parent first')
    target.mkdir(mode=0o700)
    target.chmod(0o700)
    audio = target / 'audio'; audio.mkdir(mode=0o700); audio.chmod(0o700)
    previous_mask = os.umask(0o077)
    prior_cache = os.environ.get('NUMBA_CACHE_DIR')
    os.environ['NUMBA_CACHE_DIR'] = str(target / 'decode-cache')
    accepted, exclusions, creators, works, content = [], [], Counter(), set(), set(old_hashes)
    saved_audio_proofs = {}
    def recheck():
        for path, expected in bindings.items():
            require(digest(regular(path).read_bytes()) == expected, 'Frozen source evidence changed during collection')
    def exclude(row, reason, error=None):
        record = {'source_provider': row['source_provider'], 'source_id': row['source_id'],
                  'priority_sha256': priority(row['source_id'], row['source_provider']), 'reason': reason}
        if error is not None:
            record.update(error_type=type(error).__name__, error=str(error)[:2000])
        exclusions.append(record)
    def recheck_downloads():
        for path, expected in saved_audio_proofs.items():
            require(digest(regular(path).read_bytes()) == expected,
                    'Previously downloaded audio or proof changed; source collection aborted')
    try:
        write_new(target / 'priority-queue.json', [{'source_provider': r['source_provider'], 'source_id': r['source_id'],
            'priority_sha256': priority(r['source_id'], r['source_provider'])} for r in rows])
        for row in rows:
            review = reviews[row['source_id']]
            if review['decision'] != 'eligible':
                exclude(row, 'group_' + review['decision']); continue
            creator, work = review['creator_group'], review['work_group']
            creator_key, work_key = key(creator), key(work)
            if key(creator) in old_names or any(key(name) in old_names for name in row['contributors']) or key(work) in old_titles or key(row['title']) in old_titles:
                exclude(row, 'old_creator_or_work_overlap'); continue
            if creators[creator_key] >= 4:
                exclude(row, 'creator_group_cap4'); continue
            if work_key in works:
                exclude(row, 'work_or_version_already_selected'); continue
            url = audio_url(row['download_url'], row['source_id'], row['source_provider'])
            body, final_url = (fetch or fetch_audio)(url, MAX_AUDIO)
            require(isinstance(body, bytes) and final_url == url, 'Download changed source identity')
            name = row['source_id'] + '.mp3'
            path = audio / name
            write_new(path, body, raw=True)
            saved_audio_proofs[path] = digest(body)
            proof = {'source_url': row['source_url'], 'download_url': url, 'final_url': final_url,
                'bytes_read': len(body), 'sha256': digest(body), 'download_within_complete_size_bound': 0 < len(body) <= MAX_AUDIO,
                'rights_id': row['rights_id'], 'rights_statement': row.get('rights_statement', RIGHTS),
                'rights_snapshot': row['rights_snapshot'], 'rights_snapshot_sha256': row['rights_snapshot_sha256']}
            proof_name = row['source_id'] + '.download.json'
            write_new(audio / proof_name, proof)
            saved_audio_proofs[audio / proof_name] = digest(canonical(proof) + b'\n')
            if not 0 < len(body) <= MAX_AUDIO:
                exclude(row, 'download_size_outside_bounds'); continue
            if digest(body) in content:
                exclude(row, 'old_or_new_exact_content_duplicate'); continue
            try:
                info = (decode or decode_actual)(path)
                validate_decode(info)
            except PermissionError:
                raise
            except (ValueError, RuntimeError, OSError) as exc:
                require(digest(regular(path).read_bytes()) == digest(body), 'Downloaded bytes changed during decoding')
                recheck()
                recheck_downloads()
                exclude(row, 'unsupported_invalid_or_out_of_bounds_actual_audio', exc); continue
            require(digest(regular(path).read_bytes()) == digest(body), 'Downloaded bytes changed during decoding')
            recheck()  # Input pin failures are never a reason to skip to another recording.
            recheck_downloads()
            accepted.append({**row, 'recording_key': row['source_provider'] + ':' + row['source_id'],
                'creator_group': creator, 'work_group': work, 'audio_filename': 'audio/' + name,
                'content_sha256': digest(body), 'content_bytes': len(body),
                'download_proof_filename': 'audio/' + proof_name,
                'download_proof_sha256': digest((audio / proof_name).read_bytes()), **info})
            creators[creator_key] += 1; works.add(work_key); content.add(digest(body))
            if len(accepted) == 20:
                break
        recheck()
        recheck_downloads()
        write_new(target / 'exclusions.json', exclusions)
        require(len(accepted) == 20 and len(creators) >= 5 and max(creators.values()) <= 4,
                'Frozen frame cannot supply twenty valid recordings across at least five groups')
        for track in accepted:
            require(digest(regular(target / track['audio_filename']).read_bytes()) == track['content_sha256']
                    and digest(regular(target / track['download_proof_filename']).read_bytes()) == track['download_proof_sha256'],
                    'Accepted audio or proof changed before source freeze')
        manifest = {'schema': 'sonora-holdout-corpus-v1', 'split': 'independent_test_source_only',
            'protocol_sha256': protocol_sha, 'source_frame_sha256': frame_sha256,
            'group_review_sha256': group_review_sha256, 'old_group_review_sha256': old_group_review_sha256,
            'source_decoder_version': DECODER, 'collector_sha256': digest(Path(__file__).read_bytes()),
            'source_hashes': source_hashes,
            'priority_seed': SEED, 'creator_group_cap': 4, 'tracks': accepted,
            'priority_queue_sha256': digest((target / 'priority-queue.json').read_bytes()),
            'exclusions_sha256': digest((target / 'exclusions.json').read_bytes()),
            'limits': ['Source-only; no Java identity, owner, labels, queries, vectors or model scores.',
                'Pinned metadata/group review and exact byte deduplication; no acoustic fingerprinting performed.',
                'Provider-specific LOC rights wording and official MP3 derivative status retained; no precise CC0 URI inferred.']}
        manifest['dataset_sha256'] = digest(canonical(manifest))
        write_new(target / 'manifest.json', manifest)
        return {'status': 'collected_independent_source_only', 'tracks': 20, 'creator_groups': len(creators),
                'excluded': len(exclusions), 'manifest_sha256': digest((target / 'manifest.json').read_bytes()),
                'dataset_sha256': manifest['dataset_sha256'], 'model_runs': 0}
    except Exception as exc:
        if not (target / 'exclusions.json').exists():
            write_new(target / 'exclusions.json', exclusions)
        write_new(target / 'partial.json', {'schema': 'sonora-holdout-incomplete-source-v1', 'tracks': accepted})
        write_new(target / 'failure.json', {'status': 'incomplete_source_collection', 'accepted': len(accepted),
            'creator_groups': len(creators), 'error_type': type(exc).__name__, 'error': str(exc)})
        raise
    finally:
        os.umask(previous_mask)
        if prior_cache is None: os.environ.pop('NUMBA_CACHE_DIR', None)
        else: os.environ['NUMBA_CACHE_DIR'] = prior_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frame', 'group-review', 'old-group-review'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    try:
        result = run(**vars(parser.parse_args()))
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, UnicodeError) as exc:
        parser.exit(1, 'Holdout source collection stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

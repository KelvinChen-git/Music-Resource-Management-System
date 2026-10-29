#!/usr/bin/env python3
"""Build/check source-qualification judgments; no model run or human-label inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import quote

import review_pack as rp

SCHEMA = 'sonora-source-review-pack-v1'
SPLIT = 'development_source_candidates_not_held_out'
BUCKETS = ('exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08')
BASE = 'https://incompetech.com/music/royalty-free/'
LICENSE = 'https://creativecommons.org/licenses/by/4.0/'
ISRC = re.compile(r'[A-Z]{2}[A-Z0-9]{3}[0-9]{7}')


def keys(value, expected):
    rp.require(isinstance(value, dict) and set(value) == set(expected), 'Unexpected object fields')


def prepare(source_manifest_path, decode_report_path, import_catalog_path, query_fixture_path,
            expected_manifest_sha256, expected_decode_sha256, expected_catalog_sha256,
            expected_query_sha256, selection_path, baseline_catalog_path):
    """Reconstruct only new20 candidates from explicitly pinned local evidence."""
    for value in (expected_manifest_sha256, expected_decode_sha256,
                  expected_catalog_sha256, expected_query_sha256):
        rp.sha(value)  # None must never disable the explicit pin.
    inputs = {}

    def read(path, expected=None, limit=2 * 1024 * 1024):
        value, digest = rp.read_json(path, expected=expected, limit=limit)
        inputs[Path(path)] = (digest, limit)
        return value

    manifest = read(source_manifest_path, expected_manifest_sha256)
    keys(manifest, ('schema', 'split', 'created_at', 'selection_sha256', 'baseline_catalog_sha256',
                    'collector_sha256', 'snapshots', 'tracks', 'limits'))
    rp.require(manifest['schema'] == 'sonora-source-candidates-v1' and manifest['split'] == SPLIT,
               'Wrong source manifest schema/split')
    rp.sha(manifest['collector_sha256'])
    selection_hash = rp.sha(manifest['selection_sha256'])
    baseline_hash = rp.sha(manifest['baseline_catalog_sha256'])
    selection = read(selection_path, selection_hash)
    keys(selection, ('schema', 'split', 'tracks'))
    rp.require(selection['schema'] == 'sonora-source-selection-v1' and selection['split'] == SPLIT,
               'Wrong selection schema/split')
    plan = selection['tracks']
    rp.require(isinstance(plan, list) and len(plan) == 20, 'Expected twenty selected recordings')
    selected = {}
    for row in plan:
        keys(row, ('bucket_id', 'isrc', 'title'))
        sid = row['isrc']
        rp.require(isinstance(sid, str) and ISRC.fullmatch(sid) and sid not in selected,
                   'Invalid/duplicate selected ISRC')
        rp.require(row['bucket_id'] in BUCKETS, 'Unknown selected query')
        rp.text(row['title'], 160)
        selected[sid] = row
    rp.require(Counter(row['bucket_id'] for row in plan) == dict.fromkeys(BUCKETS, 4),
               'Expected four selected recordings per query')
    root = Path(source_manifest_path).parent.resolve(strict=True)

    def asset_path(name):
        rp.require(isinstance(name, str) and name == Path(name).name and name not in ('', '.', '..'),
                   'Invalid evidence filename')
        path = root / name
        rp.require(not path.is_symlink() and path.resolve(strict=True).is_relative_to(root),
                   'Evidence escapes source root')
        return path

    snapshots = manifest['snapshots']
    keys(snapshots, ('official-catalog.json', 'official-track-template.html', 'official-license.html'))
    snapshot_urls = {'official-catalog.json': BASE + 'pieces.json',
                     'official-track-template.html': BASE + 'index.html?isrc=' + plan[0]['isrc'],
                     'official-license.html': BASE + 'licenses/'}
    snapshot_data = {}
    for name, evidence in snapshots.items():
        keys(evidence, ('url', 'sha256'))
        rp.require(evidence['url'] == snapshot_urls[name], 'Unexpected official snapshot URL')
        with asset_path(name).open('rb') as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
        rp.require(0 < len(raw) <= 2 * 1024 * 1024 and rp.digest(raw) == rp.sha(evidence['sha256']),
                   'Snapshot bytes/SHA mismatch')
        inputs[asset_path(name)] = (rp.digest(raw), 2 * 1024 * 1024)
        snapshot_data[name] = raw
    template = snapshot_data['official-track-template.html'].decode('utf-8')
    license_page = snapshot_data['official-license.html'].decode('utf-8')
    rp.require('Licensed under Creative Commons: By Attribution 4.0 License' in template
               and 'creativecommons.org/licenses/by/4.0/' in template
               and 'encodeURIComponent(p.filename)' in template, 'Official track template changed')
    rp.require('Creative Commons' in license_page and 'Requires that you credit' in license_page,
               'Official license description changed')
    official = read(asset_path('official-catalog.json'), snapshots['official-catalog.json']['sha256'])
    rp.require(isinstance(official, list), 'Expected official recording list')
    tracks = manifest['tracks']
    rp.require(isinstance(tracks, list) and len(tracks) == 20, 'Expected twenty source tracks')
    sources, contents = {}, set()
    for track in tracks:
        sid = track['source_id']
        rp.require(sid in selected and sid not in sources and track['provider'] == 'incompetech',
                   'Unknown/duplicate source recording')
        choice = selected[sid]
        records = [row for row in official if isinstance(row, dict) and row.get('isrc') == sid]
        rp.require(len(records) == 1, 'Missing/ambiguous official recording')
        record = records[0]
        filename = record['filename']
        rp.require(isinstance(filename, str) and 5 <= len(filename) <= 180 and filename.endswith('.mp3')
                   and '..' not in filename and not any(c in filename for c in '/\\?#%')
                   and all(ord(c) >= 32 and ord(c) != 127 for c in filename), 'Invalid source audio filename')
        length = record['length']
        rp.require(isinstance(length, str) and re.fullmatch(r'[0-9]{2}:[0-5][0-9]:[0-5][0-9]', length),
                   'Invalid provider duration')
        h, m, s = map(int, length.split(':'))
        seconds = rp.integer(h * 3600 + m * 60 + s, 30, 600)
        expected = {'provider': 'incompetech', 'source_id': sid, 'bucket_id': choice['bucket_id'],
                    'title': choice['title'], 'artist': 'Kevin MacLeod', 'duration_seconds': seconds,
                    'source_url': BASE + 'index.html?isrc=' + sid, 'license_url': LICENSE,
                    'download_url': BASE + 'mp3-royaltyfree/' + quote(filename, safe=''),
                    'audio_filename': sid + '.mp3', 'metadata_record_sha256': rp.digest(rp.canonical(record)),
                    'provider_instruments': str(record.get('instruments') or '')[:1000],
                    'provider_feel': str(record.get('feel') or '')[:1000],
                    'provider_bpm': str(record.get('bpm') or '')[:100],
                    'attribution': choice['title'] + ' — Kevin MacLeod (incompetech.com), CC BY 4.0',
                    'changes': 'Audio file unchanged', 'human_relevance': None}
        rp.require(record['title'] == choice['title'] and all(track.get(k) == v for k, v in expected.items()),
                   'Source manifest/selection/official metadata mismatch')
        digest = rp.sha(track['sha256'])
        rp.require(digest not in contents, 'Duplicate source audio content')
        size = rp.integer(track['bytes'], 1, 30 * 1024 * 1024)
        audio_path = asset_path(track['audio_filename'])
        with audio_path.open('rb') as handle:
            raw = handle.read(30 * 1024 * 1024 + 1)
        rp.require(len(raw) == size and rp.digest(raw) == digest, 'Source audio bytes/SHA mismatch')
        inputs[audio_path] = (digest, 30 * 1024 * 1024)
        proof = read(asset_path(sid + '.download.json'))
        keys(proof, ('sha256', 'size', 'source', 'license', 'download_url', 'metadata_record_sha256', 'snapshots'))
        rp.require(proof == {'sha256': digest, 'size': size, 'source': expected['source_url'],
                             'license': LICENSE, 'download_url': expected['download_url'],
                             'metadata_record_sha256': expected['metadata_record_sha256'],
                             'snapshots': snapshots}, 'Source download proof mismatch')
        sources[sid] = track
        contents.add(digest)
    rp.require(set(sources) == set(selected), 'Missing selected source recording')
    decoded = read(decode_report_path, expected_decode_sha256)
    rp.require(decoded['status'] == 'passed_full_source_decode_with_metadata_differences'
               and decoded['manifest_sha256'] == expected_manifest_sha256, 'Decode report/source mismatch')
    rp.sha(decoded['verification_script_sha256'])
    rp.require(isinstance(decoded['tracks'], list) and len(decoded['tracks']) == 20, 'Expected twenty decoded records')
    durations, within = {}, 0
    for row in decoded['tracks']:
        sid = row['source_id']
        rp.require(sid in sources and sid not in durations and row['bucket_id'] == sources[sid]['bucket_id'],
                   'Unknown/duplicate decode recording')
        rate = rp.integer(row['sample_rate_hz'], 8000, 192000)
        frames = rp.integer(row['frames'], rate * 30, rate * 600)
        duration = rp.integer(row['duration_ms'], 30000, 600000)
        delta = duration - sources[sid]['duration_seconds'] * 1000
        rp.require(row['format'] == 'MP3' and type(row['channels']) is int and row['channels'] in (1, 2)
                   and row['finite_samples'] is True and duration == frames * 1000 // rate
                   and type(row['provider_duration_delta_ms']) is int and row['provider_duration_delta_ms'] == delta
                   and row['metadata_within_2000ms'] is (abs(delta) <= 2000), 'Invalid decoded evidence')
        durations[sid] = duration
        within += abs(delta) <= 2000
    counts = decoded['counts']
    rp.require(all(type(counts[key]) is int and counts[key] == 20 for key in ('decoded', 'finite', 'hash_and_proof_matched'))
               and counts['duration_metadata_within_2000ms'] == within
               and counts['duration_metadata_outside_2000ms'] == 20 - within
               and counts['human_judged'] == 0 and counts['java_imported'] == 0
               and decoded['total_duration_ms'] == sum(durations.values())
               and decoded['min_duration_ms'] == min(durations.values())
               and decoded['max_duration_ms'] == max(durations.values()), 'Decode counts/durations mismatch')
    baseline = read(baseline_catalog_path, baseline_hash)
    catalog = read(import_catalog_path, expected_catalog_sha256)
    keys(catalog, ('schema', 'ownerId', 'slot', 'baseline_catalog_sha256', 'source_manifest_sha256',
                   'decode_report_sha256', 'importer_sha256', 'audioTracks'))
    owner = rp.identity(catalog['ownerId'], catalog=True)
    rp.require(type(catalog['ownerId']) is int and owner == rp.identity(baseline['ownerId'], catalog=True)
               and catalog['slot'] == baseline['slot'] and catalog['slot'] in ('a', 'b')
               and catalog['schema'] == 'sonora-research-catalog-v1'
               and catalog['baseline_catalog_sha256'] == baseline_hash
               and catalog['source_manifest_sha256'] == expected_manifest_sha256
               and catalog['decode_report_sha256'] == expected_decode_sha256, 'Imported catalog binding/owner mismatch')
    rp.sha(catalog['importer_sha256'])
    old = baseline['audioTracks']
    rp.require(isinstance(old, list) and len(old) == 20 and isinstance(catalog['audioTracks'], list)
               and len(catalog['audioTracks']) == 40, 'Expected original20 plus new20 imported tracks')
    old_by_id = {rp.identity(row['musicId'], catalog=True): row for row in old}
    rp.require(len(old_by_id) == 20, 'Duplicate baseline track')
    candidates, seen_tracks, seen_files, seen_content, seen_old = {}, set(), set(), set(), set()
    for row in catalog['audioTracks']:
        rp.require(type(row['musicId']) is int and type(row['fileId']) is int, 'Imported Java IDs must be integers')
        tid, fid = rp.identity(row['musicId'], catalog=True), rp.identity(row['fileId'], catalog=True)
        rp.require(tid not in seen_tracks and fid not in seen_files, 'Duplicate imported Java identity')
        digest = rp.sha(row['sha256'])
        rp.require(digest not in seen_content, 'Duplicate imported content')
        seen_tracks.add(tid); seen_files.add(fid); seen_content.add(digest)
        if row['sourceProvider'] == 'jamendo':
            rp.require(tid in old_by_id and rp.canonical(row) == rp.canonical({**old_by_id[tid], 'sourceProvider': 'jamendo'}),
                       'Original track altered/inserted')
            seen_old.add(tid)
            continue
        sid = row['sourceId']
        rp.require(row['sourceProvider'] == 'incompetech' and sid in sources and sid not in candidates,
                   'Unknown/duplicate imported source identity')
        track = sources[sid]
        rp.require(row['source'] == 'Incompetech' and row['title'] == track['title']
                   and row['artist'] == track['artist'] and row['sourceUrl'] == track['source_url']
                   and row['licenseUrl'] == LICENSE and row['license'] == 'CC BY 4.0'
                   and row['changes'] == 'Audio file unchanged' and digest == track['sha256']
                   and type(row['durationSeconds']) is int and row['durationSeconds'] == track['duration_seconds']
                   and type(row['decodedDurationMs']) is int and row['decodedDurationMs'] == durations[sid]
                   and type(row['contentBytes']) is int and row['contentBytes'] == track['bytes']
                   and row['rangeVerified'] is True and row['fullBytesVerified'] is True,
                   'Imported media/source/decode evidence mismatch')
        rp.require(row['album'] == '', 'Official source has no recorded album')
        candidates[sid] = {'track_id': tid, 'source_provider': 'incompetech', 'source_id': sid,
                           'title': track['title'], 'artist': track['artist'], 'source_url': track['source_url'],
                           'license_url': LICENSE, 'content_sha256': digest, 'content_bytes': track['bytes'],
                           'duration_ms': durations[sid], 'model_suggested_intervals_ms': [],
                           **dict.fromkeys(rp.HUMAN_FIELDS)}
    rp.require(seen_old == set(old_by_id) and set(candidates) == set(selected), 'Missing original/new imported track')
    fixture = read(query_fixture_path, expected_query_sha256)
    rp.require(fixture['split'] == 'exploratory_unjudged' and isinstance(fixture['queries'], list)
               and 5 <= len(fixture['queries']) <= 20, 'Expected exploratory query fixture')
    queries, seen_queries = [], set()
    for query in fixture['queries']:
        qid = rp.text(query['query_id'], 100)
        rp.require(qid not in seen_queries, 'Duplicate fixture query')
        seen_queries.add(qid)
        text = rp.text(query['text'], 1000)
        if qid in BUCKETS:
            rows = [candidates[sid] for sid, row in selected.items() if row['bucket_id'] == qid]
            queries.append({'query_id': qid, 'text': text, 'candidates': sorted(rows, key=lambda row: int(row['track_id']))})
    rp.require(tuple(query['query_id'] for query in queries) == BUCKETS,
               'Missing or out-of-order target fixture query')
    pack = {'schema': SCHEMA, 'split': SPLIT, 'owner_user_id': owner,
            'provenance': {'source_manifest_sha256': expected_manifest_sha256,
                           'import_catalog_sha256': expected_catalog_sha256,
                           'decode_report_sha256': expected_decode_sha256,
                           'source_selection_sha256': selection_hash, 'query_fixture_sha256': expected_query_sha256,
                           'selection': 'targeted_source_candidates_by_metadata',
                           'ordering': 'query_fixture_order_then_track_id_ascending',
                           'labeling_aid': 'no_model_intervals_source_qualification'}, 'queries': queries}
    pack['dataset_sha256'] = rp.digest(rp.canonical(pack))
    # Recheck every evidence file, including audio/proofs, so a mixed read cannot be accepted.
    for path, (digest, limit) in inputs.items():
        with path.open('rb') as handle:
            raw = handle.read(limit + 1)
        rp.require(0 < len(raw) <= limit and rp.digest(raw) == digest, 'Input changed during source-pack reconstruction')
    return pack


def validate(pack, expected):
    rp.require(expected.get('schema') == SCHEMA and expected.get('split') == SPLIT, 'Expected source-qualification pack')
    result = rp.validate(pack, expected)
    return {**result, 'schema': SCHEMA, 'split': SPLIT}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('build', 'validate'):
        child = sub.add_parser(command)
        for name in ('source-manifest', 'decode-report', 'import-catalog', 'query-fixture'):
            child.add_argument('--' + name, type=Path, required=True)
            child.add_argument('--' + name + '-sha256', required=True)
        child.add_argument('--selection', type=Path, required=True)
        child.add_argument('--baseline-catalog', type=Path, required=True)
        child.add_argument('--output' if command == 'build' else '--pack', type=Path, required=True)
    args = parser.parse_args()
    try:
        expected = prepare(args.source_manifest, args.decode_report, args.import_catalog, args.query_fixture,
                           args.source_manifest_sha256, args.decode_report_sha256,
                           args.import_catalog_sha256, args.query_fixture_sha256,
                           args.selection, args.baseline_catalog)
        pack = expected if args.command == 'build' else rp.read_json(args.pack)[0]
        result = validate(pack, expected)
        if args.command == 'build':
            rp.write_new(args.output, pack)
            result['status'] = 'created_unjudged_source_qualification_pack'
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        parser.exit(1, 'Source review pack rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

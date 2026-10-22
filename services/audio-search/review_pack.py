#!/usr/bin/env python3
"""Prepare/check exploratory judgment JSON; never infer human labels or metrics."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = 'sonora-judgment-pack-v1'
SPLIT = 'exploratory_only_not_held_out'
HUMAN_FIELDS = ('relevance', 'human_intervals_ms', 'annotator', 'judged_at')
ARTIFACTS = ('corpus-manifest.json', 'queries.json', 'rankings.json', 'segments.json')
REPO = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value), 'Invalid SHA256')
    return value


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'Integer outside allowed range')
    return value


def identity(value, catalog=False):
    if catalog and type(value) is int:
        value = str(value)
    require(isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,18}', value)
            and int(value) <= 9223372036854775807, 'Expected positive decimal Java Long ID')
    return value


def text(value, limit):
    require(isinstance(value, str) and 0 < len(value) <= limit and value.strip() == value
            and not any(ord(c) < 32 for c in value), 'Invalid bounded text')
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read_json(path, limit=2 * 1024 * 1024, expected=None):
    with Path(path).open('rb') as handle:
        raw = handle.read(limit + 1)
    require(0 < len(raw) <= limit, 'JSON size outside allowed range')
    if expected is not None:
        require(digest(raw) == sha(expected), 'JSON artifact hash mismatch: ' + Path(path).name)
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda _: require(False, 'Nonfinite JSON value'))
    return value, digest(raw)


def public_urls(source, source_id, license_url):
    parsed = urlsplit(source)
    require(parsed.scheme == 'https' and parsed.netloc == 'www.jamendo.com'
            and not parsed.query and not parsed.fragment
            and re.fullmatch('/track/' + source_id + r'(?:/[^?#]*)?', parsed.path),
            'Source URL/ID mismatch')
    license_page = urlsplit(license_url)
    require(license_page.scheme in ('http', 'https') and license_page.netloc == 'creativecommons.org'
            and re.fullmatch(r'/licenses/by/(2\.0|2\.5|3\.0|4\.0)/', license_page.path)
            and not license_page.query and not license_page.fragment, 'Invalid recorded CC BY URL')
    return 'https://www.jamendo.com/track/' + source_id, 'https://creativecommons.org' + license_page.path


def interval(value, duration):
    require(isinstance(value, list) and len(value) == 2, 'Expected [start_ms, end_ms]')
    start, end = value
    integer(start, 0, duration - 1)
    integer(end, start + 1, duration)
    return value


def prepare(run_dir, catalog_path, expected_report_sha256):
    """Reconstruct immutable candidates from pinned report and four hashed artifacts."""
    run = Path(run_dir)
    report, report_hash = read_json(run / 'report.json', expected=expected_report_sha256)
    require(report['status'] == 'passed_offline_pipeline_only' and report['working_tree_dirty'] is False,
            'Expected completed clean offline run')
    require(re.fullmatch(r'[a-f0-9]{40}', report['code_sha']), 'Invalid source commit')
    require(report['model']['dimension'] == 512 and not report['model']['strict_missing']
            and not report['model']['strict_unexpected'], 'Expected strict pinned model load')
    checkpoint = sha(report['model']['checkpoint_sha256'])
    pipeline = text(report['pipeline_version'], 200)
    catalog, catalog_hash = read_json(catalog_path, expected=report['input_catalog_sha256'])
    owner = identity(catalog['ownerId'], catalog=True)
    artifacts = {name: read_json(run / name, limit=16 * 1024 * 1024,
                               expected=report['artifact_sha256'][name])[0] for name in ARTIFACTS}
    manifest = artifacts['corpus-manifest.json']
    require(manifest['pipeline_version'] == pipeline, 'Manifest pipeline mismatch')
    require(isinstance(manifest['tracks'], list) and 1 <= len(manifest['tracks']) <= 100,
            'Expected 1..100 tracks')
    require(isinstance(catalog['audioTracks'], list) and len(catalog['audioTracks']) == len(manifest['tracks']),
            'Catalog/manifest track count mismatch')
    recorded = {}
    for row in catalog['audioTracks']:
        tid = identity(row['musicId'], catalog=True)
        require(tid not in recorded, 'Duplicate catalog track')
        recorded[tid] = row
    tracks, source_ids, contents = {}, set(), set()
    for asset in manifest['tracks']:
        tid, sid = identity(asset['track_id']), identity(asset['source_id'])
        require(tid in recorded and tid not in tracks and sid not in source_ids, 'Unknown/duplicate manifest track')
        original = recorded[tid]
        require(identity(original['sourceId'], catalog=True) == sid, 'Source identity changed')
        source_url, license_url = public_urls(asset['source_url'], sid, asset['license_url'])
        require(public_urls(original['sourceUrl'], sid, original['licenseUrl']) == (source_url, license_url),
                'Catalog/manifest source or license mismatch')
        content = sha(asset['content_sha256'])
        require(content == sha(original['sha256']) and content not in contents, 'Content mismatch/duplicate')
        duration = integer(asset['duration_ms'], 1, 600000)
        require(asset['sample_rate_hz'] == 48000 and duration == asset['decoded_samples'] * 1000 // 48000,
                'Decoded duration mismatch')
        integer(asset['decoded_samples'], 48, 28800000)
        require(asset['title'] == original['title'] and asset['artist'] == original['artist'], 'Metadata mismatch')
        tracks[tid] = {'track_id': tid, 'source_id': sid, 'title': text(asset['title'], 500),
                       'artist': text(asset['artist'], 500), 'source_url': source_url, 'license_url': license_url,
                       'content_sha256': content, 'content_bytes': integer(asset['bytes'], 1, 30 * 1024 * 1024),
                       'duration_ms': duration}
        source_ids.add(sid)
        contents.add(content)
    segments = artifacts['segments.json']
    require(isinstance(segments, list) and 1 <= len(segments) <= 20000, 'Invalid segment list')
    known_segments = {}
    for segment in segments:
        tid = identity(segment['track_id'])
        require(tid in tracks, 'Unknown segment track')
        start = integer(segment['start_sample'], 0, 28800000 - 1)
        end = integer(segment['end_sample'], start + 1, 28800000)
        require(end <= next(a['decoded_samples'] for a in manifest['tracks'] if a['track_id'] == tid),
                'Segment exceeds decoded samples')
        require(segment['start_ms'] == start * 1000 // 48000 and segment['end_ms'] == end * 1000 // 48000,
                'Segment sample/millisecond mismatch')
        interval([segment['start_ms'], segment['end_ms']], tracks[tid]['duration_ms'])
        require(end - start <= 480000 and segment['padded_samples'] == 480000 - (end - start),
                'Segment padding mismatch')
        key = tid + ':' + str(start) + ':' + str(end)
        require(segment['segment_id'] == key and key not in known_segments, 'Segment identity mismatch/duplicate')
        known_segments[key] = segment
    fixture = artifacts['queries.json']
    require(fixture['split'] == 'exploratory_unjudged' and isinstance(fixture['queries'], list)
            and 1 <= len(fixture['queries']) <= 20, 'Expected exploratory text queries')
    queries = {}
    for query in fixture['queries']:
        qid = text(query['query_id'], 100)
        require(qid not in queries, 'Duplicate query')
        queries[qid] = text(query['text'], 1000)
    rankings = artifacts['rankings.json']
    require(rankings['judgments'] == 'unjudged' and isinstance(rankings['queries'], list), 'Expected unjudged rankings')
    pools, all_queries = {}, set()
    for query in rankings['queries']:
        qid = text(query['query_id'], 100)
        require(qid not in all_queries and query['kind'] in ('text', 'audio'), 'Duplicate/unknown ranking query')
        all_queries.add(qid)
        if query['kind'] != 'text':
            continue  # Same-corpus reference clips intentionally not offered as human test queries.
        require(qid in queries and query['text'] == queries[qid], 'Ranking/fixture query mismatch')
        selected, suggested = set(), {}
        for mode in ('whole_track', 'segment'):
            rows = query[mode]
            require(isinstance(rows, list) and len(rows) == min(5, len(tracks)), 'Expected top5 per baseline')
            mode_ids = set()
            for row in rows:
                tid = identity(row['track_id'])
                require(tid in tracks and tid not in mode_ids, 'Unknown/duplicate ranking track')
                require(type(row['score']) in (int, float) and math.isfinite(row['score']), 'Invalid ranking score')
                mode_ids.add(tid)
                selected.add(tid)
                if mode == 'segment':
                    require(isinstance(row['segments'], list) and 1 <= len(row['segments']) <= 3,
                            'Expected 1..3 suggested segments')
                    ranges = []
                    for segment in row['segments']:
                        key = segment['segment_id']
                        require(key in known_segments and segment['track_id'] == tid
                                and {k: v for k, v in segment.items() if k != 'score'} == known_segments[key],
                                'Suggested segment not in hashed segment artifact')
                        value = [segment['start_ms'], segment['end_ms']]
                        require(value not in ranges, 'Duplicate suggested segment')
                        ranges.append(value)
                    suggested[tid] = ranges
        pools[qid] = [{'model_suggested_intervals_ms': suggested.get(tid, []), **tracks[tid],
                       **dict.fromkeys(HUMAN_FIELDS)} for tid in sorted(selected, key=int)]
    require(set(pools) == set(queries), 'Missing text ranking query')
    counts = report['counts']
    require(counts['tracks'] == len(tracks) and counts['segments'] == len(segments)
            and counts['text_queries'] == len(queries)
            and counts['reference_queries'] == len(all_queries) - len(queries), 'Report counts mismatch')
    pack = {'schema': SCHEMA, 'split': SPLIT, 'owner_user_id': owner,
            'provenance': {'source_report_sha256': report_hash, 'run_code_sha': report['code_sha'],
                           'input_catalog_sha256': catalog_hash, 'checkpoint_sha256': checkpoint,
                           'pipeline_version': pipeline,
                           'artifact_sha256': {name: report['artifact_sha256'][name] for name in ARTIFACTS},
                           'selection': 'union_whole_track_top5_and_segment_top5',
                           'ordering': 'query_fixture_order_then_track_id_ascending',
                           'labeling_aid': 'model_intervals_visible_not_blind'},
            'queries': [{'query_id': qid, 'text': value, 'candidates': pools[qid]} for qid, value in queries.items()]}
    # Canonical null-filled dataset, excluding only the fingerprint itself.
    pack['dataset_sha256'] = digest(canonical(pack))
    return pack


def validate(pack, expected):
    """Only the four human fields may differ from reconstructed null-filled pack."""
    require(isinstance(pack, dict) and isinstance(pack.get('queries'), list), 'Invalid pack object')
    immutable = deepcopy(pack)
    for query in immutable['queries']:
        require(isinstance(query, dict) and isinstance(query.get('candidates'), list), 'Invalid candidate list')
        for candidate in query['candidates']:
            require(isinstance(candidate, dict) and all(k in candidate for k in HUMAN_FIELDS), 'Missing human fields')
            for field in HUMAN_FIELDS:
                candidate[field] = None
    # JSON comparison distinguishes bool/float from integer identity/time fields.
    require(canonical(immutable) == canonical(expected), 'Immutable dataset/provenance/candidates changed')
    labels = {str(n): 0 for n in range(4)}
    total, unjudged, intervals = 0, 0, 0
    for query in pack['queries']:
        for candidate in query['candidates']:
            total += 1
            rating = candidate['relevance']
            if rating is None:
                require(all(candidate[k] is None for k in HUMAN_FIELDS), 'Unjudged candidate has annotation data')
                unjudged += 1
            else:
                integer(rating, 0, 3)
                require(isinstance(candidate['annotator'], str)
                        and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', candidate['annotator']),
                        'Judged candidate needs anonymous annotator alias')
                stamp = candidate['judged_at']
                require(isinstance(stamp, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', stamp),
                        'Judged candidate needs UTC second timestamp')
                datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
                ranges = candidate['human_intervals_ms']
                if ranges is not None:
                    require(isinstance(ranges, list) and 1 <= len(ranges) <= 20 and rating > 0,
                            'Human intervals need positive relevance and 1..20 ranges')
                    previous_end = -1
                    for value in ranges:
                        start, end = interval(value, candidate['duration_ms'])
                        require(start >= previous_end, 'Human ranges must be sorted and nonoverlapping')
                        previous_end = end
                        intervals += 1
                labels[str(rating)] += 1
    return {'status': 'validated_unverified_judgments', 'split': SPLIT, 'queries': len(pack['queries']),
            'candidate_pairs': total, 'judged': total - unjudged, 'unjudged': unjudged,
            'relevance_counts': labels, 'human_intervals': intervals,
            'dataset_sha256': expected['dataset_sha256'], 'identity_or_listening_verified': False}


def write_new(path, pack):
    target = Path(path).absolute()
    require(target.resolve().is_relative_to(REPO / '.local'), 'Output must be under this checkout .local/')
    raw = (json.dumps(pack, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    require(len(raw) <= 2 * 1024 * 1024, 'Pack exceeds import size limit')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Resolve again after mkdir; existing parent symlinks must not escape ignored storage.
    require(target.resolve().is_relative_to(REPO / '.local'), 'Output parent escapes .local/')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('build', 'validate'):
        child = sub.add_parser(command)
        child.add_argument('--run-dir', type=Path, required=True)
        child.add_argument('--catalog', type=Path, required=True)
        child.add_argument('--report-sha256', required=True)
        child.add_argument('--output' if command == 'build' else '--pack', type=Path, required=True)
    args = parser.parse_args()
    try:
        expected = prepare(args.run_dir, args.catalog, args.report_sha256)
        pack = expected if args.command == 'build' else read_json(args.pack)[0]
        result = validate(pack, expected)
        if args.command == 'build':
            write_new(args.output, pack)
            result['status'] = 'created_unjudged_exploratory_pack'
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        parser.exit(1, 'Review pack rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

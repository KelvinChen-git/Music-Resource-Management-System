#!/usr/bin/env python3
"""Prepare/check independent complement judgments; keep original labels and audio read-only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import review_pack as rp

SCHEMA = 'sonora-diagnostic-pack-v1'
SELECTION = 'unjudged_complement_for_selected_queries'
LABELING_AID = 'no_model_intervals_for_diagnostic_complement'


def prepare(run_dir, catalog_path, expected_report_sha256, base_pack_path, expected_base_sha256, query_ids):
    rp.sha(expected_report_sha256)
    rp.sha(expected_base_sha256)
    rp.require(isinstance(query_ids, (list, tuple)) and 1 <= len(query_ids) <= 20,
               'Select 1..20 distinct diagnostic query IDs')
    for qid in query_ids:
        rp.text(qid, 100)
    rp.require(len(set(query_ids)) == len(query_ids), 'Duplicate diagnostic query ID')
    original = rp.prepare(run_dir, catalog_path, expected_report_sha256)
    base, base_hash = rp.read_json(base_pack_path, expected=expected_base_sha256)
    base_summary = rp.validate(base, original)
    rp.require(base_summary['unjudged'] == 0, 'Complete the original judgment pack first')
    known = {query['query_id'] for query in original['queries']}
    rp.require(set(query_ids) <= known, 'Unknown diagnostic query ID')

    # E1 validated every manifest/catalog track, including ones never returned by either mode.
    # Rebind bytes here before reading the complete universe; union candidates are not the universe.
    manifest, _ = rp.read_json(Path(run_dir) / 'corpus-manifest.json', limit=16 * 1024 * 1024,
        expected=original['provenance']['artifact_sha256']['corpus-manifest.json'])
    tracks = {}
    for asset in manifest['tracks']:
        source, license_url = rp.public_urls(asset['source_url'], asset['source_id'], asset['license_url'])
        tracks[asset['track_id']] = {
            'track_id': asset['track_id'], 'source_id': asset['source_id'],
            'title': asset['title'], 'artist': asset['artist'],
            'source_url': source, 'license_url': license_url,
            'content_sha256': asset['content_sha256'], 'content_bytes': asset['bytes'],
            'duration_ms': asset['duration_ms']}
    selected = set(query_ids)
    queries = []
    for query in original['queries']:
        if query['query_id'] not in selected:
            continue
        old_pool = {row['track_id'] for row in query['candidates']}
        complement = sorted(set(tracks) - old_pool, key=int)
        rp.require(complement, 'Selected query has no unjudged complement: ' + query['query_id'])
        queries.append({'query_id': query['query_id'], 'text': query['text'],
            'candidates': [{**tracks[tid], 'model_suggested_intervals_ms': [],
                            **dict.fromkeys(rp.HUMAN_FIELDS)} for tid in complement]})
    provenance = deepcopy(original['provenance'])
    provenance.update(selection=SELECTION, labeling_aid=LABELING_AID,
                      base_judgments_sha256=base_hash, base_dataset_sha256=base['dataset_sha256'],
                      diagnostic_query_ids=[query['query_id'] for query in queries])
    pack = {'schema': SCHEMA, 'split': rp.SPLIT, 'owner_user_id': original['owner_user_id'],
            'provenance': provenance, 'queries': queries}
    pack['dataset_sha256'] = rp.digest(rp.canonical(pack))
    return pack


def validate(pack, expected):
    rp.require(expected.get('schema') == SCHEMA, 'Expected reconstructed diagnostic pack')
    result = rp.validate(pack, expected)
    return {**result, 'schema': SCHEMA}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('build', 'validate'):
        child = sub.add_parser(command)
        child.add_argument('--run-dir', type=Path, required=True)
        child.add_argument('--catalog', type=Path, required=True)
        child.add_argument('--report-sha256', required=True)
        child.add_argument('--base-pack', type=Path, required=True)
        child.add_argument('--base-pack-sha256', required=True)
        child.add_argument('--query-ids', nargs='+', required=True)
        child.add_argument('--output' if command == 'build' else '--pack', type=Path, required=True)
    args = parser.parse_args()
    try:
        expected = prepare(args.run_dir, args.catalog, args.report_sha256,
                           args.base_pack, args.base_pack_sha256, args.query_ids)
        pack = expected if args.command == 'build' else rp.read_json(args.pack)[0]
        result = validate(pack, expected)
        if args.command == 'build':
            rp.write_new(args.output, pack)
            result['status'] = 'created_unjudged_diagnostic_pack'
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        parser.exit(1, 'Diagnostic pack rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

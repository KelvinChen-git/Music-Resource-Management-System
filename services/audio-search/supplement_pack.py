#!/usr/bin/env python3
"""Reconstruct only frozen retrieval-top5 unknown pairs; never infer human labels."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import research_evaluate as ev
import review_pack as rp
import source_review_pack as sp

SCHEMA = 'sonora-retrieval-supplement-pack-v1'
SPLIT = 'development_not_held_out'
ROOT = Path(__file__).resolve().parents[2]
SELECTION = 'unjudged_union_whole_track_top5_and_segment_top5'
ORDERING = 'query_fixture_order_then_track_id_ascending'
LABELING_AID = 'no_model_intervals_retrieval_supplement'


def candidate(asset):
    """Use the checked run's actual decode time and provider-specific public identity."""
    provider, sid = asset['source_provider'], asset['source_id']
    if provider == 'jamendo':
        rp.identity(sid)
        source_url, license_url = rp.public_urls(asset['source_url'], sid, asset['license_url'])
        rp.require(asset['source_url'] == source_url and asset['license_url'] == license_url,
                   'Expected canonical recorded Jamendo and CC BY URLs')
    else:
        rp.require(provider == 'incompetech' and isinstance(sid, str) and sp.ISRC.fullmatch(sid),
                   'Unknown provider or invalid source ISRC')
        source_url, license_url = sp.BASE + 'index.html?isrc=' + sid, sp.LICENSE
        rp.require(asset['source_url'] == source_url and asset['license_url'] == license_url,
                   'Source recording URL/license mismatch')
    return {'track_id': rp.identity(asset['track_id']), 'source_provider': provider, 'source_id': sid,
            'title': rp.text(asset['title'], 500), 'artist': rp.text(asset['artist'], 500),
            'source_url': source_url, 'license_url': license_url,
            'content_sha256': rp.sha(asset['content_sha256']),
            'content_bytes': rp.integer(asset['bytes'], 1, 30 * 1024 * 1024),
            'duration_ms': rp.integer(asset['duration_ms'], 1, 600000),
            'model_suggested_intervals_ms': [], **dict.fromkeys(rp.HUMAN_FIELDS)}


def prepare(*, evaluation, evaluation_sha256, **arguments):
    """Require the archived evaluation to equal a complete, freshly rebuilt evaluation."""
    rp.sha(evaluation_sha256)
    rp.require(not Path(evaluation).is_symlink(), 'Evaluation archive cannot be a symlink')
    archived, _ = rp.read_json(evaluation, expected=evaluation_sha256)
    rebuilt = ev.evaluate(**arguments)
    rp.require(rp.canonical(archived) == rp.canonical(rebuilt),
               'Archived evaluation differs from complete pinned-input reconstruction')
    run = Path(arguments['new_run_dir'])
    report, _ = rp.read_json(run / 'report.json', expected=arguments['new_report_sha256'])
    manifest, _ = rp.read_json(run / 'corpus-manifest.json', limit=16 * 1024 * 1024,
                             expected=report['artifact_sha256']['corpus-manifest.json'])
    catalog, _ = rp.read_json(arguments['import_catalog'], expected=arguments['import_catalog_sha256'])
    tracks, source_ids, contents = {}, set(), set()
    for asset in manifest['tracks']:
        row = candidate(asset)
        tid, source_id, content = row['track_id'], (row['source_provider'], row['source_id']), row['content_sha256']
        rp.require(tid not in tracks and source_id not in source_ids and content not in contents,
                   'Duplicate run track/source/content identity')
        tracks[tid] = row
        source_ids.add(source_id)
        contents.add(content)
    queries = []
    for query in rebuilt['queries']:
        unknown = set()
        for mode in ev.MODES:
            rows = query['new_modes'][mode]
            unknown.update(tid for tid, grade in zip(rows['track_ids'], rows['relevance']) if grade is None)
        if not unknown:
            continue
        rp.require(1 <= len(unknown) <= 10 and unknown <= set(tracks), 'Invalid unknown top5 union')
        queries.append({'query_id': query['query_id'], 'text': query['text'],
                        'candidates': [deepcopy(tracks[tid]) for tid in sorted(unknown, key=int)]})
    count = sum(len(query['candidates']) for query in queries)
    rp.require(1 <= count <= 50, 'No unknown results remain or supplement exceeds fifty pairs')
    provenance = {'source_report_sha256': arguments['new_report_sha256'], 'run_code_sha': report['code_sha'],
        'input_catalog_sha256': arguments['import_catalog_sha256'],
        'checkpoint_sha256': report['model']['checkpoint_sha256'], 'pipeline_version': report['pipeline_version'],
        'source_decoder_version': report['source_decoder_version'],
        'artifact_sha256': {name: report['artifact_sha256'][name] for name in ev.ARTIFACTS},
        'evaluation_sha256': evaluation_sha256,
        'known_judgments_sha256': {name: arguments[name + '_pack_sha256'] for name in ('base', 'diagnostic', 'source')},
        'supplement_query_ids': [query['query_id'] for query in queries],
        'selection': SELECTION, 'ordering': ORDERING, 'labeling_aid': LABELING_AID}
    pack = {'schema': SCHEMA, 'split': SPLIT, 'owner_user_id': rp.identity(catalog['ownerId'], catalog=True),
            'provenance': provenance, 'queries': queries}
    pack['dataset_sha256'] = rp.digest(rp.canonical(pack))
    # Detect changes between evaluation reconstruction and candidate assembly.
    rp.read_json(evaluation, expected=evaluation_sha256)
    rp.read_json(run / 'report.json', expected=arguments['new_report_sha256'])
    rp.read_json(run / 'corpus-manifest.json', limit=16 * 1024 * 1024,
                 expected=report['artifact_sha256']['corpus-manifest.json'])
    rp.read_json(arguments['import_catalog'], expected=arguments['import_catalog_sha256'])
    for name in ('baseline_catalog', 'import_catalog', 'source_manifest', 'decode_report', 'selection',
                 'query_fixture', 'base_pack', 'diagnostic_pack', 'source_pack'):
        rp.require(ev.file_hash(arguments[name]) == arguments[name + '_sha256'],
                   'Pinned input changed during supplement reconstruction')
    for prefix in ('old', 'new'):
        rp.require(ev.file_hash(Path(arguments[prefix + '_run_dir']) / 'report.json')
                   == arguments[prefix + '_report_sha256'], 'Pinned report changed during supplement reconstruction')
    return pack


def validate(pack, expected):
    rp.require(isinstance(expected, dict) and expected.get('schema') == SCHEMA and expected.get('split') == SPLIT,
               'Expected a reconstructed retrieval supplement pack')
    return {**rp.validate(pack, expected), 'schema': SCHEMA, 'split': SPLIT}


def write_new(path, pack):
    target, local = Path(path).absolute(), ROOT / '.local'
    rp.require(local.is_dir() and not local.is_symlink()
               and not any(p.is_symlink() for p in (target, *target.parents)), 'Output cannot traverse symlinks')
    rp.require(target.resolve().is_relative_to(local.resolve()) and target.resolve() != local.resolve(),
               'Supplement output must stay below this checkout .local')
    target = target.resolve()
    rp.require(subprocess.run(['git', 'check-ignore', '--quiet', '--no-index', str(target)], cwd=ROOT,
                              capture_output=True).returncode == 0, 'Supplement output must be ignored by Git')
    missing, parent = [], target.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    rp.require(not any(p.is_symlink() for p in (target, *target.parents)), 'Output parent changed to a symlink')
    rp.require(target.resolve().is_relative_to(local.resolve()) and (target.parent.stat().st_mode & 0o777) == 0o700,
               'Supplement output directory must be private mode 0700')
    raw = (json.dumps(pack, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    rp.require(len(raw) <= 2 * 1024 * 1024, 'Supplement pack exceeds import size limit')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('build', 'validate'):
        child = sub.add_parser(command)
        child.add_argument('--old-run-dir', type=Path, required=True)
        child.add_argument('--new-run-dir', type=Path, required=True)
        for name in ('old-report', 'new-report'):
            child.add_argument('--' + name + '-sha256', required=True)
        for name in ('baseline-catalog', 'import-catalog', 'source-manifest', 'decode-report', 'selection',
                     'query-fixture', 'base-pack', 'diagnostic-pack', 'source-pack', 'evaluation'):
            child.add_argument('--' + name, type=Path, required=True)
            child.add_argument('--' + name + '-sha256', required=True)
        child.add_argument('--output' if command == 'build' else '--pack', type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop('command')
    target = args.pop('output' if command == 'build' else 'pack')
    try:
        expected = prepare(**args)
        pack = expected if command == 'build' else rp.read_json(target)[0]
        summary = validate(pack, expected)
        if command == 'build':
            write_new(target, pack)
            summary['status'] = 'created_unjudged_retrieval_supplement_pack'
        print(json.dumps(summary, indent=2))
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, StopIteration) as exc:
        parser.exit(1, 'Retrieval supplement rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

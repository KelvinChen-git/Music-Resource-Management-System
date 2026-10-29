#!/usr/bin/env python3
"""Compare frozen development rankings with explicit unknown judgments; no model loading."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import diagnostic_pack as dp
import review_pack as rp
import source_review_pack as sp

TARGETS = ('exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08')
QUERY_IDS = tuple('exp-%02d' % n for n in range(1, 9))
MODES = ('whole_track', 'segment')
SOURCE_ROOT = Path(__file__).resolve().parent
SOURCE_NAMES = ('research_corpus.py', 'research_probe.py', 'test_research_probe.py',
                'corpus.py', 'preprocess.py', 'probe.py', 'review_pack.py',
                'source_review_pack.py', 'exploratory_queries.json')
ARTIFACTS = (*rp.ARTIFACTS, 'vectors.npz')
PIPELINE = 'candidate-soundfile-soxr-mono-zero-10s-hop5s-v1'
SOURCE_DECODER = 'soundfile-read-out-65536-actual-eof-v1'
MODEL = {'checkpoint_sha256': 'fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd',
         'checkpoint_revision': 'b3708341862f581175dba5c356a4ebf74a9b6651',
         'roberta_revision': 'e2da8e2f811d1448a5b465c236feacd80ffbac7b',
         'audio_architecture': 'HTSAT-base', 'fusion': False, 'dimension': 512,
         'strict_missing': [], 'strict_unexpected': [], 'removed_nonlearned_position_ids': True}
PREPROCESSING = {'sample_rate_hz': 48000, 'window_samples': 480000, 'hop_samples': 240000,
                 'downmix': 'channel arithmetic mean',
                 'resampler': 'whole-track soxr_hq with integer-ceiling sample count',
                 'padding': 'right zeros before SDK',
                 'sdk_quantization': 'clip [-1,1], float32 -> int16 -> float32'}
DECODE_KEYS = ('format', 'source_frames', 'source_sample_rate_hz', 'source_channels',
               'sample_rate_hz', 'decoded_samples', 'duration_ms')


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def window_segments(tracks):
    """Check the frozen 10s/5s arithmetic without importing numpy or decoding audio."""
    result = []
    for track in tracks:
        frames = rp.integer(track['source_frames'], 1, 192000 * 600)
        rate = rp.integer(track['source_sample_rate_hz'], 8000, 192000)
        rp.require(frames <= rate * 600 and type(track['source_channels']) is int
                   and track['source_channels'] in (1, 2) and track['format'] == 'MP3',
                   'Invalid source decode dimensions')
        length = (frames * 48000 + rate - 1) // rate
        rp.require(type(track['sample_rate_hz']) is int and track['sample_rate_hz'] == 48000
                   and type(track['decoded_samples']) is int and track['decoded_samples'] == length
                   and type(track['duration_ms']) is int and track['duration_ms'] == length * 1000 // 48000,
                   'Decoded samples must equal exact integer-ceiling resampling')
        rp.integer(track['duration_ms'], 1, 600000)
        if length <= 480000:
            bounds = [(0, length)]
        else:
            starts = list(range(0, length - 480000 + 1, 240000))
            bounds = [(start, start + 480000) for start in starts]
            if bounds[-1][1] < length:
                bounds.append((starts[-1] + 240000, length))
        tid = track['track_id']
        for start, end in bounds:
            result.append({'segment_id': f'{tid}:{start}:{end}', 'track_id': tid,
                           'start_sample': start, 'end_sample': end,
                           'start_ms': start * 1000 // 48000, 'end_ms': end * 1000 // 48000,
                           'padded_samples': 480000 - (end - start)})
    return result


def validate_rankings(value, fixture, tracks, segments, allow_references=False):
    rp.require(isinstance(value, dict) and value['judgments'] == 'unjudged'
               and isinstance(value['queries'], list), 'Invalid frozen rankings')
    known_segments = {row['segment_id']: row for row in segments}
    queries, all_ids = {}, set()
    expected = {query['query_id']: query['text'] for query in fixture['queries']}
    for query in value['queries']:
        qid = query['query_id']
        rp.require(qid not in all_ids, 'Duplicate ranking query')
        all_ids.add(qid)
        if allow_references and query['kind'] == 'audio':
            continue
        rp.require(query['kind'] == 'text' and qid in expected and query['text'] == expected[qid],
                   'Ranking query identity/text mismatch')
        for mode in MODES:
            rows = query[mode]
            rp.require(isinstance(rows, list) and len(rows) == 5, 'Expected five frozen ranked tracks')
            seen = set()
            for row in rows:
                tid = rp.identity(row['track_id'])
                rp.require(tid in tracks and tid not in seen, 'Unknown/duplicate ranking track')
                seen.add(tid)
                rp.require(type(row['score']) in (int, float) and math.isfinite(row['score']),
                           'Invalid ranking score')
                if mode == 'segment':
                    choices = row['segments']
                    rp.require(isinstance(choices, list) and 1 <= len(choices) <= 3,
                               'Expected one to three suggested segments')
                    previous = []
                    for segment in choices:
                        sid = segment['segment_id']
                        rp.require(sid in known_segments and segment['track_id'] == tid
                                   and rp.canonical({k: v for k, v in segment.items() if k != 'score'})
                                   == rp.canonical(known_segments[sid]), 'Ranked segment mismatch')
                        score = segment['score']
                        rp.require(type(score) in (int, float) and math.isfinite(score), 'Invalid segment score')
                        for other in previous:
                            intersection = max(0, min(segment['end_sample'], other['end_sample'])
                                               - max(segment['start_sample'], other['start_sample']))
                            union = max(segment['end_sample'], other['end_sample']) - min(segment['start_sample'], other['start_sample'])
                            rp.require(intersection / union <= 0.5, 'Suggested segments violate overlap suppression')
                        previous.append(segment)
                    rp.require(row['score'] == choices[0]['score'], 'Track score is not its maximum segment score')
        # Do not sort: these arrays, including their tie order, are the actual frozen run.
        queries[qid] = query
    rp.require(tuple(queries) == QUERY_IDS and tuple(expected) == QUERY_IDS,
               'Expected all eight original queries in their frozen fixture order')
    return queries


def ranking_bounds(track_ids, known, new_ids):
    rp.require(isinstance(track_ids, (list, tuple)) and len(track_ids) == 5
               and len(set(track_ids)) == 5, 'Expected five distinct ordered tracks')
    for grade in known.values():
        rp.integer(grade, 0, 3)
    grades = [known.get(tid) for tid in track_ids]
    relevant = sum(grade is not None and grade >= 2 for grade in grades)
    unknown = sum(grade is None for grade in grades)
    return {'track_ids': list(track_ids), 'relevance': grades,
            'known_relevant': relevant, 'known_nonrelevant': 5 - relevant - unknown, 'unknown': unknown,
            'precision_at_5_lower': relevant / 5, 'precision_at_5_upper': (relevant + unknown) / 5,
            'exact_precision_at_5': relevant / 5 if unknown == 0 else None,
            'confirmed_new_source_relevant_hits': sum(tid in new_ids and grade is not None and grade >= 2
                                                    for tid, grade in zip(track_ids, grades))}


def evaluate(*, old_run_dir, old_report_sha256, new_run_dir, new_report_sha256,
             baseline_catalog, baseline_catalog_sha256, import_catalog, import_catalog_sha256,
             source_manifest, source_manifest_sha256, decode_report, decode_report_sha256,
             selection, selection_sha256, query_fixture, query_fixture_sha256,
             base_pack, base_pack_sha256, diagnostic_pack, diagnostic_pack_sha256,
             source_pack, source_pack_sha256):
    pins = {'old_report': old_report_sha256, 'new_report': new_report_sha256,
            'baseline_catalog': baseline_catalog_sha256, 'catalog': import_catalog_sha256,
            'source_manifest': source_manifest_sha256, 'decode_report': decode_report_sha256,
            'selection': selection_sha256, 'queries': query_fixture_sha256,
            'base_judgments': base_pack_sha256, 'diagnostic_judgments': diagnostic_pack_sha256,
            'source_judgments': source_pack_sha256}
    for digest in pins.values():
        rp.sha(digest)
    paths = {'baseline_catalog': baseline_catalog, 'catalog': import_catalog,
             'source_manifest': source_manifest, 'decode_report': decode_report,
             'selection': selection, 'queries': query_fixture}
    inputs = {}
    for name, path in paths.items():
        inputs[name], _ = rp.read_json(path, expected=pins[name])
    original = rp.prepare(old_run_dir, baseline_catalog, old_report_sha256)
    base, _ = rp.read_json(base_pack, expected=base_pack_sha256)
    base_validation = rp.validate(base, original)
    diagnostic_expected = dp.prepare(old_run_dir, baseline_catalog, old_report_sha256,
                                     base_pack, base_pack_sha256, TARGETS)
    diagnostic, _ = rp.read_json(diagnostic_pack, expected=diagnostic_pack_sha256)
    diagnostic_validation = dp.validate(diagnostic, diagnostic_expected)
    source_expected = sp.prepare(source_manifest, decode_report, import_catalog, query_fixture,
                                 source_manifest_sha256, decode_report_sha256,
                                 import_catalog_sha256, query_fixture_sha256, selection, baseline_catalog)
    source, _ = rp.read_json(source_pack, expected=source_pack_sha256)
    source_validation = sp.validate(source, source_expected)
    for validation in (base_validation, diagnostic_validation, source_validation):
        rp.require(validation['unjudged'] == 0, 'All three supplied packages must be fully judged')
        rp.require(validation['human_intervals'] == 0,
                   'This track-only comparison requires packages without human localization intervals')
    rp.require(base['owner_user_id'] == diagnostic['owner_user_id'] == source['owner_user_id'],
               'Judgment owner mismatch')
    old_report, _ = rp.read_json(Path(old_run_dir) / 'report.json', expected=old_report_sha256)
    report, _ = rp.read_json(Path(new_run_dir) / 'report.json', expected=new_report_sha256)
    rp.require(report['schema'] == 'sonora-research-probe-v1'
               and report['status'] == 'passed_private_research_pipeline_only'
               and report['source_decoder_version'] == SOURCE_DECODER
               and report['working_tree_dirty'] is False
               and isinstance(report['code_sha'], str) and re.fullmatch('[a-f0-9]{40}', report['code_sha']),
               'Expected clean completed research run')
    six_pins = {name: pins[name] for name in paths}
    rp.require(report['input_sha256'] == six_pins and report['input_catalog_sha256'] == import_catalog_sha256,
               'Research run six-input pin mismatch')
    for item in (old_report, report):
        rp.require(rp.canonical(item['model']) == rp.canonical(MODEL)
                   and item['pipeline_version'] == PIPELINE
                   and rp.canonical(item['preprocessing']) == rp.canonical(PREPROCESSING)
                   and item['environment']['device'] == 'cpu', 'Fixed model/pipeline/preprocessing mismatch')
    hashes = report['source_hashes']
    rp.require(isinstance(hashes, dict) and set(hashes) == set(SOURCE_NAMES), 'Research source hash set mismatch')
    for name, digest in hashes.items():
        rp.require(file_hash(SOURCE_ROOT / name) == rp.sha(digest), 'Research source hash mismatch: ' + name)
    for name in ('corpus.py', 'preprocess.py', 'probe.py'):
        rp.require(old_report['source_hashes'][name] == hashes[name], 'Changed original retrieval dependency')
    rp.require(set(report['artifact_sha256']) == set(ARTIFACTS), 'Research artifact set mismatch')
    artifacts = {}
    for name in ARTIFACTS:
        path = Path(new_run_dir) / name
        rp.require(not path.is_symlink(), 'Research artifact cannot be a symlink')
        digest = rp.sha(report['artifact_sha256'][name])
        rp.require(file_hash(path) == digest, 'Research artifact hash mismatch: ' + name)
        if name.endswith('.json'):
            artifacts[name], _ = rp.read_json(path, limit=16 * 1024 * 1024, expected=digest)
    fixture = inputs['queries']
    old_fixture, _ = rp.read_json(Path(old_run_dir) / 'queries.json',
        expected=old_report['artifact_sha256']['queries.json'])
    rp.require(rp.canonical(artifacts['queries.json']) == rp.canonical(fixture)
               and rp.canonical(old_fixture) == rp.canonical(fixture),
               'New and old query fixture differ')
    manifest = artifacts['corpus-manifest.json']
    rp.require(manifest['schema'] == 'sonora-research-corpus-v1'
               and manifest['pipeline_version'] == PIPELINE
               and manifest['source_decoder_version'] == SOURCE_DECODER,
               'Research corpus schema/pipeline/source decoder mismatch')
    old_manifest, _ = rp.read_json(Path(old_run_dir) / 'corpus-manifest.json', limit=16 * 1024 * 1024,
        expected=old_report['artifact_sha256']['corpus-manifest.json'])
    old_tracks = {track['track_id']: track for track in old_manifest['tracks']}
    catalog = {rp.identity(row['musicId'], catalog=True): row for row in inputs['catalog']['audioTracks']}
    rows = manifest['tracks']
    rp.require(isinstance(rows, list) and len(rows) == 40 and len(catalog) == 40 and len(old_tracks) == 20,
               'Expected original20 plus new20 corpus')
    new_candidates = {row['track_id']: row for query in source_expected['queries'] for row in query['candidates']}
    rp.require(len(new_candidates) == 20 and not set(new_candidates) & set(old_tracks),
               'Old/new track universes intersect')
    recorded = {row['source_id']: row for row in inputs['decode_report']['tracks']}
    tracks, sources, content = {}, set(), set()
    for track in rows:
        tid = rp.identity(track['track_id'])
        rp.require(tid in catalog and tid not in tracks, 'Unknown/duplicate research track')
        entry = catalog[tid]
        provider, sid = track['source_provider'], track['source_id']
        rp.require(provider == entry['sourceProvider'] and sid == str(entry['sourceId'])
                   and (provider, sid) not in sources, 'Research source identity mismatch/duplicate')
        digest = rp.sha(track['content_sha256'])
        rp.require(digest == entry['sha256'] and digest not in content
                   and track['title'] == entry['title'] and track['artist'] == entry['artist']
                   and track['source_url'] == entry['sourceUrl']
                   and track['provider_duration_seconds'] == entry['durationSeconds']
                   and type(track['provider_duration_seconds']) is int
                   and track['asset_filename'] == provider + '-' + sid + '.mp3',
                   'Research corpus immutable content/metadata mismatch')
        rp.integer(track['bytes'], 1, 30 * 1024 * 1024)
        rp.sha(track['download_proof_sha256'])
        if tid in old_tracks:
            old = old_tracks[tid]
            rp.require(provider == 'jamendo' and set(track) == set(old) | {'source_provider'}
                       and all(rp.canonical(track[k]) == rp.canonical(v) for k, v in old.items() if k != 'asset_filename'),
                       'Original track decode/content/proof changed')
        else:
            rp.require(tid in new_candidates and provider == 'incompetech', 'Unknown added source recording')
            candidate = new_candidates[tid]
            rp.require(track['bytes'] == candidate['content_bytes'] and track['license_url'] == candidate['license_url'],
                       'Added recording bytes/license mismatch')
            raw = recorded[sid]
            expected_decode = {key: raw[key] for key in ('frames', 'sample_rate_hz', 'channels', 'format', 'duration_ms')}
            rp.integer(track['source_frames'], raw['sample_rate_hz'] * 30, raw['sample_rate_hz'] * 600)
            rp.require(rp.canonical(track['recorded_decode']) == rp.canonical(expected_decode)
                       and type(track['declared_source_frames']) is int
                       and track['declared_source_frames'] == raw['frames']
                       and track['source_sample_rate_hz'] == raw['sample_rate_hz']
                       and track['source_channels'] == raw['channels'] and track['format'] == raw['format']
                       and candidate['duration_ms'] == raw['frames'] * 1000 // raw['sample_rate_hz'],
                       'Added source historical header/actual decode binding mismatch')
            proof = Path(source_manifest).parent / (sid + '.download.json')
            rp.require(track['download_proof_sha256'] == file_hash(proof), 'Added source proof hash mismatch')
        tracks[tid] = track; sources.add((provider, sid)); content.add(digest)
    rp.require(set(tracks) == set(catalog) == set(old_tracks) | set(new_candidates)
               and [track['track_id'] for track in rows] == sorted(tracks, key=int),
               'Incomplete or unordered research corpus')
    segments = window_segments(rows)
    rp.require(rp.canonical(segments) == rp.canonical(artifacts['segments.json']),
               'Research windows differ from complete frozen window rules')
    old_segments, _ = rp.read_json(Path(old_run_dir) / 'segments.json', limit=16 * 1024 * 1024,
        expected=old_report['artifact_sha256']['segments.json'])
    rp.require(rp.canonical(window_segments(old_manifest['tracks'])) == rp.canonical(old_segments),
               'Original window rules mismatch')
    counts = report['counts']
    expected_counts = {'tracks': 40, 'segments': len(segments), 'text_queries': 8, 'reference_queries': 0,
                       'padded_tail_segments': sum(row['padded_samples'] > 0 for row in segments),
                       'decoded_duration_ms': sum(row['duration_ms'] for row in rows)}
    rp.require(all(type(counts[key]) is int and counts[key] == value for key, value in expected_counts.items()),
               'Research run counts mismatch')
    old_rankings, _ = rp.read_json(Path(old_run_dir) / 'rankings.json', limit=16 * 1024 * 1024,
        expected=old_report['artifact_sha256']['rankings.json'])
    old_rankings = validate_rankings(old_rankings, fixture, old_tracks, old_segments, allow_references=True)
    new_rankings = validate_rankings(artifacts['rankings.json'], fixture, tracks, segments)
    known, texts = {}, {}
    for pack in (base, diagnostic, source):
        for query in pack['queries']:
            qid = query['query_id']
            rp.require(qid not in texts or texts[qid] == query['text'], 'Judgment query text mismatch')
            texts[qid] = query['text']
            for candidate in query['candidates']:
                key = (qid, candidate['track_id'])
                rp.require(key not in known, 'Judgment packages overlap')
                known[key] = candidate['relevance']
    results = []
    for qid in TARGETS:
        grades = {tid: grade for (query, tid), grade in known.items() if query == qid}
        rp.require(set(grades) & set(old_tracks) == set(old_tracks)
                   and len(set(grades) & set(new_candidates)) == 4 and len(grades) == 24,
                   'Expected twenty old plus four new known judgments per target')
        result = {'query_id': qid, 'text': texts[qid], 'corpus_size': 40, 'known_pairs': 24, 'unknown_pairs': 16,
                  'known_relevant_old': sum(grades[tid] >= 2 for tid in old_tracks),
                  'known_relevant_new': sum(grade >= 2 for tid, grade in grades.items() if tid in new_candidates),
                  'old_modes': {}, 'new_modes': {}}
        for mode in MODES:
            old_ids = [row['track_id'] for row in old_rankings[qid][mode]]
            new_ids = [row['track_id'] for row in new_rankings[qid][mode]]
            result['old_modes'][mode] = ranking_bounds(old_ids, grades, set())
            result['new_modes'][mode] = ranking_bounds(new_ids, grades, set(new_candidates))
        results.append(result)
    summary = {}
    for mode in MODES:
        new = [query['new_modes'][mode] for query in results]
        old = [query['old_modes'][mode] for query in results]
        unknown = sum(row['unknown'] for row in new)
        lower = math.fsum(row['precision_at_5_lower'] for row in new) / len(results)
        summary[mode] = {'query_count': len(results),
                         'old_macro_exact_precision_at_5': math.fsum(row['exact_precision_at_5'] for row in old) / len(results),
                         'new_macro_precision_at_5_lower': lower,
                         'new_macro_precision_at_5_upper': math.fsum(row['precision_at_5_upper'] for row in new) / len(results),
                         'new_macro_exact_precision_at_5': lower if unknown == 0 else None,
                         'new_unknown_returned_positions': unknown,
                         'new_fully_judged_queries': sum(row['unknown'] == 0 for row in new),
                         'new_known_relevant_positions': sum(row['known_relevant'] for row in new),
                         'new_confirmed_source_relevant_hits': sum(row['confirmed_new_source_relevant_hits'] for row in new)}
    # Recheck every pinned input and both report/artifact snapshots before returning a mixed analysis.
    for name, path in paths.items():
        rp.require(file_hash(path) == pins[name], 'Input changed during evaluation')
    for path, digest in ((base_pack, base_pack_sha256), (diagnostic_pack, diagnostic_pack_sha256),
                         (source_pack, source_pack_sha256), (Path(old_run_dir) / 'report.json', old_report_sha256),
                         (Path(new_run_dir) / 'report.json', new_report_sha256)):
        rp.require(file_hash(path) == digest, 'Pinned report or judgments changed during evaluation')
    for run, artifact_hashes in ((old_run_dir, old_report['artifact_sha256']), (new_run_dir, report['artifact_sha256'])):
        for name, digest in artifact_hashes.items():
            rp.require(name == Path(name).name and file_hash(Path(run) / name) == rp.sha(digest),
                       'Run artifact changed during evaluation')
    return {'schema': 'sonora-research-evaluation-v1', 'status': 'evaluated_unknown_aware_development_only',
            'target_query_ids': list(TARGETS), 'query_count': len(results), 'corpus_size': 40,
            'known_pairs_in_targets': 120, 'unknown_pairs_in_targets': 80,
            'input_sha256': pins, 'validation': {'base': base_validation, 'diagnostic': diagnostic_validation,
                                               'source': source_validation},
            'new_run_source_sha': report['code_sha'], 'retrieval_model': report['model'],
            'pipeline_version': PIPELINE, 'source_decoder_version': SOURCE_DECODER,
            'preprocessing': report['preprocessing'],
            'evaluator_sha256': file_hash(__file__), 'summary': summary, 'queries': results,
            'protocol': {'positive_grade_min': 2, 'denominator': 5, 'unknown': 'unjudged, never zero',
                         'precision_bounds': '[known_relevant/5, (known_relevant+unknown)/5]',
                         'macro': 'all five target queries equally weighted; never exclude unknown queries',
                         'exact': 'null unless all returned positions in the reported scope are judged',
                         'ranking_order': 'frozen original array order; labels never reorder results'},
            'limits': ['Development expansion selected around known failed descriptions; one new author.',
                       'Twenty new tracks have only four judgments per target query; remaining sixteen are unknown.',
                       'Track relevance does not establish suggested-interval localization accuracy.',
                       'New-source historical header frames remain separate from versioned actual-EOF reads.',
                       'No new nDCG, Recall, IoU, P95, significance, held-out or exact overall improvement claim.',
                       'No training, score threshold calibration, model acceptance, identity or listening verification.',
                       'Per-track ranking and judgment links are private local output only.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-run-dir', type=Path, required=True)
    parser.add_argument('--new-run-dir', type=Path, required=True)
    for name in ('old-report', 'new-report'):
        parser.add_argument('--' + name + '-sha256', required=True)
    for name in ('baseline-catalog', 'import-catalog', 'source-manifest', 'decode-report', 'selection',
                 'query-fixture', 'base-pack', 'diagnostic-pack', 'source-pack'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = vars(parser.parse_args())
    output = args.pop('output')
    try:
        result = evaluate(**args)
        rp.write_new(output, result)
        print(json.dumps({key: result[key] for key in ('status', 'query_count', 'corpus_size',
                                                      'known_pairs_in_targets', 'unknown_pairs_in_targets', 'summary')}, indent=2))
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, StopIteration) as exc:
        parser.exit(1, 'Research evaluation rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

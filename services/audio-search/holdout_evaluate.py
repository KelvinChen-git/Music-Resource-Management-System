#!/usr/bin/env python3
"""G5: verify all committed bytes before any grade parsing; compare five frozen runs."""
import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

import holdout_contract as hc
import holdout_review as hr
import review_pack as rp

CONFIGS = ('A-whole', 'A-segment', 'B-whole', 'B-segment', 'title-tfidf')
QUERIES = tuple(f'holdout-{n:02}' for n in range(1, 9))
CONTRASTS = (('B-whole', 'A-whole'), ('B-segment', 'A-segment'),
             ('A-segment', 'A-whole'), ('B-segment', 'B-whole'))


def committed_bytes(archive, exports):
    """No JSON parse here, including when the fourth file fails its commitment."""
    rp.require(len(exports) == 4 and [x['batch'] for x in exports] == [1, 2, 3, 4]
               and len({x['payload_sha256'] for x in exports}) == 4, 'Four distinct commitments required')
    raw_zip = hc.assets.read(archive, 16 * 1024 * 1024)
    import io
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
        files = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith('__MACOSX/')]
        rp.require(len(files) == 4 and len({i.filename for i in files}) == 4, 'Exactly four payload files required')
        results = []
        for x in exports:
            prefix = 'sonora-judgments-' + rp.sha(x['dataset_sha256'])[:12]
            candidates = [i for i in files if re.fullmatch(re.escape(prefix) + r'(?:-[0-9]+)?\.json', PurePosixPath(i.filename).name)]
            rp.require(len(candidates) == 1, 'Missing or duplicate batch export')
            i = candidates[0]
            mode = i.external_attr >> 16
            rp.require(not i.flag_bits & 1 and 0 < i.file_size <= 2 * 1024 * 1024
                       and not stat.S_ISLNK(mode), 'Invalid archive member')
            raw = z.read(i)
            rp.require(len(raw) == i.file_size and hc.digest(raw) == rp.sha(x['payload_sha256']),
                       'Payload differs from receipt commitment; no grades parsed')
            results.append(raw)
    return raw_zip, results


def compare(labels, rankings):
    rp.require(tuple(labels) == QUERIES and set(rankings) == set(CONFIGS), 'All eight queries and five runs required')
    universe = set(labels[QUERIES[0]])
    rp.require(len(universe) == 20, 'Expected twenty unique tracks')
    for q in QUERIES:
        rp.require(set(labels[q]) == universe, 'Full common twenty-track qrels required')
        for grade in labels[q].values(): rp.integer(grade, 0, 3)
    for c in CONFIGS:
        rp.require(tuple(rankings[c]) == QUERIES, 'Ranking query order changed')
        for q in QUERIES:
            rows = rankings[c][q]
            rp.require(len(rows) == 20 and len(set(rows)) == 20 and set(rows) == universe,
                       'Full unique twenty-track ranking required')
    def dcg(grades): return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades[:5]))
    per_query = []
    for q in QUERIES:
        grades = labels[q]
        positives = sum(g >= 2 for g in grades.values())
        idcg = dcg(sorted(grades.values(), reverse=True))
        scores = {}
        for c in CONFIGS:
            top = [grades[t] for t in rankings[c][q][:5]]
            hits = sum(g >= 2 for g in top)
            scores[c] = {'relevant_top5': hits, 'P_at_5': hits / 5,
                         'nDCG_at_5': dcg(top) / idcg if idcg else None}
        per_query.append({'query_id': q, 'grade_counts': {str(g): list(grades.values()).count(g) for g in range(4)},
                          'positives': positives, 'P_at_5_ceiling': min(positives, 5) / 5,
                          'IDCG_at_5': idcg, 'scores': scores})
    eligible = [q['query_id'] for q in per_query if q['IDCG_at_5'] > 0]
    macro = {c: {'P_at_5': sum(q['scores'][c]['P_at_5'] for q in per_query) / 8,
                 'P_query_denominator': 8,
                 'nDCG_at_5': sum(q['scores'][c]['nDCG_at_5'] for q in per_query if q['IDCG_at_5']) / len(eligible) if eligible else None,
                 'nDCG_query_denominator': len(eligible)} for c in CONFIGS}
    contrasts = []
    for index, (candidate, anchor) in enumerate(CONTRASTS):
        row = {'candidate': candidate, 'anchor': anchor, 'role': 'primary' if index == 0 else 'secondary'}
        for metric in ('P_at_5', 'nDCG_at_5'):
            deltas = {q['query_id']: q['scores'][candidate][metric] - q['scores'][anchor][metric]
                      for q in per_query if q['scores'][candidate][metric] is not None}
            mean = sum(deltas.values()) / len(deltas) if deltas else None
            row[metric] = {'paired_query_deltas': deltas, 'mean_delta': mean,
                           'absolute_percentage_point_delta': mean * 100 if mean is not None else None,
                           'wins': sum(v > 1e-12 for v in deltas.values()),
                           'ties': sum(abs(v) <= 1e-12 for v in deltas.values()),
                           'losses': sum(v < -1e-12 for v in deltas.values()), 'query_denominator': len(deltas)}
        contrasts.append(row)
    return {'per_query': per_query, 'macro': macro, 'contrasts': contrasts,
            'zero_positive_queries': [q['query_id'] for q in per_query if q['positives'] == 0],
            'zero_IDCG_queries': [q['query_id'] for q in per_query if not q['IDCG_at_5']],
            'nDCG_eligible_queries': eligible, 'unknown_pairs': 0}


def evaluate(*, archive, gate, gate_sha256, freeze, runs, packages, output):
    request = hc.assets.document(gate, gate_sha256)
    rp.require(request['status'] == 'ready_to_request_all4_committed_exports_not_opened'
               and request['readable_payloads_opened'] == 0, 'Published G5 request eligibility required')
    # Check all bytes before even constructing an output or parsing a judgment JSON.
    raw_zip, raws = committed_bytes(archive, request['requested_exports'])
    f, data = hc.checked_freeze(freeze, request['runner_freeze_sha256'], verify_environment=True)
    runs, packages = Path(runs), Path(packages)
    commit = hc.assets.document(runs / 'all-runs-commitment.json', request['all_runs_commitment_sha256'])
    rp.require(commit['runner_freeze_sha256'] == request['runner_freeze_sha256']
               and commit['counts'] == {'tracks': 20, 'queries': 8, 'configurations': 5, 'qrels_opened': 0}
               and set(commit['ranking_sha256']) == {c + '.json' for c in CONFIGS}
               and f['created_at_utc'] < commit['created_at_utc'], 'Incomplete or mismatched frozen runs')
    rp.require(set(commit['vector_artifact_sha256']) == {'A/segments.json', 'A/vectors.npz', 'B/segments.json', 'B/vectors.npz'}, 'Four original vector artifacts required')
    artifact_hashes = {**commit['ranking_sha256'], **commit['vector_artifact_sha256']}
    for name, h in artifact_hashes.items():
        rp.require(PurePosixPath(name).is_relative_to('.') and '..' not in PurePosixPath(name).parts
                   and hc.file_hash(runs / name) == h, 'Frozen run artifact changed')
    bases = hr.packages(data, request['runner_freeze_sha256'])
    for i, base in enumerate(bases, 1):
        raw = hc.assets.read(packages / f'sonora-independent-batch-{i}.json', 2 * 1024 * 1024)
        rp.require(raw == (json.dumps(base, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
                   and hc.assets.source.strict_json(raw) == base
                   and base['dataset_sha256'] == request['requested_exports'][i - 1]['dataset_sha256']
                   and base['provenance']['test_dataset_sha256'] == request['test_dataset_sha256'], 'Blank package reconstruction mismatch')
    track_ids = {t['track_id'] for t in data['tracks']}
    rankings = {}
    for c in CONFIGS:
        run = hc.assets.document(runs / (c + '.json'), commit['ranking_sha256'][c + '.json'])
        rp.require(run['runner_freeze_sha256'] == request['runner_freeze_sha256']
                   and [q['query_id'] for q in run['queries']] == list(QUERIES), 'Run freeze/query mismatch')
        rankings[c] = {q['query_id']: [t['track_id'] for t in q['ranking']] for q in run['queries']}
        rp.require(all(len(v) == 20 and set(v) == track_ids for v in rankings[c].values()), 'Run track universe changed')
    target = hc.private_output(output)
    def raw_write(path, raw):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as handle: handle.write(raw)
    try:
        raw_write(target / 'original.zip', raw_zip)
        for i, raw in enumerate(raws, 1): raw_write(target / f'batch-{i}.json', raw)
        event = {'schema': 'sonora-G5-once-only-opening-v1', 'all4_payload_hashes_checked_before_parse': True,
                 'archive_sha256': hc.digest(raw_zip), 'gate_sha256': gate_sha256,
                 'payload_sha256': [hc.digest(r) for r in raws], 'gate_checks_finished_at_utc': hc.now(),
                 'first_judgment_JSON_parse_at_utc': hc.now(), 'original_G4_created_at_utc': commit['created_at_utc'],
                 'runner_source': hc.source_state(clean=False), 'evaluator_sha256': hc.file_hash(Path(__file__)),
                 'operation': 'single_joint_opening_after_all4_receipts_and_all5_frozen_runs'}
        hc.write_json(target / 'opening.json', event)
        labels, validations = {}, []
        for raw, base in zip(raws, bases):
            pack = hc.assets.source.strict_json(raw)
            v = rp.validate(pack, base)
            rp.require(v['candidate_pairs'] == 40 and v['judged'] == 40 and v['unjudged'] == 0, 'Incomplete forty-pair batch')
            # Legacy validator split summary is a constant; authoritative split is immutable pack/base.
            v['split'] = pack['split']; validations.append(v)
            for q in pack['queries']:
                rp.require(q['query_id'] not in labels, 'Duplicate query across batches')
                labels[q['query_id']] = {t['track_id']: t['relevance'] for t in q['candidates']}
        metrics = compare(labels, rankings)
        for name, h in artifact_hashes.items(): rp.require(hc.file_hash(runs / name) == h, 'Run changed during evaluation')
        result = {'schema': 'sonora-independent-five-run-evaluation-v1', 'status': 'complete_small_project_holdout_comparison',
                  'split': 'independent_test', 'evaluated_at_utc': hc.now(), 'gate_sha256': gate_sha256,
                  'runner_freeze_sha256': request['runner_freeze_sha256'],
                  'all_runs_commitment_sha256': request['all_runs_commitment_sha256'],
                  'test_dataset_sha256': request['test_dataset_sha256'], 'archive_sha256': event['archive_sha256'],
                  'opening_receipt_sha256': hc.file_hash(target / 'opening.json'),
                  'payload_sha256': event['payload_sha256'], 'counts': {'tracks': 20, 'queries': 8, 'judged_pairs': 160,
                  'unjudged_pairs': 0, 'configurations': 5, 'new_model_runs': 0, 'training_runs': 0},
                  'validation': validations, **metrics,
                  'limits': ['Single user subjective model-blind judgments; identity/listening and interrater reliability not verified.',
                             'Full qrels only for twenty new recordings, not the combined sixty-track library.',
                             'Eight queries/small source frame; no significance, pretraining-unseen or population-generalization claim.',
                             'No Recall, localization IoU, P95, tuning, model switch, training or online retrieval.',
                             'Future changes selected using these labels make this a development regression set.']}
        hc.write_json(target / 'result.json', result)
        return result
    except Exception as exc:
        hc.write_json(target / 'failure.json', {'status': 'failed_G5', 'error_type': type(exc).__name__, 'error': str(exc)})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('archive', 'gate', 'freeze', 'runs', 'packages', 'output'): p.add_argument('--' + n, type=Path, required=True)
    p.add_argument('--gate-sha256', required=True)
    result = evaluate(**vars(p.parse_args()))
    print(json.dumps({'status': result['status'], 'counts': result['counts'], 'macro': result['macro']}))


if __name__ == '__main__': main()

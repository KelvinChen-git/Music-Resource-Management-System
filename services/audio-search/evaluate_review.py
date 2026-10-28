#!/usr/bin/env python3
"""Compare frozen top-five runs on fully judged exploratory pools; never tune retrieval."""
import argparse
import json
import math
from pathlib import Path

import review_pack as rp

MODES = ('whole_track', 'segment')
METRICS = ('precision_at_5', 'pooled_ndcg_at_5')
TOP_K = 5


def score_ranking(track_ids, relevance):
    """Exponential graded gain; ideal ranking is limited to this query's judged pool."""
    rp.require(isinstance(relevance, dict) and len(relevance) >= TOP_K,
               'Expected at least five fully judged pool entries')
    for key, value in relevance.items():
        rp.require(isinstance(key, str) and key, 'Invalid pool identity')
        rp.integer(value, 0, 3)  # Includes pool entries outside this mode's top five.
    rp.require(isinstance(track_ids, (list, tuple)) and len(track_ids) == TOP_K,
               'Expected exactly five ranked tracks')
    rp.require(all(isinstance(tid, str) and tid in relevance for tid in track_ids),
               'Ranking includes unknown or unjudged track')
    rp.require(len(set(track_ids)) == TOP_K, 'Duplicate ranked track')
    grades = [relevance[tid] for tid in track_ids]

    def dcg(values):
        return math.fsum((2 ** grade - 1) / math.log2(rank + 1)
                         for rank, grade in enumerate(values, 1))

    actual = dcg(grades)
    ideal = dcg(sorted(relevance.values(), reverse=True)[:TOP_K])
    positives = sum(grade >= 2 for grade in grades)
    return {'precision_at_5': positives / TOP_K,
            'pooled_ndcg_at_5': actual / ideal if ideal else None,
            'dcg_at_5': actual, 'pool_idcg_at_5': ideal,
            'positive_count': positives,
            'low_relevance_ranks': [rank for rank, grade in enumerate(grades, 1) if grade < 2]}


def evaluate(run_dir, catalog_path, expected_report_sha256, pack_path, expected_pack_sha256):
    # read_json permits an optional pin for other callers; evaluation requires both explicitly.
    rp.sha(expected_report_sha256)
    rp.sha(expected_pack_sha256)
    expected = rp.prepare(run_dir, catalog_path, expected_report_sha256)
    pack, pack_hash = rp.read_json(pack_path, expected=expected_pack_sha256)
    validation = rp.validate(pack, expected)
    rp.require(validation['unjudged'] == 0, 'Complete all judgments before evaluation')
    # Recheck the frozen rankings bytes instead of reopening an unbound mutable artifact.
    rankings, rankings_hash = rp.read_json(Path(run_dir) / 'rankings.json',
        limit=16 * 1024 * 1024, expected=expected['provenance']['artifact_sha256']['rankings.json'])
    text_rankings = {query['query_id']: query for query in rankings['queries'] if query['kind'] == 'text'}
    queries = []
    for query in pack['queries']:
        grades = {row['track_id']: row['relevance'] for row in query['candidates']}
        modes = {}
        for mode in MODES:
            # Preserve the actual run order, including its frozen tie order. The pack is ID-sorted.
            ids = [row['track_id'] for row in text_rankings[query['query_id']][mode]]
            metrics = score_ranking(ids, grades)
            modes[mode] = {'track_ids': ids, 'relevance': [grades[tid] for tid in ids], **metrics}
        queries.append({'query_id': query['query_id'], 'text': query['text'],
                        'pool_size': len(grades),
                        'relevance_counts': {str(n): sum(grade == n for grade in grades.values()) for n in range(4)},
                        'pool_positive_count': sum(grade >= 2 for grade in grades.values()),
                        'modes': modes})

    summary = {}
    for mode in MODES:
        valid_ndcg = [query['modes'][mode]['pooled_ndcg_at_5'] for query in queries
                      if query['modes'][mode]['pooled_ndcg_at_5'] is not None]
        summary[mode] = {
            'macro_precision_at_5': math.fsum(query['modes'][mode]['precision_at_5'] for query in queries) / len(queries),
            'macro_pooled_ndcg_at_5': math.fsum(valid_ndcg) / len(valid_ndcg) if valid_ndcg else None,
            'ndcg_valid_queries': len(valid_ndcg), 'zero_idcg_queries': len(queries) - len(valid_ndcg)}
    paired = {}
    for metric in METRICS:
        result = {'segment_wins': 0, 'ties': 0, 'whole_track_wins': 0, 'compared_queries': 0}
        for query in queries:
            whole, segment = [query['modes'][mode][metric] for mode in MODES]
            if whole is None or segment is None:
                continue
            result['compared_queries'] += 1
            if math.isclose(whole, segment, rel_tol=0, abs_tol=1e-12):
                result['ties'] += 1
            else:
                result['segment_wins' if segment > whole else 'whole_track_wins'] += 1
        paired[metric] = result

    return {
        'schema': 'sonora-exploratory-evaluation-v1', 'status': 'evaluated_exploratory_pool_only',
        'split': rp.SPLIT, 'top_k': TOP_K, 'query_count': len(queries),
        'candidate_pairs': validation['candidate_pairs'],
        'distinct_tracks': len({row['track_id'] for query in pack['queries'] for row in query['candidates']}),
        'validation': validation,
        'input_sha256': {'source_report': expected_report_sha256,
                         'catalog': expected['provenance']['input_catalog_sha256'],
                         'judgments': pack_hash, 'rankings': rankings_hash},
        'evaluator_sha256': rp.digest(Path(__file__).read_bytes()),
        'validator_sha256': rp.digest(Path(rp.__file__).read_bytes()),
        'retrieval_provenance': expected['provenance'],
        'protocol': {'precision_positive_grade_min': 2, 'precision_denominator': TOP_K,
                     'gain': '2**relevance - 1', 'discount': 'log2(rank + 1)',
                     'ideal_pool': 'top5 of all judged union candidates for same query',
                     'zero_idcg': 'null; excluded from macro nDCG; included as zero P@5',
                     'ranking_order': 'frozen rankings.json array order; never package ID order',
                     'paired_tie_absolute_tolerance': 1e-12},
        'summary': summary, 'paired': paired, 'queries': queries,
        'limits': ['Exploratory pooled judgments, model suggestions visible; not blind or held-out.',
                   'Pooled nDCG can be high with few relevant candidates; see pool positive counts.',
                   'No full-corpus Recall, localization IoU, significance, model freeze or P95.',
                   'Judgment identity/listening and current media permissions are not verified.',
                   'Raw per-track rankings and grades are private local output only.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--report-sha256', required=True)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--pack-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.run_dir, args.catalog, args.report_sha256, args.pack, args.pack_sha256)
        rp.write_new(args.output, result)
        # Only aggregates in stdout; private per-track labels stay in the explicit output file.
        print(json.dumps({key: result[key] for key in ('status', 'query_count', 'summary', 'paired')}, indent=2))
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        parser.exit(1, 'Exploratory evaluation rejected: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

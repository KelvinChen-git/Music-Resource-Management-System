"""Development known-pair metrics with additional semantically unjudged candidates."""
from collections import defaultdict
import numpy as np
from review_pack import require

METRICS = ('R1', 'R5', 'MRR')


def paired(scores, query_tracks, candidate_tracks):
    scores = np.asarray(scores, dtype=np.float64)
    require(scores.shape == (len(query_tracks), len(candidate_tracks)) and scores.size
            and np.isfinite(scores).all(), 'Matching finite nonempty scores required')
    require(all(isinstance(t, str) and t for t in candidate_tracks)
            and len(set(candidate_tracks)) == len(candidate_tracks), 'Unique string candidates required')
    positions = {t: i for i, t in enumerate(candidate_tracks)}
    groups = defaultdict(list)
    for row, tid in zip(scores, query_tracks):
        require(tid in positions, 'Known paired recording absent')
        rank = sorted(range(len(row)), key=lambda i: (-float(row[i]), candidate_tracks[i])).index(positions[tid]) + 1
        groups[tid].append({'R1': float(rank == 1), 'R5': float(rank <= 5), 'MRR': 1 / rank})
    records = {tid: {k: float(np.mean([v[k] for v in values])) for k in METRICS}
               for tid, values in groups.items()}
    return {'recording_macro': {k: float(np.mean([v[k] for v in records.values()])) for k in METRICS},
            'query_macro': {k: float(np.mean([v[k] for values in groups.values() for v in values])) for k in METRICS},
            'per_recording': records, 'recordings': len(records), 'queries': len(query_tracks),
            'candidates': len(candidate_tracks), 'unqueried_candidates': len(candidate_tracks) - len(records),
            'scope': 'known_pair_only_unpaired_semantics_unjudged_development_not_final_test'}


def deltas(candidate, identity, iterations, seed):
    keys = sorted(identity['per_recording'])
    require(keys and set(keys) == set(candidate['per_recording'])
            and type(iterations) is int and iterations >= 1, 'Paired recording sets required')
    samples = np.random.default_rng(seed).integers(0, len(keys), size=(iterations, len(keys)))
    out = {}
    for k in METRICS:
        diff = np.array([candidate['per_recording'][t][k] - identity['per_recording'][t][k] for t in keys])
        require(np.isfinite(diff).all(), 'Finite paired differences required')
        lo, hi = np.quantile(diff[samples].mean(axis=1), [.025, .975])
        out[k] = {'mean_delta': float(diff.mean()), 'bootstrap95_lower': float(lo), 'bootstrap95_upper': float(hi),
                  'wins': int(np.sum(diff > 1e-12)), 'ties': int(np.sum(np.abs(diff) <= 1e-12)),
                  'losses': int(np.sum(diff < -1e-12))}
    return out


def mean_pair_cosine(vectors):
    from tag_adapter import unit
    z = unit(vectors)
    require(len(z) > 1, 'At least two vectors required')
    return float((np.square(z.sum(axis=0)).sum() - len(z)) / (len(z) * (len(z) - 1)))


def paired_cosine_mean(text, audio, query_tracks, candidate_tracks):
    """Equal recording weight, not equal caption count."""
    from tag_adapter import unit
    text, audio = unit(text), unit(audio)
    require(text.shape[1] == audio.shape[1] and len(text) == len(query_tracks)
            and len(audio) == len(candidate_tracks) and len(set(candidate_tracks)) == len(candidate_tracks), 'Cosine binding mismatch')
    index = {t: i for i, t in enumerate(candidate_tracks)}
    values = defaultdict(list)
    for z, t in zip(text, query_tracks):
        require(t in index, 'Missing paired audio')
        values[t].append(float(z @ audio[index[t]]))
    return float(np.mean([np.mean(v) for v in values.values()]))

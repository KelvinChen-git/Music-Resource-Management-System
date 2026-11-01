"""Recording-weighted audio-to-generated-text ridge and known-pair diagnostics."""
from collections import Counter, defaultdict
import numpy as np
from review_pack import require
from tag_adapter import unit


def recording_weights(ids):
    require(ids and all(isinstance(x, str) and x for x in ids), 'Recording identities required')
    counts = Counter(ids)
    return np.array([1/len(counts)/counts[x] for x in ids])


def fit(x, text, weights, recording_ids, alpha):
    x, text, weights = (np.asarray(v, dtype=np.float64) for v in (x, text, weights))
    require(x.ndim == text.ndim == 2 and x.shape == text.shape and x.size and len(x) == len(recording_ids)
            and weights.shape == (len(x),) and all(np.isfinite(z).all() for z in (x, text, weights))
            and np.all(weights > 0) and np.max(abs(weights-recording_weights(recording_ids))) < 1e-15
            and np.max(abs(np.linalg.norm(x, axis=1)-1)) < 1e-4 and np.max(abs(np.linalg.norm(text, axis=1)-1)) < 1e-4
            and type(alpha) in (int, float) and np.isfinite(alpha) and alpha > 0, 'Finite unit pairs and recording-equal weights required')
    n, d = x.shape; eye = np.eye(d); root = np.sqrt(weights)[:, None]
    z = root*x; residual = root*(text-x)
    w = eye+z.T@np.linalg.solve(z@z.T+alpha*np.eye(n), residual)
    before = float(np.sum(weights[:, None]*(x-text)**2))
    data = float(np.sum(weights[:, None]*(x@w-text)**2)); penalty = alpha*float(np.square(w-eye).sum())
    gradient = x.T@(weights[:, None]*(x@w-text))+alpha*(w-eye)
    error = float(np.max(abs(gradient)))
    require(np.isfinite(w).all() and data+penalty <= before+1e-12 and error < 1e-9, 'Weighted ridge normal equation failed')
    return w, {'objective_before': before, 'objective_after': data+penalty, 'weighted_squared_error_after': data,
               'identity_prior_penalty': penalty, 'alpha': alpha, 'normal_equation_max_abs_residual': error,
               'parameter_delta_frobenius': float(np.linalg.norm(w-eye)), 'parameter_count': int(w.size),
               'fit_intervals': n, 'fit_recordings': len(set(recording_ids)), 'solver': 'weighted_dual_closed_form',
               'closed_form_optimum_verified': True,
               'weighted_paired_cosine_before': float(np.sum(weights*np.sum(unit(x)*unit(text), axis=1))),
               'weighted_paired_cosine_after': float(np.sum(weights*np.sum(unit(x@w)*unit(text), axis=1)))}


def exact_interval_pairs(scores, recording_ids):
    """Diagonal pairs only; average within recording before macro across recordings."""
    scores = np.asarray(scores, dtype=np.float64); n = len(recording_ids)
    require(n > 0 and scores.shape == (n, n) and np.isfinite(scores).all(), 'Square finite exact-pair scores required')
    ranks = []; groups = defaultdict(list)
    for i, row in enumerate(scores):
        rank = sorted(range(n), key=lambda j: (-float(row[j]), j)).index(i)+1
        ranks.append(rank); groups[recording_ids[i]].append({'R1': float(rank == 1), 'R5': float(rank <= 5), 'MRR': 1/rank})
    per = {tid: {k: float(np.mean([x[k] for x in values])) for k in ('R1', 'R5', 'MRR')} for tid, values in groups.items()}
    return {'recording_macro': {k: float(np.mean([r[k] for r in per.values()])) for k in ('R1', 'R5', 'MRR')},
            'query_macro': {k: float(np.mean([x[k] for values in groups.values() for x in values])) for k in ('R1', 'R5', 'MRR')},
            'per_recording': per, 'ranks': ranks, 'recordings': len(per), 'queries': n, 'candidates': n,
            'scope': 'generated_exact_interval_pair_only_other_pairs_semantically_unjudged_not_human_test'}


def validation_metrics(audio, text, recording_ids, w):
    from expanded_caption_metrics import paired
    scores = unit(text)@unit(audio@w).T
    ids = sorted(set(recording_ids))
    recording_scores = np.stack([scores[:, [i for i, tid in enumerate(recording_ids) if tid == key]].max(axis=1) for key in ids], axis=1)
    return {'exact_interval': exact_interval_pairs(scores, recording_ids),
            'recording_max_interval': paired(recording_scores, recording_ids, ids)}

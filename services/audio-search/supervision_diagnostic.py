"""Descriptive lexical/geometry/known-pair diagnostics; never learns or labels relevance."""
from collections import Counter, defaultdict
import re
import unicodedata
import numpy as np
from review_pack import require
from tag_adapter import unit
from weighted_caption_adapter import recording_weights


def words(text):
    require(isinstance(text, str) and text.strip(), 'Nonempty original text required')
    result = re.findall(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", unicodedata.normalize('NFKC', text).casefold())
    require(result, 'English-word/number diagnostic tokens required; no unsupported text silently dropped')
    return result


def grams(tokens, n):
    return {tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)}


def summary(values, weights=None):
    a = np.asarray(values, dtype=np.float64)
    require(a.ndim == 1 and a.size and np.isfinite(a).all(), 'Finite nonempty scalar sample required')
    w = np.ones(len(a))/len(a) if weights is None else np.asarray(weights, dtype=np.float64)
    require(w.shape == a.shape and np.isfinite(w).all() and np.all(w > 0) and abs(w.sum()-1) < 1e-12, 'Normalized positive weights required')
    return {'mean': float(w@a), 'min': float(a.min()), 'median_unweighted': float(np.median(a)), 'max': float(a.max())}


def text_audit(texts, rows, *, n=5, prevalence=.2, near=.8):
    require(len(texts) == len(rows) > 0 and type(n) is int and n >= 2 and 0 < prevalence <= 1 and 0 < near <= 1, 'Fixed lexical policy required')
    tokens = [words(t) for t in texts]; sets = [grams(t, n) for t in tokens]
    train_ids = {r['id'] for r in rows if r['split'] == 'train'}
    require(train_ids, 'Training-only phrase dictionary required')
    owners = defaultdict(set)
    for r, g in zip(rows, sets):
        if r['split'] == 'train':
            for phrase in g: owners[phrase].add(r['id'])
    common = {g for g, ids in owners.items() if len(ids)/len(train_ids) >= prevalence}
    vocabulary = set().union(*(set(t) for t, r in zip(tokens, rows) if r['split'] == 'train'))
    fractions = []
    for t in tokens:
        covered = set()
        for i in range(len(t)-n+1):
            if tuple(t[i:i+n]) in common: covered.update(range(i, i+n))
        fractions.append(len(covered)/len(t))
    sentences = defaultdict(set)
    for i, (text, t, r) in enumerate(zip(texts, tokens, rows)):
        for sentence in re.split(r'(?<=[.!?])\s+', text.strip()):
            key = tuple(words(sentence)) if sentence.strip() else ()
            if len(key) >= n: sentences[key].add(r['id'])
    exact_pairs = []; near_pairs = []
    for i in range(len(rows)):
        for j in range(i+1, len(rows)):
            if tokens[i] == tokens[j]: exact_pairs.append((i, j))
            union = sets[i] | sets[j]
            if union and len(sets[i] & sets[j])/len(union) >= near: near_pairs.append((i, j))
    def pair_counts(pairs):
        cross = [(i, j) for i, j in pairs if rows[i]['id'] != rows[j]['id']]
        return {'all_interval_pairs': len(pairs), 'cross_recording_pairs': len(cross),
                'cross_recording_affected_recordings': len({rows[i]['id'] for pair in cross for i in pair})}
    splits = {}
    for split in ('train', 'validation'):
        ix = [i for i, r in enumerate(rows) if r['split'] == split]; q = recording_weights([rows[i]['id'] for i in ix])
        splits[split] = {'recordings': len({rows[i]['id'] for i in ix}), 'captions': len(ix),
                        'word_count': summary([len(tokens[i]) for i in ix], q),
                        'common_train_5gram_token_coverage': summary([fractions[i] for i in ix], q)}
    public = {'train_only_dictionary_recordings': len(train_ids), 'common_5gram_types': len(common),
              'exact_normalized_duplicates': pair_counts(exact_pairs), 'near_duplicate_5gram_jaccard': pair_counts(near_pairs),
              'repeated_sentence_types_across_recordings': sum(len(ids) > 1 for ids in sentences.values()), 'splits': splits,
              'scope': 'Repeated wording, not incorrect semantic labels; no edits or exclusions.'}
    private = {'exact_pairs': exact_pairs, 'near_pairs': near_pairs, 'coverage_by_interval': fractions,
               'common_5grams': [list(g) for g in sorted(common)]}
    return public, private, vocabulary


def geometry(x, ids):
    x = unit(x); q = recording_weights(ids); mean = q@x; centered = x-mean
    covariance = centered.T@(q[:, None]*centered)
    trace = float(np.trace(covariance)); square = float(np.square(covariance).sum())
    groups = [x[[i for i, tid in enumerate(ids) if tid == key]] for key in sorted(set(ids))]
    require(len(groups) >= 2, 'At least2 recordings required')
    within = [(float(np.square(z.sum(axis=0)).sum())-len(z))/(len(z)*(len(z)-1)) for z in groups if len(z) >= 2]
    means = np.stack([z.mean(axis=0) for z in groups]); n = len(means)
    cross = (float(np.square(means.sum(axis=0)).sum())-float(np.square(means).sum()))/(n*(n-1))
    return {'recordings': len(set(ids)), 'intervals': len(ids), 'mean_vector_norm': float(np.linalg.norm(mean)),
            'centered_variance_trace': trace, 'centered_participation_ratio': trace*trace/square if square > 1e-24 else 0.,
            'mean_within_recording_distinct_interval_cosine': float(np.mean(within)) if within else None,
            'recordings_with_multiple_intervals': len(within), 'recordings_with_one_interval': len(groups)-len(within),
            'mean_between_distinct_recordings_cosine': cross}


def ridge_attribution(x, text, ids, w, alpha=1.):
    x, text, w = (np.asarray(v, dtype=np.float64) for v in (x, text, w)); q = recording_weights(ids)
    require(x.ndim == text.ndim == w.ndim == 2 and x.shape == text.shape and len(x) == len(ids)
            and w.shape == (x.shape[1], x.shape[1]) and alpha > 0
            and all(np.isfinite(z).all() for z in (x, text, w)), 'Finite saved ridge model/pairs required')
    delta = w-np.eye(x.shape[1]); residual = text-x; mx = q@x; mr = q@residual
    g = x.T@(q[:, None]*residual); gm = np.outer(mx, mr); gc = g-gm
    normal = x.T@(q[:, None]*(x@delta))+alpha*delta-g
    total = float(np.square(delta).sum()); direction = mr/np.linalg.norm(mr) if np.linalg.norm(mr) > 1e-12 else np.zeros_like(mr)
    common_energy = float(np.square(delta@direction).sum())
    cosine = lambda a, b: float((a*b).sum()/np.sqrt(np.square(a).sum()*np.square(b).sum())) if np.any(a) and np.any(b) else 0.
    return {'delta_frobenius': float(np.sqrt(total)), 'normal_equation_maxabs': float(np.max(abs(normal))),
            'rhs_norm': float(np.linalg.norm(g)), 'mean_outer_rhs_norm': float(np.linalg.norm(gm)),
            'centered_rhs_norm': float(np.linalg.norm(gc)), 'mean_centered_rhs_cosine': cosine(gm, gc),
            'rhs_to_mean_cosine': cosine(g, gm),
            'saved_update_energy_in_common_residual_target_direction': common_energy/total if total > 1e-24 else 0.,
            'scope': 'Algebra of saved W and training normal-equation RHS; no solve or new candidate fit.'}


def score_contrasts(audio, text, ids, w):
    q = recording_weights(ids); x = unit(np.asarray(audio)@w); t = unit(text); scores = t@x.T
    require(scores.shape == (len(ids), len(ids)), 'Aligned known interval pairs required')
    labels = np.array(ids); target = np.diag(scores); other_mean = []; other_max = []; temporal = []; temporal_ix = []
    for i, row in enumerate(scores):
        other = labels != ids[i]; same = (labels == ids[i]) & (np.arange(len(ids)) != i)
        require(other.any(), 'At least2 recordings required')
        other_mean.append(float(row[other]@q[other]/q[other].sum())); other_max.append(float(row[other].max()))
        if same.any(): temporal.append(float(row[same].mean())); temporal_ix.append(i)
    temporal_weights = q[temporal_ix]/q[temporal_ix].sum() if temporal_ix else None
    return {'known_pair_cosine': float(q@target), 'other_recording_mean_cosine': float(q@other_mean),
            'known_minus_other_recording_mean': float(q@(target-other_mean)),
            'known_minus_best_other_recording': float(q@(target-other_max)),
            'known_minus_other_same_recording_interval_mean': float(temporal_weights@(target[temporal_ix]-temporal)) if temporal_ix else None,
            'temporal_comparison_recordings': len({ids[i] for i in temporal_ix}),
            'temporal_comparison_recording_fraction': float(q[temporal_ix].sum()),
            'scope': 'Alternatives semantically unjudged; contrasts are not relevance/negative-label accuracy.'}


def language_coverage(texts, ids, vocabulary, clap_lengths):
    require(len(texts) == len(ids) == len(clap_lengths), 'Text/recording/token bindings required')
    tokens = [words(t) for t in texts]; q = recording_weights(ids)
    return {'recordings': len(set(ids)), 'captions': len(texts),
            'word_count': summary([len(t) for t in tokens], q), 'CLAP_token_count': summary(clap_lengths, q),
            'word_occurrence_OOV_from_train': summary([sum(w not in vocabulary for w in t)/len(t) for t in tokens], q),
            'scope': 'Lexical coverage only; OOV or length difference does not establish semantic domain failure.'}


def mean_direction_cosine(a, a_ids, b, b_ids):
    ma = recording_weights(a_ids)@unit(a); mb = recording_weights(b_ids)@unit(b)
    require(np.linalg.norm(ma) > 1e-12 and np.linalg.norm(mb) > 1e-12, 'Nonzero means required')
    return float(ma@mb/np.linalg.norm(ma)/np.linalg.norm(mb))


def ranking_changes(text, audio, ids, targets, prior, expanded):
    require(len(ids) == len(set(ids)) and set(targets) <= set(ids), 'Unique bound candidate IDs required')
    orders = []; ranks = []; pairs = []
    for w in (prior, expanded):
        s = unit(text)@unit(np.asarray(audio)@w).T
        order = [sorted(range(len(ids)), key=lambda j: (-float(row[j]), ids[j])) for row in s]
        orders.append(order); ranks.append([o.index(ids.index(t))+1 for o, t in zip(order, targets)])
        pairs.append([s[i, ids.index(t)] for i, t in enumerate(targets)])
    return {'queries': len(targets), 'paired_rank_changed_queries': sum(a != b for a, b in zip(*ranks)),
            'top5_set_changed_queries': sum(set(a[:5]) != set(b[:5]) for a, b in zip(*orders)),
            'top5_order_changed_queries': sum(a[:5] != b[:5] for a, b in zip(*orders)),
            'full_order_changed_queries': sum(a != b for a, b in zip(*orders)),
            'paired_rank_threshold_R1_changed_queries': sum((a == 1) != (b == 1) for a, b in zip(*ranks)),
            'paired_rank_threshold_R5_changed_queries': sum((a <= 5) != (b <= 5) for a, b in zip(*ranks)),
            'private': {'prior_ranks': ranks[0], 'expanded_ranks': ranks[1], 'prior_pair_cosines': pairs[0], 'expanded_pair_cosines': pairs[1]}}

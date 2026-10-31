"""Explicit typed device features; parity failures cannot create a readable ready cache."""
from pathlib import Path
from collections import Counter
import numpy as np
import review_pack as rp
import tag_adapter as adapter
import device_calibration as calibration

VIEWS = {'tag_training': ('train_fullsong', 'fullsong_first_mid_last10s', 'train', 100),
         'tag_validation': ('validation_fullsong', 'fullsong_first_mid_last10s', 'validation', 20),
         'caption_retrieval': ('retrieval_first120', 'first120_first_mid_last10s', None, 140)}


def matrix(value, shape):
    z = np.asarray(value, dtype=np.float64)
    rp.require(z.ndim == 2 and z.shape == shape and z.size and np.isfinite(z).all()
               and np.all(np.abs(np.linalg.norm(z, axis=1)-1) <= 1e-4), 'Expected finite unit feature matrix')
    return z


def vector_parity(reference, actual, policy):
    reference = np.asarray(reference)
    a = matrix(reference, reference.shape); b = matrix(actual, reference.shape)
    delta = float(np.max(np.abs(a-b)))
    cosine = max(0., float(np.max(1-np.sum(adapter.unit(a)*adapter.unit(b), axis=1))))
    return {'status': 'passed' if delta <= policy['atol_vector_maxabs'] and cosine <= policy['atol_cosine_distance'] else 'failed',
            'max_abs_difference': delta, 'max_cosine_distance': cosine, 'vectors': len(a)}


def score_parity(reference, actual, policy):
    a, b = np.asarray(reference, dtype=float), np.asarray(actual, dtype=float)
    rp.require(a.ndim == 2 and a.shape == b.shape and a.size and np.isfinite(a).all() and np.isfinite(b).all(), 'Matching finite scores required')
    i, j = np.triu_indices(a.shape[1], 1)
    difference = a[:, i]-a[:, j]; other = b[:, i]-b[:, j]
    stable = np.abs(difference) > policy['stable_order_score_gap']
    flips = int(np.sum(stable & (difference*other <= 0)))
    delta = float(np.max(np.abs(a-b)))
    # Candidate inputs are in fixed source-ID order; stable sort handles exact ties.
    ar, br = np.argsort(-a, axis=1, kind='stable'), np.argsort(-b, axis=1, kind='stable')
    return {'status': 'passed' if delta <= policy['atol_score_maxabs'] and flips == 0 else 'failed',
            'score_max_abs_difference': delta, 'stable_pairs': int(stable.sum()),
            'stable_pair_flips': flips, 'near_tie_pairs': int(stable.size-stable.sum()),
            'queries_with_any_rank_change': int(np.any(ar != br, axis=1).sum()),
            'queries_with_top5_set_change': int(sum(set(x[:5]) != set(y[:5]) for x, y in zip(ar, br)))}


def ready_view(cache, cache_sha256, *, expected_device, expected_model_sha256, view):
    import holdout_contract as h
    rp.require(view in VIEWS, 'Explicit tag_training/tag_validation/caption_retrieval required')
    meta = h.assets.document(cache, cache_sha256)
    rp.require(meta['schema'] == 'sonora-typed-device-feature-cache-v1' and meta['status'] == 'ready_after_parity'
               and meta['device'] == expected_device and meta['model_sha256'] == expected_model_sha256
               and meta['key_context']['device'] == expected_device
               and meta['key_context']['model_sha256'] == expected_model_sha256
               and calibration.cache_key(**meta['key_context']) == meta['cache_key_sha256'], 'Ready cache/device/model identity differs')
    report = h.assets.document(Path(cache).parent/'result.json', meta['parity_report_sha256'])
    rp.require(report['status'] == 'passed' and report['ready_cache_written'] is True
               and report['cache_key_sha256'] == meta['cache_key_sha256'], 'Successful parity report required')
    rows = meta['rows']; ids = [r['source_track_id'] for r in rows]
    rp.require(len(rows) == len(set(ids)) == 140 and ids == sorted(ids)
               and set(meta['views']) == set(VIEWS)
               and Counter(r['split'] for r in rows) == {'train': 100, 'validation': 20, 'caption_dev': 20}, 'Complete canonical source identities required')
    key, recipe, split, count = VIEWS[view]; descriptor = meta['views'][view]
    positions = [i for i, row in enumerate(rows) if split is None or row['split'] == split]
    rp.require(descriptor == {'npz_key': key, 'recipe': recipe, 'row_indices': positions}
               and len(positions) == count, 'Typed feature view recipe/rows differ')
    path = Path(cache).parent/'features.npz'
    rp.require(h.file_hash(path) == meta['feature_sha256'], 'Ready feature bytes changed')
    with np.load(h.assets.regular(path), allow_pickle=False) as f:
        features = matrix(f[key], (count, 512)); prototypes = matrix(f['prototypes'], (183, 512))
        texts = matrix(f['texts'], (24, 512)) if view == 'caption_retrieval' else None
    selected = [rows[i] for i in positions]
    for row in selected:
        positive = row['positive_indices']
        rp.require(positive and len(set(positive)) == len(positive)
                   and all(type(i) is int and 0 <= i < 183 for i in positive), 'Observed tag indices required')
    result = {'view': view, 'device': meta['device'], 'model_sha256': meta['model_sha256'],
              'cache_key_sha256': meta['cache_key_sha256'], 'features': features, 'prototypes': prototypes,
              'source_track_ids': [r['source_track_id'] for r in selected],
              'positive_indices': [r['positive_indices'] for r in selected]}
    if texts is not None:
        dev = {r['source_track_id'] for r in rows if r['split'] == 'caption_dev'}
        rp.require(len(dev) == 20 and len(meta['query_tracks']) == 24 and set(meta['query_tracks']) == dev, 'Only original20 dev queries allowed')
        result.update(texts=texts, query_tracks=meta['query_tracks'])
    return result

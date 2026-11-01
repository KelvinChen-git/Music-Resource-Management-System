"""Explicit256-token text overlay on immutable MUS053 interval audio features."""
from pathlib import Path
import numpy as np
import holdout_contract as h
import device_calibration as calibration
import interval_feature_cache as intervals
from device_feature_cache import matrix

POLICY = 'exact_original_caption_RoBERTa256_no_truncation_no_filter'
SEED = 'MUS-055-short-long-training-controls-v1'
PARITY = {'CPU77_to_old77_controls', 'CPU256_to_MPS256_controls', 'all_short256_to_old77'}


def captions_for(candidates, rows):
    source = sorted(candidates['candidates'], key=lambda r: (int(r['id']), r['start_time'], r['end_time']))
    h.require(len(source) == len(rows) == 232, 'Exact232 original captions required')
    texts = []
    for candidate, row in zip(source, rows):
        h.require(all(candidate[k] == row[k] for k in ('id', 'start_time', 'end_time', 'label_source', 'raw_line_sha256'))
                  and h.digest(candidate['caption'].encode()) == row['caption_sha256'], 'Original caption identity/order differs')
        texts.append(candidate['caption'])
    return texts


def controls(rows, lengths, seed=SEED):
    h.require(len(rows) == len(lengths) and all(type(n) is int and 0 < n <= 256 for n in lengths), 'Lengths must fit256')
    groups = set(); result = {}
    for kind in ('short', 'long'):
        candidates = [i for i, row in enumerate(rows) if row['split'] == 'train' and (lengths[i] <= 77) == (kind == 'short')]
        order = sorted(candidates, key=lambda i: h.digest((seed+'|'+rows[i]['id']+'|'+str(rows[i]['start_sample'])).encode()))
        result[kind] = []
        for i in order:
            group = rows[i]['creator_component']
            if group not in groups:
                result[kind].append(i); groups.add(group)
            if len(result[kind]) == 3: break
        h.require(len(result[kind]) == 3, 'Three short and three long distinct train creators required')
    return result


def token_proof(encoded, raw_ids, length=256):
    """Check actual nonpadding tokens, not merely a reported string length."""
    ids, mask = np.asarray(encoded['input_ids']), np.asarray(encoded['attention_mask'])
    h.require(ids.shape == mask.shape == (len(raw_ids), length) and np.issubdtype(ids.dtype, np.integer)
              and np.issubdtype(mask.dtype, np.integer), 'Fixed256 integer tokens/masks required')
    proofs = []
    for values, keep, raw in zip(ids, mask, raw_ids):
        n = len(raw)
        h.require(2 <= n <= length and raw[0] == 0 and raw[-1] == 2
                  and np.array_equal(keep, np.r_[np.ones(n, dtype=int), np.zeros(length-n, dtype=int)])
                  and values[:n].tolist() == raw and np.all(values[n:] == 1), 'Truncated/changed tokens or invalid padding refused')
        proofs.append({'untruncated_tokens': n, 'encoded_nonpad_tokens': int(keep.sum()),
                       'input_ids_sha256': h.digest(h.canonical(raw))})
    return proofs


def ready_view(*, base_cache, base_sha256, text_cache, text_sha256, expected_device, expected_model_sha256, split):
    h.require(split in ('train', 'validation'), 'Explicit train/validation required')
    meta = h.assets.document(text_cache, text_sha256)
    h.require(meta['schema'] == 'sonora-long-caption-text-cache-v1' and meta['status'] == 'ready_after_parity'
              and meta['policy'] == POLICY and meta['token_length'] == 256 and meta['base_cache_sha256'] == base_sha256
              and meta['device'] == expected_device and meta['model_sha256'] == expected_model_sha256
              and meta['key_context']['device'] == expected_device and meta['key_context']['model_sha256'] == expected_model_sha256
              and calibration.cache_key(**meta['key_context']) == meta['cache_key_sha256'], 'Explicit overlay/base/model/device/length/key differs')
    base = h.assets.document(base_cache, base_sha256); rows = base['rows']
    h.require(meta['rows_sha256'] == h.digest(h.canonical(rows)) and meta['token_lengths'] == base['token_lengths']
              and meta['control_indices'] == controls(rows, meta['token_lengths']), 'Original rows/lengths/controls differ')
    report = h.assets.document(Path(text_cache).parent/'result.json', meta['result_sha256'])
    h.require(report['status'] == 'passed' and report['ready_cache_written'] is True and report['truncated_captions'] == 0
              and report['cache_key_sha256'] == meta['cache_key_sha256'] and report['captions'] == 232
              and set(report['vector_parity']) == PARITY and all(v['status'] == 'passed' for v in report['vector_parity'].values()),
              'Successful complete nontruncated parity report required')
    path = Path(text_cache).parent/'features.npz'
    h.require(h.file_hash(path) == meta['feature_sha256'], 'Overlay feature bytes changed')
    with np.load(h.assets.regular(path), allow_pickle=False) as f: text = matrix(f['text256'], (232, 512))
    result = intervals.ready_view(base_cache, base_sha256, expected_device=expected_device, expected_model_sha256=expected_model_sha256, split=split)
    positions = [i for i, row in enumerate(rows) if row['split'] == split]
    result['text77'] = result['text']; result['text'] = text[positions].copy()
    result['base_cache_key_sha256'] = result['cache_key_sha256']; result['cache_key_sha256'] = meta['cache_key_sha256']
    result['token_length'] = 256
    return result

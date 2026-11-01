"""Time-bound generated-caption pairs; explicit split reader without encoder imports."""
from collections import Counter, defaultdict
import math
from pathlib import Path
import numpy as np
import holdout_contract as h
import device_calibration as calibration
from device_feature_cache import matrix

RATE = 48000
WINDOW = 480000
RECIPE = 'inside_interval_first_middle_last10s_unique_starts_unit_mean_then_unit'
COUNTS = {'train_recordings': 37, 'train_components': 33, 'train_intervals': 209,
          'validation_recordings': 7, 'validation_components': 7, 'validation_intervals': 23}


def windows(start, end, samples):
    h.require(type(samples) is int and samples > 0 and all(type(v) in (int, float) and math.isfinite(v) for v in (start, end))
              and 0 <= start < end <= samples/RATE and 15 <= end-start <= 30, 'Finite 15..30s interval inside actual EOF required')
    lo, hi = round(start*RATE), round(end*RATE)
    h.require(0 <= lo < hi <= samples and hi-lo >= WINDOW, 'Sample bounds outside actual EOF')
    last = hi-WINDOW
    return lo, hi, sorted({lo, lo+(last-lo)//2, last})


def validate_rows(rows, expected=None):
    h.require(rows and all(r['split'] in ('train', 'validation') for r in rows), 'Only train/validation intervals allowed')
    keys = [(int(r['id']), r['start_sample'], r['end_sample']) for r in rows]
    h.require(keys == sorted(set(keys)), 'Unique canonical recording/interval order required')
    seen = {}; components = defaultdict(set); counts = {}; by = defaultdict(list)
    for row in rows:
        tid, split = row['id'], row['split']; by[(split, tid)].append(row)
        h.require(tid not in seen or seen[tid] == split, 'Recording crosses splits'); seen[tid] = split
        components[row['creator_component']].add(split)
        lo, hi, starts = windows(row['start_time'], row['end_time'], row['decoded_samples'])
        h.require((row['start_sample'], row['end_sample'], row['window_start_samples']) == (lo, hi, starts)
                  and row['label_source'] == 'model_generated', 'Exact interval recipe/generated label required')
        h.require(all(type(i) is int and i >= 0 for i in row['window_indices'])
                  and len(set(row['window_indices'])) == len(starts) == len(row['window_indices']), 'Window bindings differ')
    h.require(all(len(v) == 1 for v in components.values()), 'Creator component crosses splits')
    for split in ('train', 'validation'):
        subset = [r for r in rows if r['split'] == split]; ids = {r['id'] for r in subset}
        h.require(ids, 'Both splits required')
        counts.update({split+'_recordings': len(ids), split+'_intervals': len(subset),
                       split+'_components': len({r['creator_component'] for r in subset})})
        for tid in ids:
            group = by[(split, tid)]; weight = 1/len(ids)/len(group)
            h.require(all(type(r['weight']) in (int, float) and math.isfinite(r['weight']) and abs(r['weight']-weight) < 1e-15 for r in group),
                      'Equal recording then interval weights required')
            h.require(len({r['creator_component'] for r in group}) == 1
                      and all(a['end_sample'] <= b['start_sample'] for a, b in zip(group, group[1:])), 'Inconsistent recording group/overlap')
    h.require(expected is None or counts == expected, 'Frozen split capacity differs')
    return counts


def plan(candidates, allowlist, corpus, expected=COUNTS):
    h.require(candidates['label_source'] == 'model_generated' and candidates['training_ready'] is False, 'Unmodified generated candidates required')
    allowed = {r['id']: r for r in allowlist['records']}
    h.require(len(allowed) == len(allowlist['records']), 'Duplicate allowlist recording')
    proofs = {str(int(r['source_track_id'].split('_')[-1])): r for r in corpus['tracks']}
    h.require(len(proofs) == len(corpus['tracks']), 'Duplicate corpus recording')
    rows = []; captions = []; unique = []; lookup = {}
    source = sorted(candidates['candidates'], key=lambda r: (int(r['id']), r['start_time'], r['end_time']))
    occurrences = Counter(r['id'] for r in source)
    splits = {s: {r['id'] for r in source if allowed[r['id']]['split'] == s} for s in ('train', 'validation')}
    for r in source:
        a, p = allowed[r['id']], proofs[r['id']]
        h.require(a['split'] == p['split'] and a['audio_sha256'] == p['audio_sha256']
                  and a['pcm_sha256'] == p['decode']['pcm_sha256'] and r['label_source'] == 'model_generated', 'Allowlist split/audio/PCM differs')
        h.require(isinstance(r['caption'], str) and r['caption'].strip(), 'Exact nonempty caption required')
        lo, hi, starts = windows(r['start_time'], r['end_time'], p['decode']['decoded_samples'])
        indices = []
        for start in starts:
            key = (r['id'], start)
            if key not in lookup:
                lookup[key] = len(unique); unique.append({'id': r['id'], 'start_sample': start})
            indices.append(lookup[key])
        rows.append({k: r[k] for k in ('id', 'start_time', 'end_time', 'label_source', 'raw_line_sha256')})
        rows[-1].update(split=a['split'], creator_component=a['creator_component'],
                        source_track_id=p['source_track_id'], audio_sha256=p['audio_sha256'], pcm_sha256=a['pcm_sha256'],
                        decoded_samples=p['decode']['decoded_samples'], start_sample=lo, end_sample=hi,
                        window_start_samples=starts, window_indices=indices, caption_sha256=h.digest(r['caption'].encode()),
                        weight=1/len(splits[a['split']])/occurrences[r['id']])
        captions.append(r['caption'])
    counts = validate_rows(rows, expected)
    return rows, captions, unique, proofs, counts


def control_indices(rows, seed, count=3):
    order = sorted((i for i, r in enumerate(rows) if r['split'] == 'train'),
                   key=lambda i: h.digest((seed+'|'+rows[i]['id']+'|'+str(rows[i]['start_sample'])).encode()))
    selected = []; groups = set()
    for i in order:
        group = rows[i]['creator_component']
        if group not in groups:
            selected.append(i); groups.add(group)
        if len(selected) == count: break
    h.require(len(selected) == count, 'Not enough distinct train components for CPU controls')
    return selected


def token_summary(lengths):
    h.require(lengths and all(type(n) is int and n > 0 for n in lengths), 'Positive raw token lengths required')
    return {'captions': len(lengths), 'min_untruncated_tokens': min(lengths), 'max_untruncated_tokens': max(lengths),
            'truncated_at_77': sum(n > 77 for n in lengths), 'policy': 'SDK77tokens_exact_raw_caption_no_filter'}


def ready_view(cache, cache_sha256, *, expected_device, expected_model_sha256, split):
    h.require(split in ('train', 'validation'), 'Explicit train/validation split required')
    meta = h.assets.document(cache, cache_sha256)
    h.require(meta['schema'] == 'sonora-interval-feature-cache-v1' and meta['status'] == 'ready_for_bounded_pilot'
              and meta['device'] == expected_device and meta['model_sha256'] == expected_model_sha256
              and meta['key_context']['device'] == expected_device and meta['key_context']['model_sha256'] == expected_model_sha256
              and calibration.cache_key(**meta['key_context']) == meta['cache_key_sha256'] and meta['recipe'] == RECIPE,
              'Cache status/device/model/recipe/key differs')
    result = h.assets.document(Path(cache).parent/'result.json', meta['result_sha256'])
    h.require(result['status'] == 'passed' and result['ready_cache_written'] is True
              and result['cache_key_sha256'] == meta['cache_key_sha256'], 'Successful build report required')
    rows = meta['rows']; validate_rows(rows, COUNTS)
    h.require(token_summary(meta['token_lengths']) == result['tokenization'] and len(meta['token_lengths']) == len(rows), 'Tokenization receipt differs')
    controls = meta['control_indices']
    h.require(controls == control_indices(rows, 'MUS-053-fixed-train-controls-v1') and result['CPU_control_intervals'] == 3
              and set(result['vector_parity']) == {'windows', 'interval_audio', 'caption_text'}
              and all(v['status'] == 'passed' for v in result['vector_parity'].values()), 'Three successful train-only CPU controls required')
    path = Path(cache).parent/'features.npz'; h.require(h.file_hash(path) == meta['feature_sha256'], 'Feature bytes differ')
    positions = [i for i, r in enumerate(rows) if r['split'] == split]
    unique = meta['unique_windows']; canonical = sorted({(r['id'], s) for r in rows for s in r['window_start_samples']}, key=lambda x: (int(x[0]), x[1]))
    h.require([(r['id'], r['start_sample']) for r in unique] == canonical, 'Canonical unique windows differ')
    for row in rows:
        h.require([(unique[i]['id'], unique[i]['start_sample']) for i in row['window_indices']] == [(row['id'], s) for s in row['window_start_samples']], 'Window index mapping differs')
    with np.load(h.assets.regular(path), allow_pickle=False) as f:
        audio = matrix(f['audio'], (len(rows), 512)); text = matrix(f['text'], (len(rows), 512))
        matrix(f['windows'], (len(unique), 512))
        h.require(np.array_equal(f['weights'], np.array([r['weight'] for r in rows])), 'Stored weights differ')
        selected_audio, selected_text = audio[positions].copy(), text[positions].copy()
    return {'split': split, 'audio': selected_audio, 'text': selected_text,
            'weights': np.array([rows[i]['weight'] for i in positions]),
            'recording_ids': [rows[i]['id'] for i in positions], 'creator_components': [rows[i]['creator_component'] for i in positions],
            'cache_key_sha256': meta['cache_key_sha256'], 'label_source': 'model_generated'}

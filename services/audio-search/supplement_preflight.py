"""Fixed six-source metadata and exact-content checks; no text/model processing."""
import math
import numpy as np

import holdout_contract as h
import mtg_dataset as mtg
from corpus import window_bounds
from preprocess import prepare_window


def validate_config(cfg):
    h.require(cfg['schema'] == 'sonora-six-development-audio-preflight-v1'
              and cfg['task_directory'] == '.local/a/mus063'
              and cfg['fixed_recordings'] == 6 and cfg['fixed_validated_captions'] == 7
              and cfg['audio_base_url'] == 'https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/'
              and cfg['max_track_bytes'] == 20*1024*1024
              and cfg['max_total_body_bytes'] == 128*1024*1024
              and cfg['max_download_attempts_per_track'] == 1
              and cfg['duration_bounds_seconds'] == [30, 600]
              and cfg['max_actual_duration_delta_seconds'] == 2.
              and cfg['retrieval_clip_seconds'] == 120
              and cfg['automatic_replacements'] is False
              and cfg['operations'] == dict.fromkeys(('caption_bodies_extracted', 'encodes', 'models_loaded',
                    'fits', 'scores', 'reserved_test_audio', 'new_manual_labels'), 0),
              'Fixed six-source preflight without retry, replacement or models required')


def validate_selection(plan, allowed, base, names, licenses, hashes, test_ids):
    selected = plan['selected']
    h.require(plan['role'] == 'development_metadata_only' and len(selected) == 6
              and plan['summary']['validated_caption_queries'] == 7, 'Original six-source plan required')
    original = {r['source_track_id']: r for r in allowed}
    h.require(len(original) == 8, 'Original eight unused candidates required')
    for field in ('source_track_id', 'creator_component', 'work_key', 'audio_sha256'):
        h.require(len({r[field] for r in selected}) == 6, 'Selected source/group/work/content conflict')
    for row in selected:
        tid = row['source_track_id']
        h.require(tid in original and tid in test_ids and tid in base and tid in names,
                  'Unknown, non-test or unallocated supplement identity')
        for field in ('creator_component', 'work_key', 'audio_sha256', 'validated_caption_count'):
            h.require(row[field] == original[tid][field], 'Frozen unused source changed')
        b, n = base[tid], names[tid]
        low = b['path'].removesuffix('.mp3') + '.low.mp3'
        h.require(row['artist_id'] == b['artist_id'] == n['artist_id']
                  and row['artist_name'] == n['artist'] and row['title'] == n['title']
                  and row['work_key'] == mtg.norm(n['title'])
                  and row['path'] == b['path'] and row['official_low_path'] == low
                  and row['audio_sha256'] == hashes.get(low)
                  and row['duration_metadata_seconds'] == b['duration']
                  and row['audio_license'] == licenses.get(b['path'])
                  and row['audio_license']['family'] in ('by', 'by-sa'),
                  'Pinned per-track identity/rights/official hash mismatch')
    h.require(sum(r['validated_caption_count'] for r in selected) == 7, 'Frozen seven valid captions required')
    return selected


def prior_content(documents):
    records = []
    records.extend(documents['prior60']['tracks'])
    records.extend({'audio_sha256': r['audio_sha256'], 'pcm_sha256': r['decode']['pcm_sha256']}
                   for r in documents['prior140']['tracks'])
    records.extend({'audio_sha256': r['audio_sha256'], 'pcm_sha256': r['pcm_sha256']}
                   for r in documents['prior76']['records'])
    fetched = {r['source_track_id']: r for r in documents['pilot_fetched']['tracks']}
    for row in documents['pilot_decoded']['tracks']:
        h.require(row['source_track_id'] in fetched, 'Pilot fetch/decode identity mismatch')
        records.append({'audio_sha256': fetched[row['source_track_id']]['sha256'], 'pcm_sha256': row['pcm_sha256']})
    by_byte = {}
    for row in records:
        for field in ('audio_sha256', 'pcm_sha256'): h.rp.sha(row[field])
        h.require(row['audio_sha256'] not in by_byte or by_byte[row['audio_sha256']] == row['pcm_sha256'],
                  'Same old bytes have conflicting normalized PCM evidence')
        by_byte[row['audio_sha256']] = row['pcm_sha256']
    return {'bytes': set(by_byte), 'pcm': {r['pcm_sha256'] for r in records},
            'summary': {'record_references': len(records), 'unique_audio_hashes': len(by_byte),
                        'unique_pcm_hashes': len({r['pcm_sha256'] for r in records}),
                        'reused_references': len(records) - len(by_byte)}}


def check_duplicate(audio_sha256, pcm_sha256, prior, seen_bytes, seen_pcm):
    h.require(audio_sha256 not in prior['bytes'] and audio_sha256 not in seen_bytes,
              'Prior or new exact audio-byte duplicate')
    h.require(pcm_sha256 not in prior['pcm'] and pcm_sha256 not in seen_pcm,
              'Prior or new normalized PCM duplicate')


def inspect_audio(audio, metadata_seconds):
    h.require(isinstance(audio, np.ndarray) and audio.ndim == 1 and audio.dtype == np.float32
              and audio.flags.c_contiguous and 30*48000 <= len(audio) <= 600*48000
              and np.isfinite(audio).all() and np.any(audio != 0),
              'Expected finite nonempty30..600-second actual mono FP32 audio')
    h.require(isinstance(metadata_seconds, (float, int)) and not isinstance(metadata_seconds, bool)
              and math.isfinite(metadata_seconds)
              and abs(len(audio)/48000 - metadata_seconds) <= 2., 'Actual/source duration differs by more than2 seconds')
    slots = window_bounds(len(audio))
    h.require(slots[0][0] == 0 and slots[-1][1] == len(audio)
              and all(0 <= a < b <= len(audio) and b-a <= 480000 for a, b in slots), 'Invalid full-song window bounds')
    checks = []
    for start, end in (slots[0], slots[-1]):
        value, meta = prepare_window(audio[start:end], 48000)
        h.require(value.shape == (480000,) and np.isfinite(value).all()
                  and meta['real_samples'] == end-start and meta['padded_samples'] == 480000-(end-start)
                  and np.count_nonzero(value[end-start:]) == 0, 'Invalid first/tail padding')
        checks.append({'start_sample': start, 'end_sample': end,
                       'real_samples': end-start, 'padded_samples': 480000-(end-start)})
    clip = min(len(audio), 120*48000)
    return {'pcm_sha256': h.digest(audio.astype('<f4', copy=False).tobytes()),
            'duration_seconds': len(audio)/48000,
            'metadata_duration_delta_seconds': len(audio)/48000 - metadata_seconds,
            'whole_song_window_count': len(slots), 'first_tail_checks': checks,
            'retrieval_clip_samples': clip,
            'retrieval_clip_pcm_sha256': h.digest(audio[:clip].astype('<f4', copy=False).tobytes())}

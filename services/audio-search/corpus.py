"""Offline corpus checks and candidate retrieval rules, not a discovery API."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import librosa
import numpy as np
import soundfile as sf

from preprocess import SAMPLE_RATE, WINDOW_SAMPLES

HOP_SAMPLES = SAMPLE_RATE * 5
PIPELINE_VERSION = 'candidate-soundfile-soxr-mono-zero-10s-hop5s-v1'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_license(value):
    parsed = urlparse(value)
    if (parsed.scheme not in ('http', 'https') or parsed.hostname != 'creativecommons.org'
            or parsed.username or parsed.password or parsed.port not in (None, 443, 80)
            or parsed.query or parsed.fragment
            or not re.fullmatch(r'/licenses/by/(2\.0|2\.5|3\.0|4\.0)/', parsed.path)):
        raise ValueError('Expected a recorded CC BY license URL')
    return 'https://creativecommons.org' + parsed.path


def checked_assets(catalog_path, audio_root):
    """Read recorded evidence, never credentials or a provider API; fail closed."""
    root = Path(audio_root).resolve(strict=True)
    tracks = json.loads(Path(catalog_path).read_text())['audioTracks']
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 100:
        raise ValueError('Expected 1..100 recorded tracks')
    seen_ids, seen_sources, seen_hashes = set(), set(), set()
    assets = []
    for track in tracks:
        source_id, track_id = str(track['sourceId']), str(track['musicId'])
        if not all(re.fullmatch(r'[1-9][0-9]*', value) for value in (source_id, track_id)):
            raise ValueError('Track/source IDs must be positive decimal strings')
        if source_id in seen_sources or track_id in seen_ids:
            raise ValueError('Duplicate track/source identity')
        source_url = urlparse(track['sourceUrl'])
        if (source_url.scheme != 'https' or source_url.hostname != 'www.jamendo.com'
                or source_url.username or source_url.password or source_url.port not in (None, 443)
                or source_url.query or source_url.fragment
                or not re.fullmatch(r'/track/' + source_id + r'(?:/[^?#]*)?', source_url.path)):
            raise ValueError('Unexpected recorded source page')
        audio = root / (source_id + '.mp3')
        proof = root / (source_id + '.download.json')
        for path in (audio, proof):
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError('Asset/proof escapes read-only corpus root')
        if not 0 < audio.stat().st_size <= 30 * 1024 * 1024:
            raise ValueError('Audio file is empty or too large')
        evidence = json.loads(proof.read_text())
        digest = file_hash(audio)
        license_url = canonical_license(track['licenseUrl'])
        if (not re.fullmatch(r'[a-f0-9]{64}', track['sha256'])
                or digest != track['sha256'] or digest != evidence['sha256']
                or evidence['size'] != audio.stat().st_size
                or evidence['source'] != track['sourceUrl']
                or canonical_license(evidence['license']) != license_url):
            raise ValueError('Audio/catalog/download evidence mismatch for source ' + source_id)
        if digest in seen_hashes:
            raise ValueError('Duplicate audio content in candidate corpus')
        seen_sources.add(source_id); seen_ids.add(track_id); seen_hashes.add(digest)
        assets.append({
            'track_id': track_id, 'source_id': source_id, 'asset_filename': audio.name,
            'content_sha256': digest, 'bytes': audio.stat().st_size,
            'download_proof_sha256': file_hash(proof),
            'source_url': track['sourceUrl'], 'license_url': license_url,
            'title': track['title'], 'artist': track['artist'],
            'provider_duration_seconds': track['durationSeconds'],
        })
    return sorted(assets, key=lambda item: int(item['track_id']))


def decode_mono(path):
    """Decode actual MP3/WAV samples, bound allocations, resample once per track."""
    with sf.SoundFile(path) as source:
        if (source.format not in ('MP3', 'WAV', 'WAVEX') or source.channels not in (1, 2)
                or not 8000 <= source.samplerate <= 192000
                or not 0 < source.frames <= source.samplerate * 600):
            raise ValueError('Unsupported format/channels/rate/duration')
        info = {'format': source.format, 'source_frames': source.frames,
                'source_sample_rate_hz': source.samplerate, 'source_channels': source.channels}
        samples = source.read(dtype='float32', always_2d=True)
    if len(samples) != info['source_frames'] or not np.isfinite(samples).all():
        raise ValueError('Incomplete or nonfinite decoded audio')
    samples = samples.mean(axis=1)
    if info['source_sample_rate_hz'] != SAMPLE_RATE:
        expected = (len(samples) * SAMPLE_RATE + info['source_sample_rate_hz'] - 1) // info['source_sample_rate_hz']
        samples = librosa.resample(samples, orig_sr=info['source_sample_rate_hz'],
                                   target_sr=SAMPLE_RATE, res_type='soxr_hq', fix=False)
        samples = librosa.util.fix_length(samples, size=expected)
    if len(samples) < SAMPLE_RATE // 1000 or not np.isfinite(samples).all():
        raise ValueError('Decoded audio must have at least one finite millisecond')
    info.update(sample_rate_hz=SAMPLE_RATE, decoded_samples=len(samples),
                duration_ms=len(samples) * 1000 // SAMPLE_RATE)
    return np.ascontiguousarray(samples, dtype=np.float32), info


def window_bounds(sample_count):
    if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count <= 0:
        raise ValueError('Expected a positive integer sample count')
    if sample_count <= WINDOW_SAMPLES:
        return [(0, sample_count)]
    starts = list(range(0, sample_count - WINDOW_SAMPLES + 1, HOP_SAMPLES))
    windows = [(start, start + WINDOW_SAMPLES) for start in starts]
    if windows[-1][1] < sample_count:
        windows.append((starts[-1] + HOP_SAMPLES, sample_count))
    return windows


def unit_vectors(vectors):
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or not values.size or not np.isfinite(values).all():
        raise ValueError('Expected a finite nonempty vector matrix')
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 1e-12):
        raise ValueError('Zero/invalid embedding norm')
    return values / norms


def rank_segments(scores, segments, top_k=5):
    values = np.asarray(scores)
    if values.shape != (len(segments),) or not np.isfinite(values).all():
        raise ValueError('Score/segment mismatch')
    groups = {}
    for index in sorted(range(len(segments)), key=lambda i: (-float(values[i]), int(segments[i]['track_id']), segments[i]['start_sample'])):
        segment = segments[index]
        group = groups.setdefault(segment['track_id'], {'track_id': segment['track_id'], 'score': float(values[index]), 'segments': []})
        if len(group['segments']) >= 3:
            continue
        def overlap(other):
            intersection = max(0, min(segment['end_sample'], other['end_sample']) - max(segment['start_sample'], other['start_sample']))
            union = max(segment['end_sample'], other['end_sample']) - min(segment['start_sample'], other['start_sample'])
            return intersection / union
        if any(overlap(other) > 0.5 for other in group['segments']):
            continue
        group['segments'].append({**segment, 'score': float(values[index])})
    return sorted(groups.values(), key=lambda item: (-item['score'], int(item['track_id'])))[:top_k]

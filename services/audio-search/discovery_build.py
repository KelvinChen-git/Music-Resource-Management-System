"""Offline real-audio index producer. No downloads, database writes or activation."""
from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from urllib.parse import urlsplit

import numpy as np

from discovery_index import (CHECKPOINT_REVISION, CHECKPOINT_SHA256, ROBERTA_REVISION,
    MODEL_VERSION, PREPROCESSING_VERSION, SAMPLE_RATE, WINDOW_SAMPLES, MAX_BYTES,
    MAX_TRACKS, DiscoveryIndex, ClapTextEncoder, digest, fields, file_hash, matrix,
    regular, require, strict_json, track_id, window_bounds)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = ['services/audio-search/' + name for name in
    ('discovery_build.py', 'discovery_index.py', 'discovery_server.py', 'checkpoint_model.py',
     'probe.py', 'preprocess.py')] + ['scripts/build_discovery_index.py']


def private_path(path, slot, *, directory=False):
    require(slot in ('a', 'b'), 'Unknown development slot')
    path = Path(path).absolute()
    selected = ROOT / '.local' / slot
    require(not any(p.is_symlink() for p in (path, *path.parents))
            and path.resolve().is_relative_to(selected.resolve()) and path.resolve() != selected.resolve(),
            'Input/output must stay within this checkout and selected private slot')
    if directory:
        require(path.is_dir(), 'Private directory missing')
    return path.resolve()


def new_output(path, slot):
    path = private_path(path, slot)
    require(path.parent.is_dir(), 'Create the private output parent first')
    require(subprocess.run(['git', 'check-ignore', '--quiet', '--no-index', str(path)],
                           cwd=ROOT, capture_output=True).returncode == 0, 'Output must be ignored')
    path.mkdir(mode=0o700)  # No reuse of successful, failed or partial runs.
    path.chmod(0o700)
    return path


def write_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(raw)
    return hashlib.sha256(raw).hexdigest()


def basename(name):
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ ()-]{0,179}', name)
            and name == Path(name).name and name not in ('.', '..'), 'Invalid asset basename')
    return name


def checked_catalog(path, audio_root):
    pins = {}

    def read(path, limit):
        path = regular(path)
        require(0 < path.stat().st_size <= limit, 'Asset size outside bounds')
        raw = path.read_bytes()
        require(0 < len(raw) <= limit, 'Asset changed during read')
        pin = hashlib.sha256(raw).hexdigest()
        if path in pins:
            require(pins[path] == pin, 'Shared evidence changed during preflight')
        pins[path] = pin
        return raw

    path = regular(path)
    document = strict_json(read(path, 16 * 1024 * 1024))
    fields(document, ('schema', 'tracks'))
    require(document['schema'] == 'sonora-discovery-catalog-v1' and isinstance(document['tracks'], list)
            and 0 < len(document['tracks']) <= MAX_TRACKS, 'Invalid discovery catalog')
    rows, identities, contents, filenames = [], set(), set(), set()
    for row in document['tracks']:
        fields(row, ('track_id', 'audio_filename', 'content_bytes', 'content_md5', 'content_sha256',
                     'proof_filename', 'proof_sha256'))
        tid = track_id(row['track_id'])
        require(tid not in identities and row['audio_filename'] not in filenames,
                'Duplicate track or file identity')
        require(type(row['content_bytes']) is int and 0 < row['content_bytes'] <= MAX_BYTES)
        digest(row['content_md5'], 32); digest(row['content_sha256']); digest(row['proof_sha256'])
        audio = audio_root / basename(row['audio_filename'])
        require(audio.suffix.lower() == '.mp3', 'Only MP3 resources are supported')
        raw = read(audio, MAX_BYTES)
        require(len(raw) == row['content_bytes'] and hashlib.md5(raw).hexdigest() == row['content_md5']
                and pins[audio] == row['content_sha256'], 'Audio/catalog content mismatch')
        require(pins[audio] not in contents, 'Duplicate source bytes in this index')
        proof_path = audio_root / basename(row['proof_filename'])
        proof = strict_json(read(proof_path, 4 * 1024 * 1024))
        require(pins[proof_path] == row['proof_sha256'], 'Source proof pin mismatch')
        fields(proof, ('schema', 'track_id', 'source_url', 'license_url', 'title', 'artist',
                       'attribution', 'changes', 'content_bytes', 'content_md5', 'content_sha256', 'evidence'))
        require(proof['schema'] == 'sonora-discovery-source-proof-v1'
                and all(proof[k] == row[k] for k in ('track_id', 'content_bytes', 'content_md5', 'content_sha256')),
                'Source proof content/identity mismatch')
        require(isinstance(proof['source_url'], str), 'Source URL required')
        source = urlsplit(proof['source_url'])
        require(source.scheme == 'https' and source.hostname and not source.username and not source.password
                and source.port in (None, 443) and not source.fragment
                and proof['license_url'] == 'https://creativecommons.org/licenses/by/4.0/',
                'Explicit credential-free source and CC BY4 record required')
        for key in ('title', 'artist', 'attribution', 'changes'):
            require(isinstance(proof[key], str) and 0 < len(proof[key].strip()) <= 1000,
                    'Source identity/attribution missing')
        evidence = proof['evidence']
        require(isinstance(evidence, list) and 1 <= len(evidence) <= 8, 'Source evidence required')
        evidence_names = set()
        for item in evidence:
            fields(item, ('filename', 'sha256'))
            name = basename(item['filename']); digest(item['sha256'])
            require(name not in evidence_names and name not in (audio.name, proof_path.name),
                    'Evidence must name independent snapshots')
            evidence_names.add(name)
            item_path = audio_root / name
            read(item_path, 4 * 1024 * 1024)
            require(pins[item_path] == item['sha256'], 'Source evidence pin mismatch')
        rows.append({**row, 'path': audio, 'source': proof})
        identities.add(tid); filenames.add(row['audio_filename']); contents.add(row['content_sha256'])
    return sorted(rows, key=lambda r: int(r['track_id'])), pins, pins[path]


def decode_audio(path):
    """Read out-buffer blocks to EOF, bypassing estimated MP3 header clamping."""
    import librosa
    import soundfile as sf

    with sf.SoundFile(path) as source:
        rate, channels, declared = source.samplerate, source.channels, source.frames
        require(source.format == 'MP3' and type(rate) is int and 8000 <= rate <= 192000
                and type(channels) is int and channels in (1, 2)
                and type(declared) is int and 0 < declared <= rate * 600 and source.tell() == 0,
                'Unsupported MP3 format/rate/channels/declared duration')
        buffer = np.empty((65536, channels), dtype=np.float32)
        parts, frames = [], 0
        while True:
            before = source.tell()
            block = source.read(frames=65536, out=buffer)
            after = source.tell()
            require(isinstance(block, np.ndarray) and block.dtype == np.float32
                    and block.ndim == 2 and block.shape[1] == channels
                    and len(block) <= 65536 and np.isfinite(block).all()
                    and before == frames and after - before == len(block), 'Invalid actual-EOF decoder output')
            if not len(block):
                break
            frames += len(block)
            require(frames <= rate * 600, 'Actual audio exceeds duration cap')
            parts.append(block.copy())
    require(frames > 0, 'Empty decoded audio')
    mono = np.concatenate(parts).mean(axis=1)
    expected = (frames * SAMPLE_RATE + rate - 1) // rate
    if rate != SAMPLE_RATE:
        mono = librosa.resample(mono, orig_sr=rate, target_sr=SAMPLE_RATE, res_type='soxr_hq', fix=False)
        mono = librosa.util.fix_length(mono, size=expected)
    require(len(mono) == expected and expected >= SAMPLE_RATE // 1000
            and np.isfinite(mono).all(), 'Invalid resampled audio or sub-millisecond source')
    mono = np.ascontiguousarray(mono, dtype=np.float32)
    info = {'source_frames': frames, 'declared_source_frames': declared,
            'source_sample_rate_hz': rate, 'source_channels': channels,
            'decoded_samples': len(mono), 'duration_ms': len(mono) * 1000 // SAMPLE_RATE,
            'pcm_sha256': hashlib.sha256(mono.astype('<f4', copy=False).tobytes()).hexdigest()}
    return mono, info


def runtime_identity():
    packages = {}
    for name in ('numpy', 'soundfile', 'librosa', 'soxr', 'torch', 'torchaudio', 'torchvision',
                 'transformers', 'laion-clap'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {'python': platform.python_version(), 'packages': packages,
            'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))}


def build(catalog, audio_root, checkpoint, offline_cache, output, index_version, slot='b', batch_size=2):
    require(type(batch_size) is int and 1 <= batch_size <= 4, 'Batch size must be 1..4')
    require(isinstance(index_version, str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,160}', index_version),
            'Explicit index version required')
    # The fresh-output guard precedes all decoding/model construction, including retries.
    output = new_output(output, slot)
    started = time.monotonic()
    try:
        catalog = regular(private_path(catalog, slot))
        audio_root = private_path(audio_root, slot, directory=True)
        checkpoint = regular(private_path(checkpoint, slot))
        offline_cache = private_path(offline_cache, slot, directory=True)
        rows, pins, catalog_sha = checked_catalog(catalog, audio_root)
        source_files = {name: file_hash(ROOT / name) for name in SOURCE_FILES}
        source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        encoder = ClapTextEncoder(checkpoint, offline_cache)
        write_json(output / 'model-ready.json', {'encoder_class': type(encoder).__name__,
                   'checkpoint': getattr(encoder, 'checkpoint_meta', None),
                   'offline_cache_files': encoder.cache_fingerprints})
        tracks, segments, blocks, whole, proofs = [], [], [], [], []
        for row in rows:
            samples, info = decode_audio(row['path'])
            bounds = window_bounds(len(samples))
            require(len(segments) + len(bounds) <= 100000, 'Index segment cap exceeded')
            track_vectors, windows = [], []
            for offset in range(0, len(bounds), batch_size):
                batch = bounds[offset:offset + batch_size]
                waveforms = np.zeros((len(batch), WINDOW_SAMPLES), dtype=np.float32)
                for i, (start, end) in enumerate(batch):
                    waveforms[i, :end - start] = samples[start:end]
                    sid = row['track_id'] + ':' + str(start) + ':' + str(end)
                    windows.append({'segment_id': sid, 'start_sample': start, 'end_sample': end,
                                    'padded_samples': WINDOW_SAMPLES - (end - start)})
                    segments.append({'track_id': row['track_id'], 'segment_id': sid,
                                     'start_ms': start * 1000 // SAMPLE_RATE, 'end_ms': end * 1000 // SAMPLE_RATE})
                vector = matrix(encoder.encode_audio(waveforms), (len(batch), 512)).astype(np.float32)
                track_vectors.append(vector)
            vectors = np.concatenate(track_vectors)
            mean = vectors.mean(axis=0, dtype=np.float64)
            require(np.linalg.norm(mean) > 1e-12, 'Invalid whole-track mean')
            whole.append((mean / np.linalg.norm(mean)).astype(np.float32)); blocks.append(vectors)
            track = {k: row[k] for k in ('track_id', 'content_bytes', 'content_md5', 'content_sha256')}
            track['duration_ms'] = info['duration_ms']; tracks.append(track)
            proofs.append({**track, **info, 'source_proof_sha256': row['proof_sha256'],
                           'evidence_sha256': [e['sha256'] for e in row['source']['evidence']], 'windows': windows})
            write_json(output / ('track-progress-' + row['track_id'] + '.json'),
                       {'track_id': row['track_id'], 'decoded_samples': len(samples),
                        'duration_ms': info['duration_ms'], 'encoded_segments': len(bounds)})
        for path, pin in pins.items():
            require(file_hash(path) == pin, 'Input or evidence changed during encoding')
        require({name: file_hash(ROOT / name) for name in SOURCE_FILES} == source_files,
                'Builder source changed during encoding')
        encoder.verify_assets()
        features = output / 'features.npz'
        descriptor = os.open(features, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as target:
            np.savez(target, segments=np.concatenate(blocks), whole=np.stack(whole))
        require(features.stat().st_size <= 512 * 1024 * 1024, 'Index feature size cap exceeded')
        feature_sha = file_hash(features)
        proof = {'schema': 'sonora-discovery-build-proof-v1', 'status': 'complete', 'engine_kind': 'clap_identity',
                 'index_version': index_version, 'model_version': MODEL_VERSION,
                 'checkpoint_sha256': CHECKPOINT_SHA256, 'checkpoint_revision': CHECKPOINT_REVISION,
                 'roberta_revision': ROBERTA_REVISION, 'preprocessing_version': PREPROCESSING_VERSION,
                 'catalog_sha256': catalog_sha, 'feature_sha256': feature_sha,
                 'offline_cache_files': encoder.cache_fingerprints,
                 'source_sha': source_sha, 'source_files': source_files,
                 'runtime': runtime_identity(), 'tracks': proofs}
        proof_sha = write_json(output / 'build-proof.json', proof)
        manifest = {'schema': 'sonora-discovery-index-v1', 'index_version': index_version,
                    'model_version': MODEL_VERSION, 'engine_kind': 'clap_identity', 'dimension': 512,
                    'feature_sha256': feature_sha, 'build_proof_sha256': proof_sha,
                    'tracks': tracks, 'segments': segments}
        pending = output / 'manifest.pending.json'
        manifest_sha = write_json(pending, manifest)
        DiscoveryIndex(pending)  # Run the exact consumer, before activating a manifest.
        result = {'status': 'built_real_audio_index', 'engine_kind': 'clap_identity',
                  'index_version': index_version, 'model_version': MODEL_VERSION,
                  'tracks': len(tracks), 'segments': len(segments), 'manifest_sha256': manifest_sha,
                  'feature_sha256': feature_sha, 'build_proof_sha256': proof_sha,
                  'elapsed_ms': (time.monotonic() - started) * 1000}
        write_json(output / 'result.json', result)
        pending.rename(output / 'manifest.json')
        return result
    except Exception as error:
        write_json(output / 'failure.json', {'status': 'failed', 'error_type': type(error).__name__,
                   'message': str(error)[:300], 'manifest_activated': False})
        raise

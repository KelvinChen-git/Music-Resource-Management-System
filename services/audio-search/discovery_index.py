"""Immutable, versioned exact retrieval. No SDK imports until explicitly selected."""
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np

MAX_TRACKS = 5000
MAX_BYTES = 30 * 1024 * 1024
MODEL_VERSION = 'clap-A-fae3e9c0-identity-fulltext256-v1'
CHECKPOINT_SHA256 = 'fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd'


class DiscoveryError(Exception):
    def __init__(self, status, kind, message):
        super().__init__(message)
        self.status, self.kind, self.message = status, kind, message


def require(value, message='Invalid discovery input', status=400, kind='invalid_input'):
    if not value:
        raise DiscoveryError(status, kind, message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def bad_constant(_):
        raise ValueError('nonfinite JSON')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError):
        raise DiscoveryError(400, 'invalid_json', 'Invalid JSON') from None


def fields(obj, required, optional=()):
    require(isinstance(obj, dict) and set(required) <= set(obj)
            and set(obj) <= set(required) | set(optional))


def track_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,18}', value)
            and int(value) <= 9223372036854775807, 'Canonical positive track ID required')
    return value


def digest(value, length=64):
    require(isinstance(value, str) and re.fullmatch('[a-f0-9]{%d}' % length, value), 'Invalid content digest')
    return value


def regular(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents))
            and path.is_file() and path.stat().st_nlink == 1, 'Index input must be a regular file')
    return path


def file_hash(path):
    with regular(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def matrix(value, shape):
    value = np.asarray(value)
    require(value.shape == shape and np.issubdtype(value.dtype, np.floating)
            and np.isfinite(value).all(), 'Invalid feature matrix')
    value = value.astype(np.float64)
    norms = np.linalg.norm(value, axis=1, keepdims=True)
    require(np.all(np.abs(norms - 1) <= 1e-4), 'Unit vectors required')
    return value / norms


class DiscoveryIndex:
    def __init__(self, manifest):
        path = regular(manifest)
        require(0 < path.stat().st_size <= 32 * 1024 * 1024, 'Index manifest size outside bounds')
        meta = strict_json(path.read_bytes())
        fields(meta, ('schema', 'index_version', 'model_version', 'engine_kind', 'dimension',
                      'feature_sha256', 'tracks', 'segments'), ('fixture_queries',))
        require(meta['schema'] == 'sonora-discovery-index-v1' and meta['dimension'] == 512)
        for key in ('index_version', 'model_version'):
            require(isinstance(meta[key], str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,160}', meta[key]))
        require(meta['engine_kind'] in ('clap_identity', 'synthetic_fixture'))
        if meta['engine_kind'] == 'clap_identity':
            require(meta['model_version'] == MODEL_VERSION and 'fixture_queries' not in meta,
                    'Frozen identity/fulltext model required')
        require(isinstance(meta['tracks'], list) and 0 < len(meta['tracks']) <= MAX_TRACKS)
        require(isinstance(meta['segments'], list) and 0 < len(meta['segments']) <= 100000)
        tracks, positions = {}, {}
        for i, row in enumerate(meta['tracks']):
            fields(row, ('track_id', 'duration_ms', 'content_bytes', 'content_md5', 'content_sha256'))
            tid = track_id(row['track_id'])
            require(tid not in tracks, 'Duplicate indexed track')
            require(type(row['duration_ms']) is int and 0 < row['duration_ms'] <= 2147483647)
            require(type(row['content_bytes']) is int and 0 < row['content_bytes'] <= MAX_BYTES)
            digest(row['content_md5'], 32); digest(row['content_sha256'])
            tracks[tid], positions[tid] = dict(row), i
        seen, ranges, indices = set(), set(), {tid: [] for tid in tracks}
        for i, row in enumerate(meta['segments']):
            fields(row, ('track_id', 'segment_id', 'start_ms', 'end_ms'))
            tid = track_id(row['track_id'])
            require(tid in tracks and isinstance(row['segment_id'], str)
                    and re.fullmatch(r'[A-Za-z0-9._:-]{1,100}', row['segment_id']))
            start, end = row['start_ms'], row['end_ms']
            require(type(start) is int and type(end) is int and 0 <= start < end <= tracks[tid]['duration_ms'],
                    'Invalid segment time')
            require(row['segment_id'] not in seen and (tid, start, end) not in ranges, 'Duplicate segment')
            seen.add(row['segment_id']); ranges.add((tid, start, end)); indices[tid].append(i)
        require(all(indices.values()), 'Every track needs a segment')
        features = regular(path.parent / 'features.npz')
        require(features.stat().st_size <= 512 * 1024 * 1024
                and file_hash(features) == digest(meta['feature_sha256']), 'Feature pin mismatch')
        with np.load(features, allow_pickle=False) as stored:
            require(set(stored.files) == {'segments', 'whole'}, 'Unexpected feature fields')
            segments = matrix(stored['segments'], (len(meta['segments']), 512))
            whole = matrix(stored['whole'], (len(tracks), 512))
        require(file_hash(features) == meta['feature_sha256'], 'Feature bytes changed during load')
        for tid, group in indices.items():
            mean = segments[group].mean(axis=0)
            norm = np.linalg.norm(mean)
            require(norm > 1e-12 and np.max(np.abs(mean / norm - whole[positions[tid]])) <= 1e-5,
                    'Whole vector differs from identity mean recipe')
        segments.flags.writeable = whole.flags.writeable = False
        self.meta, self.tracks, self.positions, self.indices = meta, tracks, positions, indices
        self.segments, self.whole = segments, whole

    def search(self, body, encoder):
        fields(body, ('query_text', 'allowed_tracks', 'retrieval_mode', 'top_k', 'index_version', 'model_version'))
        require(body['index_version'] == self.meta['index_version']
                and body['model_version'] == self.meta['model_version'], 'Index/model version unavailable', 503, 'version_mismatch')
        require(body['retrieval_mode'] in ('segment', 'whole_track'), 'Unsupported retrieval mode')
        text, top = body['query_text'], body['top_k']
        require(isinstance(text, str) and 0 < len(text.strip()) <= 1000, 'Nonempty query of at most1000 characters required')
        require(type(top) is int and 1 <= top <= 20)
        require(isinstance(body['allowed_tracks'], list) and len(body['allowed_tracks']) <= MAX_TRACKS)
        allowed, seen = [], set()
        for row in body['allowed_tracks']:
            fields(row, ('track_id', 'content_md5', 'content_bytes'))
            tid = track_id(row['track_id']); digest(row['content_md5'], 32)
            require(tid not in seen and type(row['content_bytes']) is int and 0 < row['content_bytes'] <= MAX_BYTES)
            seen.add(tid)
            indexed = self.tracks.get(tid)
            if indexed and all(indexed[k] == row[k] for k in ('content_md5', 'content_bytes')):
                allowed.append(tid)
        opening = time.perf_counter()
        result = {'index_version': self.meta['index_version'], 'model_version': self.meta['model_version'],
                  'engine_kind': self.meta['engine_kind'], 'retrieval_mode': body['retrieval_mode'], 'results': []}
        if not allowed:
            result['timings_ms'] = {'query_encoding': 0., 'retrieval': 0.}
            return result
        query = matrix(encoder.encode(text.strip()), (1, 512))[0]
        encoded = time.perf_counter()
        ranked = []
        for tid in allowed:
            group = self.indices[tid]
            scores = self.segments[group] @ query
            order = sorted(range(len(group)), key=lambda j: (-float(scores[j]),
                           self.meta['segments'][group[j]]['start_ms'], self.meta['segments'][group[j]]['segment_id']))
            selected = []
            for j in order:
                row = self.meta['segments'][group[j]]
                if any(max(row['start_ms'], s['start_ms']) < min(row['end_ms'], s['end_ms']) for s in selected):
                    continue
                selected.append({**row, 'score': float(np.clip(scores[j], -1, 1))})
                if len(selected) == 3:
                    break
            score = float(self.whole[self.positions[tid]] @ query) if body['retrieval_mode'] == 'whole_track' else float(scores.max())
            ranked.append({**self.tracks[tid], 'score': float(np.clip(score, -1, 1)),
                           'segments': [{k: v for k, v in s.items() if k != 'track_id'} for s in selected]})
        result['results'] = sorted(ranked, key=lambda r: (-r['score'], int(r['track_id'])))[:top]
        result['timings_ms'] = {'query_encoding': (encoded - opening) * 1000,
                                'retrieval': (time.perf_counter() - encoded) * 1000}
        return result


class FixtureEncoder:
    """Explicit synthetic query lookup, never a semantic fallback."""
    def __init__(self, index, *, enabled=False):
        require(enabled and index.meta['engine_kind'] == 'synthetic_fixture', 'Synthetic encoder requires explicit opt-in', 503)
        self.queries = index.meta.get('fixture_queries', {})
        require(isinstance(self.queries, dict) and 0 < len(self.queries) <= 8)
        for text, vector in self.queries.items():
            require(isinstance(text, str) and 0 < len(text) <= 1000)
            matrix(np.asarray([vector], dtype=float), (1, 512))

    def encode(self, text):
        require(text in self.queries, 'Synthetic mode only supports its documented fixture queries', 503, 'fixture_query_unavailable')
        return np.asarray([self.queries[text]], dtype=np.float32)


class ClapTextEncoder:
    """Frozen A checkpoint; full256 tokens with no truncation or network fallback."""
    def __init__(self, checkpoint, offline_cache):
        import os
        require(Path(offline_cache).is_dir(), 'Offline model cache unavailable', 503, 'model_unavailable')
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_CACHE=str(Path(offline_cache).absolute()))
        try:
            import torch
            from checkpoint_model import load_checkpoint
            self.torch = torch
            torch.set_num_threads(2)
            self.sdk, _ = load_checkpoint(checkpoint, 'A')
            require(self.sdk.model.text_branch_type == 'roberta'
                    and self.sdk.model.text_branch.config.max_position_embeddings >= 258, 'Fulltext positional capacity unavailable', 503)
            for parameter in self.sdk.model.parameters():
                parameter.requires_grad_(False)
                require(str(parameter.device) == 'cpu' and (not parameter.is_floating_point() or parameter.dtype == torch.float32),
                        'Frozen CPU FP32 model required', 503)
        except ImportError:
            raise DiscoveryError(503, 'model_unavailable', 'CLAP dependencies unavailable') from None

    def encode(self, text):
        raw = self.sdk.tokenize(text, truncation=False)['input_ids']
        require(2 <= len(raw) <= 256, 'Complete query exceeds256 tokens', 400, 'query_tokens_exceeded')
        tokenizer = lambda batch: self.sdk.tokenize(batch, padding='max_length', truncation=False,
                                                   max_length=256, return_tensors='pt')
        with self.torch.inference_mode():
            return self.sdk.get_text_embedding([text], tokenizer=tokenizer, use_tensor=False)

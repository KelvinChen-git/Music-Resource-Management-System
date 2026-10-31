"""Pure numerical acceptance for an isolated frozen-encoder device calibration."""
import hashlib
import json
import re
import numpy as np
from review_pack import require


def device_status(request, inventory, *, mps_fallback=False):
    require(request in ('cpu', 'mps', 'cuda:0'), 'Explicit cpu/mps/cuda:0 required; no auto device')
    if not inventory.get('torch_available'):
        return {'status': 'blocked', 'reason': 'torch_not_installed', 'device': request}
    if request == 'mps':
        require(not mps_fallback, 'MPS CPU fallback must be disabled')
        ready = inventory.get('mps_available', False)
    elif request == 'cuda:0':
        ready = bool(inventory.get('cuda_build') and inventory.get('cuda_available') and inventory.get('cuda_count', 0) > 0)
    else:
        ready = True
    return {'status': 'ready' if ready else 'blocked', 'reason': None if ready else 'requested_device_unavailable', 'device': request}


def cache_key(*, device, environment, model_sha256, input_sha256, recipe_sha256, source_sha256):
    require(device in ('cpu', 'mps', 'cuda:0'), 'Explicit cache device required')
    values = [model_sha256, input_sha256, recipe_sha256, *source_sha256.values()]
    require(all(isinstance(x, str) and re.fullmatch('[a-f0-9]{64}', x) for x in values), 'Cache digests required')
    raw = json.dumps({'device': device, 'environment': environment, 'model': model_sha256,
                      'input': input_sha256, 'recipe': recipe_sha256, 'source': source_sha256}, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def valid_vectors(x, shape):
    z = np.asarray(x, dtype=np.float64)
    require(z.shape == shape and np.isfinite(z).all() and np.all(np.abs(np.linalg.norm(z, axis=1)-1) <= 1e-4),
            'Expected finite unit feature matrix')
    return z


def compare(reference_audio, reference_text, actual_audio, actual_text, policy):
    from tag_adapter import unit
    shape_a = (policy['audio_windows'], policy['dimension']); shape_t = (policy['text_prompts'], policy['dimension'])
    ra = valid_vectors(reference_audio, shape_a); rt = valid_vectors(reference_text, shape_t)
    aa = valid_vectors(actual_audio, shape_a); at = valid_vectors(actual_text, shape_t)
    require(len(ra) == 3 * policy['audio_tracks'], 'Exactly three windows per track required')
    vector_abs = max(float(np.max(np.abs(ra-aa))), float(np.max(np.abs(rt-at))))
    distance = max(float(np.max(1-np.sum(unit(ra)*unit(aa), axis=1))), float(np.max(1-np.sum(unit(rt)*unit(at), axis=1))), 0.)
    modes = {}; failures = 0
    for name in ('whole', 'segment'):
        def scores(audio, text):
            if name == 'whole': return unit(text) @ unit(unit(audio).reshape(-1, 3, audio.shape[1]).mean(axis=1)).T
            return (unit(text) @ unit(audio).T).reshape(len(text), -1, 3).max(axis=2)
        r, actual = scores(ra, rt), scores(aa, at)
        stable = near = flips = 0
        for x, y in zip(r, actual):
            for i in range(len(x)):
                for j in range(i+1, len(x)):
                    if abs(x[i]-x[j]) > policy['stable_order_score_gap']:
                        stable += 1; flips += int((x[i]-x[j])*(y[i]-y[j]) <= 0)
                    else: near += 1
        score_abs = float(np.max(np.abs(r-actual)))
        failures += flips + int(score_abs > policy['atol_score_maxabs'])
        modes[name] = {'score_max_abs_difference': score_abs, 'stable_pairs': stable,
                       'stable_pair_flips': flips, 'near_tie_pairs': near}
    ok = vector_abs <= policy['atol_vector_maxabs'] and distance <= policy['atol_cosine_distance'] and failures == 0
    return {'status': 'passed' if ok else 'failed', 'vector_max_abs_difference': vector_abs,
            'max_cosine_distance': distance, 'modes': modes,
            'scope': 'small_fixed_calibration_numerics_not_retrieval_quality_or_training_speed'}

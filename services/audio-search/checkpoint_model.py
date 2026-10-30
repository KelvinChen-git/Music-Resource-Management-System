"""Restricted loader for the two preregistered CLAP checkpoints; never downloads."""
import os
from pathlib import Path
import stat

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['WANDB_MODE'] = 'disabled'

import numpy as np
import torch
from probe import create_pinned_model, sha256, CHECKPOINT_REVISION, ROBERTA_REVISION

PINS = {
    'A': ('music_audioset_epoch_15_esc_90.14.pt', 2352471003,
          'fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd'),
    'B': ('music_speech_audioset_epoch_15_esc_89.98.pt', 2352471003,
          '51c68f12f9d7ea25fdaaccf741ec7f81e93ee594455410f3bca4f47f88d8e006'),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink input refused')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Independent regular file required')
    return path


def checked_checkpoint(path, model_id):
    require(model_id in PINS, 'Only preregistered A or B is supported')
    path = regular(path)
    name, size, digest = PINS[model_id]
    require(path.name == name and path.stat().st_size == size, 'Checkpoint name or size mismatch')
    require(sha256(path) == digest, 'Checkpoint SHA256 mismatch; deserialization refused')
    return path, digest


def load_checkpoint(path, model_id):
    path, digest = checked_checkpoint(path, model_id)
    sdk = create_pinned_model()
    checked_checkpoint(path, model_id)  # Construction must not swap the trusted bytes.
    with torch.serialization.safe_globals([np.core.multiarray.scalar, np.dtype,
            type(np.dtype(np.float64)), type(np.dtype(np.float32))]):
        package = torch.load(path, map_location='cpu', weights_only=True, mmap=True)
    require(isinstance(package, dict), 'Checkpoint must contain a state dictionary')
    original = package.get('state_dict', package)
    require(isinstance(original, dict) and all(isinstance(k, str) for k in original), 'Invalid state dictionary')
    state = {}
    for name, value in original.items():
        key = name.removeprefix('module.')
        require(key not in state, 'Duplicate normalized state key')
        state[key] = value
    removed = state.pop('text_branch.embeddings.position_ids', None) is not None
    loaded = sdk.model.load_state_dict(state, strict=True)
    require(not loaded.missing_keys and not loaded.unexpected_keys, 'Strict checkpoint load mismatch')
    del package, original, state
    sdk.model.eval()
    checked_checkpoint(path, model_id)
    return sdk, {'id': model_id, 'checkpoint_sha256': digest,
        'checkpoint_filename': path.name, 'checkpoint_revision': CHECKPOINT_REVISION,
        'roberta_revision': ROBERTA_REVISION, 'audio_architecture': 'HTSAT-base', 'fusion': False,
        'strict_missing': loaded.missing_keys, 'strict_unexpected': loaded.unexpected_keys,
        'removed_nonlearned_position_ids': removed,
        'loader': 'torch_weights_only_true_mmap_cpu_strict_v1'}

"""Probe-only preprocessing; discovery-v0 remains proposed."""
import numpy as np
import librosa

SAMPLE_RATE = 48000
WINDOW_SAMPLES = 480000


def prepare_window(audio, sample_rate):
    """Float32 mono, resample, then right-zero-pad a <=10-second window."""
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError('sample_rate must be a positive integer')
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim not in (1, 2) or not audio.size or not np.isfinite(audio).all():
        raise ValueError('audio must be finite, nonempty samples or samples-by-channels')
    if audio.shape[0] > sample_rate * 10:
        raise ValueError('slice long audio before encoding; implicit random cropping is forbidden')
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if sample_rate != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=SAMPLE_RATE,
                                res_type='soxr_hq')
    real_samples = len(audio)
    if real_samples > WINDOW_SAMPLES:
        raise ValueError('resampled window exceeds checkpoint capacity')
    audio = np.pad(audio, (0, WINDOW_SAMPLES - real_samples))
    return np.ascontiguousarray(audio, dtype=np.float32), {
        'real_samples': real_samples,
        'padded_samples': WINDOW_SAMPLES - real_samples,
        'sample_rate_hz': SAMPLE_RATE,
    }

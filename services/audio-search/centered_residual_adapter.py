"""One recording-weighted ridge fit to training-mean-centered pair residuals."""
import numpy as np
from review_pack import require
from weighted_caption_adapter import recording_weights


def fit(audio, text, weights, recording_ids, alpha):
    x, t, q = (np.asarray(v, dtype=np.float64) for v in (audio, text, weights))
    require(x.ndim == t.ndim == 2 and x.shape == t.shape and x.size and len(x) == len(recording_ids)
            and q.shape == (len(x),) and all(np.isfinite(v).all() for v in (x, t, q)) and np.all(q > 0)
            and np.max(abs(q-recording_weights(recording_ids))) < 1e-15
            and np.max(abs(np.linalg.norm(x, axis=1)-1)) < 1e-4 and np.max(abs(np.linalg.norm(t, axis=1)-1)) < 1e-4
            and type(alpha) in (float, int) and np.isfinite(alpha) and alpha > 0,
            'Finite unit original pairs and recording-equal weights required')
    residual = t-x; mean = q@residual; target = residual-mean; eye = np.eye(x.shape[1])
    rhs = x.T@(q[:, None]*target)
    delta = np.linalg.solve(x.T@(q[:, None]*x)+alpha*eye, rhs)
    w = eye+delta
    before = float(np.sum(q[:, None]*target**2))
    data = float(np.sum(q[:, None]*(x@delta-target)**2)); penalty = alpha*float(np.square(delta).sum())
    normal = x.T@(q[:, None]*(x@delta-target))+alpha*delta
    zero_mean_error = float(np.max(abs(q@target))); equation_error = float(np.max(abs(normal)))
    require(np.isfinite(w).all() and data+penalty <= before+1e-12 and equation_error < 1e-9 and zero_mean_error < 1e-12,
            'Centered training residual or normal equation failed')
    direction = mean/np.linalg.norm(mean) if np.linalg.norm(mean) > 1e-12 else np.zeros_like(mean)
    energy = float(np.square(delta).sum())
    diagnostic = {'objective_before': before, 'objective_after': data+penalty, 'centered_data_error_after': data,
                  'identity_prior_penalty': penalty, 'alpha': alpha, 'fit_recordings': len(set(recording_ids)), 'fit_intervals': len(x),
                  'solver': 'weighted_primal_closed_form', 'normal_equation_max_abs_residual': equation_error,
                  'centered_target_weighted_mean_maxabs': zero_mean_error, 'training_residual_mean_norm': float(np.linalg.norm(mean)),
                  'parameter_delta_frobenius': float(np.sqrt(energy)), 'parameter_count': int(w.size),
                  'update_energy_in_original_common_residual_direction': float(np.square(delta@direction).sum())/energy if energy > 1e-24 else 0.,
                  'closed_form_optimum_verified': True, 'training_mean_only': True,
                  'inference': 'unit(original_audio_feature@W);original_text_unchanged;no_mean_subtraction'}
    return w, mean, diagnostic

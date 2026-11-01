"""Recording-weighted normalized positive-pair distance, with identity regularization."""
import numpy as np
from review_pack import require
from weighted_caption_adapter import recording_weights


def problem(x, text, weights, recording_ids):
    x, text, weights = (np.asarray(z, dtype=np.float64) for z in (x, text, weights))
    require(x.ndim == text.ndim == 2 and x.shape == text.shape and x.size and len(x) == len(recording_ids)
            and weights.shape == (len(x),) and all(np.isfinite(z).all() for z in (x, text, weights))
            and np.all(weights > 0) and np.max(abs(weights-recording_weights(recording_ids))) < 1e-15
            and np.max(abs(np.linalg.norm(x, axis=1)-1)) < 1e-4 and np.max(abs(np.linalg.norm(text, axis=1)-1)) < 1e-4,
            'Finite unit pairs and equal-recording weights required')
    return x, text, weights


def loss_gradient(x, text, weights, w, alpha):
    require(x.ndim == text.ndim == w.ndim == 2 and x.shape == text.shape and w.shape == (x.shape[1], x.shape[1])
            and weights.shape == (len(x),) and x.size and all(np.isfinite(z).all() for z in (x, text, weights, w))
            and np.all(weights > 0) and abs(float(weights.sum())-1) < 1e-12
            and type(alpha) in (int, float) and np.isfinite(alpha) and alpha > 0, 'Finite weighted normalized-pair objective required')
    z = x@w; norms = np.linalg.norm(z, axis=1, keepdims=True)
    require(np.all(norms > 1e-12), 'Zero mapped vector refused')
    u = z/norms; residual = u-text; delta = w-np.eye(w.shape[0])
    data = float(np.sum(weights[:, None]*residual**2)); penalty = alpha*float(np.square(delta).sum())
    gu = 2*weights[:, None]*residual
    gz = (gu-u*np.sum(gu*u, axis=1, keepdims=True))/norms
    gradient = x.T@gz+2*alpha*delta; objective = data+penalty
    require(np.isfinite(objective) and np.isfinite(gradient).all(), 'Nonfinite normalized objective/gradient')
    return objective, gradient, {'data_loss': data, 'identity_prior_penalty': penalty,
          'weighted_paired_cosine': float(np.sum(weights*np.sum(u*text, axis=1))),
          'mapped_norm_min': float(norms.min()), 'mapped_norm_max': float(norms.max())}


def fit(x, text, weights, recording_ids, *, alpha, initial_step, max_steps, max_backtracks,
        armijo, backtrack_factor, gradient_max_tol, relative_loss_tol):
    x, text, weights = problem(x, text, weights, recording_ids)
    require(type(max_steps) is int and max_steps > 0 and type(max_backtracks) is int and max_backtracks > 0
            and all(type(v) in (int, float) and np.isfinite(v) for v in
                    (alpha, initial_step, armijo, backtrack_factor, gradient_max_tol, relative_loss_tol))
            and alpha > 0 and initial_step > 0 and 0 < armijo < 1 and 0 < backtrack_factor < 1
            and gradient_max_tol > 0 and relative_loss_tol > 0, 'Fixed finite training-only optimizer budget required')
    w = np.eye(x.shape[1]); loss, gradient, stats = loss_gradient(x, text, weights, w, alpha)
    initial_stats = stats.copy(); trace = [loss]; stepsizes = []; evaluations = 1; reason = 'step_limit'
    for _ in range(max_steps):
        if np.max(abs(gradient)) <= gradient_max_tol:
            reason = 'gradient_tolerance'; break
        step = float(initial_step); accepted = False; g2 = float(np.square(gradient).sum())
        for _ in range(max_backtracks):
            trial = w-step*gradient
            try: newloss, newgradient, newstats = loss_gradient(x, text, weights, trial, alpha)
            except ValueError:
                step *= backtrack_factor; evaluations += 1; continue
            evaluations += 1
            if newloss <= loss-armijo*step*g2:
                accepted = True; break
            step *= backtrack_factor
        require(accepted, 'Fixed Armijo budget exhausted; no restart or tolerance widening')
        improvement = loss-newloss; before = loss
        w, loss, gradient, stats = trial, newloss, newgradient, newstats
        trace.append(loss); stepsizes.append(step)
        if improvement <= relative_loss_tol*max(1., abs(before)):
            reason = 'relative_loss_tolerance'; break
    require(np.isfinite(w).all() and all(b <= a+1e-14 for a, b in zip(trace, trace[1:])), 'Finite monotonic normalized fit required')
    return w, {'objective_before': trace[0], 'objective_after': trace[-1], 'loss_trace': trace,
               'accepted_step_sizes': stepsizes, 'steps': len(stepsizes), 'objective_evaluations': evaluations,
               'stop_reason': reason, 'training_stopping_tolerance_reached': reason != 'step_limit',
               'max_abs_gradient': float(np.max(abs(gradient))), 'parameter_delta_frobenius': float(np.linalg.norm(w-np.eye(w.shape[0]))),
               'parameter_count': int(w.size), 'fit_intervals': len(x), 'fit_recordings': len(set(recording_ids)),
               'alpha': alpha, 'initial_stats': initial_stats, 'final_stats': stats,
               'validation_used_for_stopping': False, 'global_optimum_claimed': False}

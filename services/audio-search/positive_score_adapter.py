"""One experimental normalized positive-only score objective, never unknown-tag negatives."""
import numpy as np
from review_pack import require
from tag_adapter import unit


def problem(x, prototypes, positive_indices, margin):
    x, p = unit(x), unit(prototypes)
    require(x.shape[1] == p.shape[1] and len(positive_indices) == len(x)
            and type(margin) in (int, float) and np.isfinite(margin) and 0 < margin < 1, 'Observed positive problem required')
    weights = np.zeros((len(x), len(p)))
    for i, ids in enumerate(positive_indices):
        require(ids and len(set(ids)) == len(ids) and all(type(j) is int and 0 <= j < len(p) for j in ids), 'Valid nonempty positive indices required')
        weights[i, ids] = 1/len(ids)
    targets = np.where(weights > 0, np.minimum(1., x@p.T+margin), 0.)
    return x, p, weights, targets


def loss_gradient(x, p, weights, targets, w, alpha):
    require(x.ndim == p.ndim == w.ndim == 2 and x.shape[1] == p.shape[1]
            and w.shape == (x.shape[1], x.shape[1]) and weights.shape == targets.shape == (len(x), len(p))
            and all(np.isfinite(z).all() for z in (x, p, weights, targets, w))
            and np.all(weights >= 0) and np.allclose(weights.sum(axis=1), 1)
            and type(alpha) in (int, float) and np.isfinite(alpha) and alpha > 0, 'Finite aligned positive-only loss inputs required')
    z = x@w; norms = np.linalg.norm(z, axis=1, keepdims=True)
    require(np.all(norms > 1e-12), 'Zero mapped vector refused')
    u = z/norms; scores = u@p.T
    residual = np.where(weights > 0, scores-targets, 0.)
    data_loss = float(np.sum(weights*residual**2)/len(x)); delta = w-np.eye(w.shape[0])
    objective = data_loss+alpha*float(np.square(delta).sum())
    gu = (2/len(x))*(weights*residual)@p
    gz = (gu-u*np.sum(gu*u, axis=1, keepdims=True))/norms
    gradient = x.T@gz+2*alpha*delta
    require(np.isfinite(objective) and np.isfinite(gradient).all(), 'Nonfinite objective or gradient')
    return objective, gradient, {'data_loss': data_loss,
            'mean_observed_positive_cosine': float(np.sum(weights*scores)/len(x)),
            'mapped_norm_min': float(norms.min()), 'mapped_norm_max': float(norms.max())}


def fit(x, prototypes, positive_indices, *, margin, alpha, initial_step, max_steps,
        max_backtracks, armijo, backtrack_factor, gradient_max_tol, relative_loss_tol):
    x, p, weights, targets = problem(x, prototypes, positive_indices, margin)
    require(type(max_steps) is int and max_steps > 0 and type(max_backtracks) is int and max_backtracks > 0
            and initial_step > 0 and 0 < armijo < 1 and 0 < backtrack_factor < 1
            and gradient_max_tol > 0 and relative_loss_tol > 0, 'Fixed finite optimizer budget required')
    w = np.eye(x.shape[1]); loss, gradient, stats = loss_gradient(x, p, weights, targets, w, alpha)
    initial_stats = stats.copy(); trace = [loss]; stepsizes = []; evaluations = 1; reason = 'step_limit'
    for _ in range(max_steps):
        if np.max(np.abs(gradient)) <= gradient_max_tol:
            reason = 'gradient_tolerance'; break
        step = float(initial_step); accepted = False; g2 = float(np.square(gradient).sum())
        for _ in range(max_backtracks):
            trial = w-step*gradient
            try: newloss, newgradient, newstats = loss_gradient(x, p, weights, targets, trial, alpha)
            except ValueError:
                step *= backtrack_factor; evaluations += 1; continue
            evaluations += 1
            if newloss <= loss-armijo*step*g2:
                accepted = True; break
            step *= backtrack_factor
        require(accepted, 'Fixed Armijo search exhausted; no restart or tolerance widening')
        improvement = loss-newloss; before = loss
        w, loss, gradient, stats = trial, newloss, newgradient, newstats
        trace.append(loss); stepsizes.append(step)
        if improvement <= relative_loss_tol*max(1., abs(before)):
            reason = 'relative_loss_tolerance'; break
    require(all(b <= a+1e-14 for a, b in zip(trace, trace[1:])) and np.isfinite(w).all(), 'Monotonic finite fit required')
    return w, {'objective_before': trace[0], 'objective_after': trace[-1], 'loss_trace': trace,
               'accepted_step_sizes': stepsizes, 'steps': len(stepsizes), 'objective_evaluations': evaluations,
               'stop_reason': reason, 'convergence_tolerance_reached': reason != 'step_limit',
               'max_abs_gradient': float(np.max(np.abs(gradient))), 'parameter_delta_frobenius': float(np.linalg.norm(w-np.eye(w.shape[0]))),
               'fit_tracks': len(x), 'observed_positive_pairs': int(np.sum(weights > 0)),
               'alpha': alpha, 'margin': margin, 'initial_stats': initial_stats, 'final_stats': stats,
               'parameter_count': int(w.size), 'validation_used_for_early_stopping': False}

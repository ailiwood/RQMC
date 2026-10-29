"""Explicitly versioned rescue selectors; final inference stays in intervals.py."""
from __future__ import annotations

from functools import lru_cache
import numpy as np
from .allocation import choose as original_choose


@lru_cache(maxsize=64)
def expected_moment_coefficients(reps: int):
    if reps < 2:
        raise ValueError('Need at least two production scrambles')
    i = np.arange(1, reps + 1, dtype=float)
    h = np.cumsum(1 / i)
    h2 = np.cumsum(1 / i**2)
    return i, h, h2


def expected_pre_moments(mean, variance, reps):
    i, h, h2 = expected_moment_coefficients(int(reps))
    delta2 = (float(mean) - .5)**2
    var_pre = (.25 + variance * (i + 1 - h - h2) + delta2 * (h2 - 1)) / i
    pred_error = variance * (1 + (i - 1) / i**2) + delta2 / i**2
    return var_pre, pred_error


def matched_eb_score(mean, variance, reps, alpha=.05, cap=.5):
    """Moment-substitution objective, not a CI or a general expected-width identity."""
    if not 0 <= mean <= 1 or not 0 <= variance <= .25 or not 0 < cap < 1:
        raise ValueError('Invalid moment/cap')
    if not 0 < alpha < 1:
        raise ValueError('Invalid alpha')
    var_pre, err = expected_pre_moments(mean, variance, reps)
    log = np.log(2 / alpha)
    lam = np.minimum(cap, np.sqrt(2 * log / (reps * var_pre)))
    radius = (log + np.cumsum(err * (-np.log1p(-lam) - lam))) / np.cumsum(lam)
    rad = float(np.min(radius))
    return min(1., mean + rad) - max(0., mean - rad)


def smoothed_variance(raw, ns, cfg):
    z = np.log(np.maximum(raw, cfg['variance_floor']))
    w = np.log(ns)
    slope = float(np.clip(np.polyfit(w, z, 1)[0], *cfg['smooth_slope']))
    intercept = float(np.mean(z - slope * w))
    return np.clip(np.exp(intercept + slope * w), 0, .25), slope


def choose_rescue(pilot, ns, budget, pilot_calls, method, cfg, specification):
    if method in ('A', 'B', 'PLUGIN'):
        return original_choose(pilot, ns, budget, pilot_calls, method, cfg)
    x = np.asarray(pilot, dtype=float)
    ns = np.asarray(ns, dtype=int)
    if x.shape != (specification['pilot_replicates'], len(ns)):
        raise ValueError('Unexpected pilot shape')
    if not np.isfinite(x).all() or np.any(x < 0) or np.any(x > 1):
        raise ValueError('Pilot outside known bounds')
    if pilot_calls != len(x) * int(max(ns)):
        raise ValueError('Pilot accounting mismatch')
    raw = np.var(x, axis=0, ddof=1)
    if specification['variance'] == 'log_smooth':
        v, slope = smoothed_variance(raw, ns, cfg)
    elif specification['variance'] == 'raw':
        v, slope = np.clip(raw, 0, .25), None
    else:
        raise ValueError('Unregistered variance estimator')
    mean = float(np.mean(x[:, -1]))
    reps = (budget - pilot_calls) // ns
    scores = np.full(len(ns), np.inf)
    for j, r in enumerate(reps):
        if r >= cfg['min_production_replicates']:
            if specification['objective'] != 'moment_eb':
                raise ValueError('Unregistered objective')
            scores[j] = matched_eb_score(mean, float(v[j]), int(r), cfg['alpha'], cfg['eb_cap'])
    if not np.isfinite(scores).any():
        raise ValueError('Insufficient production budget')
    best = int(np.argmin(scores))
    return int(ns[best]), int(reps[best]), {
        'candidate_n': ns.tolist(), 'pilot_variances': raw.tolist(),
        'selection_variances': v.tolist(), 'pilot_mean': mean, 'fitted_slope': slope,
        'selection_scores': [float(s) if np.isfinite(s) else None for s in scores],
        'raw_zero_variances': int(np.sum(raw == 0)),
        'objective': specification['objective'],
    }

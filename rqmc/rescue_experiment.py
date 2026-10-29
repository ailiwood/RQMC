from __future__ import annotations
from time import perf_counter
import numpy as np
from .common import seed_words, digest
from .experiment import execute_task, task_id
from .sampling import batch_means, blocks
from .rescue_allocation import choose_rescue
from .intervals import ebci, hbci
from .integrands import truth, evaluate


def adaptive_depth_pilot(case, budget, method, cfg, spec, entropy):
    """Generate one bounded pilot net, evaluate disjoint suffixes only as needed."""
    cap = spec['pilot_nmax'][str(budget)]
    count = spec['pilot_replicates']
    if count > cfg['batch_scrambles']:
        raise ValueError('Adaptive pilot must fit a single bounded generation block')
    t = perf_counter()
    u = next(blocks(case['d'], cap, count, entropy, cfg['backend'], cfg['batch_scrambles']))
    sampling_s = perf_counter() - t
    values = np.empty((count, cap))
    depth, previous, evaluation_s, selection_s, trace = min(spec['initial_depth'], cap), 0, 0., 0., []
    while True:
        t = perf_counter()
        values[:, previous:depth] = evaluate(case, u[:, previous:depth, :])
        ns = [n for n in cfg['fixed_n'] if n <= depth]
        cumulative = np.cumsum(values[:, :depth], axis=1)
        pilot = np.stack([cumulative[:, n-1]/n for n in ns], axis=1)
        evaluation_s += perf_counter() - t
        t = perf_counter()
        n, reps, diag = choose_rescue(pilot, ns, budget, count*depth, method, cfg, spec)
        selection_s += perf_counter() - t
        trace.append({'depth':depth, 'calls':count*depth, 'selected_n':n})
        if n <= depth//2 or depth == cap:
            break
        previous, depth = depth, min(depth*2, cap)
    diag['pilot_stages'] = trace
    diag['pilot_generated_points'] = count*cap
    times = {'sampling_s':sampling_s, 'evaluation_s':evaluation_s, 'calls':count*depth}
    return pilot, times, n, reps, diag, selection_s


def execute_rescue_task(task):
    cfg, phase, case, budget, method, rep, with_hbci, spec = task
    if method in ('A', 'B', 'PLUGIN') or method.startswith(('fixed_', 't_R')):
        return execute_task(task[:-1])
    start = perf_counter()
    info = {'task_id': task_id(phase, case, budget, method, rep), 'phase': phase,
            'case_id': case['id'], 'budget': budget, 'method': method, 'rep': rep,
            'backend': cfg['backend'], 'status': 'ok'}
    try:
        base = (phase, case['id'], budget, method, rep)
        pseed = seed_words(cfg['seed'], *base, 'pilot')
        sseed = seed_words(cfg['seed'], *base, 'production')
        assert pseed != sseed
        if spec.get('objective') == 'budget_fixed':
            n = int(spec['n_by_budget'][str(budget)])
            reps = budget // n
            p = np.empty((0,0))
            pt = {'calls':0, 'sampling_s':0., 'evaluation_s':0.}
            pilot_s, selection_s = 0., 0.
            diag = {'fixed_schedule':spec['n_by_budget']}
        elif spec.get('pilot_strategy') == 'adaptive_depth':
            t = perf_counter()
            p, pt, n, reps, diag, selection_s = adaptive_depth_pilot(case, budget, method, cfg, spec, pseed)
            pilot_s = perf_counter() - t - selection_s
        else:
            nmax = spec['pilot_nmax'][str(budget)]
            ns = [n for n in cfg['fixed_n'] if n <= nmax]
            t = perf_counter()
            p, pt = batch_means(case, nmax, spec['pilot_replicates'], pseed, cfg['backend'],
                                cfg['batch_scrambles'], prefixes=ns)
            pilot_s = perf_counter() - t
            t = perf_counter()
            n, reps, diag = choose_rescue(p, ns, budget, pt['calls'], method, cfg, spec)
            selection_s = perf_counter() - t
        diag.update(pilot_means=p.tolist(), pilot_sampling_s=pt['sampling_s'],
                    pilot_evaluation_s=pt['evaluation_s'])
        x, times = batch_means(case, n, reps, sseed, cfg['backend'], cfg['batch_scrambles'])
        calls = pt['calls'] + times['calls']
        if calls > budget:
            raise ArithmeticError('Exceeded evaluation budget')
        t = perf_counter()
        intervals = {'ebci': ebci(x, cfg['alpha'], cfg['eb_cap'])}
        primary_ci_s = perf_counter() - t
        hb_s = 0.
        if with_hbci:
            t = perf_counter()
            intervals['hbci'] = hbci(x, cfg['alpha'], cfg['hb_cap'], cfg['hb_theta'])
            hb_s = perf_counter() - t
        # Evaluator boundary: allocation and final inference completed before truth.
        mu = truth(case)
        for ci in intervals.values():
            ci['covered'] = bool(not ci['empty'] and ci['lower'] <= mu <= ci['upper'])
        info.update(selected_n=n, production_reps=reps, pilot_calls=pt['calls'],
                    calls_used=calls, unused_budget=budget-calls, estimate=float(np.mean(x)),
                    truth=mu, squared_error=float((np.mean(x)-mu)**2), pilot_s=pilot_s,
                    selection_s=selection_s, primary_ci_s=primary_ci_s, hbci_s=hb_s,
                    intervals=intervals, diagnostics=diag, **times)
        info['seed_digest'] = digest({'pilot': pseed, 'production': sseed})
        info['production_means_digest'] = digest(x.tolist())
    except Exception as exc:
        info.update(status='error', error_type=type(exc).__name__, error=str(exc))
    info['total_s'] = perf_counter() - start
    return info

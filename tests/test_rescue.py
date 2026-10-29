import itertools
import numpy as np
import pytest
from rqmc.intervals import ebci, moments
from rqmc.rescue_allocation import expected_pre_moments, matched_eb_score, choose_rescue
from rqmc.common import load_config
from rqmc.rescue_experiment import adaptive_depth_pilot
from rqmc.rescue_experiment import execute_rescue_task
from rqmc.sampling import batch_means


@pytest.mark.parametrize('mean', [0., .2, .5, 1.])
@pytest.mark.parametrize('reps', [2, 16, 128])
def test_moment_objective_is_exact_for_constants(mean, reps):
    actual = ebci(np.full(reps, mean))['width']
    assert matched_eb_score(mean, 0., reps) == pytest.approx(actual, abs=2e-14)


@pytest.mark.parametrize('prob', [.1, .5, .8])
def test_expected_moment_identities_by_exact_bernoulli_enumeration(prob):
    reps = 7
    got_v = np.zeros(reps)
    got_err = np.zeros(reps)
    for bits in itertools.product([0., 1.], repeat=reps):
        x = np.array(bits)
        weight = prob**sum(bits) * (1-prob)**(reps-sum(bits))
        pre_m, pre_v = moments(x)
        got_v += weight * pre_v
        got_err += weight * (x-pre_m)**2
    expected_v, expected_err = expected_pre_moments(prob, prob*(1-prob), reps)
    np.testing.assert_allclose(got_v, expected_v, atol=2e-14, rtol=1e-13)
    np.testing.assert_allclose(got_err, expected_err, atol=2e-14, rtol=1e-13)


def test_selector_respects_pilot_budget_and_constant_data():
    cfg = load_config()
    spec = {'pilot_replicates':16, 'variance':'log_smooth', 'objective':'moment_eb'}
    n, reps, diag = choose_rescue(np.full((16, 5), .25), [1,2,4,8,16], 4096, 256, 'A01', cfg, spec)
    assert n == 1 and reps == 3840
    assert n*reps + 256 <= 4096
    assert diag['raw_zero_variances'] == 5
    with pytest.raises(ValueError, match='accounting'):
        choose_rescue(np.full((16, 5), .25), [1,2,4,8,16], 4096, 0, 'A01', cfg, spec)


def test_adaptive_pilot_suffix_accounting_and_prefix_replay(monkeypatch):
    import rqmc.rescue_experiment as experiment
    from rqmc.integrands import evaluate as real_evaluate
    cfg = load_config()
    spec = {'pilot_replicates':16, 'variance':'log_smooth', 'objective':'moment_eb',
            'pilot_strategy':'adaptive_depth', 'initial_depth':4, 'pilot_nmax':{'4096':16}}
    seen = []
    def counting_evaluate(case, points):
        seen.append(points.shape[0]*points.shape[1])
        return real_evaluate(case, points)
    monkeypatch.setattr(experiment, 'evaluate', counting_evaluate)
    case = {'id':'unit','kind':'smooth1','d':1}
    entropy = [91,83,72]
    p, times, n, reps, diag, selection_s = adaptive_depth_pilot(case,4096,'A02',cfg,spec,entropy)
    final_depth = diag['pilot_stages'][-1]['depth']
    assert sum(seen) == times['calls'] == 16*final_depth
    ns = [x for x in cfg['fixed_n'] if x <= final_depth]
    reference, _ = batch_means(case,16,16,entropy,cfg['backend'],cfg['batch_scrambles'],prefixes=ns)
    np.testing.assert_array_equal(p,reference)
    assert times['calls'] + n*reps <= 4096
    assert diag['pilot_generated_points'] == 256


def test_adaptive_pilot_stops_early_on_constant_data(monkeypatch):
    import rqmc.rescue_experiment as experiment
    cfg = load_config()
    spec = {'pilot_replicates':16, 'variance':'log_smooth', 'objective':'moment_eb',
            'pilot_strategy':'adaptive_depth', 'initial_depth':4, 'pilot_nmax':{'4096':16}}
    monkeypatch.setattr(experiment, 'evaluate', lambda case,u:np.full(u.shape[:2],.25))
    p, times, n, reps, diag, selection_s = adaptive_depth_pilot({'d':1},4096,'A02',cfg,spec,[4,5,6])
    assert times['calls'] == 64 and n == 1 and len(diag['pilot_stages']) == 1


def test_budget_fixed_schedule_has_no_artificial_pilot_cost():
    cfg = load_config()
    case = {'id':'unit','kind':'smooth1','d':1}
    spec = {'objective':'budget_fixed','n_by_budget':{'4096':2}}
    row = execute_rescue_task((cfg,'unit_phase',case,4096,'BUDGET_FIXED',0,False,spec))
    assert row['status'] == 'ok'
    assert row['pilot_calls'] == 0 and row['calls_used'] == 4096
    assert row['selected_n'] == 2 and row['production_reps'] == 2048
    assert row['task_id'] == 'unit_phase|unit|4096|BUDGET_FIXED|0'

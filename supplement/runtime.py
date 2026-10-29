"""New supplementary worker; frozen original allocation, sampler and CIs reused.

The only changes are integrand dispatch, selectable interval mode for isolated
timing, and added pilot diagnostics. No reference is fetched before inference.
"""
from functools import lru_cache
import json
from time import perf_counter
import numpy as np
from rqmc.common import root, seed_words, digest
from rqmc.experiment import task_id
from rqmc.sampling import blocks
from rqmc.rescue_allocation import choose_rescue
from rqmc.intervals import ebci,hbci
from rqmc.integrands import truth as original_truth
from .integrands import evaluate


def batch_means(case,n,reps,entropy,cfg):
    means=[]; sampling_s=evaluation_s=0.
    iterator=iter(blocks(case['d'],n,reps,entropy,cfg['backend'],cfg['batch_scrambles']))
    while True:
        t=perf_counter()
        try: u=next(iterator)
        except StopIteration: break
        sampling_s+=perf_counter()-t
        t=perf_counter(); values=evaluate(case,u); means.append(values.mean(axis=1))
        evaluation_s+=perf_counter()-t
    return np.concatenate(means),{'sampling_s':sampling_s,'evaluation_s':evaluation_s,'calls':n*reps}


def adaptive_pilot(case,budget,method,cfg,spec,entropy):
    cap=spec['pilot_nmax'][str(budget)]; count=spec['pilot_replicates']
    if count>cfg['batch_scrambles']: raise ValueError('Pilot exceeds bounded generation chunk')
    t=perf_counter()
    u=next(blocks(case['d'],cap,count,entropy,cfg['backend'],cfg['batch_scrambles']))
    sampling_s=perf_counter()-t
    values=np.empty((count,cap)); depth=min(spec['initial_depth'],cap); previous=0
    evaluation_s=selection_s=0.; trace=[]
    while True:
        t=perf_counter(); values[:,previous:depth]=evaluate(case,u[:,previous:depth,:])
        ns=[n for n in cfg['fixed_n'] if n<=depth]
        cumulative=np.cumsum(values[:,:depth],axis=1)
        pilot=np.stack([cumulative[:,n-1]/n for n in ns],axis=1)
        evaluation_s+=perf_counter()-t
        t=perf_counter(); n,reps,diag=choose_rescue(pilot,ns,budget,count*depth,method,cfg,spec)
        selection_s+=perf_counter()-t
        trace.append({'depth':depth,'calls':count*depth,'selected_n':n,
                      'all_zero':bool(np.all(pilot==0))})
        if n<=depth//2 or depth==cap: break
        previous,depth=depth,min(depth*2,cap)
    diag.update(pilot_stages=trace,pilot_generated_points=count*cap,pilot_means=pilot.tolist(),
                pilot_all_zero=bool(np.all(pilot==0)),pilot_sampling_s=sampling_s,
                pilot_evaluation_s=evaluation_s)
    return n,reps,count*depth,diag,selection_s


@lru_cache(maxsize=1)
def application_references():
    return json.loads((root()/'state/supplement_v2/application_references.json').read_text(encoding='utf-8'))['cases']


def execute(task):
    cfg,phase,case,budget,method,rep,spec,ci_mode=task
    start=perf_counter()
    info={'task_id':task_id(phase,case,budget,method,rep),'phase':phase,'case_id':case['id'],
          'budget':budget,'method':method,'rep':rep,'backend':cfg['backend'],'status':'ok','ci_mode':ci_mode}
    try:
        base=(phase,case['id'],budget,method,rep)
        pseed=seed_words(cfg['seed'],*base,'pilot'); sseed=seed_words(cfg['seed'],*base,'production')
        if pseed==sseed: raise ArithmeticError('Pilot/production stream collision')
        pilot_s=selection_s=0.; pilot_calls=0; diag={}
        if method.startswith('fixed_'):
            n=int(method.split('_')[1]); reps=budget//n
        else:
            t=perf_counter()
            n,reps,pilot_calls,diag,selection_s=adaptive_pilot(case,budget,method,cfg,spec,pseed)
            pilot_s=perf_counter()-t-selection_s
        x,times=batch_means(case,n,reps,sseed,cfg)
        calls=pilot_calls+times['calls']
        if calls>budget or reps<cfg['min_production_replicates']: raise ArithmeticError('Invalid call/repetition accounting')
        intervals={}; eb_s=hb_s=0.
        if ci_mode in ('both','ebci'):
            t=perf_counter(); intervals['ebci']=ebci(x,cfg['alpha'],cfg['eb_cap']); eb_s=perf_counter()-t
        if ci_mode in ('both','hbci'):
            t=perf_counter(); intervals['hbci']=hbci(x,cfg['alpha'],cfg['hb_cap'],cfg['hb_theta']); hb_s=perf_counter()-t
        if not intervals: raise ValueError('Invalid CI mode')
        # Evaluator boundary: references cannot influence pilot, selection or CIs.
        if case['kind']=='mvn_upper':
            ref=application_references()[case['id']]; mu=ref['reference']; tolerance=ref['coverage_sensitivity_radius']
        else:
            mu=original_truth(case); tolerance=0.
        for ci in intervals.values():
            ci['covered']=bool(not ci['empty'] and ci['lower']<=mu<=ci['upper'])
            ci['covered_all_reference_values']=bool(not ci['empty'] and ci['lower']<=mu-tolerance and mu+tolerance<=ci['upper'])
            ci['covered_any_reference_value']=bool(not ci['empty'] and ci['lower']<=mu+tolerance and mu-tolerance<=ci['upper'])
        info.update(selected_n=n,production_reps=reps,pilot_calls=pilot_calls,calls_used=calls,
                    unused_budget=budget-calls,estimate=float(np.mean(x)),truth=mu,reference_radius=tolerance,
                    squared_error=float((np.mean(x)-mu)**2),pilot_s=pilot_s,selection_s=selection_s,
                    primary_ci_s=eb_s,hbci_s=hb_s,intervals=intervals,diagnostics=diag,**times)
        info['seed_digest']=digest({'pilot':pseed,'production':sseed})
        info['production_means_digest']=digest(x.tolist())
    except Exception as exc:
        info.update(status='error',error_type=type(exc).__name__,error=str(exc))
    info['total_s']=perf_counter()-start
    return info

from __future__ import annotations
from time import perf_counter
import numpy as np
from .common import seed_words,digest
from .sampling import batch_means
from .allocation import choose
from .intervals import ebci,hbci,t_interval
from .integrands import truth

def task_id(phase,case,budget,method,rep):
    return f'{phase}|{case["id"]}|{budget}|{method}|{rep}'

def execute_task(task):
    """One independent full pilot-selection-production repetition."""
    cfg,phase,case,budget,method,rep,with_hbci=task
    tid=task_id(phase,case,budget,method,rep);start=perf_counter()
    info={'task_id':tid,'phase':phase,'case_id':case['id'],'budget':budget,
          'method':method,'rep':rep,'backend':cfg['backend'],'status':'ok'}
    try:
        # Separate entropy streams even for identical method/task labels.
        base=(phase,case['id'],budget,method,rep)
        pseed=seed_words(cfg['seed'],*base,'pilot')
        sseed=seed_words(cfg['seed'],*base,'production')
        if pseed==sseed:raise RuntimeError('Seed domain collision')
        pilot_calls=0;pilot_s=0.;select_s=0.;diag={}
        if method.startswith('fixed_'):
            n=int(method.split('_')[1]);reps=budget//n
        elif method.startswith('t_R'):
            reps=int(method[3:]);n=budget//reps
            if n*reps!=budget:raise ValueError('Fixed R not compatible with budget')
        else:
            nmax=cfg['pilot_nmax'][str(budget)]
            ns=[int(v) for v in cfg['fixed_n'] if v<=nmax]
            t=perf_counter()
            p,pt=batch_means(case,nmax,cfg['pilot_replicates'],pseed,cfg['backend'],
                            cfg['batch_scrambles'],prefixes=ns)
            pilot_s=perf_counter()-t;pilot_calls=pt['calls'];t=perf_counter()
            n,reps,diag=choose(p,ns,budget,pilot_calls,method,cfg);select_s=perf_counter()-t
            diag['pilot_means']=p.tolist()
            diag['pilot_sampling_s']=pt['sampling_s']
            diag['pilot_evaluation_s']=pt['evaluation_s']
        if reps<2:raise ValueError('Too few production replications')
        x,times=batch_means(case,n,reps,sseed,cfg['backend'],cfg['batch_scrambles'])
        calls=pilot_calls+times['calls']
        if calls>budget:raise ArithmeticError('Exceeded evaluation budget')
        t=perf_counter()
        intervals={'t':t_interval(x,cfg['alpha'])} if method.startswith('t_R') else {
            'ebci':ebci(x,cfg['alpha'],cfg['eb_cap'])}
        primary_ci_s=perf_counter()-t;hb_s=0.
        if with_hbci and not method.startswith('t_R'):
            t=perf_counter();intervals['hbci']=hbci(x,cfg['alpha'],cfg['hb_cap'],cfg['hb_theta']);hb_s=perf_counter()-t
        # Truth is fetched only AFTER choices, production and CI construction.
        mu=truth(case)
        for ci in intervals.values():ci['covered']=bool(not ci['empty'] and ci['lower']<=mu<=ci['upper'])
        info.update({'selected_n':n,'production_reps':reps,'pilot_calls':pilot_calls,
          'calls_used':calls,'unused_budget':budget-calls,'estimate':float(np.mean(x)),
          'truth':mu,'squared_error':float((np.mean(x)-mu)**2),'pilot_s':pilot_s,
          'selection_s':select_s,**times,'primary_ci_s':primary_ci_s,'hbci_s':hb_s,
          'intervals':intervals,'diagnostics':diag,'seed_digest':digest({'pilot':pseed,'production':sseed})})
        info['production_means_digest']=digest(x.tolist())
    except Exception as e:
        info.update(status='error',error_type=type(e).__name__,error=str(e))
    info['total_s']=perf_counter()-start
    return info

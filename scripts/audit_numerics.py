"""Independent scalar and reviewed external-reference checks, not coverage estimates."""
import _bootstrap
import ast
import math
from typing import Callable, Union
import json
import numpy as np
from qmcpy import DigitalNetB2
from rqmc.common import root, write_json, sha_file, seed_words
from rqmc.intervals import ebci, hbci, hb_capital, moments
from rqmc.sampling import blocks

def reviewed_function(filename, name, namespace):
    # Only explicitly reviewed pure numeric functions; no downloaded imports,
    # top-level statements, shell commands, or installation hooks are executed.
    source=root()/'docs/source_records'/filename
    tree=ast.parse(source.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(nodes)!=1:raise ValueError('Reference function missing')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
    return namespace[name]

def scalar_moments(x):
    prior_m=[];prior_v=[];s=0.;q=0.;m=.5;v=.25
    for i,y in enumerate(x,1):
        prior_m.append(m);prior_v.append(v)
        s+=float(y);m=(.5+s)/(i+1);q+=(float(y)-m)**2;v=(.25+q)/(i+1)
    return np.array(prior_m),np.array(prior_v)

def main():
    env={'np':np,'math':math,'Callable':Callable,'Union':Union,'RealArray':np.ndarray}
    bets=reviewed_function('confseq_betting_strategies.py.txt','lambda_predmix_eb',env)
    lower=reviewed_function('confseq_predmix.py.txt','predmix_lower_cs',env)
    capital=reviewed_function('confseq_betting.py.txt','betting_mart',env)
    rng=np.random.default_rng(810927)
    datasets={'zero':np.zeros(128),'one':np.ones(128),'constant':np.full(128,.2),
              'bernoulli':rng.binomial(1,.1,256).astype(float),
              'continuous':rng.beta(.5,2,256),'abrupt':np.r_[np.zeros(512),np.ones(512)]}
    checks=[]
    for name,x in datasets.items():
        mu,v=scalar_moments(x);assert np.allclose(v,moments(x)[1],atol=1e-15,rtol=0)
        l=bets(x,alpha=.025,fixed_n=len(x),truncation=.5)
        assert np.allclose(l,np.minimum(.5,np.sqrt(2*math.log(40)/(len(x)*v))),atol=1e-14)
        pred=(x-mu)**2
        kwargs={'v':pred,'lambdas_fn':lambda y:l,'psi_fn':lambda z:-np.log1p(-z)-z,
                'alpha':.025,'running_intersection':True}
        lo=float(lower(x,**kwargs)[-1]);hi=float(1-lower(1-x,**kwargs)[-1])
        ours=ebci(x);err=max(abs(ours['lower']-lo),abs(ours['upper']-hi))
        assert err<2e-12,(name,err)
        h=hbci(x);max_log_error=0.;accepted=[]
        uncapped=lambda y,m:bets(y,alpha=.025,fixed_n=len(y))
        for m in np.linspace(0,1,101):
            ref=capital(x,float(m),alpha=.05,lambdas_fn_positive=uncapped,
                        lambdas_fn_negative=uncapped,convex_comb=False,theta=.5,trunc_scale=.5)
            ref_log=math.log(max(.5,float(ref.max())))
            ours_log=max(hb_capital(x,float(m)))-math.log(2)
            max_log_error=max(max_log_error,abs(ref_log-ours_log))
            if ref_log<=math.log(20):accepted.append(float(m))
        assert max_log_error<2e-9,(name,max_log_error)
        if accepted:
            assert h['lower']<=min(accepted)+1e-12 and h['upper']>=max(accepted)-1e-12
        checks.append({'input':name,'R':len(x),'ebci_max_endpoint_difference':err,
                       'hbci_max_log_capital_difference':max_log_error,'ebci':ours,'hbci':h,
                       'accepted_reference_grid_points':len(accepted)})
    samplers=[]
    for backend in ['scipy','qmcpy']:
        for d in [1,8,32]:
            for n in [1,2,4,16,64,2048]:
                a=np.concatenate(list(blocks(d,n,8,[318,d,n],backend,chunk=3)))
                b=np.concatenate(list(blocks(d,n,8,[318,d,n],backend,chunk=3)))
                assert np.array_equal(a,b)
                assert np.isfinite(a).all() and a.min()>=0 and a.max()<1
                assert np.equal(a*2**52,np.floor(a*2**52)).all()
                assert not np.array_equal(a[0],a[1])
                for k in range(int(math.log2(n))+1):
                    prefix=2**k
                    assert np.array_equal(np.sort((a[:,:prefix,0]*prefix).astype(int),axis=1),
                                          np.tile(np.arange(prefix),(8,1)))
                samplers.append({'backend':backend,'d':d,'n':n,'reps':8,'passed':True})
    engine=DigitalNetB2(dimension=8,replications=16,seed=88910,randomize='LMS DS',order='GRAY',t=52)
    distinct_matrices=len({g.tobytes() for g in engine.gen_mats})
    distinct_shifts=len({s.tobytes() for s in engine.rshift})
    assert distinct_matrices==16 and distinct_shifts==16
    # Fixed seed, diagnostic only: first-point marginals and cross-replicate correlation.
    a=np.concatenate(list(blocks(2,4,8192,[819271],'qmcpy',chunk=128)))
    marginal_mean=float(a[:,0,0].mean());se=math.sqrt(1/(12*len(a)))
    assert abs(marginal_mean-.5)<6*se
    adjacent_corr=float(np.corrcoef(a[::2,0,0],a[1::2,0,0])[0,1])
    assert abs(adjacent_corr)<.1
    receipt={'status':'PASSED_IMPLEMENTATION_AUDIT_NOT_COVERAGE_ESTIMATE','interval_checks':checks,
             'sampling_checks':samplers,'qmcpy_distinct_LMS_matrices':distinct_matrices,
             'qmcpy_distinct_digital_shifts':distinct_shifts,'first_point_mean':marginal_mean,
             'marginal_mean_standard_error':se,'adjacent_replication_correlation':adjacent_corr,
             'reference_files':{p.name:sha_file(p) for p in (root()/'docs/source_records').glob('confseq_*')},
             'reference_note':'Reviewed author low-level functions executed. Explicit R01 predictable errors supplied; high-level confseq predmix uses a different mean predictor. No claim of full official reproduction.'}
    write_json(root()/'validation/current/numerical_audit.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['sampling_checks','reference_files']},indent=2))

if __name__=='__main__':main()

"""Predeclared secondary whole-repetition bootstrap and full fixed-grid audit."""
import _bootstrap
import json
import numpy as np
import pandas as pd
from rqmc.common import root, seed_words, write_json, sha_file


def main():
    r=root();folder=r/'results/rescue_v1/analysis/confirmation'
    receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    assert receipt['tasks']==324000 and receipt['failures']==0
    frozen=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    summary=pd.read_csv(folder/'summary.csv')
    e=summary[summary.ci=='ebci']
    absolute=e.groupby('method').mean_width.apply(lambda v:float(np.exp(np.log(v).mean())))
    fixed=[f'fixed_{n}' for n in [1,2,4,8,16,32,64]]
    best=min(fixed,key=lambda m:absolute[m])
    oracle=[]
    for (case,N),group in e.groupby(['case','budget']):
        fixed_group=group[group.method.isin(fixed)]
        opt=fixed_group.loc[fixed_group.mean_width.idxmin()]
        a=group[group.method=='A02'].iloc[0]
        oracle.append({'case':case,'budget':int(N),'empirical_best_fixed':opt['method'],
                       'A02_vs_empirical_cellwise_minimum':float(a.mean_width/opt.mean_width)})
    methods=['A02','fixed_4','BUDGET_FIXED'];arrays={}
    for method in methods:
        for line in (r/f'results/rescue_v1/confirmation/{method}.jsonl').open(encoding='utf-8'):
            row=json.loads(line);assert row['status']=='ok'
            key=(row['case_id'],row['budget'],method)
            if key not in arrays:arrays[key]=np.full(1000,np.nan)
            assert np.isnan(arrays[key][row['rep']])
            arrays[key][row['rep']]=row['intervals']['ebci']['width']
    assert all(np.isfinite(v).all() for v in arrays.values())
    count=5000;logsum={m:np.zeros(count) for m in methods[1:]}
    rng=np.random.default_rng(seed_words(frozen['config']['seed'],'rescue_v1_aggregate_bootstrap'))
    keys=sorted((c['id'],N) for c in frozen['config']['confirmation_cases'] for N in frozen['config']['budgets'])
    for case,N in keys:
        for lo in range(0,count,125):
            hi=min(count,lo+125);indices=rng.integers(0,1000,size=(hi-lo,1000))
            numerator=arrays[(case,N,'A02')][indices].mean(axis=1)
            for reference in methods[1:]:
                denominator=arrays[(case,N,reference)][indices].mean(axis=1)
                logsum[reference][lo:hi]+=np.log(numerator/denominator)/len(keys)
    boot=pd.DataFrame({m:np.exp(v) for m,v in logsum.items()})
    boot.to_csv(folder/'aggregate_bootstrap_samples.csv',index=False)
    intervals={m:{'bootstrap_replicates':count,'percentile_lo':float(boot[m].quantile(.025)),
                  'percentile_hi':float(boot[m].quantile(.975))} for m in methods[1:]}
    write_json(r/'handoff/rescue_robustness_review.json',{
        'status':'SECONDARY_CHECKS_COMPLETE','bootstrap':intervals,
        'bootstrap_unit':'Paired full-repetition IDs within each fixed case/budget; cases not resampled',
        'new_integrand_evaluations':0,'independent_confirmation_repetitions_added':0,
        'primary_decision_changed':False,'all_fixed_geometric_mean_widths':absolute[fixed].to_dict(),
        'retrospective_best_common_fixed':best,'A02_vs_retrospective_best_common_fixed':float(absolute['A02']/absolute[best]),
        'A02_better_than_every_fixed_geometric_mean':bool((absolute['A02']<absolute[fixed]).all()),
        'cellwise_fixed_minimum_diagnostic':oracle,
        'limits':['Retrospective minima are optimistic finite-simulation diagnostics, not deployable or exact oracles.',
                  'Bootstrap bounds are a secondary sensitivity check; frozen delta-method primary rules remain authoritative.'],
        'bootstrap_samples_sha256':sha_file(folder/'aggregate_bootstrap_samples.csv')})
    print(json.dumps({'bootstrap':intervals,'best_fixed':best,'A02_vs_best_fixed':float(absolute['A02']/absolute[best])},indent=2))


if __name__=='__main__':main()

"""Complete-denominator summaries and paired full-repetition contrasts."""
import _bootstrap
import argparse
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import norm,t
from rqmc.common import root,load_config,write_json,sha_file
from rqmc.experiment import task_id

def wilson(k,n):
    z=norm.ppf(.975);den=1+z*z/n;p=k/n
    mid=(p+z*z/(2*n))/den;rad=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return float(mid-rad),float(mid+rad)

def analyze(phase):
    cfg=load_config();r=root();raw=r/f'results/raw/{phase}.jsonl'
    rows=[json.loads(line) for line in raw.open(encoding='utf-8')]
    reps=cfg[f'{phase}_repetitions'];cases=cfg[f'{phase}_cases']
    methods=cfg['main_methods']+cfg['secondary_methods']
    expected={task_id(phase,c,N,m,i) for c in cases for N in cfg['budgets'] for m in methods for i in range(reps)}
    actual=[x['task_id'] for x in rows]
    if len(set(actual))!=len(actual) or set(actual)!=expected:
        raise RuntimeError(f'Incomplete/duplicate matrix: expected {len(expected)}, got {len(actual)}, unique {len(set(actual))}')
    hb=cfg['hbci_cases'] if phase=='confirmation' else cfg['hbci_development_cases']
    flat=[];selection=[]
    for x in rows:
        cis=['t'] if x['method'].startswith('t_R') else ['ebci']+(['hbci'] if x['case_id'] in hb else [])
        failed=x['status']!='ok'
        if not failed:
            assert x['calls_used']+x['unused_budget']==x['budget']
            assert x['pilot_calls']+x['production_reps']*x['selected_n']==x['calls_used']
            assert set(x['intervals'])==set(cis)
        for ci in cis:
            entry=x.get('intervals',{}).get(ci,{})
            flat.append({'case':x['case_id'],'budget':x['budget'],'method':x['method'],'ci':ci,'rep':x['rep'],
                         'failed':failed,'covered':bool(entry.get('covered',False)),
                         'empty':bool(entry.get('empty',False)),'width':entry.get('width',np.nan),
                         'calls_used':x.get('calls_used',np.nan),'pilot_calls':x.get('pilot_calls',np.nan),
                         'unused_budget':x.get('unused_budget',np.nan),'total_s':x['total_s']})
        if not failed:
            selection.append({'case':x['case_id'],'budget':x['budget'],'method':x['method'],'rep':x['rep'],
                              'selected_n':x['selected_n'],'saturation':x.get('diagnostics',{}).get('variance_upper_saturation',0),
                              'zero_variances':x.get('diagnostics',{}).get('raw_zero_variances',0)})
    df=pd.DataFrame(flat);summaries=[]
    for key,g in df.groupby(['case','budget','method','ci'],sort=True):
        nn=len(g);covered=int(g.covered.sum());failed=int(g.failed.sum());lo,hi=wilson(covered,nn)
        valid=g.loc[~g.failed];width=valid.width
        summaries.append(dict(zip(['case','budget','method','ci'],key))|{
            'attempted':nn,'successful':nn-failed,'failures':failed,'failure_rate':failed/nn,
            'covered':covered,'coverage':covered/nn,'coverage_wilson_lo':lo,'coverage_wilson_hi':hi,
            'empty_count':int(g['empty'].sum()),'empty_rate':float(g['empty'].mean()),
            'mean_width':float(width.mean()),'width_mcse':float(width.std(ddof=1)/np.sqrt(len(width))),
            'median_width':float(width.median()),'p90_width':float(width.quantile(.9)),
            'mean_calls':float(valid.calls_used.mean()),'mean_pilot_calls':float(valid.pilot_calls.mean()),
            'mean_unused_budget':float(valid.unused_budget.mean()),'mean_parallel_task_s':float(g.total_s.mean())})
    summary=pd.DataFrame(summaries)
    fixed=summary[(summary.ci=='ebci')&summary.method.str.startswith('fixed_')]
    eligible=fixed.groupby('method').filter(lambda g:g.failures.sum()==0 and g.empty_count.sum()==0)
    scores=eligible.groupby('method').mean_width.apply(lambda x:float(np.exp(np.log(x).mean())))
    baseline=scores.idxmin() if phase=='development' else cfg['primary_fixed_baseline']
    contrasts=[]
    pairs=[(m,baseline) for m in ['A','B','PLUGIN']]+[('A','PLUGIN'),('B','A')]
    for (case,N,ci),g in df.groupby(['case','budget','ci']):
        if ci=='t':continue
        for method,reference in pairs:
            a=g[g.method==method].set_index('rep');b=g[g.method==reference].set_index('rep')
            if not len(a) or not len(b):continue
            merged=a[['width','failed']].join(b[['width','failed']],lsuffix='_a',rsuffix='_b',how='inner')
            valid=merged[~merged.failed_a & ~merged.failed_b]
            x=valid.width_a.to_numpy();y=valid.width_b.to_numpy();nn=len(x)
            if nn<2:continue
            delta=x-y;se=float(delta.std(ddof=1)/np.sqrt(nn));difference=float(delta.mean())
            ratio=float(x.mean()/y.mean());ratio_se=float((x-ratio*y).std(ddof=1)/(np.sqrt(nn)*y.mean()))
            q=float(t.ppf(.975,nn-1));p=float(t.cdf(difference/se,nn-1)) if se>0 else float(difference>=0)
            contrasts.append({'case':case,'budget':N,'ci':ci,'method':method,'reference':reference,
                              'paired_reps':nn,'width_difference':difference,'difference_mcse':se,
                              'difference_lo':difference-q*se,'difference_hi':difference+q*se,
                              'mean_width_ratio':ratio,'ratio_mcse_delta':ratio_se,
                              'ratio_lo':ratio-q*ratio_se,'ratio_hi':ratio+q*ratio_se,
                              'one_sided_p':p})
    cd=pd.DataFrame(contrasts);cd['holm_p']=np.nan
    for _,idx in cd.groupby(['method','reference','ci']).groups.items():
        indices=list(idx);order=sorted(indices,key=lambda i:cd.loc[i,'one_sided_p']);prev=0.
        for rank,i in enumerate(order):
            prev=max(prev,min(1.,(len(order)-rank)*float(cd.loc[i,'one_sided_p'])))
            cd.loc[i,'holm_p']=prev
    out=r/'results/analysis';out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/f'{phase}_summary.csv',index=False)
    cd.to_csv(out/f'{phase}_contrasts.csv',index=False)
    pd.DataFrame(selection).groupby(['case','budget','method','selected_n']).size().rename('count').to_csv(out/f'{phase}_selection.csv')
    diagnostic=pd.DataFrame(selection).groupby(['case','budget','method'])[['saturation','zero_variances']].mean()
    diagnostic.to_csv(out/f'{phase}_diagnostics.csv')
    receipt={'phase':phase,'expected_tasks':len(expected),'actual_tasks':len(rows),'interval_records':len(df),
             'numerical_failures':sum(x['status']!='ok' for x in rows),'raw_sha256':sha_file(raw),
             'baseline_rule':'Equal cell weight geometric mean of EBCI mean widths, complete valid fixed methods without empty sets',
             'fixed_baseline_scores':scores.to_dict(),'selected_fixed_baseline':baseline,
             'interpretation':'Development estimates are exploratory, not independent confirmation. Paired repetition IDs do not imply shared random numbers.',
             'width_note':'Empty sets retained with width zero, separately counted. Numerical failures counted as noncoverage; width conditional on successful calculations.'}
    write_json(out/f'{phase}_receipt.json',receipt)
    print(json.dumps(receipt,indent=2))
    print(cd[(cd.ci=='ebci')&(cd.method=='A')].to_string(index=False))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],required=True)
    analyze(p.parse_args().phase)

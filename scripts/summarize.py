import _bootstrap
import argparse,json,math
import numpy as np
import pandas as pd
from scipy.stats import norm
from rqmc.common import root

def wilson(k,n,level=.95):
    z=norm.ppf(.5+level/2);p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return mid-rad,mid+rad

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['smoke','development','confirmation'],required=True)
    a=p.parse_args();r=root();rows=[];errors=[]
    with (r/f'results/raw/{a.phase}.jsonl').open(encoding='utf-8') as f:
        for line in f:
            x=json.loads(line)
            if x['status']!='ok':errors.append(x);continue
            for kind,ci in x['intervals'].items():
                rows.append({'case':x['case_id'],'budget':x['budget'],'method':x['method'],'ci':kind,
                  'rep':x['rep'],'n':x['selected_n'],'covered':ci['covered'],'empty':ci['empty'],
                  'width':ci['width'],'time_s':x['total_s'],'calls_used':x['calls_used'],
                  'pilot_calls':x['pilot_calls'],'squared_error':x['squared_error']})
    out=r/'results/summary';out.mkdir(parents=True,exist_ok=True)
    if not rows:raise SystemExit('No successful rows')
    df=pd.DataFrame(rows);summary=[]
    for key,g in df.groupby(['case','budget','method','ci'],sort=True):
        n=len(g);k=int(g.covered.sum());lo,hi=wilson(k,n)
        summary.append(dict(zip(['case','budget','method','ci'],key))|{
          'repetitions_successful':n,'coverage':k/n,'coverage_wilson_lo':lo,'coverage_wilson_hi':hi,
          'empty_rate':g['empty'].mean(),'mean_width':g.width.mean(),'width_mcse':g.width.std(ddof=1)/np.sqrt(n),
          'median_width':g.width.median(),'p90_width':g.width.quantile(.9),
          'mean_total_s_parallel':g.time_s.mean(),'mean_calls':g.calls_used.mean(),
          'mean_pilot_calls':g.pilot_calls.mean(),'rmse':np.sqrt(g.squared_error.mean())})
    pd.DataFrame(summary).to_csv(out/f'{a.phase}.csv',index=False)
    df.groupby(['case','budget','method','ci','n']).size().rename('count').to_csv(out/f'{a.phase}_selected_n.csv')
    (out/f'{a.phase}_errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf-8')
    note='Summary is preliminary: add full-repetition contrasts, uncertainty, error denominators and protocol review before manuscript. '
    note+='Any numerical errors must be resolved or included in intention-to-run failure statistics; successful-only tables are NOT sufficient for publication.\n'
    (out/f'{a.phase}_README.txt').write_text(note,encoding='utf-8')
    print(f'Wrote {len(summary)} summary rows; {len(errors)} numerical errors retained.')
if __name__=='__main__':main()

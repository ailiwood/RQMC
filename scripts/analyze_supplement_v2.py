"""All-case secondary summaries; no tuning, filtering or new simulations."""
import _bootstrap
import argparse
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import t
from rqmc.common import root,write_json,sha_file
from rqmc.experiment import task_id
from analyze_results import wilson

METHODS=[f'fixed_{n}' for n in (1,2,4,8,16,32,64)]+['A02','PLUGIN_STAGE']


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def collect(kind):
    r=root();rows=[];allocations=[];calls=pilot=0;hashes={};seen=set()
    old=read(r/'config/rescue_v1.json');new=read(r/'config/supplement_v2.json')
    if kind=='s1':
        folder=r/'results/supplement_v2/s1_replay';receipt=read(folder/'s1_complete.receipt.json')
        assert receipt['status']=='COMPLETE' and receipt['total_tasks']==108000 and not receipt['errors']
        extra={}
        p=folder/'s1_complete.jsonl';hashes[str(p.relative_to(r))]=sha_file(p)
        for line in p.open(encoding='utf-8'):
            w=json.loads(line);assert w['exact_original_scientific_match'];x=w['replay']
            assert x['task_id'] not in extra;extra[x['task_id']]=x['intervals']['hbci']
        def original():
            for m in METHODS:
                p=r/f'results/rescue_v1/confirmation/{m}.jsonl';hashes[str(p.relative_to(r))]=sha_file(p)
                for line in p.open(encoding='utf-8'):
                    x=json.loads(line)
                    if 'hbci' not in x['intervals']:x['intervals']['hbci']=extra[x['task_id']]
                    yield x
        iterator=original()
        expected={task_id('rescue_v1_confirmation',c,N,m,i) for c in old['confirmation_cases']
                  for N in old['budgets'] for m in METHODS for i in range(1000)}
    else:
        mode='confirmation' if kind=='s2' else 'sensitivity'
        folder=r/f'results/supplement_v2/{mode}';receipt=read(folder/f'{mode}.receipt.json')
        assert receipt['status']=='COMPLETE' and not receipt['errors']
        p=folder/f'{mode}.jsonl';hashes[str(p.relative_to(r))]=sha_file(p)
        iterator=(json.loads(line) for line in p.open(encoding='utf-8'))
        if kind=='s2':
            expected={task_id(new['phase_confirmation'],c,N,m,i) for c in new['cases']
                      for N in new['budgets'] for m in METHODS for i in range(1000)}
        else:
            s=new['sensitivity'];expected={task_id(new['phase_sensitivity'],c,s['budget'],f'A02_K{k}',i)
                    for c in new['cases'] if c['id'] in s['cases'] for k in s['pilot_counts'] for i in range(1000)}
    for x in iterator:
        tid=x['task_id'];assert tid in expected and tid not in seen;seen.add(tid)
        failed=x['status']!='ok'
        if not failed:
            assert x['pilot_calls']+x['selected_n']*x['production_reps']==x['calls_used']<=x['budget']
            assert x['calls_used']+x['unused_budget']==x['budget']
            assert set(x['intervals'])=={'ebci','hbci'}
            calls+=x['calls_used'];pilot+=x['pilot_calls'];d=x['diagnostics']
            stages=d.get('pilot_stages',[])
            zero=d.get('pilot_all_zero',bool(d.get('pilot_means')) and bool(np.all(np.asarray(d.get('pilot_means'))==0)))
            allocations.append({'case':x['case_id'],'budget':x['budget'],'method':x['method'],'rep':x['rep'],
                'selected_n':x['selected_n'],'production_reps':x['production_reps'],'pilot_calls':x['pilot_calls'],
                'unused_budget':x['unused_budget'],'pilot_all_zero':zero,'pilot_depth':stages[-1]['depth'] if stages else 0,
                'pilot_stage_count':len(stages),'total_s':x['total_s'],'selection_s':x.get('selection_s',0)})
        for ci in ('ebci','hbci'):
            e=x.get('intervals',{}).get(ci,{})
            rows.append({'case':x['case_id'],'budget':x['budget'],'method':x['method'],'rep':x['rep'],'ci':ci,
                         'failed':failed,'covered':bool(e.get('covered',False)),'empty':bool(e.get('empty',False)),
                         'width':e.get('width',np.nan),
                         'covered_reference_all':bool(e.get('covered_all_reference_values',e.get('covered',False))),
                         'covered_reference_any':bool(e.get('covered_any_reference_value',e.get('covered',False)))})
    assert seen==expected,(len(seen),len(expected))
    return pd.DataFrame(rows),pd.DataFrame(allocations),{'kind':kind,'tasks':len(seen),'intervals':len(rows),
            'total_calls':calls,'pilot_calls':pilot,'raw_sha256':hashes,'supplement_run_receipt':receipt}


def summarize(df):
    rows=[]
    for key,g in df.groupby(['case','budget','method','ci']):
        w=g.loc[~g.failed,'width'];lo,hi=wilson(int(g.covered.sum()),len(g))
        rows.append(dict(zip(['case','budget','method','ci'],key))|{
            'attempted':len(g),'failures':int(g.failed.sum()),'empty_count':int(g['empty'].sum()),
            'covered':int(g.covered.sum()),'coverage':float(g.covered.mean()),'coverage_wilson_lo':lo,'coverage_wilson_hi':hi,
            'reference_ambiguous_coverages':int((g.covered_reference_all!=g.covered_reference_any).sum()),
            'mean_width':float(w.mean()),'width_mcse':float(w.std(ddof=1)/np.sqrt(len(w))),
            'median_width':float(w.median()),'p90_width':float(w.quantile(.9)),'p99_width':float(w.quantile(.99)),
            'min_width':float(w.min()),'max_width':float(w.max())})
    return pd.DataFrame(rows)


def contrasts(df):
    rows=[]
    for (case,N),g in df.groupby(['case','budget']):
        candidate_methods=sorted(m for m in g.method.unique() if m=='A02' or m.startswith('A02_K'))
        for method in candidate_methods:
            for ci in ('ebci','hbci'):
                a=g[(g.method==method)&(g.ci==ci)].set_index('rep')
                if a.empty:continue
                for reference in sorted(g.method.unique()):
                    for refci in ('ebci','hbci'):
                        if reference==method and ci==refci:continue
                        b=g[(g.method==reference)&(g.ci==refci)].set_index('rep')
                        z=a[['width','failed']].join(b[['width','failed']],lsuffix='_a',rsuffix='_b')
                        z=z[~z.failed_a & ~z.failed_b]
                        if len(z)<2:continue
                        x,y=z.width_a.to_numpy(),z.width_b.to_numpy();ratio=float(x.mean()/y.mean())
                        se=float((x-ratio*y).std(ddof=1)/np.sqrt(len(z))/y.mean())
                        logse=float((x/x.mean()-y/y.mean()).std(ddof=1)/np.sqrt(len(z)))
                        q=float(t.ppf(.975,len(z)-1))
                        rows.append({'case':case,'budget':N,'method':method,'ci':ci,'reference':reference,'reference_ci':refci,
                            'repetitions':len(z),'mean_width_ratio':ratio,'ratio_mcse':se,'ratio_lo':ratio-q*se,'ratio_hi':ratio+q*se,
                            'log_ratio_mcse':logse,'secondary_no_new_primary_test':True})
    result=pd.DataFrame(rows);aggregates=[]
    for key,g in result.groupby(['method','ci','reference','reference_ci']):
        lr=float(np.log(g.mean_width_ratio).mean());se=float(np.sqrt(np.square(g.log_ratio_mcse).sum())/len(g))
        aggregates.append(dict(zip(['method','ci','reference','reference_ci'],key))|{
            'cells':len(g),'geometric_mean_ratio':math.exp(lr),'ratio_lo':math.exp(lr-1.96*se),'ratio_hi':math.exp(lr+1.96*se),
            'worst_ratio':float(g.mean_width_ratio.max()),'best_ratio':float(g.mean_width_ratio.min()),
            'scope':'Secondary fixed matrix; no primary multiplicity claim; post hoc minima are optimistic'})
    return result,pd.DataFrame(aggregates)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['s1','s2','s3'],required=True);args=ap.parse_args();r=root()
    df,alloc,receipt=collect(args.kind)
    # S3 default16 is reused from S2, never regenerated or picked by outcome.
    if args.kind=='s3':
        base,basealloc,_=collect('s2');s=read(r/'config/supplement_v2.json')['sensitivity']
        chosen=(base.method=='A02')&base['case'].isin(s['cases'])&(base.budget==s['budget'])
        base=base[chosen].copy();base['method']='A02_K16'
        ba=basealloc[(basealloc.method=='A02')&basealloc['case'].isin(s['cases'])&(basealloc.budget==s['budget'])].copy();ba['method']='A02_K16'
        df=pd.concat([df,base],ignore_index=True);alloc=pd.concat([alloc,ba],ignore_index=True)
        receipt['reused_default16_tasks']=len(ba)
    summary=summarize(df);comparison,aggregate=contrasts(df)
    out=r/f'results/supplement_v2/analysis/{args.kind}';out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/'summary.csv',index=False);comparison.to_csv(out/'contrasts.csv',index=False);aggregate.to_csv(out/'aggregate.csv',index=False)
    alloc.to_csv(out/'allocations.csv',index=False)
    alloc.groupby(['case','budget','method','selected_n']).size().rename('count').to_csv(out/'selection.csv')
    alloc.groupby(['case','budget','method']).agg(mean_pilot_calls=('pilot_calls','mean'),zero_pilot_rate=('pilot_all_zero','mean'),
        mean_pilot_depth=('pilot_depth','mean'),mean_unused_budget=('unused_budget','mean'),mean_parallel_task_s=('total_s','mean')).to_csv(out/'pilot_summary.csv')
    receipt.update(failures=int(df.failed.sum()),empty_intervals=int(df['empty'].sum()),
                   reference_sensitive_interval_count=int((df.covered_reference_all!=df.covered_reference_any).sum()),
                   interpretation='All secondary cells retained. No tuning or redefinition of original primary estimands.',
                   analysis_source_sha256=sha_file(r/'scripts/analyze_supplement_v2.py'))
    write_json(out/'receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('raw_sha256','supplement_run_receipt')},indent=2))


if __name__=='__main__':main()

"""All-cell rescue summaries; no experiment execution or outcome-based filtering."""
import _bootstrap
import argparse
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import norm, t
from rqmc.common import root, write_json, sha_file
from rqmc.experiment import task_id
from analyze_results import wilson


def analyze(phase, methods=None):
    r = root()
    cfg = json.loads((r/'config/rescue_v1.json').read_text(encoding='utf-8'))
    folder = r/f'results/rescue_v1/{phase}'
    if methods is None:
        methods = sorted(p.stem for p in folder.glob('*.jsonl'))
    cases, reps = cfg[f'{phase}_cases'], cfg[f'{phase}_repetitions']
    hb = cfg['hbci_cases'] if phase == 'confirmation' else cfg['hbci_development_cases']
    flat, selections, raw_hashes = [], [], {}
    total_calls = total_pilot = tasks = failures = 0
    for method in methods:
        path = folder/f'{method}.jsonl'
        raw_hashes[method] = sha_file(path)
        expected = {task_id(f'rescue_v1_{phase}',c,N,method,i)
                    for c in cases for N in cfg['budgets'] for i in range(reps)}
        seen = set()
        for line in path.open(encoding='utf-8'):
            x = json.loads(line)
            if x['task_id'] in seen:
                raise RuntimeError('Duplicate task')
            seen.add(x['task_id']); tasks += 1
            failed = x['status'] != 'ok'; failures += failed
            cis = ['t'] if method.startswith('t_R') else ['ebci'] + (['hbci'] if x['case_id'] in hb else [])
            if not failed:
                assert x['calls_used'] + x['unused_budget'] == x['budget']
                assert x['pilot_calls'] + x['selected_n']*x['production_reps'] == x['calls_used']
                assert set(x['intervals']) == set(cis)
                total_calls += x['calls_used']; total_pilot += x['pilot_calls']
                selections.append({'case':x['case_id'],'budget':x['budget'],'method':method,
                                   'selected_n':x['selected_n'],'pilot_calls':x['pilot_calls']})
            for ci in cis:
                entry = x.get('intervals',{}).get(ci,{})
                flat.append({'case':x['case_id'],'budget':x['budget'],'method':method,'ci':ci,'rep':x['rep'],
                             'failed':failed,'covered':bool(entry.get('covered',False)),
                             'empty':bool(entry.get('empty',False)),'width':entry.get('width',np.nan),
                             'calls_used':x.get('calls_used',np.nan),'pilot_calls':x.get('pilot_calls',np.nan),
                             'unused_budget':x.get('unused_budget',np.nan),'total_s':x['total_s'],
                             'selection_s':x.get('selection_s',np.nan)})
        if seen != expected:
            raise RuntimeError(f'Incomplete matrix for {method}: got {len(seen)}, expected {len(expected)}')
    df = pd.DataFrame(flat)
    summary = []
    for key, group in df.groupby(['case','budget','method','ci']):
        width = group.loc[~group.failed,'width']
        lo, hi = wilson(int(group.covered.sum()), len(group))
        summary.append(dict(zip(['case','budget','method','ci'], key)) | {
            'attempted':len(group),'successful':len(width),'failures':int(group.failed.sum()),
            'coverage':float(group.covered.mean()),'covered':int(group.covered.sum()),
            'coverage_wilson_lo':lo,'coverage_wilson_hi':hi,'empty_count':int(group['empty'].sum()),
            'mean_width':float(width.mean()),'width_mcse':float(width.std(ddof=1)/np.sqrt(len(width))),
            'median_width':float(width.median()),'p90_width':float(width.quantile(.9)),
            'mean_calls':float(group.calls_used.mean()),'mean_pilot_calls':float(group.pilot_calls.mean()),
            'mean_unused_budget':float(group.unused_budget.mean()),
            'mean_parallel_task_s':float(group.total_s.mean()),'mean_selection_s':float(group.selection_s.mean())})
    summary = pd.DataFrame(summary)
    fixed = summary[(summary.ci=='ebci') & summary.method.str.startswith('fixed_')]
    scores = fixed.groupby('method').mean_width.apply(lambda x:float(np.exp(np.log(x).mean())))
    if phase == 'confirmation':
        frozen = json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
        baseline = frozen['primary_baseline']
    else:
        if len(scores) != 7:
            raise RuntimeError('Full fixed grid required before development ranking')
        baseline = str(scores.idxmin())
    references = [baseline,'PLUGIN','PLUGIN_MATCH','PLUGIN_STAGE','BUDGET_FIXED','A']
    candidates = [m for m in methods if m not in ('B',) and not m.startswith(('fixed_','t_R'))]
    contrast = []
    for (case,N,ci), group in df.groupby(['case','budget','ci']):
        if ci == 't':
            continue
        for method in candidates:
            for reference in references:
                if method == reference or reference not in methods:
                    continue
                a = group[group.method==method].set_index('rep')
                b = group[group.method==reference].set_index('rep')
                pair = a[['width','failed']].join(b[['width','failed']],lsuffix='_a',rsuffix='_b')
                valid = pair[~pair.failed_a & ~pair.failed_b]
                x,y = valid.width_a.to_numpy(),valid.width_b.to_numpy()
                nn = len(x)
                if nn < 2:
                    continue
                ratio = float(x.mean()/y.mean())
                ratio_se = float((x-ratio*y).std(ddof=1)/(np.sqrt(nn)*y.mean()))
                diff = x-y; se = float(diff.std(ddof=1)/np.sqrt(nn))
                logse = float((x/x.mean()-y/y.mean()).std(ddof=1)/np.sqrt(nn))
                q = float(t.ppf(.975,nn-1))
                p = float(t.cdf(diff.mean()/se,nn-1)) if se else float(diff.mean()>=0)
                contrast.append({'case':case,'budget':N,'ci':ci,'method':method,'reference':reference,
                                 'paired_reps':nn,'mean_width_ratio':ratio,'ratio_mcse':ratio_se,
                                 'ratio_lo':ratio-q*ratio_se,'ratio_hi':ratio+q*ratio_se,
                                 'log_ratio_mcse':logse,'mean_difference':float(diff.mean()),
                                 'difference_mcse':se,'one_sided_p':p})
    contrasts = pd.DataFrame(contrast)
    contrasts['holm_p'] = np.nan
    aggregates = []
    for (method,reference,ci), indices in contrasts.groupby(['method','reference','ci']).groups.items():
        group = contrasts.loc[indices]
        order = sorted(indices,key=lambda i:contrasts.loc[i,'one_sided_p']);prev = 0.
        for j, i in enumerate(order):
            prev = max(prev,min(1.,(len(order)-j)*float(contrasts.loc[i,'one_sided_p'])))
            contrasts.loc[i,'holm_p'] = prev
        logratio = float(np.log(group.mean_width_ratio).mean())
        logse = float(np.sqrt(np.square(group.log_ratio_mcse).sum())/len(group))
        wins = group[group.mean_width_ratio<=.9]
        aggregates.append({'method':method,'reference':reference,'ci':ci,'cells':len(group),
                           'geometric_mean_ratio':math.exp(logratio),
                           'ratio_lo':math.exp(logratio-1.96*logse),'ratio_hi':math.exp(logratio+1.96*logse),
                           'families_with_10pct_gain':sorted(set(wins['case'])),
                           'cells_with_10pct_gain':len(wins),
                           'worst_ratio':float(group.mean_width_ratio.max())})
    out = r/f'results/rescue_v1/analysis/{phase}'
    out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/'summary.csv',index=False)
    contrasts.to_csv(out/'contrasts.csv',index=False)
    pd.DataFrame(aggregates).to_csv(out/'aggregate.csv',index=False)
    pd.DataFrame(selections).groupby(['case','budget','method','selected_n']).size().rename('count').to_csv(out/'selection.csv')
    receipt = {'phase':phase,'tasks':tasks,'intervals':len(df),'failures':failures,
               'empty_intervals':int(df['empty'].sum()),'total_calls':total_calls,'pilot_calls':total_pilot,
               'methods':methods,'selected_fixed_baseline':baseline,'fixed_scores':scores.to_dict(),
               'raw_sha256':raw_hashes,'aggregates':aggregates,
               'interpretation':'Development comparisons are exploratory; independent method streams are paired by repetition ID, not CRN. No selection-adjusted confirmation claim.' if phase=='development' else 'Use the frozen claim and multiplicity family; secondary exploratory contrasts are not primary tests.'}
    write_json(out/'receipt.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['phase','tasks','intervals','failures','empty_intervals','selected_fixed_baseline']},indent=2))
    print(pd.DataFrame(aggregates).query("ci == 'ebci'").to_string(index=False))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['development','confirmation'], default='development')
    parser.add_argument('--methods', nargs='+')
    args = parser.parse_args()
    analyze(args.phase,args.methods)

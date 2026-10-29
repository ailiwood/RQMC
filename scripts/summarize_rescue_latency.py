"""Descriptive timing and t-interval pathology audit; no new simulations."""
import _bootstrap
import json
import pandas as pd
from rqmc.common import root, write_json, sha_file


def main():
    r=root(); raw=r/'results/rescue_v1/isolated_latency.jsonl'
    rows=[json.loads(x) for x in raw.read_text().splitlines()]
    assert len(rows)==108 and all(x['status']=='ok' for x in rows)
    fields=['total_s','pilot_s','selection_s','sampling_s','evaluation_s','primary_ci_s','hbci_s']
    df=pd.DataFrame(rows)
    summary=df.groupby(['case_id','budget','method'])[fields].median().reset_index()
    summary.to_csv(r/'paper/generated/latency.csv',index=False)
    table=[r'\begin{table}[htbp]',r'\caption{Isolated median task latency (milliseconds), three repetitions per cell, one CPU worker and one numerical-library thread. Each task computes both EBCI and HBCI. Timing includes sampling, integrand evaluation, selection, interval construction and evaluator/digest overhead; it excludes interpreter startup, shared warm-up and the JSONL writer. These development functions are timing probes only.}\label{tab:latency}',
           r'\small\setlength{\tabcolsep}{4pt}\begin{tabular}{llrrrrrr}\toprule',
           r'Case & $N$ & Fixed-4 & Budget fixed & PLUGIN & P-STAGE & A01 & A02\\\midrule']
    for case,label in [('d_smooth1','Smooth1'),('d_ridge','Ridge ($d=8$)')]:
        for N in [4096,16384,65536]:
            vals=[float(summary[(summary.case_id==case)&(summary.budget==N)&(summary.method==m)].iloc[0].total_s)*1000 for m in ['fixed_4','BUDGET_FIXED','PLUGIN','PLUGIN_STAGE','A01','A02']]
            table.append(label+f' & {N} & '+' & '.join(f'{v:.2f}' for v in vals)+r' \\')
    table.append(r'\bottomrule\end{tabular}\end{table}')
    (r/'paper/generated/latency_table.tex').write_text('\n'.join(table)+'\n')
    s=pd.read_csv(r/'results/rescue_v1/analysis/confirmation/summary.csv')
    t=s[s.ci=='t'];worst=t.loc[t.coverage.idxmin()]
    zero=0;count=0;noncovered_zero=0
    for line in (r/f'results/rescue_v1/confirmation/{worst["method"]}.jsonl').open():
        x=json.loads(line)
        if x['case_id']!=worst['case'] or x['budget']!=int(worst.budget):continue
        count+=1;interval=x['intervals']['t']
        if interval['width']==0:
            zero+=1;noncovered_zero+=int(not interval['covered'])
    write_json(r/'handoff/rescue_latency_and_t_audit.json',{
        'latency_tasks':len(rows),'latency_raw_sha256':sha_file(raw),
        'timing_summary':'Median of exactly three original timing tasks per case/budget/method; descriptive only',
        'worst_t_cell':{'case':worst['case'],'budget':int(worst.budget),'method':worst['method'],
                        'coverage':float(worst.coverage),'repetitions':count,'zero_width':zero,'noncovered_zero_width':noncovered_zero},
        'new_integrand_calls':0})
    print(summary[['case_id','budget','method','total_s']].to_string(index=False))
    print({'worst_t_case':worst['case'],'method':worst['method'],'N':int(worst.budget),'coverage':float(worst.coverage),'zero':zero,'zero_noncoverage':noncovered_zero})


if __name__=='__main__':main()

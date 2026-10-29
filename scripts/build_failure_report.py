"""Build the stopping report and figure strictly from complete development records."""
import _bootstrap
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rqmc.common import root,sha_file,write_json

def table(frame,formats=None):
    formats=formats or {}
    def fmt(col,val):
        if col in formats:return formats[col].format(val)
        return str(val)
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+''.join(
        '| '+' | '.join(fmt(col,v) for col,v in zip(frame.columns,row))+' |\n' for row in frame.itertuples(index=False,name=None))

def main():
    r=root();out=r/'results/analysis'
    s=pd.read_csv(out/'development_summary.csv');c=pd.read_csv(out/'development_contrasts.csv')
    receipt=json.loads((out/'development_receipt.json').read_text())
    replay=json.loads((r/'handoff/reproducibility_receipt.json').read_text())
    if receipt['actual_tasks']!=20800 or replay['status']!='FULL_DEVELOPMENT_REPRODUCED':
        raise RuntimeError('Complete verified data required')
    rows=[json.loads(line) for line in (r/'results/raw/development.jsonl').open(encoding='utf-8')]
    assert not (r/'results/raw/confirmation.jsonl').exists()
    calls=sum(x['calls_used'] for x in rows);pilot=sum(x['pilot_calls'] for x in rows)
    primary=c[(c.ci=='ebci')&(c.method=='A')&(c.reference=='fixed_2')].copy()
    primary['A / fixed_2']=primary.mean_width_ratio.map(lambda x:f'{x:.4f}')
    primary['95% MC interval']=primary.apply(lambda x:f'[{x.ratio_lo:.4f}, {x.ratio_hi:.4f}]',axis=1)
    primary['Width increase']=primary.mean_width_ratio.map(lambda x:f'{100*(x-1):.2f}%')
    primary_table=primary[['case','budget','A / fixed_2','95% MC interval','Width increase']]
    hb=[]
    for case in ['d_smooth1','d_ridge']:
        for N in [4096,16384]:
            x=np.array([z['intervals']['hbci']['width'] for z in sorted(rows,key=lambda z:z['rep'])
                        if z['case_id']==case and z['budget']==N and z['method']=='A'])
            y=np.array([z['intervals']['hbci']['width'] for z in sorted(rows,key=lambda z:z['rep'])
                        if z['case_id']==case and z['budget']==N and z['method']=='fixed_4'])
            ratio=x.mean()/y.mean();se=(x-ratio*y).std(ddof=1)/(math.sqrt(len(x))*y.mean());q=t.ppf(.975,len(x)-1)
            hb.append({'case':case,'budget':N,'ratio':ratio,'mcse':se,'lo':ratio-q*se,'hi':ratio+q*se})
    hb=pd.DataFrame(hb);hb.to_csv(out/'development_hbci_fixed4_diagnostic.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,5.2),gridspec_kw={'width_ratios':[1.3,1]},layout='constrained')
    panels=[(primary.rename(columns={'mean_width_ratio':'ratio','ratio_lo':'lo','ratio_hi':'hi'}),
             'Primary EBCI: A / fixed n = 2'),(hb,'HBCI diagnostic: A / fixed n = 4')]
    for ax,(data,title) in zip(axes,panels):
        ypos=np.arange(len(data));value=data.ratio.to_numpy()
        ax.errorbar(value,ypos,xerr=np.array([value-data.lo.to_numpy(),data.hi.to_numpy()-value]),fmt='o',color='#b45309',capsize=3)
        ax.axvline(1,color='#334155',linestyle='--',linewidth=1)
        ax.set_yticks(ypos,[f'{z.case[2:]} | N={z.budget:,}' for z in data.itertuples()]);ax.invert_yaxis()
        ax.set_xlabel('Mean interval width ratio (smaller is better)');ax.set_title(title,fontweight='bold')
        ax.grid(axis='x',color='#e5e7eb');ax.set_axisbelow(True)
    fig.suptitle('No useful increment over strong fixed allocations in development',fontsize=14,fontweight='bold')
    fig.supxlabel('200 full repetitions per cell. Bars: paired delta-method 95% Monte Carlo intervals. Development only.\nHBCI fixed n=4 is a disclosed development diagnostic; the primary baseline rule selects n=2.',fontsize=9)
    figures=r/'results/figures';figures.mkdir(exist_ok=True)
    fig.savefig(figures/'development_stopping_evidence.png',dpi=160)
    fig.savefig(figures/'development_stopping_evidence.svg')
    plt.close(fig)
    display=s[['case','budget','method','ci','attempted','covered','coverage','coverage_wilson_lo','coverage_wilson_hi',
               'empty_count','failures','mean_width','width_mcse','median_width','p90_width','mean_calls','mean_pilot_calls']]
    (out/'ALL_RESULTS.md').write_text('# Complete development results\n\nEvery prespecified method and CI cell is included. Coverage denominator is all 200 intended repetitions.\n\n'+
        table(display,{k:'{:.6g}' for k in display.columns if k not in ['case','budget','method','ci','attempted','covered','empty_count','failures']})+'\n',encoding='utf-8')
    hb_display=hb.copy();hb_display['A / fixed_4']=hb.ratio.map(lambda x:f'{x:.4f}')
    hb_display['95% MC interval']=hb.apply(lambda x:f'[{x.lo:.4f}, {x.hi:.4f}]',axis=1)
    run=json.loads((r/'state/development_receipt.json').read_text())
    report=f'''# FAILURE_REPORT — RQMC pilot allocation

**Final status: STOPPED_NO_SIGNAL.**

结论：预定 A/B 设置没有显示足以支持继续投入的增量。A 在全部 8 个主要开发比较单元中均比统一固定基线更宽；B 在两个预算下都解析退化为 n=1。确认实验未运行，未编造论文成功状态。

## Decision and scope

The prescribed development gate was not passed. Route A is the unchanged bounded-slope log-variance smoothing rule; route B is the unchanged paired Hoeffding upper-variance rule. PLUGIN remains a baseline. No third route, case removal, seed replacement, hyperparameter search, or confirmation inspection was used to rescue either route.

This is a failure of these concrete settings on the specified development functions, not a general impossibility result for pilot allocation. There are no held-out results, no independent confirmation, and no claim that a negative-results article has a sufficient original contribution. The primary protocol remains EBCI over the full matrix; its endpoint is not switched after observing the supplementary HBCI results.

## Exact completed experiment

- Four fixed development cases: u exp(u-1); threshold 1/3; 8-dimensional exponential with lambda=2; 8-dimensional normal ridge with threshold 0.
- Budgets: 4096 and 16384 calls. Thirteen methods: fixed n=1,2,4,8,16,32,64; PLUGIN; A; B; fixed-R t intervals at R=8,16,32.
- 200 complete independent pilot-selection-production repetitions per case/budget/method: **20,800 tasks**, all present exactly once.
- 16,000 EBCI records, 8,000 HBCI records in the two prespecified development families, and 4,800 t records: **28,800 intervals**.
- **{calls:,} total calls**, including **{pilot:,} pilot calls**. No unused budget in this particular power-of-two matrix. Fixed methods paid zero pilot calls; adaptive methods paid 256 or 1024 (6.25%).
- Zero numerical failures and zero empty confidence sets in the experiment. Adversarial unit checks separately verified that empty sets are retained when they occur.
- Actual development wall time: **{run['elapsed_s']:.3f} seconds** on this machine, including spawn, intervals and streaming output. This is observed throughput, not a fixed-wall-time budget theorem. Installation, audit, benchmarking and packaging time is additional.

Raw SHA-256: `{receipt['raw_sha256']}`. The complete counts, calls, pilot means, selected n, diagnostics, interval endpoints, coverage flags, seed digests and production-mean digests are retained in [results/raw/development.jsonl](results/raw/development.jsonl).

## Route A: primary EBCI result

The prespecified cross-cell geometric-mean rule selected **fixed n=2** as the single primary fixed baseline. Every case/budget has equal weight. Its geometric mean width was 0.0113263; fixed n=4 was 0.0118433. All seven fixed methods remain reported. No case-specific oracle is treated as deployable.

{table(primary_table)}

The ratios are ratios of mean widths. Monte Carlo intervals use the paired full-repetition influence values, with 199-degree-of-freedom t quantiles. Method streams are independent; pairing IDs does not imply common random numbers. The baseline was selected from development, so these intervals are descriptive Monte Carlo uncertainty, not independent confirmatory inference or simultaneous bounds. The CSV also retains within-contrast Holm-adjusted one-sided diagnostics; the stopping decision does not depend on p-values.

A improved on PLUGIN in two low-budget cells (approximately 13.05% for smooth1 and 8.05% for exp), but still lost to the fixed baseline in those same cells. In the other six cells its mean width was larger than PLUGIN's. These favorable comparisons are retained and do not establish useful increment over strong fixed methods.

## Route B: analytical failure, not a tuned replacement

With 8 independent pilot pairs, the additive upper-variance term is 0.2472354 for K=5 and 0.2576485 for K=7. For K=7 it exceeds 1/4, so all bounds saturate. For K=5, every bound is in [0.2472354,0.25]; for n>=2, n times its lower bound exceeds the largest possible n=1 bound, and the finite-R penalty also increases. Thus both budgets always select n=1. All **1,600 B development tasks** selected n=1, consistent with the prior proof.

B therefore pays a pilot without changing the allocation of the fixed n=1 baseline. The analytic retirement was written before development. Constants, beta, pilot size and cases were not altered. See [handoff/B_RETIREMENT.md](handoff/B_RETIREMENT.md).

## HBCI and practical t comparators

The supplementary HBCI results contain real favorable comparisons: A was 9.69%–30.41% narrower than fixed n=2 across its four cells. That must not be mistaken for beating the strong HBCI fixed choices. The single, already-listed fixed n=4 had smaller mean HBCI width in **all four** cells:

{table(hb_display[['case','budget','A / fixed_4','95% MC interval']])}

Fixed n=4 is presented here as an explicitly disclosed development diagnostic, not a new frozen primary comparator. The small ridge difference at N=16384 is uncertain; absence of useful increment is not a claim that every difference is statistically distinguishable.

All fixed-R t comparisons are included. Their observed development coverage ranged from 0.900 to 1.000 across cells. For the threshold function at N=16384, R=16 covered 180/200, Wilson 95% interval [0.8506,0.9343]. These are practical/asymptotic comparators, not distribution-free finite-sample intervals. No narrow undercovered t interval is used as a shortcut to an efficiency claim.

## Coverage and numerical qualifications

A's primary EBCI coverage was 199/200 in each ridge cell and 200/200 in the other six. Wilson 95% intervals are [0.9722,0.9991] and [0.9812,1.0000], respectively. Zero observed failures does not imply zero failure probability. Two hundred repeats cannot establish precise nominal coverage or broad generality. The functions were deliberately fixed, not randomly sampled from a population of integrands.

The independent unit is a full outer repetition; within each interval it is an independent scramble mean, never a Sobol point. Pilot prefixes share a randomization, their evaluations are charged once, and production uses a separate named stream. Exact continuous integrals are accessed only after production and interval construction. Float64, the 52-bit digital grid, and the tiny finite-grid/continuous-target distinction are disclosed in the mathematical audit; this is not interval-arithmetic certification.

## Verification and reproducibility

- Environment: project-local Python 3.12.13; QMCPy 2.4; QMCToolsCL 1.2.4; NumPy 2.5.4; SciPy 1.18.1. Exact installed versions and environment metadata are retained.
- Initial execution used 12 workers. Three balanced throughput rounds selected 16 workers, numerical threads 1, based solely on runtime. Median throughput was 139.68 / 194.04 / 232.67 tasks/s at 8 / 12 / 16 workers. The sampled process-tree memory peak was about 1.54 GiB on 61.56 GiB RAM.
- Implementation tests: 77 passed, 2 Windows symlink-privilege skips. EBCI scalar/vector and reviewed author-code checks passed; HBCI direct capital/grid checks passed. Source transcription issues were identified and corrected according to WSR. These are implementation checks, not coverage claims.
- The sealed source ZIP was extracted into an isolated project-local root and **all 20,800 tasks were replayed**. Every scientific result field matched bit-for-bit; only timing fields were excluded. All generated statistical tables matched within declared floating aggregation tolerance. Replay does not add independent repetitions. The source archive was rebuilt from that isolated root and all file contents matched.
- This is same-machine, same-locked-environment reproducibility. It is not cross-platform validation or an independent research-team review. See [handoff/reproducibility_receipt.json](handoff/reproducibility_receipt.json) and [REPRODUCE.md](REPRODUCE.md).

## Sources, novelty and journal checks

R01 already introduces the RQMC use of these intervals and the n/R tradeoff; its remaining empirical-selection question is not a novelty certificate for the present rules. WSR supplies the inference machinery. The focused nearest-neighbor search did not establish complete duplication of this exact charged-pilot experiment, but the lack of performance increment independently closes the gate. No new interval theorem, first adaptive QMC claim, or PLUGIN relabeling is made. [Jain et al.](https://doi.org/10.1093/imaiai/iaag003), [Waudby-Smith and Ramdas](https://doi.org/10.1093/jrsssb/qkad009)

The current Elsevier page linked its August 2026 source list. The downloaded workbook lists Algorithms as Journal, ISSN 1999-4893, SERIALS row 245, with no matching entry in DISCONTINUED. MDPI lists ESCI; Algorithms is not described here as SCIE Q4. Direct MDPI author/template pages returned 403/429. The template access issue did not cause the research stop. No manuscript formatting compliance, compiled manuscript, submission, publication guarantee, fee, or data upload is claimed. [Elsevier Compendex](https://www.elsevier.com/products/engineering-village/databases/compendex), [Algorithms indexing](https://www.mdpi.com/journal/algorithms/indexing)

## Delivered evidence and deliberate omissions

The raw repetitions, full baseline tables, selection distributions, paired contrasts, diagnostics, source/claim ledger, mathematical and runtime audits, exact environment lock, sealed development source, rebuilt archive and full reproduction receipt are supplied. [Complete 144-cell table](results/analysis/ALL_RESULTS.md); [stopping-evidence figure](results/figures/development_stopping_evidence.png).

Confirmation count is **zero**. No confirmation freeze was manufactured. No English journal manuscript or manuscript PDF is produced because the authorized failure branch was reached; no negative-results article contribution has been independently established. Continuing toward a publication claim would require a separate research decision, not a third route smuggled into this experiment.

## AI-use and author note

An OpenAI Codex agent implemented engineering changes, ran the simulations, checked formulas and sources, generated the statistical summaries, and drafted this report. The supplied design set the two scientific routes and stopping rules. AI output is not a substitute for independent methodological review. No human author identities, affiliations, funding, competing-interest declarations, or approval of a manuscript were invented. No correspondence or submission was sent.
'''
    (r/'FAILURE_REPORT.md').write_text(report,encoding='utf-8')
    write_json(r/'handoff/failure_report_receipt.json',{'status':'STOPPED_NO_SIGNAL','raw_sha256':sha_file(r/'results/raw/development.jsonl'),
                'report_sha256':sha_file(r/'FAILURE_REPORT.md'),'primary_cells':len(primary),'primary_mean_ratio_range':[float(primary.mean_width_ratio.min()),float(primary.mean_width_ratio.max())],
                'confirmation_tasks':0,'no_extra_scientific_route':True})
    print('Generated FAILURE_REPORT.md, ALL_RESULTS.md and stopping-evidence plot from complete verified raw results.')

if __name__=='__main__':main()

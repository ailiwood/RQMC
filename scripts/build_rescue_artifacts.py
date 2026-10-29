"""Generate manuscript numbers, complete tables and plots from complete confirmation."""
import _bootstrap
import json
import shutil
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from rqmc.common import root, write_json, sha_file

CASES=['c_smooth1','c_step','c_exp','c_ridge','c_smoothridge','c_product']
LABELS={'c_smooth1':'Smooth1','c_step':'Step','c_exp':'Exp','c_ridge':'Ridge','c_smoothridge':'Smooth ridge','c_product':'Product'}
BUDGETS=[4096,16384,65536]
METHOD_LABELS={'A':'Original A','B':'Original B','PLUGIN':'Original PLUGIN','PLUGIN_MATCH':'PLUGIN-MATCH',
               'PLUGIN_STAGE':'PLUGIN-STAGE','BUDGET_FIXED':'Budget-specific fixed','A01':'A01','A02':'A02'}


def label(method):
    return METHOD_LABELS.get(method,method.replace('fixed_','Fixed $n=')+'$' if method.startswith('fixed_') else method)


def texnum(x):
    if x==0:return '0'
    if .001<=abs(x)<1000:return f'{x:.4g}'
    exponent=int(math.floor(math.log10(abs(x))))
    return f'${x/10**exponent:.3g}\\times10^{{{exponent}}}$'


def main():
    r=root();source=r/'results/rescue_v1/analysis/confirmation'
    receipt=json.loads((source/'receipt.json').read_text(encoding='utf-8'))
    decision=json.loads((r/'handoff/rescue_confirmation_decision.json').read_text(encoding='utf-8'))
    assert receipt['tasks']==324000 and receipt['intervals']==414000
    summary=pd.read_csv(source/'summary.csv');contrasts=pd.read_csv(source/'contrasts.csv')
    aggregate=pd.read_csv(source/'aggregate.csv');selection=pd.read_csv(source/'selection.csv')
    generated=r/'paper/generated';figures=r/'paper/figures'
    generated.mkdir(exist_ok=True);figures.mkdir(exist_ok=True)
    for name in ['summary.csv','contrasts.csv','aggregate.csv','selection.csv']:
        shutil.copy2(source/name,generated/name)
    a=summary[(summary.method=='A02')&(summary.ci=='ebci')]
    def agg(ref):return aggregate[(aggregate.method=='A02')&(aggregate.reference==ref)&(aggregate.ci=='ebci')].iloc[0]
    numbers={'ConfirmationTasks':str(receipt['tasks']),'ConfirmationIntervals':str(receipt['intervals']),
             'TotalConfirmationCalls':f"{receipt['total_calls']:,}",
             'TotalConfirmationPilotCalls':f"{receipt['pilot_calls']:,}",
             'PrimaryGain':f"{100*(1-agg('fixed_4').geometric_mean_ratio):.2f}",
             'ScheduleGain':f"{100*(1-agg('BUDGET_FIXED').geometric_mean_ratio):.2f}",
             'PluginGain':f"{100*(1-agg('PLUGIN').geometric_mean_ratio):.2f}",
             'StageRatio':f"{agg('PLUGIN_STAGE').geometric_mean_ratio:.4f}",
             'CoverageMin':f'{a.coverage.min():.3f}','CoverageMax':f'{a.coverage.max():.3f}',
             'NumericalFailures':str(receipt['failures']),'EmptyIntervals':str(receipt['empty_intervals']),
             'QualifyingFamilies':str(len({x['case'] for x in decision['qualifying_gain_cells']}))}
    (generated/'numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in numbers.items())+'\n',encoding='utf-8')
    rows=[]
    for case in CASES:
        for N in BUDGETS:
            x=a[(a['case']==case)&(a.budget==N)].iloc[0]
            cells=[]
            for ref in ['fixed_4','BUDGET_FIXED']:
                c=contrasts[(contrasts.method=='A02')&(contrasts.reference==ref)&(contrasts.ci=='ebci')&(contrasts['case']==case)&(contrasts.budget==N)].iloc[0]
                cells.append(f'{c.mean_width_ratio:.3f} [{c.ratio_lo:.3f}, {c.ratio_hi:.3f}]')
            rows.append(f"{LABELS[case]} & {N} & {texnum(x.mean_width)} & {int(x.covered)}/1000 & "+' & '.join(cells)+r' \\')
    main_table=r'''\begin{table}[htbp]
\caption{Complete primary confirmation results for A02. Ratios compare mean EBCI widths; brackets are 95\% Monte Carlo intervals. All pilot calls are charged. Coverage counts have denominator 1000. Full Wilson intervals and all methods appear in the accompanying CSV tables.}\label{tab:primary}
\small\setlength{\tabcolsep}{3pt}
\begin{tabular}{llrrrr}\toprule
Case & $N$ & A02 width & Covered & A02/fixed-4 & A02/budget-fixed\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}\end{table}
'''
    (generated/'primary_table.tex').write_text(main_table,encoding='utf-8')
    rows=[]
    for method in [f'fixed_{n}' for n in [1,2,4,8,16,32,64]]+['A','B','PLUGIN','PLUGIN_MATCH','PLUGIN_STAGE','A01','A02','BUDGET_FIXED']:
        sub=summary[(summary.method==method)&(summary.ci=='ebci')]
        fixed=summary[(summary.method=='fixed_4')&(summary.ci=='ebci')]
        z=sub.merge(fixed,on=['case','budget','ci'],suffixes=('_m','_f'),validate='one_to_one')
        ratio=float(np.exp(np.log(z.mean_width_m/z.mean_width_f).mean()))
        rows.append(f"{label(method)} & {ratio:.4f} & {sub.coverage.min():.3f}--{sub.coverage.max():.3f} & {sub.mean_pilot_calls.mean():.1f}"+r' \\')
    (generated/'ablation_table.tex').write_text(r'''\begin{table}[htbp]
\caption{All allocation variants in confirmation. The width statistic is the equal-cell geometric mean of mean-width ratios to fixed-4. The coverage range is across the 18 primary cells. Mean pilot calls average cells with equal weight. Smoothing is isolated by comparing A01/PLUGIN-MATCH and A02/PLUGIN-STAGE.}\label{tab:ablation}
\begin{tabular}{lrrr}\toprule
Method & Width ratio & Coverage range & Mean pilot calls\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}\end{table}
''',encoding='utf-8')
    methods=[f'fixed_{n}' for n in [1,2,4,8,16,32,64]]+['BUDGET_FIXED','A','B','PLUGIN','PLUGIN_MATCH','PLUGIN_STAGE','A01','A02']
    tables=[]
    for ci,cases in [('ebci',CASES),('hbci',['c_smooth1','c_ridge'])]:
        for case in cases:
            lines=[]
            for method in methods:
                values=[]
                for N in BUDGETS:
                    x=summary[(summary['case']==case)&(summary.budget==N)&(summary.method==method)&(summary.ci==ci)].iloc[0]
                    values.extend([texnum(x.mean_width),f'{x.coverage:.3f}'])
                lines.append(label(method)+' & '+' & '.join(values)+r' \\')
            tables.append(r'\begin{table}[htbp]\caption{'+ci.upper()+' confirmation for '+LABELS[case]+r'''. Each entry is a mean width ($w$) or coverage fraction ($p$), from 1000 complete repetitions. Numerical failures and empty sets are reported in the complete machine-readable tables.}\footnotesize
\begin{tabular}{lrrrrrr}\toprule
 & \multicolumn{2}{c}{4096} & \multicolumn{2}{c}{16384} & \multicolumn{2}{c}{65536}\\
Method & $w$ & $p$ & $w$ & $p$ & $w$ & $p$\\\midrule
'''+ '\n'.join(lines)+r'\bottomrule\end{tabular}\end{table}'+'\n')
    for subset in [CASES[:3],CASES[3:]]:
        lines=[]
        for case in subset:
            for N in BUDGETS:
                values=[]
                for method in ['t_R8','t_R16','t_R32']:
                    x=summary[(summary['case']==case)&(summary.budget==N)&(summary.method==method)&(summary.ci=='t')].iloc[0]
                    values.extend([texnum(x.mean_width),f'{x.coverage:.3f}'])
                lines.append(LABELS[case]+f' & {N} & '+' & '.join(values)+r' \\')
        tables.append(r'''\begin{table}[htbp]\caption{All fixed-replication practical $t$ comparators for the listed cases. These are asymptotic/practical intervals, not distribution-free finite-sample guarantees. $w$ is mean width and $p$ is empirical coverage from 1000 repetitions.}\footnotesize\setlength{\tabcolsep}{3pt}
\begin{tabular}{llrrrrrr}\toprule
 & & \multicolumn{2}{c}{$R=8$} & \multicolumn{2}{c}{$R=16$} & \multicolumn{2}{c}{$R=32$}\\
Case & $N$ & $w$ & $p$ & $w$ & $p$ & $w$ & $p$\\\midrule
'''+ '\n'.join(lines)+r'\bottomrule\end{tabular}\end{table}'+'\n')
    (generated/'all_interval_tables.tex').write_text('\n'.join(tables),encoding='utf-8')
    plt.rcParams.update({'font.size':9.5,'axes.labelsize':9.5,'axes.titlesize':10.5,'legend.fontsize':8.5,'savefig.dpi':240,'pdf.fonttype':42,'ps.fonttype':42})
    def save(fig,name):
        fig.savefig(figures/f'{name}.pdf',bbox_inches='tight');fig.savefig(figures/f'{name}.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(5.6,6.7),constrained_layout=True)
    plotted=['fixed_4','BUDGET_FIXED','PLUGIN','PLUGIN_STAGE','A02']
    colors={'fixed_4':'#666666','BUDGET_FIXED':'#b07732','PLUGIN':'#a14242','PLUGIN_STAGE':'#6f5aa1','A02':'#087f8c'}
    for ax,case in zip(axes.flat,CASES):
        for method in plotted:
            g=summary[(summary['case']==case)&(summary.ci=='ebci')&(summary.method==method)].sort_values('budget')
            ax.plot(g.budget,g.mean_width,marker='o',markersize=3,label=label(method),color=colors[method],linewidth=1.7 if method=='A02' else 1)
        ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks(BUDGETS,[r'$2^{12}$',r'$2^{14}$',r'$2^{16}$'])
        ax.set_title(LABELS[case]);ax.grid(alpha=.2);ax.set_ylabel('Mean EBCI width')
    handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3)
    save(fig,'confirmation_width_budget')
    fig,axes=plt.subplots(1,2,figsize=(5.6,4),constrained_layout=True)
    selected_ratios=contrasts[(contrasts.method=='A02')&(contrasts.ci=='ebci')&contrasts.reference.isin(['fixed_4','BUDGET_FIXED'])].mean_width_ratio
    ratio_norm=TwoSlopeNorm(vmin=min(.15,float(selected_ratios.min())-.01),vcenter=1,vmax=max(1.4,float(selected_ratios.max())+.01))
    for ax,reference in zip(axes,['fixed_4','BUDGET_FIXED']):
        mat=np.array([[contrasts[(contrasts.method=='A02')&(contrasts.reference==reference)&(contrasts.ci=='ebci')&(contrasts['case']==case)&(contrasts.budget==N)].iloc[0].mean_width_ratio for N in BUDGETS] for case in CASES])
        image=ax.imshow(mat,cmap='RdBu_r',norm=ratio_norm,aspect='auto')
        ax.set_xticks(range(3),['4096','16384','65536']);ax.set_yticks(range(6),[LABELS[c] for c in CASES]);ax.set_title('A02 / '+label(reference))
        for i in range(6):
            for j in range(3):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',color='white' if mat[i,j]<.45 else 'black',fontsize=10)
    fig.colorbar(image,ax=axes,label='Mean-width ratio (smaller is better)',shrink=.7)
    save(fig,'confirmation_ratio_matrix')
    fig,ax=plt.subplots(figsize=(5.6,6.2),constrained_layout=True)
    for method,offset,color in [('A02',-.13,'#087f8c'),('t_R16',.13,'#b07732')]:
        g=summary[(summary.method==method)&(summary.ci==('t' if method.startswith('t_') else 'ebci'))].set_index(['case','budget']).loc[[(c,N) for c in CASES for N in BUDGETS]]
        ax.errorbar(g.coverage,np.arange(18)+offset,xerr=[np.maximum(0,g.coverage-g.coverage_wilson_lo),np.maximum(0,g.coverage_wilson_hi-g.coverage)],fmt='o',markersize=3,capsize=2,color=color,label='A02 EBCI' if method=='A02' else r'Practical $t$, $R=16$')
    ax.axvline(.95,color='#444444',linestyle='--',linewidth=1);ax.set_yticks(range(18),[f'{LABELS[c]} / {N}' for c in CASES for N in BUDGETS]);ax.invert_yaxis();ax.set_xlabel('Coverage and 95% Wilson interval');ax.grid(axis='x',alpha=.2);ax.legend(loc='lower left')
    save(fig,'confirmation_coverage')
    fig,ax=plt.subplots(figsize=(5.6,4),constrained_layout=True)
    bottom=np.zeros(18);x=np.arange(18)
    for n,color in zip([1,2,4,8,16,32,64],plt.cm.viridis(np.linspace(.1,.9,7))):
        values=np.array([selection[(selection.method=='A02')&(selection['case']==case)&(selection.budget==N)&(selection.selected_n==n)]['count'].sum()/1000 for case in CASES for N in BUDGETS])
        ax.bar(x,values,bottom=bottom,label=str(n),color=color,width=.8);bottom+=values
    assert np.allclose(bottom,1)
    ax.set_ylim(0,1);ax.set_ylabel('Selected net-size share');ax.set_xticks(np.arange(1,18,3),[LABELS[c] for c in CASES],rotation=20,ha='right');ax.legend(title='n',ncol=7,loc='upper center',bbox_to_anchor=(.5,1.22),frameon=False)
    for boundary in [2.5,5.5,8.5,11.5,14.5]:ax.axvline(boundary,color='white',linewidth=2)
    ax.set_xlabel('Within each group: budgets 4096, 16384, 65536')
    costs=np.array([a[(a['case']==case)&(a.budget==N)].iloc[0].mean_pilot_calls/N*100 for case in CASES for N in BUDGETS])
    second=ax.twinx();second.plot(x,costs,'k.--',markersize=3,linewidth=1);second.set_ylabel('Mean evaluated pilot calls (% of N)');second.set_ylim(0,6.5)
    save(fig,'confirmation_allocation')
    write_json(generated/'artifact_receipt.json',{'tasks':receipt['tasks'],'decision_status':decision['status'],
        'files':{p.relative_to(r/'paper').as_posix():sha_file(p) for p in [*generated.glob('*.tex'),*figures.glob('*.pdf'),*figures.glob('*.png')]},
        'note':'Figures and tables are generated from the complete frozen confirmation; never hand-edited numerical results.'})
    print('Generated complete manuscript numbers/tables and four confirmation figures.')


if __name__=='__main__':main()

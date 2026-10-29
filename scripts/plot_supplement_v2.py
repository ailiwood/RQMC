"""Publication figures and compact tables generated only from complete data."""
import _bootstrap
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import LogLocator, NullFormatter
from rqmc.common import root,write_json,sha_file

r=root();out=r/'paper/figures';gen=r/'paper/generated';out.mkdir(exist_ok=True);gen.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'savefig.bbox':'tight'})
NAMES={'c_smooth1':'Smooth1','c_step':'Step','c_exp':'Exp','c_ridge':'Ridge','c_smoothridge':'Smooth ridge','c_product':'Product',
       's_mvn16':'MVN16','s_mvn32':'MVN32','s_rare3':'Rare 1e-3','s_rare4':'Rare 1e-4','d_smooth1':'Dev smooth1','d_ridge':'Dev ridge'}
fixed=[f'fixed_{n}' for n in (1,2,4,8,16,32,64)];methods=fixed+['A02','PLUGIN_STAGE']
FILES=[]


def save(fig,name):
    fig.savefig(out/f'{name}.pdf');fig.savefig(out/f'{name}.png',dpi=160);plt.close(fig)
    FILES.append(f'paper/figures/{name}.pdf')


def latency(scope,folder):
    folders=[folder,'fixed_development_timing' if scope=='development' else 'fixed_application_timing']
    rows=[]
    for folder_name in folders:
        path=r/f'results/supplement_v2/{folder_name}/timing.jsonl'
        receipt=json.loads(path.with_name('timing.receipt.json').read_text(encoding='utf-8'))
        assert receipt['status']=='COMPLETE'
        for line in path.open(encoding='utf-8'):
            x=json.loads(line);assert x['status']=='ok';e=x['intervals'][x['ci_mode']]
            rows.append({k:x[k] for k in ('case_id','budget','method','rep','ci_mode','total_s','pilot_calls','selection_s','sampling_s','evaluation_s','primary_ci_s','hbci_s')}|
                        {'width':e['width'],'covered':e['covered'],'digest':x['production_means_digest']})
    df=pd.DataFrame(rows);keys=['case_id','budget','method','ci_mode']
    summary=df.groupby(keys).agg(repetitions=('rep','size'),median_total_s=('total_s','median'),mean_total_s=('total_s','mean'),
         total_q25=('total_s',lambda x:x.quantile(.25)),total_q75=('total_s',lambda x:x.quantile(.75)),
         mean_width=('width','mean'),width_mcse=('width',lambda x:x.std(ddof=1)/np.sqrt(len(x))),mean_pilot_calls=('pilot_calls','mean'),mean_selection_s=('selection_s','mean'),
         mean_sampling_s=('sampling_s','mean'),mean_evaluation_s=('evaluation_s','mean'),mean_ebci_s=('primary_ci_s','mean'),mean_hbci_s=('hbci_s','mean')).reset_index()
    assert (summary.repetitions==15).all()
    assert (df.groupby(['case_id','budget','method','rep']).digest.nunique()==1).all()
    summary.to_csv(r/f'results/supplement_v2/{folder}/summary.csv',index=False)
    cells=list(df[['case_id','budget']].drop_duplicates().itertuples(index=False,name=None))
    fig,axes=plt.subplots(len(cells)//2,2,figsize=(6.5,2.4*(len(cells)//2)),squeeze=False)
    colors={'A02':'#0072b2','PLUGIN_STAGE':'#d55e00'}
    for ax,(case,N) in zip(axes.flat,cells):
        g=summary[(summary.case_id==case)&(summary.budget==N)]
        for ci,marker,color in [('ebci','o','#999999'),('hbci','s','#333333')]:
            z=g[g.method.isin(fixed)&(g.ci_mode==ci)].copy();z['n']=z.method.str[6:].astype(int);z=z.sort_values('n')
            ax.errorbar(1000*z.median_total_s,z.mean_width,
                xerr=np.vstack([1000*(z.median_total_s-z.total_q25),1000*(z.total_q75-z.median_total_s)]),
                yerr=z.width_mcse,color=color,marker=marker,markersize=3,capsize=2,linestyle='none',label=f'All fixed n: {ci.upper()}')
            if ci=='hbci':
                for row in z.itertuples():ax.annotate(str(row.n),(1000*row.median_total_s,row.mean_width),xytext=(3,3),textcoords='offset points',fontsize=7)
        for method in colors:
            z=g[g.method==method].set_index('ci_mode')
            ax.plot(1000*z.median_total_s,z.mean_width,color=colors[method],alpha=.45,linewidth=.8)
            for ci,marker in [('ebci','o'),('hbci','s')]:
                row=z.loc[ci]
                ax.errorbar(1000*row.median_total_s,row.mean_width,
                    xerr=np.array([[1000*(row.median_total_s-row.total_q25)],[1000*(row.total_q75-row.median_total_s)]]),
                    yerr=row.width_mcse,
                    marker=marker,color=colors[method],capsize=2,linestyle='none',label=f'{method}: {ci.upper()}')
        ax.set(xscale='log',yscale='log',title=f'{NAMES[case]}, N={N:,}',xlabel='Median total task time (ms)',ylabel='Mean interval width')
        for axis in (ax.xaxis,ax.yaxis):
            axis.set_major_locator(LogLocator(base=10,subs=(1.0,),numticks=6))
            axis.set_minor_locator(LogLocator(base=10,subs=(2.0,5.0),numticks=12))
            axis.set_minor_formatter(NullFormatter())
        ax.grid(alpha=.2)
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8,bbox_to_anchor=(.5,-.02))
    fig.tight_layout(rect=(0,.05,1,1));save(fig,f'supplement_{scope}_cost')


def cross_interval():
    paths={'s1':r/'results/supplement_v2/analysis/s1'}
    # Every fixed-HBCI reference stays visible; no post hoc opponent selection.
    c=pd.read_csv(paths['s1']/'contrasts.csv');s1=pd.read_csv(paths['s1']/'summary.csv')
    cross=c[(c.method=='A02')&(c.ci=='ebci')&(c.reference_ci=='hbci')]
    order=list(s1[['case','budget']].drop_duplicates().itertuples(index=False,name=None))
    mat=np.array([[float(cross[(cross['case']==case)&(cross.budget==N)&(cross.reference==m)].mean_width_ratio.iloc[0])
                   for m in methods] for case,N in order])
    fig,ax=plt.subplots(figsize=(6.5,6.0));im=ax.imshow(mat,cmap='RdBu_r',norm=TwoSlopeNorm(vmin=0,vcenter=1,vmax=2),aspect='auto')
    ax.set_xticks(range(len(methods)),[m.replace('fixed_','n=') for m in methods],rotation=35,ha='right')
    ax.set_yticks(range(len(order)),[f'{NAMES[case]}, {N:,}' for case,N in order])
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',fontsize=7,color='white' if abs(mat[i,j]-1)>.65 else 'black')
    ax.set_title('A02 EBCI / reference HBCI mean widths\nRatio below one favours A02 EBCI')
    fig.colorbar(im,ax=ax,label='Mean-width ratio',ticks=[0,.5,1,1.5,2],fraction=.035,pad=.02);fig.tight_layout();save(fig,'supplement_cross_interval')


def main():
    paths={k:r/f'results/supplement_v2/analysis/{k}' for k in ('s1','s2','s3')}
    for p in paths.values():assert json.loads((p/'receipt.json').read_text(encoding='utf-8'))['tasks']>0
    cross_interval()
    # Full new matrix: seven fixed sizes plus both adaptive policies, both CIs.
    s2=pd.read_csv(paths['s2']/'summary.csv');cases=['s_mvn16','s_mvn32','s_rare3','s_rare4']
    fig,axes=plt.subplots(4,2,figsize=(6.5,8.8))
    for i,case in enumerate(cases):
        for j,N in enumerate((16384,65536)):
            ax=axes[i,j];g=s2[(s2['case']==case)&(s2.budget==N)]
            for ci,color,marker in [('ebci','#4d4d4d','o'),('hbci','#009e73','s')]:
                f=g[g.method.isin(fixed)&(g.ci==ci)].copy();f['n']=f.method.str[6:].astype(int);f=f.sort_values('n')
                ax.plot(f.n,f.mean_width,color=color,marker=marker,markersize=3,label=f'Fixed, {ci.upper()}')
                for m,col,style in [('A02','#0072b2','--'),('PLUGIN_STAGE','#d55e00',':')]:
                    width=float(g[(g.method==m)&(g.ci==ci)].mean_width.iloc[0])
                    ax.axhline(width,color=col,linestyle=style,alpha=1 if ci=='ebci' else .45,label=f'{m}, {ci.upper()}')
            ax.set(xscale='log',yscale='log',title=f'{NAMES[case]}, N={N:,}',xlabel='Fixed points per scramble n',ylabel='Mean width')
            ax.set_xticks([1,2,4,8,16,32,64],[1,2,4,8,16,32,64]);ax.grid(alpha=.2)
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='lower center',ncol=3,bbox_to_anchor=(.5,-.01),fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));save(fig,'supplement_new_matrix')
    # Main compact new-case contrast table, without hiding either interval.
    lines=['\\begin{table}[htbp]','\\caption{Secondary application/stress results for A02. Ratios compare cellwise mean widths after pilot costs; f4 denotes fixed-4, and EB/HB identify the interval. Each coverage count is out of 1000 repetitions; the last column is the all-zero pilot rate. All fixed sizes and matched controls remain in the accompanying CSV and Figure~\\ref{fig:suppmatrix}.}\\label{tab:suppcases}',
           '\\centering\\small\\setlength{\\tabcolsep}{3pt}','\\begin{tabular}{llrrrrrr}','\\toprule','Case & $N$ & EB/f4EB & EB/f4HB & HB/f4HB & EB cover & HB cover & Zero pilot\\\\\\midrule']
    comparisons=pd.read_csv(paths['s2']/'contrasts.csv');pilot=pd.read_csv(paths['s2']/'pilot_summary.csv')
    for case in cases:
        for N in (16384,65536):
            g=comparisons[(comparisons['case']==case)&(comparisons.budget==N)&(comparisons.reference=='fixed_4')]
            ratio=lambda ci,ref:float(g[(g.ci==ci)&(g.reference_ci==ref)].mean_width_ratio.iloc[0])
            coverage=int(s2[(s2['case']==case)&(s2.budget==N)&(s2.method=='A02')&(s2.ci=='ebci')].covered.iloc[0])
            hbcoverage=int(s2[(s2['case']==case)&(s2.budget==N)&(s2.method=='A02')&(s2.ci=='hbci')].covered.iloc[0])
            zero=float(pilot[(pilot['case']==case)&(pilot.budget==N)&(pilot.method=='A02')].zero_pilot_rate.iloc[0])
            lines.append(f'{NAMES[case]} & {N:,} & {ratio("ebci","ebci"):.3f} & {ratio("ebci","hbci"):.3f} & {ratio("hbci","hbci"):.3f} & {coverage} & {hbcoverage} & {zero:.3f}\\\\')
    lines+=['\\bottomrule','\\end{tabular}','\\end{table}']
    (gen/'supplement_case_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Default pilot16 reuses S2; all sensitivity variants remain displayed.
    s3=pd.read_csv(paths['s3']/'summary.csv');a3=pd.read_csv(paths['s3']/'pilot_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(6.5,5.6))
    for j,case in enumerate(('s_mvn16','s_rare4')):
        for ci,color,marker in [('ebci','#0072b2','o'),('hbci','#009e73','s')]:
            g=s3[(s3['case']==case)&(s3.ci==ci)].copy();g['K']=g.method.str.split('K').str[-1].astype(int);g=g.sort_values('K')
            axes[0,j].errorbar(g.K,g.mean_width,yerr=1.96*g.width_mcse,color=color,marker=marker,label=ci.upper(),capsize=3)
        g=a3[a3['case']==case].copy();g['K']=g.method.str.split('K').str[-1].astype(int);g=g.sort_values('K')
        axes[1,j].plot(g.K,g.mean_pilot_calls,marker='o',color='#4d4d4d')
        axes[0,j].set(title=NAMES[case],xlabel='Pilot scrambles K',ylabel='Mean interval width');axes[0,j].legend()
        axes[1,j].set(xlabel='Pilot scrambles K',ylabel='Mean pilot evaluations')
        for ax in axes[:,j]:ax.set_xticks([8,16,32]);ax.grid(alpha=.2)
    fig.tight_layout();save(fig,'supplement_pilot_sensitivity')
    latency('development','isolated_timing');latency('application','application_timing')
    write_json(r/'handoff/supplement_figures.json',{'status':'GENERATED_REQUIRES_VISUAL_REVIEW','figures':{p:sha_file(r/p) for p in FILES},
        'table':'paper/generated/supplement_case_table.tex','script_sha256':sha_file(r/'scripts/plot_supplement_v2.py')})
    print(json.dumps({'generated_figures':FILES,'table':'paper/generated/supplement_case_table.tex'}))


if __name__=='__main__':main()

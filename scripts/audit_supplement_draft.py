"""Check old/new seals, complete supplementary evidence and manuscript metadata."""
import _bootstrap
import json
import re
import csv
import pandas as pd
from rqmc.common import root,sha_file,write_json,digest


def main():
    r=root()
    def read(rel):return json.loads((r/rel).read_text(encoding='utf-8'))
    old=read('state/rescue_v1/confirmation_freeze.json');new=read('state/supplement_v2/confirmation_freeze.json')
    changes={}
    for label,manifest in [('old',old['full_source_manifest']),('supplement',new['runtime_sources'])]:
        changes[label]=[rel for rel,h in manifest.items() if not (r/rel).is_file() or sha_file(r/rel)!=h]
    assert not any(changes.values()),changes
    assert all(read('handoff/rescue_confirmation_decision.json')['checks'].values())
    original=read('results/rescue_v1/analysis/confirmation/receipt.json')
    for method,h in original['raw_sha256'].items():assert sha_file(r/f'results/rescue_v1/confirmation/{method}.jsonl')==h
    rec={k:read(f'results/supplement_v2/analysis/{k}/receipt.json') for k in ('s1','s2','s3')}
    assert rec['s1']['tasks']==162000 and rec['s2']['tasks']==72000 and rec['s3']['tasks']==4000
    for receipt in rec.values():
        for rel,h in receipt['raw_sha256'].items():assert sha_file(r/rel)==h
    for mode,count in [('isolated_timing',540),('application_timing',360),('fixed_development_timing',1080),('fixed_application_timing',720)]:
        receipt=read(f'results/supplement_v2/{mode}/timing.receipt.json')
        assert receipt['status']=='COMPLETE' and receipt['total_tasks']==count
        assert receipt['raw_sha256']==sha_file(r/f'results/supplement_v2/{mode}/timing.jsonl')
    observed=read('results/supplement_v2/timing_process_observation/receipt.json')
    assert observed['status']=='BOTH_TIMING_PROCESS_LIFETIMES_OBSERVED'
    for scope in ('fixed_development','fixed_application'):
        assert read(f'results/supplement_v2/{scope}_timing/external_process_receipt.json')['status']=='COMPLETE_PROCESS_TIME_RECORDED'
    maintex=(r/'paper/manuscript.tex').read_text(encoding='utf-8');settings=(r/'paper/draft_settings.tex').read_text(encoding='utf-8')
    alltex=maintex+'\n'+'\n'.join(p.read_text(encoding='utf-8') for p in (r/'paper/sections').glob('*.tex'))
    assert '\\funding{This research received no external funding.}' in maintex
    assert '\\acknowledgments{The authors thank the School of General Education' in maintex
    assert 'All code used in this study is publicly available at \\url{https://github.com/ailiwood/RQMC}' in maintex
    assert 'The authors declare no conflicts of interest.' in maintex
    assert 'During the preparation' not in maintex and 'Disclosure draft' not in maintex
    assert 'Draft for human review; not submitted' not in settings
    assert 'Review draft: Not submitted' not in settings
    assert '\\conflictsofinterest{The authors declare no conflicts of interest.}' in maintex
    for text in ('Guo Lina','Sun Chengyu','Shandong Huayu University of Technology','253034'):assert text in settings
    assert settings.index('Guo Lina')<settings.index('Sun Chengyu')
    assert 'AUTHOR\\_CONFIRM' not in alltex+settings
    abstract=maintex.split('\\abstract{',1)[1].split('}\n\\begin{document}',1)[0]
    assert len(abstract.split())<=200
    bib=(r/'paper/references.bib').read_text(encoding='utf-8');keys=set(re.findall(r'@\w+\{([^,]+),',bib))
    cited={k.strip() for group in re.findall(r'\\cite\{([^}]+)\}',alltex) for k in group.split(',')}
    ledger=read('docs/reference_claim_ledger.json')
    assert keys==cited=={x['key'] for x in ledger['items']},(keys,cited)
    primary=pd.read_csv(r/'results/rescue_v1/analysis/confirmation/aggregate.csv');claims=[]
    for reference in ('fixed_4','BUDGET_FIXED','PLUGIN_STAGE'):
        row=primary[(primary.method=='A02')&(primary.reference==reference)&(primary.ci=='ebci')].iloc[0]
        assert f'{row.geometric_mean_ratio:.4f}' in alltex
        claims.append({'claim':f'Original A02/{reference} EBCI ratio','value':float(row.geometric_mean_ratio),
                       'evidence':'results/rescue_v1/analysis/confirmation/aggregate.csv','scope':'Unchanged original primary/secondary fixed matrix'})
    component=primary[(primary.method=='A01')&(primary.reference=='A')&(primary.ci=='ebci')].iloc[0]
    for key in ('geometric_mean_ratio','ratio_lo','ratio_hi'):assert f'{component[key]:.4f}' in alltex
    claims.append({'claim':'A01/original-A objective contrast','value':float(component.geometric_mean_ratio),
                   'evidence':'results/rescue_v1/analysis/confirmation/aggregate.csv','scope':'Secondary; same smoother and fixed pilot design'})
    for kind in ('s1','s2','s3'):
        summary=pd.read_csv(r/f'results/supplement_v2/analysis/{kind}/summary.csv')
        claims.extend([{'claim':f'{kind} task count','value':rec[kind]['tasks'],
                        'evidence':f'results/supplement_v2/analysis/{kind}/receipt.json','scope':'Separate secondary validation'},
                       {'claim':f'{kind} reference-sensitive classifications','value':int(summary.reference_ambiguous_coverages.sum()),
                        'evidence':f'results/supplement_v2/analysis/{kind}/summary.csv','scope':'Numeric sensitivity only, not a formal reference certificate'}])
    s1=pd.read_csv(r/'results/supplement_v2/analysis/s1/aggregate.csv')
    for ci,ref,refci in [('hbci','fixed_4','hbci'),('ebci','fixed_4','hbci'),('hbci','PLUGIN_STAGE','hbci')]:
        row=s1[(s1.method=='A02')&(s1.ci==ci)&(s1.reference==ref)&(s1.reference_ci==refci)].iloc[0]
        for key in ('geometric_mean_ratio','ratio_lo','ratio_hi'):assert f'{row[key]:.4f}' in alltex
        claims.append({'claim':f'S1 A02 {ci}/{ref} {refci} ratio','value':float(row.geometric_mean_ratio),
                       'evidence':'results/supplement_v2/analysis/s1/aggregate.csv','scope':'Secondary18-cell deterministic completion; zero new independent repetitions'})
    s2=pd.read_csv(r/'results/supplement_v2/analysis/s2/aggregate.csv')
    s2_specs=[
        ('A02','ebci','fixed_4','ebci','S2 A02 EBCI/fixed-4 EBCI geometric mean width ratio'),
        ('A02','ebci','fixed_1','ebci','S2 A02 EBCI/fixed-1 EBCI geometric mean width ratio'),
        ('A02','ebci','PLUGIN_STAGE','ebci','S2 A02 EBCI/PLUGIN-STAGE EBCI geometric mean width ratio'),
        ('A02','ebci','fixed_4','hbci','S2 A02 EBCI/fixed-4 HBCI geometric mean width ratio'),
        ('A02','hbci','fixed_4','hbci','S2 A02 HBCI/fixed-4 HBCI geometric mean width ratio')]
    for method,ci,reference,reference_ci,label in s2_specs:
        row=s2[(s2.method==method)&(s2.ci==ci)&(s2.reference==reference)&(s2.reference_ci==reference_ci)].iloc[0]
        for key in ('geometric_mean_ratio','ratio_lo','ratio_hi'):assert f'{row[key]:.4f}' in alltex
        claims.append({'claim':label,'value':float(row.geometric_mean_ratio),
                       'evidence':'results/supplement_v2/analysis/s2/aggregate.csv',
                       'scope':'Eight secondary cells; descriptive Monte Carlo interval; no multiplicity-adjusted primary test'})
    s2cells=pd.read_csv(r/'results/supplement_v2/analysis/s2/contrasts.csv')
    for budget in (16384,65536):
        row=s2cells[(s2cells.case=='s_mvn32')&(s2cells.budget==budget)&(s2cells.method=='A02')&
                    (s2cells.ci=='ebci')&(s2cells.reference=='fixed_4')&(s2cells.reference_ci=='ebci')].iloc[0]
        assert f'{row.mean_width_ratio:.4f}' in alltex
        claims.append({'claim':f'S2 MVN32 A02 EBCI/fixed-4 EBCI ratio at N={budget}',
                       'value':float(row.mean_width_ratio),'evidence':'results/supplement_v2/analysis/s2/contrasts.csv',
                       'scope':'Unfavorable secondary cell retained'})
    s3=pd.read_csv(r/'results/supplement_v2/analysis/s3/aggregate.csv')
    for ref in ('A02_K8','A02_K32'):
        for ci in ('ebci','hbci'):
            row=s3[(s3.method=='A02_K16')&(s3.ci==ci)&(s3.reference==ref)&(s3.reference_ci==ci)].iloc[0]
            assert f'{row.geometric_mean_ratio:.4f}' in alltex
            claims.append({'claim':f'S3 A02 K16 {ci}/{ref} {ci} geometric mean width ratio',
                           'value':float(row.geometric_mean_ratio),'evidence':'results/supplement_v2/analysis/s3/aggregate.csv',
                           'scope':'Two-case pilot-count sensitivity; no equivalence or winner claim'})
    claims.append({'claim':'Completed isolated timing records','value':2700,
                   'evidence':'results/supplement_v2/*timing/timing.receipt.json',
                   'scope':'Four scopes; 15 repetitions per cell; 1350 matched production-digest pairs'})
    for scope,folder in [('original','isolated_timing'),('application','application_timing'),
                         ('fixed development','fixed_development_timing'),('fixed application','fixed_application_timing')]:
        p=(r/'results/supplement_v2'/folder/'external_process_receipt.json')
        if p.is_file():
            duration=json.loads(p.read_text(encoding='utf-8'))['complete_process_wall_s']
        else:
            obs=read('results/supplement_v2/timing_process_observation/receipt.json')['scopes'][scope]
            duration=(obs['complete_process_wall_lower_s']+obs['complete_process_wall_upper_s'])/2
        claims.append({'claim':f'{scope} timing process duration (seconds)','value':float(duration),
                       'evidence':f'results/supplement_v2/{folder}/external_process_receipt.json' if p.is_file() else 'results/supplement_v2/timing_process_observation/receipt.json',
                       'scope':'Observed wall time including startup/setup/teardown; not a time-budget theorem'})
    hbref=read('state/supplement_v2/development_hb_reference.json')
    assert hbref['development_summary_sha256']==sha_file(r/'results/rescue_v1/analysis/development/summary.csv')
    assert hbref['selected_reference']=='fixed_4'
    with (r/'docs/supplement_numerical_claim_ledger.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['claim','value','evidence','scope']);w.writeheader();w.writerows(claims)
    build=read('handoff/publication_pdf_build_2026-10-29.json')
    assert build['pdf_sha256']==sha_file(r/'paper/manuscript.pdf') and not build['undefined_references'] and not build['overfull_hbox_pt']
    paths=['paper/manuscript.tex','paper/draft_settings.tex','paper/references.bib','paper/template/provenance.json']
    for folder,suffixes in [('paper/Definitions',{'.tex','.cls','.bst','.sty','.eps','.pdf'}),('paper/sections',{'.tex'}),('paper/generated',{'.tex'}),('paper/figures',{'.pdf'})]:
        paths.extend(p.relative_to(r).as_posix() for p in (r/folder).iterdir() if p.is_file() and p.suffix in suffixes)
    write_json(r/'paper/source_manifest.json',sorted(paths))
    write_json(r/'handoff/publication_draft_audit_2026-10-29.json',{'status':'SEALS_COMPLETE_EVIDENCE_METADATA_AND_BUILD_CHECKED',
        'sealed_changes':changes,'original_freeze_signature':old['signature'],'supplement_freeze_signature':new['signature'],
        'original_raw_methods_verified':len(original['raw_sha256']),'supplement_counts':{k:v['tasks'] for k,v in rec.items()},
        'timing_tasks':2700,'abstract_words':len(abstract.split()),'citation_count':len(keys),'pages':build['pages'],
        'pdf_sha256':build['pdf_sha256'],'source_files':len(paths),'coauthor_final_approval_confirmed':False})
    print(json.dumps({'sealed_changes':changes,'pages':build['pages'],'citations':len(keys),'abstract_words':len(abstract.split())}))


if __name__=='__main__':main()

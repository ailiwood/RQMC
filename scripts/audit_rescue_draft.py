"""Check scientific seals, manuscript claim evidence and actual build metadata."""
import _bootstrap
import csv
import json
import re
import pandas as pd
from rqmc.common import root, sha_file, write_json


def main():
    r=root();freeze=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    changes={}
    for group in ['runtime_sources','protocol_hashes','full_source_manifest']:
        changes[group]=[p for p,h in freeze[group].items() if not (r/p).is_file() or sha_file(r/p)!=h]
    assert not changes['runtime_sources'] and not changes['protocol_hashes'],changes
    assert not changes['full_source_manifest'],changes
    assert sha_file(r/freeze['source_snapshot'])==freeze['source_snapshot_sha256']
    decision=json.loads((r/'handoff/rescue_confirmation_decision.json').read_text(encoding='utf-8'))
    assert all(decision['checks'].values())
    assert decision['freeze_signature']==freeze['signature']
    receipt=json.loads((r/'results/rescue_v1/analysis/confirmation/receipt.json').read_text(encoding='utf-8'))
    for method,h in receipt['raw_sha256'].items():
        assert sha_file(r/f'results/rescue_v1/confirmation/{method}.jsonl')==h
    aggregate=pd.read_csv(r/'results/rescue_v1/analysis/confirmation/aggregate.csv')
    results=(r/'paper/sections/results.tex').read_text(encoding='utf-8')
    claims=[]
    for ci,ref in [('ebci','fixed_4'),('ebci','BUDGET_FIXED'),('ebci','PLUGIN'),('ebci','PLUGIN_STAGE'),('hbci','fixed_4'),('hbci','BUDGET_FIXED'),('hbci','PLUGIN_STAGE')]:
        row=aggregate[(aggregate.method=='A02')&(aggregate.reference==ref)&(aggregate.ci==ci)].iloc[0]
        for field in ['geometric_mean_ratio','ratio_lo','ratio_hi']:
            assert f'{row[field]:.4f}' in results,(ci,ref,field)
        claims.append({'claim':f'A02/{ref} {ci} aggregate mean-width ratio',
                       'value':float(row.geometric_mean_ratio),'lower':float(row.ratio_lo),'upper':float(row.ratio_hi),
                       'evidence':'results/rescue_v1/analysis/confirmation/aggregate.csv','scope':f'{int(row.cells)} fixed cells; simulation uncertainty only'})
    summary=pd.read_csv(r/'results/rescue_v1/analysis/confirmation/summary.csv')
    candidate=summary[(summary.method=='A02')&(summary.ci=='ebci')]
    claims.extend([
        {'claim':'Confirmation tasks/intervals/calls/pilot calls','value':f"{receipt['tasks']}/{receipt['intervals']}/{receipt['total_calls']}/{receipt['pilot_calls']}",'evidence':'results/rescue_v1/analysis/confirmation/receipt.json','scope':'Complete confirmation only'},
        {'claim':'Candidate primary coverage range','value':f'{candidate.coverage.min():.3f}--{candidate.coverage.max():.3f}','evidence':'results/rescue_v1/analysis/confirmation/summary.csv','scope':'18 cells; binomial uncertainty in CSV and Figure 3'},
        {'claim':'Useful-gain cells/families','value':'8/3','evidence':'handoff/rescue_confirmation_decision.json','scope':'Point threshold plus adjusted superiority, not simultaneous 10% bound'},
        {'claim':'Best retrospective common fixed comparison','value':'0.8126','evidence':'handoff/rescue_robustness_review.json','scope':'Secondary optimistic reference; no new primary hypothesis'},
        {'claim':'Timing and t degeneracy','value':'108 timing tasks; 844 zero-width noncovering t_R8 Step intervals','evidence':'handoff/rescue_latency_and_t_audit.json','scope':'Descriptive timing on two development cases; t cell N4096'},
        {'claim':'Predictor moments and constant limit','value':'Equations 11--18; factor 3.0084953965','evidence':'tests/test_rescue.py; validation/current/rescue_constant_limit.json; handoff/rescue_math_audit.md','scope':'Exact identities/constant special case; general score heuristic'},
        {'claim':'Scientific numerical replay','value':'972 exact matches; complete 324000-row analysis byte identical','evidence':'handoff/rescue_reproducibility_receipt.json','scope':'Same locked machine; no independent repetitions added'}])
    with (r/'docs/rescue_numerical_claim_ledger.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['claim','value','lower','upper','evidence','scope']);writer.writeheader();writer.writerows(claims)
    ledger_path=r/'docs/rescue_reference_claim_ledger.json'
    ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
    bib=(r/'paper/references.bib').read_text(encoding='utf-8')
    keys=set(re.findall(r'@\w+\{([^,]+),',bib))
    main=(r/'paper/manuscript.tex').read_text(encoding='utf-8')
    tex=main+'\n'+'\n'.join(p.read_text(encoding='utf-8') for p in (r/'paper/sections').glob('*.tex'))
    cited=set(k.strip() for s in re.findall(r'\\cite\{([^}]+)\}',tex) for k in s.split(','))
    assert keys==cited=={x['key'] for x in ledger['items']}
    abstract=main.split('\\abstract{',1)[1].split('}\n\\begin{document}',1)[0]
    assert len(abstract.split())<=200,len(abstract.split())
    ledger['status']='SOURCE_CLAIMS_AND_NUMERICAL_EVIDENCE_REVIEWED'
    ledger['numerical_ledger']='docs/rescue_numerical_claim_ledger.csv'
    ledger['citation_keys_match_bibliography']=True
    write_json(ledger_path,ledger)
    fields=['key','doi','claim','read_level','source','local_evidence']
    with (r/'docs/rescue_reference_claim_ledger.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:x.get(k,'') for k in fields} for x in ledger['items'])
    build=json.loads((r/'handoff/rescue_pdf_build.json').read_text(encoding='utf-8'))
    assert build['pdf_sha256']==sha_file(r/'paper/manuscript.pdf') and build['pages']==23
    assert not build['undefined_references'] and not build['overfull_hbox_pt']
    write_json(r/'handoff/rescue_draft_audit.json',{
        'status':'SCIENTIFIC_SEALS_CLAIMS_AND_BUILD_CHECKED','frozen_signature':freeze['signature'],
        'changed_sealed_files':changes,'confirmation_raw_hashes_checked':len(receipt['raw_sha256']),
        'citation_keys':sorted(keys),'citation_count':len(keys),'abstract_words':len(abstract.split()),
        'numerical_ledger':'docs/rescue_numerical_claim_ledger.csv','pdf_sha256':build['pdf_sha256'],
        'limitations':'This same-session automated check does not replace human scientific review or the separate visual inspection.'})
    paths=['paper/manuscript.tex','paper/draft_settings.tex','paper/references.bib','paper/template/provenance.json']
    for folder,suffixes in [('paper/Definitions',{'.tex','.cls','.bst','.sty','.eps','.pdf'}),('paper/sections',{'.tex'}),('paper/generated',{'.tex'}),('paper/figures',{'.pdf'})]:
        paths.extend(p.relative_to(r).as_posix() for p in (r/folder).iterdir() if p.is_file() and p.suffix in suffixes)
    write_json(r/'paper/source_manifest.json',sorted(paths))
    print(json.dumps({'sealed_file_changes':changes,'abstract_words':len(abstract.split()),'citations':len(keys),'source_files':len(paths)}))


if __name__=='__main__':main()

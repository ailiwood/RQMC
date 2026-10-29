"""Build and verify a portable, explicit research-evidence bundle."""
import _bootstrap
import hashlib
import json
import zipfile
from rqmc.common import root, safe_relative, sha_file, write_json


def main():
    r=root()
    def read(rel):return json.loads((r/rel).read_text(encoding='utf-8'))
    decision=read('handoff/rescue_confirmation_decision.json');assert all(decision['checks'].values())
    replay=read('handoff/rescue_reproducibility_receipt.json');assert replay['matched_tasks']==972
    visual=read('handoff/rescue_pdf_visual_review.json');assert len(visual['pages'])==23 and not visual['unresolved_visual_defects']
    assert visual['pdf_sha256']==sha_file(r/'paper/manuscript.pdf')
    source=read('handoff/manuscript_source_reproduction.json')
    assert all(x['rendered_pixels_identical'] and x['text_identical'] for x in source['pages'])
    excluded={'handoff/rqmc_rescue_reproducibility.zip','handoff/rqmc_rescue_reproducibility.sha256','handoff/rescue_package_receipt.json','handoff/rescue_package_manifest.json'}
    rels={'.project-root','AGENTS.md','研究设计_原文.md','研究设计_72小时执行补充.md',
          'requirements.txt','requirements-fast.txt','requirements-lock.txt',
          'RESEARCH_REPORT.md','REPRODUCE_RESCUE.md','task_plan.md','notes.md',
          '当前研究入口.md','最新研究路线设计.md','evidence/original_study_20261027.zip',
          'paper/manuscript.pdf','paper/source_manifest.json','paper/template/provenance.json','paper/rendered/render_manifest.json'}
    allowed={'.py','.md','.json','.jsonl','.csv','.txt','.png','.pdf','.svg','.zip','.tex','.cls','.bst','.sty','.eps','.sha256'}
    folders=['rqmc','scripts','tests','config','state','handoff','results/raw','results/analysis',
             'results/summary','results/figures','results/benchmark','results/rescue_v1','review',
             'paper/sections','paper/generated','paper/figures','paper/Definitions']
    for folder in folders:
        for p in (r/folder).rglob('*'):
            rel=p.relative_to(r).as_posix()
            if p.is_file() and p.suffix.lower() in allowed and '__pycache__' not in p.parts and rel not in excluded:
                rels.add(rel)
    for p in (r/'docs').iterdir():
        if p.is_file() and p.suffix in {'.md','.json','.csv'}:rels.add(p.relative_to(r).as_posix())
    for p in (r/'docs/source_records').rglob('*'):
        if p.is_file() and (p.suffix=='.json' or p.name.startswith('confseq_')):
            rels.add(p.relative_to(r).as_posix())
    for p in (r/'validation/current').iterdir():
        if p.is_file() and p.suffix in {'.json','.txt','.log'}:rels.add(p.relative_to(r).as_posix())
    rels.update(read('paper/source_manifest.json'))
    records=[]
    for rel in sorted(rels):
        p=safe_relative(r,rel)
        assert p.is_file() and not p.is_symlink(),rel
        assert not any(x in p.parts for x in ['.venv','.runtime','.tmp','.cache','.git'])
        records.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha_file(p)})
    manifest=r/'handoff/rescue_package_manifest.json';write_json(manifest,records)
    target=r/'handoff/rqmc_rescue_reproducibility.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as z:
        for record in records:z.write(safe_relative(r,record['path']),record['path'])
        z.write(manifest,'handoff/rescue_package_manifest.json')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))==len(records)+1
        for record in records:
            # Stream large raw members rather than loading the bundle in memory.
            h=hashlib.sha256()
            with z.open(record['path']) as f:
                while chunk:=f.read(1024*1024):h.update(chunk)
            assert h.hexdigest()==record['sha256'],record['path']
    receipt={'status':'COMPLETE_BUNDLE_ALL_MEMBER_HASHES_VERIFIED','path':target.relative_to(r).as_posix(),
             'sha256':sha_file(target),'bytes':target.stat().st_size,'files':len(records)+1,
             'manifest_sha256':sha_file(manifest),'confirmation_tasks':324000,'confirmation_intervals':414000,
             'scientific_replay_tasks':972,'complete_analysis_reproduced':True,'source_pdf_pages_reproduced':23,
             'original_negative_evidence_preserved':True,
             'historical_evidence_archive':'evidence/original_study_20261027.zip',
             'organization_review':'review/2026-10-29/organization_receipt.json',
             'excluded':['Environments/executables/fonts/caches/scratch','Third-party full article PDFs/HTML and indexing workbooks','Page PNGs regenerable from the included final PDF; their hashes/review receipt retained'],
             'limits':'Same-machine numerical/TeX reproduction; author declarations and independent human review pending. No external upload or submission.'}
    write_json(r/'handoff/rescue_package_receipt.json',receipt)
    (r/'handoff/rqmc_rescue_reproducibility.sha256').write_text(receipt['sha256']+'  rqmc_rescue_reproducibility.zip\n',encoding='ascii')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

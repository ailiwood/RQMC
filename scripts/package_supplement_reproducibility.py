"""Explicit, stream-verified final bundle, retaining original and new evidence."""
import _bootstrap
import hashlib
import json
import zipfile
from rqmc.common import root,safe_relative,sha_file,write_json


def main():
    r=root()
    def read(rel):return json.loads((r/rel).read_text(encoding='utf-8'))
    audit=read('handoff/supplement_draft_audit_final.json');assert not any(audit['sealed_changes'].values())
    visual=read('handoff/supplement_pdf_visual_review_final.json')
    assert visual['pdf_sha256']==sha_file(r/'paper/manuscript.pdf') and not visual['unresolved_visual_defects']
    assert len(visual['pages'])==audit['pages'] and all(x['visual_review']=='PASSED' for x in visual['pages'])
    repro=read('handoff/supplement_reproducibility_receipt.json');assert repro['matched_scientific_tasks']==228
    source=read('handoff/manuscript_source_reproduction_final.json')
    assert source['status']=='ISOLATED_SOURCE_COMPILED_AND_ALL_PAGE_CONTENT_REPRODUCED'
    assert len(source['pages'])==audit['pages'] and all(x['rendered_pixels_identical'] and x['text_identical'] for x in source['pages'])
    original=read('handoff/rescue_reproducibility_receipt.json');assert original['matched_tasks']==972
    excluded={'handoff/rqmc_rescue_reproducibility.zip','handoff/rqmc_rescue_reproducibility.sha256',
              'handoff/rqmc_supplement_v2_reproducibility.zip','handoff/rqmc_supplement_v2_reproducibility.sha256',
              'handoff/supplement_package_manifest.json','handoff/supplement_package_receipt.json',
              'handoff/rqmc_supplement_v2_reproducibility_final.zip',
              'handoff/rqmc_supplement_v2_reproducibility_final.sha256',
              'handoff/supplement_package_manifest_final.json','handoff/supplement_package_receipt_final.json',
              'handoff/rqmc_supplement_v2_reproducibility_closeout.zip',
              'handoff/rqmc_supplement_v2_reproducibility_closeout.sha256',
              'handoff/supplement_package_manifest_closeout.json','handoff/supplement_package_receipt_closeout.json',
              'handoff/rqmc_supplement_v2_reproducibility_closeout_v2.zip',
              'handoff/rqmc_supplement_v2_reproducibility_closeout_v2.sha256',
              'handoff/supplement_package_manifest_closeout_v2.json','handoff/supplement_package_receipt_closeout_v2.json'}
    rels={'.project-root','AGENTS.md','研究设计_原文.md','研究设计_72小时执行补充.md',
          'requirements.txt','requirements-fast.txt','requirements-lock.txt','RESEARCH_REPORT.md',
          'REPRODUCE_RESCUE.md','REPRODUCE_SUPPLEMENT.md','task_plan.md','notes.md','当前研究入口.md','最新研究路线设计.md',
          'evidence/original_study_20261027.zip','paper/manuscript.pdf','paper/source_manifest.json',
          'paper/rendered/render_manifest.json'}
    allowed={'.py','.md','.json','.jsonl','.csv','.txt','.log','.png','.pdf','.svg','.zip','.tex','.cls','.bst','.sty','.eps','.sha256','.whl'}
    folders=['rqmc','supplement','scripts','tests','config','state','handoff','results/rescue_v1','results/supplement_v2',
             'results/benchmark','review','paper/sections','paper/generated','paper/figures','paper/Definitions','validation_dependencies']
    for folder in folders:
        for p in (r/folder).rglob('*'):
            rel=p.relative_to(r).as_posix()
            if (p.is_file() and p.suffix.lower() in allowed and '__pycache__' not in p.parts
                    and rel not in excluded and not rel.startswith('state/supplement_v2/visual_contact_sheets/')):
                rels.add(rel)
    for p in (r/'docs').iterdir():
        if p.is_file() and p.suffix in {'.md','.json','.csv'}:rels.add(p.relative_to(r).as_posix())
    for p in (r/'docs/source_records').rglob('*'):
        if p.is_file() and (p.suffix=='.json' or p.name.startswith('confseq_') or p.name=='scipy_qmvnt.py.txt'):
            rels.add(p.relative_to(r).as_posix())
    for p in (r/'validation/current').iterdir():
        if p.is_file() and p.suffix in {'.json','.txt','.log','.csv'}:rels.add(p.relative_to(r).as_posix())
    rels.update(read('paper/source_manifest.json'))
    records=[]
    for rel in sorted(rels):
        p=safe_relative(r,rel);assert p.is_file() and not p.is_symlink(),rel
        assert not any(part in p.parts for part in ('.venv','.runtime','.tmp','.cache','.git'))
        records.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha_file(p)})
    manifest=r/'handoff/supplement_package_manifest_closeout_v2.json';write_json(manifest,records)
    target=r/'handoff/rqmc_supplement_v2_reproducibility_closeout_v2.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as z:
        for entry in records:z.write(safe_relative(r,entry['path']),entry['path'])
        z.write(manifest,manifest.relative_to(r).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==len(records)+1
        for entry in records:
            h=hashlib.sha256()
            with z.open(entry['path']) as f:
                while data:=f.read(2**20):h.update(data)
            assert h.hexdigest()==entry['sha256'],entry['path']
    receipt={'status':'COMPLETE_SUPPLEMENT_BUNDLE_ALL_MEMBER_HASHES_VERIFIED','path':target.relative_to(r).as_posix(),
             'sha256':sha_file(target),'bytes':target.stat().st_size,'files':len(records)+1,
             'manifest_sha256':sha_file(manifest),'original_confirmation_tasks':324000,'original_intervals':414000,
             'new_confirmation_tasks':72000,'new_sensitivity_tasks':4000,'deterministic_hbci_replays':108000,
             'isolated_timing_tasks':2700,'scientific_subset_replays':{'original':972,'supplement':228},
             'all_supplement_analysis_outputs_byte_reproduced':True,'source_pdf_pages_reproduced':audit['pages'],
             'original_negative_evidence_preserved':True,'original_source_and_raw_unchanged':True,
             'author_metadata':'User supplied; funding, acknowledgments and data/code availability bodies intentionally empty',
             'excluded':['Environments/executables/fonts/caches/scratch','Third-party full article bodies and indexing workbooks',
                         'Page PNGs regenerable from included PDF; hashes and actual visual review retained','Previous full bundle to avoid nesting duplicate raw data'],
             'limits':'Same locked machine and dependencies; final independent human review and author declarations pending. No submission, upload or payment.'}
    write_json(r/'handoff/supplement_package_receipt_closeout_v2.json',receipt)
    (r/'handoff/rqmc_supplement_v2_reproducibility_closeout_v2.sha256').write_text(receipt['sha256']+'  rqmc_supplement_v2_reproducibility_closeout_v2.zip\n',encoding='ascii')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

"""Exact, reversible in-project archiving requested by the user; never delete data."""
import _bootstrap
import argparse
import json
import os
import shutil
import stat
import zipfile
from rqmc.common import root, safe_relative, sha_file, write_json

ARCHIVE='_archive_manual_cleanup_20261029'
CANDIDATES={
    'superseded_inputs':[
        '01_RQMC预算分配_研究设计.md','启动指引.md','CODEX_INIT.txt','Codex_RQMC_9950X_完整工作包.zip',
        'README_先读.md','PACKAGE_VALIDATION.md','CHECKSUMS.sha256',
        'RQMC_9950X_72小时执行补充.md','RQMC_9950X_启动指引.md','RQMC_9950X_Codex初始化提示词.txt',
        'RQMC_9950X_GPT项目提示词.md','docs/GPT项目提示词.md','docs/research_review.example.json'],
    'historical_loose_material':[
        'FAILURE_REPORT.md','REPRODUCE.md','results/raw','results/analysis','results/summary','results/figures',
        'handoff/B_RETIREMENT.md','handoff/development_review.md','handoff/development_source_rebuilt.zip',
        'handoff/failure_report_receipt.json','handoff/FINAL_AUDIT.md','handoff/reproducibility_manifest.json',
        'handoff/reproducibility_package_receipt.json','handoff/reproducibility_receipt.json',
        'handoff/rqmc_failure_reproducibility.zip','handoff/statistical_audit.md',
        'handoff/UPGRADE_ASSESSMENT.md','handoff/upgrade_headroom_diagnostic.json'],
    'superseded_delivery':[
        'handoff/rqmc_rescue_reproducibility.zip','handoff/rqmc_rescue_reproducibility.sha256',
        'handoff/rescue_package_manifest.json','handoff/rescue_package_receipt.json'],
    'generated_scratch':['.tmp','.cache','.pytest_cache','paper/build','paper/template/template.tex'],
}
SNAPSHOTS=['task_plan.md','notes.md','state/handoff.md','state/STATUS.md','RESEARCH_REPORT.md','REPRODUCE_RESCUE.md']


def inventory(r,rel):
    p=safe_relative(r,rel)
    if not p.exists():return []
    files=[]
    def record(q):
        key=q.relative_to(r).as_posix();safe_relative(r,key)
        st=q.lstat()
        if st.st_file_attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT:raise ValueError(f'Reparse point {key}')
        files.append({'path':key,'bytes':st.st_size,'sha256':sha_file(q)})
    if p.is_file():record(p)
    else:
        for base,dirs,names in os.walk(p,followlinks=False):
            b=type(p)(base)
            for name in dirs:safe_relative(r,(b/name).relative_to(r).as_posix())
            for name in names:record(b/name)
    return sorted(files,key=lambda x:x['path'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    r=root();planpath=r/'review/2026-10-29/organization_plan.json'
    frozen=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    protected=set(frozen['full_source_manifest'])|set(frozen['runtime_sources'])|set(frozen['protocol_hashes'])
    protected.update(json.loads((r/'paper/source_manifest.json').read_text(encoding='utf-8')))
    protected.update(['paper/manuscript.pdf','state/rescue_v1/confirmation_freeze.json',frozen['source_snapshot']])
    for rel,h in frozen['full_source_manifest'].items():assert sha_file(safe_relative(r,rel))==h,rel
    if not args.apply:
        operations=[]
        for category,paths in CANDIDATES.items():
            for rel in paths:
                p=safe_relative(r,rel)
                if not p.exists():continue
                assert not any(k==rel or k.startswith(rel+'/') for k in protected),rel
                dest=f'{ARCHIVE}/{category}/{rel}'
                assert not safe_relative(r,dest).exists(),dest
                operations.append({'source':rel,'destination':dest,'files':inventory(r,rel)})
        snapshots=[{'path':p,'sha256':sha_file(safe_relative(r,p))} for p in SNAPSHOTS]
        write_json(planpath,{'action':'ARCHIVE_ONLY_NO_DELETION','archive_root':ARCHIVE,'operations':operations,
                            'snapshots':snapshots,'protected_frozen_paths':sorted(protected),
                            'newest_paper_sha256':sha_file(r/'paper/manuscript.pdf')})
        print(json.dumps({'operations':len(operations),'files':sum(len(o['files']) for o in operations),
                          'bytes':sum(x['bytes'] for o in operations for x in o['files']),
                          'sources':[o['source'] for o in operations]},indent=2,ensure_ascii=False))
        return
    plan=json.loads(planpath.read_text(encoding='utf-8'))
    assert plan['archive_root']==ARCHIVE and plan['action']=='ARCHIVE_ONLY_NO_DELETION'
    original=r/'handoff/rqmc_failure_reproducibility.zip'
    target=r/'evidence/original_study_20261027.zip'
    target.parent.mkdir(exist_ok=True)
    expected='453f7b148e2ae9e242c74bd38515c3e7a5bedfb86f315a0e2cf2393e51b76a57'
    assert sha_file(original)==expected
    if not target.exists():shutil.copy2(original,target)
    assert sha_file(target)==expected
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert 'results/raw/development.jsonl' in z.namelist() and 'FAILURE_REPORT.md' in z.namelist()
    # Validate every source and destination before the first mutation.
    for operation in plan['operations']:
        assert inventory(r,operation['source'])==operation['files'],operation['source']
        assert not safe_relative(r,operation['destination']).exists()
    for entry in plan['snapshots']:assert sha_file(safe_relative(r,entry['path']))==entry['sha256']
    for entry in plan['snapshots']:
        dest=safe_relative(r,f'{ARCHIVE}/superseded_live_documents/{entry["path"]}')
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(safe_relative(r,entry['path']),dest)
        assert sha_file(dest)==entry['sha256']
    moved=[]
    for operation in plan['operations']:
        src=safe_relative(r,operation['source']);dst=safe_relative(r,operation['destination'])
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(src),str(dst))
        for record in operation['files']:
            suffix=record['path'][len(operation['source']):].lstrip('/')
            key=operation['destination']+('/'+suffix if suffix else '')
            assert sha_file(safe_relative(r,key))==record['sha256'],key
        moved.append({'source':operation['source'],'destination':operation['destination'],
                      'files':len(operation['files']),'bytes':sum(x['bytes'] for x in operation['files'])})
    for rel,h in frozen['full_source_manifest'].items():assert sha_file(safe_relative(r,rel))==h,rel
    assert sha_file(r/'paper/manuscript.pdf')==plan['newest_paper_sha256']
    receipt={'status':'EXACT_MANIFEST_ARCHIVED_AND_ALL_FILE_HASHES_VERIFIED','deleted_files':0,
        'archive_root':ARCHIVE,'moves':moved,'moved_files':sum(x['files'] for x in moved),
        'moved_bytes':sum(x['bytes'] for x in moved),'frozen_source_paths_unchanged':True,
        'newest_pdf_unchanged':True,'historical_evidence_kept_active':'evidence/original_study_20261027.zip',
        'historical_evidence_sha256':expected,'snapshot_copies':plan['snapshots'],
        'user_action':'May manually delete the archive after the updated active bundle verification; keep evidence/, current raw results, .venv and .runtime.'}
    write_json(r/'review/2026-10-29/organization_receipt.json',receipt)
    write_json(r/f'{ARCHIVE}/ARCHIVE_MANIFEST.json',plan)
    print(json.dumps({k:receipt[k] for k in ['status','deleted_files','moved_files','moved_bytes','archive_root']},indent=2))


if __name__=='__main__':main()

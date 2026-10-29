"""Package explicit reproducibility evidence, excluding environments and scratch."""
import _bootstrap
import json
import zipfile
from pathlib import Path
from rqmc.common import root,safe_relative,sha_file,write_json

def main():
    r=root()
    replay=json.loads((r/'handoff/reproducibility_receipt.json').read_text())
    if replay['status']!='FULL_DEVELOPMENT_REPRODUCED':raise RuntimeError('Reproduction required')
    base=['.project-root','AGENTS.md','研究设计_原文.md','研究设计_72小时执行补充.md',
          'requirements.txt','requirements-fast.txt','requirements-lock.txt','FAILURE_REPORT.md','REPRODUCE.md',
          'task_plan.md','notes.md','CHECKSUMS.sha256']
    directories=['rqmc','scripts','tests','config','results/raw','results/analysis','results/summary',
                 'results/figures','results/benchmark','state','handoff']
    allowed={'.py','.md','.json','.jsonl','.csv','.txt','.png','.svg','.zip'}
    rels=set(base)
    for folder in directories:
        for p in (r/folder).rglob('*'):
            rel=p.relative_to(r).as_posix()
            if p.is_file() and p.suffix.lower() in allowed and '__pycache__' not in p.parts:
                if rel in ['handoff/rqmc_failure_reproducibility.zip','handoff/reproducibility_package_receipt.json','handoff/reproducibility_manifest.json']:
                    continue
                rels.add(rel)
    for p in (r/'docs').glob('*'):
        if p.is_file() and p.suffix in ['.md','.json']:rels.add(p.relative_to(r).as_posix())
    for p in (r/'docs/source_records').glob('*'):
        if p.suffix=='.json' or p.name.startswith('confseq_'):
            rels.add(p.relative_to(r).as_posix())
    for p in (r/'validation/current').glob('*'):
        if p.is_file() and p.suffix in ['.json','.txt','.log'] and p.name!='package-verification.txt':
            rels.add(p.relative_to(r).as_posix())
    records=[]
    for rel in sorted(rels):
        p=safe_relative(r,rel)
        if not p.is_file():raise FileNotFoundError(rel)
        records.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha_file(p)})
    manifest=r/'handoff/reproducibility_manifest.json';write_json(manifest,records)
    target=r/'handoff/rqmc_failure_reproducibility.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for record in records:
            z.write(safe_relative(r,record['path']),record['path'])
        z.write(manifest,'handoff/reproducibility_manifest.json')
    # Verify every member after packaging, not just existence of the archive.
    import hashlib
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for record in records:
            assert hashlib.sha256(z.read(record['path'])).hexdigest()==record['sha256']
    receipt={'status':'PACKAGED_AND_MEMBER_HASHES_VERIFIED','path':target.relative_to(r).as_posix(),
             'sha256':sha_file(target),'bytes':target.stat().st_size,'files':len(records)+1,
             'scientific_reproduction':'handoff/reproducibility_receipt.json',
             'excluded':['.venv','.runtime','.tmp','.cache','third-party article PDFs/full HTML','full Compendex workbooks'],
             'note':'Source URLs/hashes/parsed journal records and MIT reference functions retained; originals remain in local project.'}
    write_json(r/'handoff/reproducibility_package_receipt.json',receipt)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()

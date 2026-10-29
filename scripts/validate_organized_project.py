"""Post-organization integrity and clean TeX check, without scientific simulation."""
import _bootstrap
import hashlib
import json
import subprocess
import sys
import zipfile
import pymupdf
from rqmc.common import root, safe_relative, sha_file, write_json


def main():
    r=root();folder=r/'review/2026-10-29'
    def read(p):return json.loads((r/p).read_text(encoding='utf-8'))
    freeze=read('state/rescue_v1/confirmation_freeze.json')
    for group in ['full_source_manifest','runtime_sources','protocol_hashes']:
        for rel,h in freeze[group].items():assert sha_file(safe_relative(r,rel))==h,(group,rel)
    for phase in ['development','confirmation']:
        receipt=read(f'results/rescue_v1/analysis/{phase}/receipt.json')
        for method,h in receipt['raw_sha256'].items():
            assert sha_file(r/f'results/rescue_v1/{phase}/{method}.jsonl')==h,(phase,method)
    decision=read('handoff/rescue_confirmation_decision.json')
    assert all(decision['checks'].values())
    for name,h in decision['source_tables_sha256'].items():assert sha_file(r/f'results/rescue_v1/analysis/confirmation/{name}')==h
    attempts=read('state/rescue_v1/attempts.json');assert len(attempts['attempts'])==2
    visual=read('handoff/rescue_pdf_visual_review.json')
    assert sha_file(r/'paper/manuscript.pdf')==visual['pdf_sha256']
    for rel in read('paper/source_manifest.json'):assert safe_relative(r,rel).is_file(),rel
    destination='.tmp/organization_compile_20261029';dest=safe_relative(r,destination)
    if dest.exists():raise RuntimeError('Preserve prior check; use fresh destination')
    dest.mkdir(parents=True);(dest/'.rqmc-generated').write_text('Post-organization compile check\n')
    with zipfile.ZipFile(r/'handoff/manuscript_source.zip') as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('/'):continue
            q=safe_relative(dest,name);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(name))
    command=[sys.executable,str(r/'scripts/build_rescue_pdf.py'),'--paper-root',destination,
             '--receipt','review/2026-10-29/organized_compile_receipt.json']
    with (folder/'organized_compile_stdout.txt').open('w',encoding='utf-8') as log:
        subprocess.run(command,cwd=r,check=True,stdout=log,stderr=subprocess.STDOUT)
    original=pymupdf.open(r/'paper/manuscript.pdf');new=pymupdf.open(dest/'manuscript.pdf')
    assert len(original)==len(new)==23
    pixels=[]
    for i,(a,b) in enumerate(zip(original,new),1):
        assert a.get_text()==b.get_text(),i
        pa=a.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        pb=b.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        assert pa.samples==pb.samples and pa.width==pb.width and pa.height==pb.height,i
        pixels.append({'page':i,'text_and_pixels_identical':True,'pixel_sha256':hashlib.sha256(pa.samples).hexdigest()})
    links=[]
    for rel in ['当前研究入口.md','最新研究路线设计.md','RESEARCH_REPORT.md',
                'review/2026-10-29/2026-10-29--A-rescue-v1--r02--round-review.md',
                'review/2026-10-29/ASSESSMENT_AND_SUPPLEMENT_PLAN.md','evidence/original_study_20261027.zip']:
        assert safe_relative(r,rel).is_file();links.append(rel)
    write_json(folder/'organization_validation.json',{
        'status':'CURRENT_SOURCES_ALL_RAW_HASHES_TABLES_AND_CLEAN_COMPILE_VERIFIED',
        'frozen_signature':freeze['signature'],'core_source_hashes_unchanged':True,
        'development_and_confirmation_raw_hashes_unchanged':True,'primary_table_hashes_unchanged':True,
        'current_pdf_unchanged':True,'pdf_sha256':visual['pdf_sha256'],'compiled_pages':pixels,
        'latest_entry_paths_checked':links,'scientific_attempt_count':2,'new_scientific_tasks':0,
        'new_integrand_calls':0,'independent_confirmation_repetitions_added':0,
        'limits':'Compilation and integrity checks after organization, not a new scientific reproduction or independent human review.'})
    print('All scientific/primary hashes unchanged; clean compile reproduces all 23 page texts and pixels; zero new scientific tasks.')


if __name__=='__main__':main()

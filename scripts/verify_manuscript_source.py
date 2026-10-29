"""Extract explicit source ZIP, compile locally, compare every rendered page, rebuild."""
import _bootstrap
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
import pymupdf
from rqmc.common import root, safe_relative, sha_file, write_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--destination',default='.tmp/manuscript_rebuild_001')
    args=parser.parse_args();r=root();dest=safe_relative(r,args.destination)
    if dest.exists():raise RuntimeError('Use a fresh destination; preserve prior evidence')
    dest.mkdir(parents=True);(dest/'.rqmc-generated').write_text('Isolated manuscript rebuild\n')
    source=r/'handoff/manuscript_source.zip'
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None
        entries=z.namelist();assert len(entries)==len(set(entries))
        for name in entries:
            target=safe_relative(dest,name)
            if name.endswith('/'):continue
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
    receipt='handoff/manuscript_isolated_build_final.json'
    subprocess.run([sys.executable,str(r/'scripts/build_rescue_pdf.py'),'--paper-root',args.destination,'--receipt',receipt],check=True,cwd=r)
    original=pymupdf.open(r/'paper/manuscript.pdf');rebuilt=pymupdf.open(dest/'manuscript.pdf')
    assert len(original)==len(rebuilt)
    pages=[]
    for i,(a,b) in enumerate(zip(original,rebuilt),1):
        assert a.get_text()==b.get_text(),f'Text difference on page {i}'
        ap=a.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        bp=b.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        assert (ap.width,ap.height,ap.samples)==(bp.width,bp.height,bp.samples),f'Raster difference page {i}'
        pages.append({'page':i,'text_identical':True,'rendered_pixels_identical':True,
                      'pixel_sha256':hashlib.sha256(ap.samples).hexdigest()})
    target=r/'handoff/manuscript_source_rebuilt_final.zip'
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as after:
        for name in sorted(entries):
            if name.endswith('/'):continue
            data=safe_relative(dest,name).read_bytes();assert data==before.read(name)
            info=zipfile.ZipInfo(name,date_time=(2026,10,29,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            after.writestr(info,data)
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    write_json(r/'handoff/manuscript_source_reproduction_final.json',{
        'status':'ISOLATED_SOURCE_COMPILED_AND_ALL_PAGE_CONTENT_REPRODUCED','source_sha256':sha_file(source),
        'rebuilt_source_sha256':sha_file(target),'source_files':len(entries),'scratch':args.destination,
        'pages':pages,'compiler_installer_disabled':True,'shell_execution_disabled':True,
        'limit':'Same installed compiler/fonts/environment; PDF metadata may differ; independent human review pending.'})
    print(f'Compiled isolated sources and reproduced {len(pages)} pages, text and pixels identical.')


if __name__=='__main__':main()

"""Actual local TeX build with installer and shell execution disabled."""
import _bootstrap
import argparse
import json
import os
import re
import shutil
import subprocess
from rqmc.common import root, safe_relative, write_json, sha_file


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--paper-root',default='paper')
    parser.add_argument('--receipt',default='handoff/rescue_pdf_build.json')
    args=parser.parse_args();r=root();paper=safe_relative(r,args.paper_root)
    main=paper/'manuscript.tex'
    if not main.is_file() or not (paper/'Definitions/mdpi.cls').is_file():
        raise SystemExit('Complete manuscript and official class required')
    source=main.read_text(encoding='utf-8')
    assert re.search(r'\\documentclass\[[^\]]*algorithms',source)
    assert '10.3390/1010000' not in source
    build=paper/'build';build.mkdir(exist_ok=True);(build/'.rqmc-generated').write_text('LaTeX output\n',encoding='utf-8')
    tex=['pdflatex','-disable-installer','-disable-write18','-interaction=nonstopmode','-halt-on-error',
         '-c-style-errors','-output-directory=build','manuscript.tex']
    # The third post-BibTeX pass stabilizes the MDPI LastPage footer in a
    # clean source extraction; two passes can leave the first page saying
    # "1 of 33" even though the PDF contains 32 pages.
    commands=[tex,['bibtex','build/manuscript'],tex,tex,tex]
    logs=[]
    for command in commands:
        result=subprocess.run(command,cwd=paper,env=dict(os.environ,MIKTEX_ENABLE_INSTALLER='0'),
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        logs.append('$ '+' '.join(command)+'\n'+result.stdout)
        (build/'compile_stdout.txt').write_text('\n'.join(logs),encoding='utf-8')
        if result.returncode:raise RuntimeError(f'Compiler exit {result.returncode}; inspect {build}/compile_stdout.txt')
    log=(build/'manuscript.log').read_text(errors='replace')
    unresolved=bool(re.search(r'(undefined references|Citation .* undefined|Reference .* undefined)',log))
    if unresolved:raise RuntimeError('Unresolved references or citations')
    duplicated_destinations=bool(re.search(r'(destination with the same identifier|duplicate ignored)',log))
    if duplicated_destinations:raise RuntimeError('Duplicate PDF destinations; repair document-level appendix anchors')
    overfull=[float(v) for v in re.findall(r'Overfull \\hbox \(([\d.]+)pt too wide\)',log)]
    if max(overfull,default=0)>2:raise RuntimeError('Material overfull box; repair generated layout')
    shutil.copy2(build/'manuscript.pdf',paper/'manuscript.pdf')
    import pymupdf
    document=pymupdf.open(paper/'manuscript.pdf')
    text='\n'.join(page.get_text() for page in document)
    if re.search(r'(?<!not )submitted\s+to\s+algorithms',text.lower()):raise RuntimeError('Template falsely labels the draft as submitted')
    if '10.3390/1010000' in text:raise RuntimeError('Template example DOI retained')
    receipt={'status':'COMPILED_REQUIRES_PAGE_REVIEW','paper_root':args.paper_root,'pages':len(document),
             'pdf_sha256':sha_file(paper/'manuscript.pdf'),'class_sha256':sha_file(paper/'Definitions/mdpi.cls'),
             'commands':commands,'undefined_references':False,'overfull_hbox_pt':overfull,
             'duplicate_destinations':False,
             'installer_disabled':True,'shell_execution_disabled':True,
             'author_information':'User supplied author names, affiliations and contact details; CRediT roles reflect user-provided work split; coauthor final approval not confirmed'}
    write_json(safe_relative(r,args.receipt),receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

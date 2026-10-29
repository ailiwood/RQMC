import _bootstrap
from pathlib import Path
import shutil,subprocess,re
from rqmc.common import root,write_json,sha_file

def main():
    r=root();paper=r/'paper';main=paper/'manuscript.tex'
    if not main.is_file():raise SystemExit('No manuscript.tex; Codex must write the real complete draft first')
    if not (paper/'Definitions/mdpi.cls').is_file():raise SystemExit('Official template dependencies missing')
    text=main.read_text(encoding='utf-8')
    if not re.search(r'\\documentclass\[[^\]]*algorithms',text):raise SystemExit('Check target journal class option')
    build=paper/'build';build.mkdir(exist_ok=True);(build/'.rqmc-generated').write_text('build\n')
    commands=[]
    if shutil.which('latexmk'):
        commands=[['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','-file-line-error',
                   '-outdir=build','-pdflatex=pdflatex -no-shell-escape %O %S','manuscript.tex']]
    elif shutil.which('pdflatex'):
        latex=['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error',
               '-file-line-error','-output-directory=build','manuscript.tex']
        commands=[latex]
    else:raise SystemExit('No LaTeX found. Record BLOCKED_FORMAT, do not substitute a screenshot as manuscript PDF')
    logs=[]
    def run(cmd,cwd=paper):
        p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        logs.append('$ '+' '.join(cmd)+'\n'+p.stdout)
        (r/'handoff').mkdir(exist_ok=True);(r/'handoff/latex_compile.txt').write_text('\n'.join(logs),encoding='utf-8')
        if p.returncode:raise RuntimeError(f'Compiler failed {p.returncode}: {cmd[0]}')
    for c in commands:run(c)
    if not shutil.which('latexmk'):
        aux=build/'manuscript.aux'
        if aux.exists() and '\\bibdata' in aux.read_text(errors='replace'):
            if not shutil.which('bibtex'):raise SystemExit('BibTeX required but missing')
            run(['bibtex','build/manuscript'])
        run(latex);run(latex)
    log=(build/'manuscript.log').read_text(errors='replace')
    if re.search(r'(undefined references|Citation .* undefined|Reference .* undefined)',log):
        raise SystemExit('Unresolved references/citations: fix and recompile')
    pdf=build/'manuscript.pdf'
    if not pdf.is_file():raise SystemExit('No compiled PDF')
    shutil.copy2(pdf,paper/'manuscript.pdf')
    write_json(r/'handoff/pdf_build.json',{'status':'COMPILED_NOT_VISUALLY_REVIEWED','pdf_sha256':sha_file(paper/'manuscript.pdf')})
    print('PDF compiled. Visual inspection and clean-source recompile still required.')
if __name__=='__main__':main()

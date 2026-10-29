import _bootstrap
import fitz
from rqmc.common import root,write_json,sha_file

def main():
    r=root();p=r/'paper/manuscript.pdf'
    if not p.is_file():raise SystemExit('Compile manuscript.pdf first')
    out=r/'paper/build/page_images';out.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(p)
    for i,page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False).save(out/f'page_{i+1:03d}.png')
    write_json(r/'handoff/page_review.json',{'pdf_sha256':sha_file(p),'status':'RENDERED_NOT_REVIEWED',
      'pages':[{'page':i+1,'reviewed':False,'notes':''} for i in range(len(doc))]})
    print('Rendered',len(doc),'pages. Codex must actually inspect them and record findings; do not auto-mark reviewed.')
if __name__=='__main__':main()

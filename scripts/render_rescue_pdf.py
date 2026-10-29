"""Render every manuscript page for visual inspection; this is not a review receipt."""
import _bootstrap
import json
import pymupdf
from rqmc.common import root, write_json, sha_file


def main():
    r=root();pdf=r/'paper/manuscript.pdf';document=pymupdf.open(pdf)
    out=r/'paper/rendered';out.mkdir(exist_ok=True)
    (out/'.rqmc-generated').write_text('Generated page rasters\n')
    pages=[]
    for i,page in enumerate(document,1):
        name=out/f'page-{i:02d}.png'
        page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(name)
        pages.append({'page':i,'raster':name.relative_to(r).as_posix(),'sha256':sha_file(name),
                      'text_characters':len(page.get_text()),'visual_review':'PENDING'})
    (out/'manuscript.txt').write_text('\n\f\n'.join(p.get_text() for p in document),encoding='utf-8')
    write_json(out/'render_manifest.json',{'pdf_sha256':sha_file(pdf),'pages':pages,'scale':1.5,
                                          'status':'RENDERED_NOT_YET_VISUALLY_REVIEWED'})
    print(json.dumps({'pages':len(document),'pdf_sha256':sha_file(pdf)}))


if __name__=='__main__':main()

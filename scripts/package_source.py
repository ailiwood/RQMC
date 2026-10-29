import _bootstrap
import argparse,zipfile,json
from rqmc.common import root,safe_relative,write_json,sha_file

# Source package only. Must later extract and recompile in an isolated scratch directory.
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',default='paper/source_manifest.json');a=p.parse_args();r=root()
    m=safe_relative(r,a.manifest)
    if not m.exists():raise SystemExit('Codex must write an explicit list of all source/assets after actual successful compile')
    rels=json.loads(m.read_text(encoding='utf-8'))
    if not isinstance(rels,list) or not all(isinstance(x,str) for x in rels):raise SystemExit('Expected JSON array of project-relative file paths')
    if 'paper/manuscript.tex' not in rels or 'paper/Definitions/mdpi.cls' not in rels:raise SystemExit('Required sources missing')
    records=[]
    for rel in rels:
        q=safe_relative(r,rel)
        if not rel.startswith('paper/') or not q.is_file() or '/build/' in rel:
            raise SystemExit('Only explicit existing paper source files, never build caches')
        if q.suffix.lower() in {'.ttf','.otf','.woff','.woff2','.exe','.dll','.key'}:
            raise SystemExit('Do not package font files, executables or secrets')
        records.append((rel,q))
    out=r/'handoff/manuscript_source.zip';out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for rel,q in records:z.write(q,rel[len('paper/'):])
    write_json(r/'handoff/source_zip_receipt.json',{'sha256':sha_file(out),
       'files':[rel for rel,q in records],'status':'PACKAGED_REQUIRES_CLEAN_RECOMPILE'})
    print('Created source ZIP. Extract, compile and inspect; packaging alone is not final validation.')
if __name__=='__main__':main()

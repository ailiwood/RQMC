import _bootstrap
import argparse,json
from pathlib import Path
from rqmc.common import root,safe_relative,sha_file,write_json

ALLOWED_SUFFIXES={'.aux','.log','.out','.toc','.fls','.fdb_latexmk','.synctex.gz','.pyc','.tmp'}

def candidates(r):
    items=[]
    for base in [r/'rqmc',r/'scripts',r/'tests']:
        for p in base.rglob('*.pyc'):
            rel=p.relative_to(r).as_posix()
            if '__pycache__' in p.parts:
                try:q=safe_relative(r,rel)
                except ValueError:continue
                if q.is_file():items.append(q)
    for name in ['.tmp','.cache','paper/build']:
        d=r/name
        try:safe_relative(r,name)
        except ValueError:continue
        if not (d/'.rqmc-generated').is_file():continue
        for p in d.rglob('*'):
            rel=p.relative_to(r).as_posix()
            try:q=safe_relative(r,rel)
            except ValueError:continue
            if q.is_file() and any(q.name.endswith(s) for s in ALLOWED_SUFFIXES):items.append(q)
    return sorted(set(items))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args();r=root()
    records=[{'path':p.relative_to(r).as_posix(),'sha256':sha_file(p),'bytes':p.stat().st_size} for p in candidates(r)]
    manifest=r/'state/cleanup_plan.json'
    if not a.apply:
        write_json(manifest,records);print(json.dumps(records,indent=2));print('Dry run only. Reproduce final results before --apply.');return
    if not manifest.exists():raise SystemExit('Run dry-run first')
    planned=json.loads(manifest.read_text(encoding='utf-8'));current={x['path']:x for x in records}
    # Atomic pre-validation: no partially deleting first, then discovering another changed file.
    for entry in planned:
        if current.get(entry['path'])!=entry:raise SystemExit('Cleanup plan changed; regenerate and review dry run')
    for entry in planned:safe_relative(r,entry['path']).unlink()
    write_json(r/'state/cleanup_receipt.json',{'deleted':planned,'scope':'allowlisted generated intermediates only'})
    print('Deleted',len(planned),'generated intermediates; preserved scientific records.')
if __name__=='__main__':main()

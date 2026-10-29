"""Replay the sealed development source in an isolated project-local directory."""
import _bootstrap
import argparse
import json
import stat
import subprocess
import sys
import zipfile
import pandas as pd
import numpy as np
from rqmc.common import root,safe_relative,sha_file,write_json,digest

def scientific(value):
    if isinstance(value,dict):
        return {k:scientific(v) for k,v in value.items() if not k.endswith('_s')}
    if isinstance(value,list):return [scientific(v) for v in value]
    return value

def records(path):
    out={}
    with path.open(encoding='utf-8') as f:
        for line in f:
            row=json.loads(line)
            if row['task_id'] in out:raise ValueError('Duplicate repetition')
            out[row['task_id']]=scientific(row)
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--destination',default='.tmp/reproduction_002')
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--verify-only',action='store_true')
    a=p.parse_args();r=root()
    if not a.destination.startswith('.tmp/') or not 1<=a.workers<=16:
        raise SystemExit('Use a new .tmp/ child and 1..16 workers')
    dest=safe_relative(r,a.destination);source=r/'state/development_source.zip'
    if not a.verify_only:
        dest.mkdir(parents=True,exist_ok=False)
        with zipfile.ZipFile(source) as z:
            for item in z.infolist():
                if item.is_dir():continue
                if stat.S_ISLNK(item.external_attr>>16):raise ValueError('Link in source archive')
                target=safe_relative(dest,item.filename);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(item))
        with (dest/'run.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,str(dest/'scripts/run.py'),'--phase','development','--workers',str(a.workers)],
                           cwd=dest,stdout=log,stderr=subprocess.STDOUT,check=True)
    raw=r/'results/raw/development.jsonl';replayed=dest/'results/raw/development.jsonl'
    original=records(raw);repeat=records(replayed)
    if original.keys()!=repeat.keys():raise RuntimeError('Task ID mismatch')
    mismatches=[tid for tid in original if original[tid]!=repeat[tid]]
    if mismatches:raise RuntimeError(f'Scientific mismatch: {mismatches[:10]}')
    with (dest/'analysis.log').open('w',encoding='utf-8') as log:
        subprocess.run([sys.executable,str(dest/'scripts/analyze_results.py'),'--phase','development'],
                       cwd=dest,stdout=log,stderr=subprocess.STDOUT,check=True)
    comparisons=[]
    for name in ['summary','contrasts','selection','diagnostics']:
        rel=f'results/analysis/development_{name}.csv'
        left=pd.read_csv(r/rel);right=pd.read_csv(dest/rel)
        keys=[x for x in ['case','budget','method','ci','reference','selected_n'] if x in left.columns]
        left=left.sort_values(keys).reset_index(drop=True);right=right.sort_values(keys).reset_index(drop=True)
        assert list(left.columns)==list(right.columns) and left.shape==right.shape
        for col in left.columns:
            if col.endswith('_s'):continue
            if pd.api.types.is_numeric_dtype(left[col]):
                assert np.allclose(left[col],right[col],rtol=1e-11,atol=1e-13,equal_nan=True),(name,col)
            else:assert left[col].equals(right[col]),(name,col)
        comparisons.append({'table':rel,'rows':len(left),'status':'MATCH_WITH_FLOAT_AGGREGATION_TOLERANCE'})
    rebuilt=r/'handoff/development_source_rebuilt.zip';rebuilt.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(source) as z,zipfile.ZipFile(rebuilt,'w',zipfile.ZIP_DEFLATED) as out:
        for item in sorted(z.namelist()):
            content=safe_relative(dest,item).read_bytes()
            assert content==z.read(item)
            info=zipfile.ZipInfo(item,date_time=(2026,10,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(info,content)
    receipt={'status':'FULL_DEVELOPMENT_REPRODUCED','task_count':len(original),'new_independent_repetitions':0,
             'scientific_records_bitwise_equal':True,'excluded_fields':'Timing keys ending _s only',
             'original_raw_sha256':sha_file(raw),'replayed_raw_sha256':sha_file(replayed),
             'scientific_digest':digest({k:original[k] for k in sorted(original)}),
             'destination':a.destination,'tables':comparisons,'source_archive_sha256':sha_file(source),
             'rebuilt_archive_sha256':sha_file(rebuilt),'rebuilt_file_contents_match':True,
             'environment_note':'Isolated source/root, same locked project .venv and same machine; not an independent-platform reproduction.'}
    write_json(r/'handoff/reproducibility_receipt.json',receipt)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()

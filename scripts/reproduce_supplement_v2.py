"""Clean-source scientific subset replay and complete raw-analysis reproduction."""
import _bootstrap
import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from rqmc.common import root,safe_relative,sha_file,write_json


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def strip_times(x):
    if isinstance(x,dict):return {k:strip_times(v) for k,v in x.items() if not k.endswith('_s')}
    if isinstance(x,list):return [strip_times(v) for v in x]
    return x


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--destination',default='.tmp/supplement_reproduction_001');args=ap.parse_args()
    r=root();dest=safe_relative(r,args.destination)
    if dest.exists():raise SystemExit('Fresh isolated destination required; previous evidence is preserved')
    dest.mkdir(parents=True);(dest/'.rqmc-generated').write_text('Isolated supplement reproduction\n',encoding='utf-8')
    old=read(r/'state/rescue_v1/confirmation_freeze.json');new=read(r/'state/supplement_v2/confirmation_freeze.json')
    archives=[r/old['source_snapshot'],r/'state/supplement_v2/confirmation_source.zip']
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for name in z.namelist():
                if name.endswith('/'):continue
                p=safe_relative(dest,name);p.parent.mkdir(parents=True,exist_ok=True);data=z.read(name)
                if p.exists():assert p.read_bytes()==data,name
                else:p.write_bytes(data)
    for rel,h in old['full_source_manifest'].items():assert sha_file(safe_relative(dest,rel))==h,rel
    for rel,h in new['runtime_sources'].items():assert sha_file(safe_relative(dest,rel))==h,rel
    # Full raw analyses read copies, never links into the live evidence tree.
    methods=[f'fixed_{n}' for n in (1,2,4,8,16,32,64)]+['A02','PLUGIN_STAGE']
    copies=[f'results/rescue_v1/confirmation/{m}.jsonl' for m in methods]
    copies += ['results/supplement_v2/s1_replay/s1_complete.jsonl','results/supplement_v2/s1_replay/s1_complete.receipt.json']
    for mode in ('confirmation','sensitivity'):
        copies += [f'results/supplement_v2/{mode}/{mode}.{ext}' for ext in ('jsonl','receipt.json')]
    copied=[]
    for rel in copies:
        p=safe_relative(dest,rel);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/rel,p)
        assert sha_file(p)==sha_file(r/rel);copied.append({'path':rel,'sha256':sha_file(p)})
    expected=[];tasks=[]
    cfg=dict(new['inherited_config']);profiles=new['profiles'];spec=new['config']
    case_by={c['id']:c for c in spec['cases']}
    for mode in ('confirmation','sensitivity'):
        p=r/f'results/supplement_v2/{mode}/{mode}.jsonl'
        for line in p.open(encoding='utf-8'):
            row=json.loads(line)
            if row['rep'] not in (0,499,999):continue
            profile=profiles.get(row['method'])
            if row['method'].startswith('A02_K'):profile=dict(profiles['A02'],pilot_replicates=int(row['method'].split('K')[1]))
            tasks.append([cfg,row['phase'],case_by[row['case_id']],row['budget'],row['method'],row['rep'],profile,'both'])
            expected.append(row)
    assert len(tasks)==228
    write_json(dest/'replay_tasks.json',tasks)
    replay_code='''import _bootstrap
import json
import multiprocessing as mp
from rqmc.common import root
from supplement.runtime import execute
from supplement.pool import stream
if __name__ == '__main__':
    mp.freeze_support()
    r=root()
    tasks=json.loads((r/'replay_tasks.json').read_text(encoding='utf-8'))
    with (r/'subset_replay.jsonl').open('w',encoding='utf-8',buffering=1) as f:
        for row in stream(execute,tasks,16):f.write(json.dumps(row,allow_nan=False)+'\\n')
'''
    (dest/'scripts/replay_supplement_subset.py').write_text(replay_code,encoding='utf-8')
    command=[sys.executable,'-X','utf8',str(dest/'scripts/replay_supplement_subset.py')]
    subprocess.run(command,cwd=dest,check=True)
    actual={x['task_id']:x for x in (json.loads(line) for line in (dest/'subset_replay.jsonl').open(encoding='utf-8'))}
    assert len(actual)==len(expected)
    for row in expected:assert strip_times(actual[row['task_id']])==strip_times(row),row['task_id']
    print(f'Exact isolated scientific-field matches: {len(actual)}',flush=True)
    analyses=[]
    for kind in ('s1','s2','s3'):
        command=[sys.executable,'-X','utf8',str(dest/'scripts/analyze_supplement_v2.py'),'--kind',kind]
        result=subprocess.run(command,cwd=dest,check=True,capture_output=True,text=True,encoding='utf-8')
        (dest/f'analysis_{kind}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        for filename in ('summary.csv','contrasts.csv','aggregate.csv','allocations.csv','selection.csv','pilot_summary.csv'):
            rel=f'results/supplement_v2/analysis/{kind}/{filename}'
            assert (dest/rel).read_bytes()==(r/rel).read_bytes(),rel
            analyses.append({'path':rel,'sha256':sha_file(r/rel),'byte_identical':True})
    receipt={'status':'ISOLATED_228_TASKS_EXACT_AND_ALL_SUPPLEMENT_ANALYSES_BYTE_REPRODUCED',
        'destination':args.destination,'source_archives':{p.relative_to(r).as_posix():sha_file(p) for p in archives},
        'matched_scientific_tasks':len(actual),'new_independent_confirmation_repetitions':0,
        'replay_integrand_calls':sum(x['calls_used'] for x in actual.values()),'analysis_outputs':analyses,
        'copied_raw_files':copied,'source_seals_verified':True,
        'excluded_comparison_fields':'Observed *_s durations only; every other scientific field exact',
        'limitations':'Same locked machine and dependencies, not a full second simulation or independent human validation.'}
    write_json(r/'handoff/supplement_reproducibility_receipt.json',receipt)
    print(json.dumps({'matched_tasks':len(actual),'complete_analysis_outputs':len(analyses)}))


if __name__=='__main__':main()

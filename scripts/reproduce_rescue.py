"""Predeclared 972-task sealed-source replay plus complete raw-to-table replay."""
import _bootstrap
import argparse
import json
import shutil
import stat
import subprocess
import sys
import zipfile
import re
import psutil
from rqmc.common import root, safe_relative, sha_file, write_json, digest


def scientific(value):
    if isinstance(value,dict):
        return {k:scientific(v) for k,v in value.items() if not k.endswith('_s')}
    if isinstance(value,list):
        return [scientific(v) for v in value]
    return value


WORKER = '''import _bootstrap
import json
from pathlib import Path
from run_rescue import stream
if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    r=Path(__file__).resolve().parents[1]
    data=json.loads((r/'replay_request.json').read_text(encoding='utf-8'))
    cfg=data['config']; profiles=data['profiles']
    tasks=[(cfg,'rescue_v1_confirmation',case,N,method,rep,case['id'] in cfg['hbci_cases'],profiles.get(method))
           for case in cfg['confirmation_cases'] for N in cfg['budgets'] for method in data['methods'] for rep in [0,499,999]]
    with (r/'replay_subset.jsonl').open('w',encoding='utf-8',buffering=1) as f:
        for i,row in enumerate(stream(tasks,data['workers']),1):
            f.write(json.dumps(row,allow_nan=False)+'\\n')
            if i%100==0:print(f'{i}/{len(tasks)} replayed',flush=True)
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',default='.tmp/rescue_reproduction_001')
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--label',default='',help='Unique label for additional replay receipts/archives; preserve the primary run')
    args=parser.parse_args()
    r=root();dest=safe_relative(r,args.destination)
    if not args.destination.startswith('.tmp/') or dest.exists():
        raise SystemExit('Require a fresh project-local .tmp destination')
    if not re.fullmatch(r'[A-Za-z0-9_-]{0,32}',args.label):
        raise SystemExit('Unsafe replay label')
    if not 1<=args.workers<=16 or psutil.virtual_memory().available<args.workers*512*2**20:
        raise SystemExit('Unsafe worker/RAM request')
    suffix='_'+args.label if args.label else ''
    rebuilt=r/f'handoff/rescue_source_rebuilt{suffix}.zip'
    receipt_path=r/f'handoff/rescue_reproducibility_receipt{suffix}.json'
    if rebuilt.exists() or receipt_path.exists():
        raise SystemExit('Choose a new replay label; preserve earlier verification evidence')
    if (r/'state/rescue_v1/RUN.lock').exists():
        raise SystemExit('Wait for confirmation to exit before CPU-intensive replay')
    frozen=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    decision=json.loads((r/'handoff/rescue_confirmation_decision.json').read_text(encoding='utf-8'))
    assert decision['freeze_signature']==frozen['signature']
    archive=r/frozen['source_snapshot']
    assert sha_file(archive)==frozen['source_snapshot_sha256']
    dest.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for info in z.infolist():
            if info.is_dir():continue
            if stat.S_ISLNK(info.external_attr>>16):raise ValueError('ZIP symlink')
            q=safe_relative(dest,info.filename);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(info))
    for rel,expected in frozen['full_source_manifest'].items():
        assert sha_file(dest/rel)==expected
    write_json(dest/'replay_request.json',{'config':frozen['config'],'profiles':frozen['profiles'],
                                         'methods':frozen['methods'],'workers':args.workers})
    (dest/'scripts/replay_worker.py').write_text(WORKER,encoding='utf-8')
    command=[sys.executable,str(dest/'scripts/replay_worker.py')]
    subprocess.run(command,cwd=dest,check=True)
    expected={}
    for method in frozen['methods']:
        raw=r/f'results/rescue_v1/confirmation/{method}.jsonl'
        for line in raw.open(encoding='utf-8'):
            row=json.loads(line)
            if row['rep'] in (0,499,999):
                assert row['task_id'] not in expected
                expected[row['task_id']]=scientific(row)
    actual={}
    for line in (dest/'replay_subset.jsonl').open(encoding='utf-8'):
        row=json.loads(line);assert row['task_id'] not in actual
        actual[row['task_id']]=scientific(row)
    assert len(expected)==len(actual)==972 and expected.keys()==actual.keys()
    mismatches=[tid for tid in expected if actual[tid]!=expected[tid]]
    if mismatches:
        write_json(r/f'handoff/rescue_reproduction_failure{suffix}.json',{'task_ids':mismatches})
        raise RuntimeError('Scientific replay mismatch; evidence retained')
    source_raw=r/'results/rescue_v1/confirmation'
    target_raw=dest/'results/rescue_v1/confirmation'
    target_raw.mkdir(parents=True)
    for method in frozen['methods']:
        shutil.copy2(source_raw/f'{method}.jsonl',target_raw/f'{method}.jsonl')
    (dest/'state/rescue_v1').mkdir(parents=True,exist_ok=True)
    shutil.copy2(r/'state/rescue_v1/confirmation_freeze.json',dest/'state/rescue_v1/confirmation_freeze.json')
    subprocess.run([sys.executable,str(dest/'scripts/analyze_rescue.py'),'--phase','confirmation'],cwd=dest,
                   stdout=(dest/'full_analysis_stdout.txt').open('w',encoding='utf-8'),stderr=subprocess.STDOUT,check=True)
    tables=['summary.csv','contrasts.csv','aggregate.csv','selection.csv','receipt.json']
    for name in tables:
        assert sha_file(dest/f'results/rescue_v1/analysis/confirmation/{name}')==sha_file(r/f'results/rescue_v1/analysis/confirmation/{name}'),name
    with zipfile.ZipFile(rebuilt,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(frozen['full_source_manifest']):
            assert sha_file(dest/rel)==frozen['full_source_manifest'][rel]
            info=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,(dest/rel).read_bytes())
    receipt={'status':'SEALED_SOURCE_SUBSET_AND_COMPLETE_ANALYSIS_REPRODUCED',
             'frozen_signature':frozen['signature'],'scratch':args.destination,
             'selected_repetitions':[0,499,999],'replayed_tasks':972,'matched_tasks':972,
             'independent_repetitions_added':0,'full_confirmation_tasks_rerun':False,
             'complete_raw_analysis_tasks':324000,'tables_byte_identical':tables,
             'scientific_subset_digest':digest(expected),'timing_exclusion':'Only recursive keys ending _s',
             'rebuilt_source_archive':rebuilt.relative_to(r).as_posix(),'rebuilt_sha256':sha_file(rebuilt),
             'rebuilt_all_source_contents_match':True,
             'limitation':'Same machine and locked dependencies; subset computational replay, full-data analysis replay, not full 324000-task simulation replay or independent human validation.'}
    write_json(receipt_path,receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

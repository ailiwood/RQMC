"""Deterministic old-task replay adding HBCI, with exact scientific-field checks.

Profiles perform the same declared matrix at rep=0. They incur repeated calls but
do not add independent confirmation observations. Original files are read-only.
"""
import _bootstrap
import argparse
from datetime import datetime, timezone, timedelta
import json
import multiprocessing as mp
import os
import time
import zipfile
import psutil
from rqmc.common import root, digest, sha_file, write_json, environment
from rqmc.experiment import task_id
from rqmc.rescue_experiment import execute_rescue_task
from supplement.pool import stream

METHODS = [f'fixed_{n}' for n in (1,2,4,8,16,32,64)] + ['A02','PLUGIN_STAGE']


def scientific(row):
    """Compare all old fields recursively except observed runtime and new HBCI."""
    if isinstance(row, dict):
        return {k:scientific(v) for k,v in row.items() if not k.endswith('_s') and k != 'hbci'}
    if isinstance(row, list):
        return [scientific(v) for v in row]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--profile', action='store_true')
    args = ap.parse_args()
    r = root()
    if args.workers not in (8,12,16) or psutil.virtual_memory().available < args.workers*512*2**20:
        raise SystemExit('Unsafe worker/RAM setting')
    if psutil.disk_usage(str(r)).free < 4*2**30:
        raise SystemExit('Insufficient disk headroom')
    old = json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    for rel, h in old['full_source_manifest'].items():
        if sha_file(r/rel) != h:
            raise SystemExit('Original source changed: '+rel)
    if old['environment'] != environment():
        raise SystemExit('Original environment changed')
    cfg, profiles = old['config'], old['profiles']
    cases = [c for c in cfg['confirmation_cases'] if c['id'] not in cfg['hbci_cases']]
    phase = 'rescue_v1_confirmation'
    folder = r/'results/supplement_v2'/('profiles' if args.profile else 's1_replay')
    folder.mkdir(parents=True, exist_ok=True)
    label = f's1_w{args.workers}' if args.profile else 's1_complete'
    fp = folder/f'{label}.jsonl'
    state = r/'state/supplement_v2'
    clock = state/'experimental_clock.json'
    if not clock.exists():
        now = datetime.now(timezone.utc)
        write_json(clock, {'started_utc':now.isoformat(), 'deadline_utc':(now+timedelta(hours=24)).isoformat(),
                           'scope':'S1--S3 supplementary experimental wall-clock cap'})
    deadline = datetime.fromisoformat(json.loads(clock.read_text())['deadline_utc'])
    sources = {p.relative_to(r).as_posix():sha_file(p) for p in [r/'scripts/run_s1_replay.py',
               r/'supplement/pool.py',r/'scripts/_bootstrap.py',r/'requirements-lock.txt']}
    old_raw = {m:sha_file(r/f'results/rescue_v1/confirmation/{m}.jsonl') for m in METHODS}
    payload = {'sources':sources,'environment':environment(),'original_freeze_signature':old['signature'],
               'original_raw_hashes':old_raw,'cases':cases,'methods':METHODS,'budgets':cfg['budgets'],
               'repetitions':1 if args.profile else 1000,'mode':'profile' if args.profile else 'exact_replay',
               'no_new_independent_confirmation_repetitions':True}
    sig = digest(payload)
    meta = folder/f'{label}.meta.json'
    if meta.exists():
        if json.loads(meta.read_text(encoding='utf-8'))['signature'] != sig:
            raise SystemExit('Supplement seal mismatch')
    else:
        write_json(meta,dict(payload,signature=sig,sealed_utc=datetime.now(timezone.utc).isoformat()))
        snap = state/f'{label}_source.zip'
        with zipfile.ZipFile(snap,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for rel in sources:
                z.write(r/rel,rel)
            z.writestr('meta.json',json.dumps(payload,indent=2))
    expected = {}
    wanted = {c['id'] for c in cases}
    for m in METHODS:
        with (r/f'results/rescue_v1/confirmation/{m}.jsonl').open(encoding='utf-8') as f:
            for line in f:
                row = json.loads(line)
                if row['case_id'] in wanted and (not args.profile or row['rep']==0):
                    expected[row['task_id']] = digest(scientific(row))
    seen = set()
    if fp.exists():
        for line in fp.open(encoding='utf-8'):
            row = json.loads(line)
            tid = row['task_id']
            if tid in seen or tid not in expected or digest(scientific(row['replay'])) != expected[tid]:
                raise SystemExit('Invalid previous replay')
            seen.add(tid)
    tasks = [(cfg,phase,c,N,m,i,True,profiles.get(m)) for c in cases for N in cfg['budgets']
             for m in METHODS for i in range(1 if args.profile else 1000)
             if task_id(phase,c,N,m,i) not in seen]
    lock = state/f'{label}.lock'
    fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode()); os.close(fd)
    started = time.perf_counter()
    process = psutil.Process()
    peak = 0
    calls = errors = count = 0
    print(json.dumps({'mode':label,'pending':len(tasks),'workers':args.workers,
                      'ram_available_gib':psutil.virtual_memory().available/2**30}),flush=True)
    try:
        with fp.open('a',encoding='utf-8',buffering=1) as f:
            for row in stream(execute_rescue_task,tasks,args.workers):
                match = row['status']=='ok' and digest(scientific(row))==expected[row['task_id']]
                hb_ok = 'hbci' in row.get('intervals',{})
                wrapped = {'task_id':row['task_id'],'exact_original_scientific_match':match,
                           'replay':row,'supplement':'S1 deterministic HBCI replay'}
                f.write(json.dumps(wrapped,allow_nan=False)+'\n')
                calls += row.get('calls_used',0)
                count += 1
                errors += not (match and hb_ok)
                if count%500==0 or count==len(tasks):
                    rss = sum(p.memory_info().rss for p in [process]+process.children(recursive=True) if p.is_running())
                    peak=max(peak,rss)
                    progress={'completed_new':count,'pending_initial':len(tasks),'errors':errors,
                              'wall_s':time.perf_counter()-started,'sampled_rss_gib':rss/2**30,'pid':os.getpid()}
                    write_json(state/f'{label}_progress.json',progress)
                    print(json.dumps(progress),flush=True)
                if errors:
                    raise RuntimeError('Deterministic replay or interval failure; preserve evidence')
                if datetime.now(timezone.utc)>deadline:
                    raise RuntimeError('Supplementary experiment wall-clock cap exhausted')
    finally:
        lock.unlink(missing_ok=True)
    wall=time.perf_counter()-started
    receipt={'status':'COMPLETE','total_tasks':len(expected),'existing_tasks':len(seen),'new_tasks':count,
             'new_independent_confirmation_repetitions':0,'repeated_integrand_calls_new':calls,
             'wall_s':wall,'workers':args.workers,'errors':errors,'peak_sampled_rss_gib':peak/2**30,
             'tasks_per_s':count/wall if wall else 0,'raw_sha256':sha_file(fp),'signature':sig}
    write_json(folder/f'{label}.receipt.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    mp.freeze_support()
    main()

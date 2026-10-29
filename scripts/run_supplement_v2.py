"""Frozen, bounded S2/S3 execution; profile streams cannot become confirmation."""
import _bootstrap
import argparse
from datetime import datetime,timezone
import json
import multiprocessing as mp
import os
import time
import zipfile
import psutil
from rqmc.common import root,write_json,sha_file,digest,environment
from rqmc.experiment import task_id
from supplement.runtime import execute
from supplement.pool import stream


def sources(r):
    paths=list((r/'supplement').glob('*.py'))+[r/'scripts/run_supplement_v2.py',r/'scripts/_bootstrap.py',
         r/'scripts/validate_supplement.py',r/'scripts/analyze_supplement_v2.py',r/'scripts/time_supplement_intervals.py',
         r/'scripts/audit_zero_pilot_mechanism.py',r/'state/supplement_v2/zero_pilot_mechanism.json',
         r/'scripts/freeze_development_hb_reference.py',r/'state/supplement_v2/development_hb_reference.json',
         r/'tests/test_supplement_v2.py',r/'config/supplement_v2.json',r/'docs/SUPPLEMENT_V2_MATH_AUDIT.md',
         r/'docs/SUPPLEMENT_V2_PROTOCOL.md',r/'state/supplement_v2/kernel_validation.json',
         r/'state/supplement_v2/application_references.json',r/'requirements-lock.txt',
         r/'validation_dependencies/mpmath-1.3.0-py3-none-any.whl']
    return {p.relative_to(r).as_posix():sha_file(p) for p in sorted(paths)}


def matrix(new,cfg,profiles,mode):
    if mode=='sensitivity':
        phase=new['phase_sensitivity']; s=new['sensitivity']
        for c in new['cases']:
            if c['id'] not in s['cases']:continue
            for k in s['pilot_counts']:
                spec=dict(profiles['A02'],pilot_replicates=k); method=f'A02_K{k}'
                for rep in range(s['repetitions']):yield(cfg,phase,c,s['budget'],method,rep,spec,'both')
    else:
        phase=new['phase_profile'] if mode=='profile' else new['phase_confirmation']
        reps=new['profile_repetitions'] if mode=='profile' else new['repetitions']
        for c in new['cases']:
            for N in new['budgets']:
                for method in new['methods']:
                    for rep in range(reps):yield(cfg,phase,c,N,method,rep,profiles.get(method),'both')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['profile','confirmation','sensitivity'],required=True)
    ap.add_argument('--workers',type=int,default=16)
    ap.add_argument('--freeze',action='store_true')
    args=ap.parse_args();r=root();state=r/'state/supplement_v2'
    if args.workers not in (8,12,16) or psutil.virtual_memory().available<args.workers*512*2**20:
        raise SystemExit('Unsafe worker/RAM setting')
    if psutil.disk_usage(str(r)).free<4*2**30:raise SystemExit('Insufficient disk')
    if json.loads((state/'kernel_validation.json').read_text(encoding='utf-8'))['status']!='PASS':raise SystemExit('Kernel not validated')
    old=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    for rel,h in old['full_source_manifest'].items():
        if sha_file(r/rel)!=h:raise SystemExit('Old source changed: '+rel)
    if environment()!=old['environment']:raise SystemExit('Simulation environment changed')
    cfg=dict(old['config']);new=json.loads((r/'config/supplement_v2.json').read_text(encoding='utf-8'));cfg['seed']=new['seed']
    profiles=old['profiles'];src=sources(r)
    payload={'original_signature':old['signature'],'config':new,'inherited_config':cfg,'profiles':profiles,
             'runtime_sources':src,'environment':environment(),'protocol': 'docs/SUPPLEMENT_V2_PROTOCOL.md'}
    sig=digest(payload); freeze=state/'confirmation_freeze.json'
    if args.mode!='profile':
        profile=r/'results/supplement_v2/profile/profile.receipt.json'
        if not profile.exists():raise SystemExit('Run representative profile first')
        prof=json.loads(profile.read_text(encoding='utf-8'))
        if prof['signature']!=sig or prof['status']!='COMPLETE':raise SystemExit('Profile/code mismatch')
        clock=json.loads((state/'experimental_clock.json').read_text(encoding='utf-8')); deadline=datetime.fromisoformat(clock['deadline_utc'])
        estimated=(72000+4000)/(prof['tasks_per_s'])*1.5
        if not freeze.exists():
            if not args.freeze:raise SystemExit('Use --freeze after profile verification')
            if (deadline-datetime.now(timezone.utc)).total_seconds()<estimated:raise SystemExit('Full fixed matrix infeasible within cap')
            write_json(freeze,dict(payload,signature=sig,sealed_utc=datetime.now(timezone.utc).isoformat(),
                       profile_sha256=sha_file(profile),estimated_pool_hours_with_50pct_headroom=estimated/3600))
            with zipfile.ZipFile(state/'confirmation_source.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
                for rel in src:z.write(r/rel,rel)
                z.writestr('freeze.json',freeze.read_text(encoding='utf-8'))
        elif json.loads(freeze.read_text(encoding='utf-8'))['signature']!=sig:raise SystemExit('Confirmation source/config seal mismatch')
    folder=r/'results/supplement_v2'/args.mode;folder.mkdir(parents=True,exist_ok=True)
    fp=folder/f'{args.mode}.jsonl';meta=folder/f'{args.mode}.meta.json'
    if meta.exists():
        if json.loads(meta.read_text(encoding='utf-8'))['signature']!=sig:raise SystemExit('Existing run seal mismatch')
    else:write_json(meta,dict(signature=sig,mode=args.mode,utc=datetime.now(timezone.utc).isoformat(),workers=args.workers))
    tasks=list(matrix(new,cfg,profiles,args.mode));expected={task_id(t[1],t[2],t[3],t[4],t[5]) for t in tasks}
    if len(expected)!=len(tasks):raise SystemExit('Duplicate planned tasks')
    seen=set()
    if fp.exists():
        for line in fp.open(encoding='utf-8'):
            row=json.loads(line);tid=row['task_id']
            if tid in seen or tid not in expected:raise SystemExit('Duplicate/unexpected stored task')
            if row['status']!='ok':raise SystemExit('Stored failure requires invalidation audit, not silent rerun')
            seen.add(tid)
    tasks=[t for t in tasks if task_id(t[1],t[2],t[3],t[4],t[5]) not in seen]
    lock=state/'s2_s3.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    started=time.perf_counter();process=psutil.Process();peak=0;count=errors=calls=pilot=0
    deadline=datetime.fromisoformat(json.loads((state/'experimental_clock.json').read_text(encoding='utf-8'))['deadline_utc'])
    print(json.dumps({'mode':args.mode,'pending':len(tasks),'workers':args.workers,'signature':sig}),flush=True)
    try:
        with fp.open('a',encoding='utf-8',buffering=1) as f:
            for row in stream(execute,tasks,args.workers):
                f.write(json.dumps(row,allow_nan=False)+'\n');count+=1;errors+=row['status']!='ok'
                calls+=row.get('calls_used',0);pilot+=row.get('pilot_calls',0)
                if count%500==0 or count==len(tasks):
                    rss=sum(p.memory_info().rss for p in [process]+process.children(recursive=True) if p.is_running());peak=max(peak,rss)
                    progress={'mode':args.mode,'completed_new':count,'pending_initial':len(tasks),'errors':errors,
                              'wall_s':time.perf_counter()-started,'sampled_rss_gib':rss/2**30,'pid':os.getpid()}
                    write_json(state/f'{args.mode}_progress.json',progress);print(json.dumps(progress),flush=True)
                if errors:raise RuntimeError('Supplement failure; preserve evidence and audit before any rerun')
                if datetime.now(timezone.utc)>deadline:raise RuntimeError('24-hour experimental cap reached')
    finally:lock.unlink(missing_ok=True)
    elapsed=time.perf_counter()-started
    receipt={'status':'COMPLETE','mode':args.mode,'total_tasks':len(expected),'existing_tasks':len(seen),
             'new_tasks':count,'new_calls':calls,'new_pilot_calls':pilot,'errors':errors,'wall_s':elapsed,
             'peak_sampled_rss_gib':peak/2**30,'workers':args.workers,'tasks_per_s':count/elapsed if elapsed else 0,
             'signature':sig,'raw_sha256':sha_file(fp),'independent_confirmation':args.mode in ('confirmation','sensitivity')}
    write_json(folder/f'{args.mode}.receipt.json',receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    mp.freeze_support();main()

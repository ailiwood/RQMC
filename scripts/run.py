import _bootstrap
import argparse,concurrent.futures as cf,json,multiprocessing as mp,os,time
from pathlib import Path
import psutil
from rqmc.common import root,load_config,source_hashes,digest,write_json,environment
from rqmc.freeze import verify_freeze
from rqmc.experiment import execute_task,task_id

def stream_pool(tasks,workers):
    if workers==1:
        for t in tasks:yield execute_task(t)
        return
    ctx=mp.get_context('spawn');it=iter(tasks)
    with cf.ProcessPoolExecutor(max_workers=workers,mp_context=ctx) as pool:
        pending=set()
        for _ in range(workers*2):
            try:pending.add(pool.submit(execute_task,next(it)))
            except StopIteration:break
        while pending:
            done,pending=cf.wait(pending,return_when=cf.FIRST_COMPLETED)
            for fut in done:
                yield fut.result()
                try:pending.add(pool.submit(execute_task,next(it)))
                except StopIteration:pass

def main():
    p=argparse.ArgumentParser(description='No Codex launcher; deterministic research tasks only')
    p.add_argument('--phase',choices=['smoke','benchmark','development','confirmation'],required=True)
    p.add_argument('--workers',type=int,default=None)
    a=p.parse_args();r=root();cfg=load_config();phase=a.phase
    workers=a.workers or cfg['workers']
    if not 1<=workers<=16:raise SystemExit('Use 1..16 processes; 32 logical threads are not 32 physical cores')
    if psutil.virtual_memory().available < workers*384*2**20:
        raise SystemExit('Insufficient available RAM for requested workers; reduce --workers')
    if phase=='confirmation':verify_freeze()
    elif (r/'state/freeze.json').exists() and phase=='development':
        raise SystemExit('Development is closed after freeze')
    if phase in ('smoke','benchmark'):
        cases=[cfg['development_cases'][0],cfg['development_cases'][2]]
        budgets=[4096];reps=cfg['smoke_repetitions'] if phase=='smoke' else 3
        methods=['fixed_1','fixed_4','fixed_16','fixed_64','PLUGIN','A','B','t_R16']
    else:
        cases=cfg[f'{phase}_cases'];budgets=cfg['budgets'];reps=cfg[f'{phase}_repetitions']
        methods=cfg['main_methods']+cfg['secondary_methods']
    with_hb=cfg['hbci_cases'] if phase=='confirmation' else cfg['hbci_development_cases']
    # Benchmark full CI costs on one preselected case; never use confirmation cases.
    if phase in ('benchmark','smoke'):with_hb=[cases[0]['id']]
    runlabel=f'benchmark_w{workers}' if phase=='benchmark' else phase
    fp=r/f'results/raw/{runlabel}.jsonl';meta=r/f'results/raw/{runlabel}.meta.json'
    sig=digest({'config':cfg,'code':source_hashes(),'env':environment(),'phase':phase,
                'cases':cases,'budgets':budgets,'reps':reps,'methods':methods})
    seen=set()
    if fp.exists():
        if not meta.exists() or json.loads(meta.read_text(encoding='utf-8'))['signature']!=sig:
            raise SystemExit('Existing results use a different config/code/environment. Preserve and review before new development run.')
        with fp.open(encoding='utf-8') as f:
            for line in f:
                try:row=json.loads(line)
                except json.JSONDecodeError:raise SystemExit('Incomplete JSONL tail: repair only the interrupted last line and log recovery')
                if row['task_id'] in seen:raise SystemExit('Duplicate task ID detected')
                seen.add(row['task_id'])
    else:
        write_json(meta,{'signature':sig,'config':cfg,'environment':environment()})
    tasks=[]
    for case in cases:
        for budget in budgets:
            for method in methods:
                for i in range(reps):
                    tid=task_id(phase,case,budget,method,i)
                    if tid not in seen:tasks.append((cfg,phase,case,budget,method,i,case['id'] in with_hb))
    fp.parent.mkdir(parents=True,exist_ok=True)
    lock=r/'state/RUN.lock';lock.parent.mkdir(exist_ok=True)
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise SystemExit('RUN.lock exists: verify no worker process alive before removing stale lock')
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    start=time.perf_counter();errors=0;count=0
    print(f'{phase}: {len(tasks)} pending, {len(seen)} existing, {workers} workers, backend={cfg["backend"]}',flush=True)
    try:
        with fp.open('a',encoding='utf-8',buffering=1) as f:
            for row in stream_pool(tasks,workers):
                f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');count+=1
                errors+=row['status']!='ok'
                if count%20==0:print(f'{count}/{len(tasks)} completed; errors={errors}',flush=True)
        elapsed=time.perf_counter()-start
        receipt={'phase':phase,'new_tasks':count,'existing_tasks':len(seen),'elapsed_s':elapsed,
                 'errors':errors,'workers':workers,'run_signature':sig,
                 'mean_wall_s_per_new_task':elapsed/count if count else None,
                 'warning':'Parallel throughput is not isolated single-task latency. Repeat on this PC before time promises.'}
        if phase=='benchmark' and count:
            formal=(len(cfg['confirmation_cases'])*len(cfg['budgets'])*
                    (len(cfg['main_methods'])+len(cfg['secondary_methods']))*cfg['confirmation_repetitions'])
            receipt['rough_confirmation_hours_unvalidated']=formal*elapsed/count/3600
            receipt['projection_warning']='Only two dev functions and one budget sampled; NOT reliable whole-matrix prediction. Codex must benchmark per cell.'
        write_json(r/f'state/{runlabel}_receipt.json',receipt)
        print(json.dumps(receipt,indent=2))
    finally:
        lock.unlink(missing_ok=True)
    if errors:raise SystemExit(2)
if __name__=='__main__':
    mp.freeze_support();main()

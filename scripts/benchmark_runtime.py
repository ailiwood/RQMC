"""Bounded, full-repetition CPU benchmark using development cases only."""
import _bootstrap
import argparse
import copy
import json
import multiprocessing as mp
import time
import psutil
from rqmc.common import root, load_config, environment, source_hashes, write_json
from run import stream_pool

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--backend', choices=['scipy','qmcpy'], required=True)
    p.add_argument('--workers', type=int, required=True)
    p.add_argument('--reps', type=int, default=3)
    p.add_argument('--round', type=int, default=0)
    a=p.parse_args()
    if a.workers not in [1,8,12,16] or not 1<=a.reps<=20:
        raise SystemExit('Bounded benchmark arguments required')
    available=psutil.virtual_memory().available
    if available<a.workers*512*2**20:
        raise SystemExit('Insufficient RAM')
    cfg=copy.deepcopy(load_config());cfg['backend']=a.backend
    label=f'{a.backend}_w{a.workers}_r{a.round}'
    out=root()/'results/benchmark'/label
    if out.with_suffix('.jsonl').exists():
        raise SystemExit('Existing benchmark retained; use a new round number')
    out.parent.mkdir(parents=True,exist_ok=True)
    tasks=[(cfg,'runtime',c,N,m,i,c['id'] in cfg['hbci_development_cases'])
           for i in range(a.reps) for c in cfg['development_cases']
           for N in cfg['budgets'] for m in cfg['main_methods']+cfg['secondary_methods']]
    started=time.perf_counter();count=0;errors=[];max_rss=0
    proc=psutil.Process()
    with out.with_suffix('.jsonl').open('w',encoding='utf-8',buffering=1) as f:
        for row in stream_pool(tasks,a.workers):
            f.write(json.dumps(row,allow_nan=False)+'\n');count+=1
            if row['status']!='ok': errors.append(row)
            if count%50==0:
                rss=proc.memory_info().rss
                for child in proc.children(recursive=True):
                    try:rss+=child.memory_info().rss
                    except psutil.Error:pass
                max_rss=max(max_rss,rss)
                print(label,count,'/',len(tasks),flush=True)
    elapsed=time.perf_counter()-started
    receipt={'label':label,'backend':a.backend,'workers':a.workers,'tasks':count,
             'elapsed_s':elapsed,'tasks_per_second':count/elapsed,'errors':errors,
             'sampled_peak_process_tree_rss_gib':max_rss/2**30,
             'initial_available_gib':available/2**30,'environment':environment(),
             'source_hashes':source_hashes(),'config':cfg,
             'note':'End-to-end including spawn, CI, accounting and JSONL. Development only. No coverage conclusions.'}
    write_json(out.with_suffix('.json'),receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_hashes','config','environment','errors']},indent=2))
    if errors:raise SystemExit(2)

if __name__=='__main__':
    mp.freeze_support();main()

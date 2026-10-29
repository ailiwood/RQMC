"""Serial matched-draw EB-only/HB-only timing, balanced order, no other pool."""
import _bootstrap
import argparse
import json
import os
import time
from datetime import datetime, timezone
import psutil
from rqmc.common import root,write_json,sha_file,digest,environment
from supplement.runtime import execute


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['original','application','fixed_development','fixed_application'],default='original');args=ap.parse_args()
    folder_names={'original':'isolated_timing','application':'application_timing',
                  'fixed_development':'fixed_development_timing','fixed_application':'fixed_application_timing'}
    r=root();state=r/'state/supplement_v2';folder=r/'results/supplement_v2'/folder_names[args.scope]
    deadline=datetime.fromisoformat(json.loads((state/'experimental_clock.json').read_text(encoding='utf-8'))['deadline_utc'])
    if datetime.now(timezone.utc)>deadline:raise SystemExit('Shared24-hour experiment cap exhausted')
    # Avoid contaminated latency measurements from another active research pool.
    if (state/'s2_s3.lock').exists() or (state/'s1_complete.lock').exists():
        raise SystemExit('Wait for all parallel research pools to finish')
    cfg=json.loads((r/'config/rescue_v1.json').read_text());profiles=cfg.pop('rescue_profiles');cfg.pop('rescue_controls')
    new=json.loads((r/'config/supplement_v2.json').read_text())
    development=args.scope in ('original','fixed_development')
    cases=[cfg['development_cases'][0],cfg['development_cases'][-1]] if development else new['cases'][:2]
    budgets=cfg['budgets'] if development else new['budgets']
    phases={'original':'supplement_v2_isolated_timing','application':'supplement_v2_application_timing',
            'fixed_development':'supplement_v2_fixed_development_timing','fixed_application':'supplement_v2_fixed_application_timing'}
    phase=phases[args.scope]
    methods=[f'fixed_{n}' for n in (1,2,8,16,32,64)] if args.scope.startswith('fixed_') else ['fixed_4','A02','PLUGIN_STAGE']
    expected=2*len(budgets)*len(methods)*2*15
    modes=['ebci','hbci']
    source_files=[r/'scripts/time_supplement_intervals.py',r/'supplement/runtime.py',r/'supplement/integrands.py']
    seal={'sources':{p.relative_to(r).as_posix():sha_file(p) for p in source_files},'cfg':cfg,'profiles':profiles,
          'cases':cases,'methods':methods,'budgets':budgets,'repetitions':15,'scope':args.scope,
          'modes':modes,'order':'rep,case,budget,method; mode order alternates with index parity',
          'warmup':f'2 cases x {len(methods)} methods x 2 modes at N={budgets[0]}, separate phase',
          'environment':environment()}
    folder.mkdir(parents=True,exist_ok=True)
    fp=folder/'timing.jsonl';meta=folder/'timing.meta.json';sig=digest(seal)
    if meta.exists():
        if json.loads(meta.read_text())['signature']!=sig:raise SystemExit('Timing seal mismatch')
    else:write_json(meta,dict(seal,signature=sig,sealed_utc=datetime.now(timezone.utc).isoformat()))
    seen=set()
    if fp.exists():
        for line in fp.open(encoding='utf-8'):
            row=json.loads(line)
            if row['timing_id'] in seen:raise SystemExit('Duplicate timing ID')
            seen.add(row['timing_id'])
    start=time.perf_counter();warm=[]
    for c in cases:
        for method in methods:
            for mode in modes:
                if datetime.now(timezone.utc)>deadline:raise RuntimeError('Experimental cap reached during warm-up')
                row=execute((cfg,phase+'_warmup',c,budgets[0],method,0,profiles.get(method),mode))
                if row['status']!='ok':raise RuntimeError(row)
                warm.append(row)
    warm_s=time.perf_counter()-start
    with (folder/f'warmup_{len(seen)}.jsonl').open('x',encoding='utf-8') as f:
        for row in warm:f.write(json.dumps(row,allow_nan=False)+'\n')
    started=time.perf_counter();count=0;calls=pilot=0;digests={}
    with fp.open('a',encoding='utf-8',buffering=1) as f:
        for rep in range(15):
            for ci,c in enumerate(cases):
                for ni,N in enumerate(budgets):
                    for mi,method in enumerate(methods):
                        order=modes if (rep+ci+ni+mi)%2==0 else modes[::-1]
                        for mode in order:
                            task=(cfg,phase,c,N,method,rep,profiles.get(method),mode)
                            tid=f'{task[1]}|{c["id"]}|{N}|{method}|{rep}|{mode}'
                            if tid in seen:continue
                            if datetime.now(timezone.utc)>deadline:raise RuntimeError('Shared24-hour experiment cap reached')
                            row=execute(task);row['timing_id']=tid
                            f.write(json.dumps(row,allow_nan=False)+'\n');count+=1
                            if row['status']!='ok':raise RuntimeError('Isolated timing failure')
                            calls+=row['calls_used'];pilot+=row['pilot_calls']
                            key=row['task_id']
                            if key in digests and digests[key]!=row['production_means_digest']:raise ArithmeticError('Unmatched CI production draws')
                            digests[key]=row['production_means_digest']
                            if count%30==0:print(json.dumps({'completed':count,'expected_new':expected-len(seen),'wall_s':time.perf_counter()-started}),flush=True)
    receipt={'status':'COMPLETE','signature':sig,'scope':args.scope,'total_tasks':expected,'new_tasks':count,'existing_tasks':len(seen),
             'serial_task_wall_s':time.perf_counter()-started,'warmup_wall_s':warm_s,'warmup_tasks':len(warm),
             'warmup_calls':sum(x['calls_used'] for x in warm),'new_calls':calls,'new_pilot_calls':pilot,
             'same_process_warm_libraries':True,'mode_production_digests_matched':len(digests),
             'raw_sha256':sha_file(fp),'rss_gib':psutil.Process().memory_info().rss/2**30,
             'not_a_strict_fixed_time_budget_experiment':True}
    receipt['experimental_deadline_utc']=deadline.isoformat()
    assert len(seen)+count==expected
    write_json(folder/'timing.receipt.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

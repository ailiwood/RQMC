"""Predeclared isolated complete-task timing; never a scientific selection input."""
import _bootstrap
import json
import time
from rqmc.common import root, write_json, seed_words, sha_file
from rqmc.sampling import batch_means
from rqmc.rescue_experiment import execute_rescue_task


def main():
    r=root()
    if (r/'state/rescue_v1/RUN.lock').exists():
        raise SystemExit('Wait for all experiment workers to exit before isolated timing')
    frozen=json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    cfg,profiles=frozen['config'],frozen['profiles']
    methods=['fixed_4','BUDGET_FIXED','PLUGIN','PLUGIN_STAGE','A01','A02']
    cases=[c for c in cfg['development_cases'] if c['id'] in ['d_smooth1','d_ridge']]
    out=r/'results/rescue_v1/isolated_latency.jsonl'
    if out.exists():raise SystemExit('Preserve existing timing run; refuse overwrite')
    started=time.perf_counter();warm_start=time.perf_counter()
    _,warm=batch_means(cases[0],4,128,seed_words(cfg['seed'],'latency_common_warmup'),cfg['backend'],cfg['batch_scrambles'])
    warmup_s=time.perf_counter()-warm_start
    count=0
    with out.open('x',encoding='utf-8',buffering=1) as f:
        for j,case in enumerate(cases):
            for k,N in enumerate(cfg['budgets']):
                for rep in range(3):
                    rotation=(j+k+rep)%len(methods)
                    order=methods[rotation:]+methods[:rotation]
                    if rep%2:order=list(reversed(order))
                    for method in order:
                        task=(cfg,'rescue_v1_isolated_latency',case,N,method,rep,True,profiles.get(method))
                        row=execute_rescue_task(task)
                        f.write(json.dumps(row,allow_nan=False)+'\n');count+=1
                        if row['status']!='ok':raise RuntimeError('Timing task failure retained')
                    print(f'{count}/108 isolated timing tasks',flush=True)
    assert count==108
    receipt={'status':'OBSERVED_ISOLATED_STEADY_STATE_TASK_LATENCY','tasks':count,'repetitions_per_cell':3,
             'methods':methods,'cases':[x['id'] for x in cases],'budgets':cfg['budgets'],
             'workers':1,'numerical_threads':1,'common_warmup_calls':warm['calls'],
             'common_warmup_s':warmup_s,'whole_script_wall_s':time.perf_counter()-started,
             'raw_sha256':sha_file(out),
             'limits':'One CPU worker with no experiment pool; shared sampling-library warmup reported separately. Interpreter/import startup excluded from task latency. Three repetitions describe observed timings, not a fixed wall-time-budget theorem or precise hardware-universal speedup.'}
    write_json(r/'handoff/rescue_latency_receipt.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

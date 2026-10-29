"""External whole-process accounting for the two additional fixed-grid timings."""
import _bootstrap
import argparse
from datetime import datetime,timezone
import json
import subprocess
import sys
import time
from rqmc.common import root,write_json,sha_file


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['fixed_development','fixed_application'],required=True);args=ap.parse_args()
    r=root();folder=r/f'results/supplement_v2/{args.scope}_timing';folder.mkdir(parents=True,exist_ok=True)
    target=folder/'external_process_receipt.json'
    if target.exists():raise SystemExit('External receipt exists; preserve it')
    start=time.perf_counter();utc=datetime.now(timezone.utc).isoformat()
    command=[sys.executable,'-X','utf8','scripts/time_supplement_intervals.py','--scope',args.scope]
    with (folder/'process_stdout.log').open('x',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=r,stdout=log,stderr=subprocess.STDOUT)
    wall=time.perf_counter()-start
    if result.returncode:raise RuntimeError(f'Timing process failed: {result.returncode}')
    internal=json.loads((folder/'timing.receipt.json').read_text(encoding='utf-8'))
    assert internal['status']=='COMPLETE'
    inside=internal['warmup_wall_s']+internal['serial_task_wall_s']
    write_json(target,{'status':'COMPLETE_PROCESS_TIME_RECORDED','scope':args.scope,'started_utc':utc,'command':command,
        'complete_process_wall_s':wall,'internal_warmup_and_measured_s':inside,'startup_preparation_and_teardown_s':wall-inside,
        'warmup_calls':internal['warmup_calls'],'measured_calls':internal['new_calls'],
        'source_sha256':sha_file(r/'scripts/run_timing_with_receipt.py'),
        'frozen_timing_source_sha256':sha_file(r/'scripts/time_supplement_intervals.py')})
    print(json.dumps({'scope':args.scope,'process_wall_s':wall,'outside_internal_s':wall-inside}))


if __name__=='__main__':main()

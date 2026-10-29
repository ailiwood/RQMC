"""Read-only process-lifetime bounds for the two already queued timing commands.

Does not inspect arbitrary processes: only direct children of this project's
known finite chain. No numerical work or changes to frozen experiment sources.
"""
import _bootstrap
import argparse
from datetime import datetime,timezone
import json
import time
import psutil
from rqmc.common import root,write_json,sha_file


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--chain-pid',type=int,required=True);args=ap.parse_args()
    r=root();parent=psutil.Process(args.chain_pid)
    assert any('run_supplement_chain.py' in s for s in parent.cmdline())
    folder=r/'results/supplement_v2/timing_process_observation';folder.mkdir(parents=True,exist_ok=True)
    meta=folder/'observer.json'
    if meta.exists():raise SystemExit('Keep existing observer evidence; do not restart over it')
    write_json(meta,{'scope':['original','application'],'chain_pid':args.chain_pid,
        'started_utc':datetime.now(timezone.utc).isoformat(),'poll_interval_s':.25,
        'source_sha256':sha_file(r/'scripts/observe_chain_timing.py'),
        'purpose':'Bound complete process time and startup/preparation/teardown outside internal warm-up/task timers'})
    active={};finished={};deadline=datetime.fromisoformat(json.loads((r/'state/supplement_v2/experimental_clock.json').read_text(encoding='utf-8'))['deadline_utc'])
    while parent.is_running() and len(finished)<2:
        if datetime.now(timezone.utc)>deadline:raise RuntimeError('Experimental deadline reached before timing observation complete')
        now=time.time();alive=set()
        for p in parent.children():
            try:
                cmd=p.cmdline()
                if not any(s.replace('\\','/').split('/')[-1]=='time_supplement_intervals.py' for s in cmd):continue
                scope=cmd[cmd.index('--scope')+1]
                if scope not in ('original','application'):continue
                alive.add(p.pid)
                if p.pid not in active:
                    active[p.pid]={'scope':scope,'pid':p.pid,'created_epoch':p.create_time(),'first_seen_epoch':now,'command':cmd}
                active[p.pid]['last_alive_epoch']=now
            except (psutil.NoSuchProcess,psutil.AccessDenied):continue
        for pid,record in list(active.items()):
            if pid in alive:continue
            record['first_missing_epoch']=now;scope=record['scope']
            name='isolated_timing' if scope=='original' else 'application_timing'
            receipt=json.loads((r/f'results/supplement_v2/{name}/timing.receipt.json').read_text(encoding='utf-8'))
            assert receipt['status']=='COMPLETE'
            inside=receipt['warmup_wall_s']+receipt['serial_task_wall_s']
            record.update(complete_process_wall_lower_s=record['last_alive_epoch']-record['created_epoch'],
                          complete_process_wall_upper_s=now-record['created_epoch'],internal_warmup_and_measured_s=inside,
                          outside_internal_timers_lower_s=record['last_alive_epoch']-record['created_epoch']-inside,
                          outside_internal_timers_upper_s=now-record['created_epoch']-inside,
                          interpretation='Outside component includes Python startup, imports, metadata preparation and teardown; it is not an isolated import-time measurement.')
            finished[scope]=record;del active[pid]
            write_json(folder/f'{scope}.json',record)
            print(json.dumps({'scope':scope,'process_wall_bounds_s':[record['complete_process_wall_lower_s'],record['complete_process_wall_upper_s']]}),flush=True)
        time.sleep(.25)
    if len(finished)!=2:raise RuntimeError('Chain ended without both complete timing observations')
    write_json(folder/'receipt.json',{'status':'BOTH_TIMING_PROCESS_LIFETIMES_OBSERVED','scopes':finished,
                                     'source_sha256':sha_file(r/'scripts/observe_chain_timing.py')})


if __name__=='__main__':main()

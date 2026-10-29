"""Finite local experiment chain, no agent restart, no scientific retuning.

Waits only for the already-running deterministic replay, then executes the
approved fixed stages. Every process result and output is retained; any error
stops the chain. It never submits, uploads, or changes environment settings.
"""
import _bootstrap
from datetime import datetime,timezone
import json
import os
import subprocess
import sys
import time
import psutil
from rqmc.common import root,write_json,sha_file


def main():
    r=root();state=r/'state/supplement_v2';status=state/'chain_progress.json'
    lock=state/'chain.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    stages=[['scripts/run_supplement_v2.py','--mode','profile','--workers','16'],
            ['scripts/run_supplement_v2.py','--mode','confirmation','--workers','16','--freeze'],
            ['scripts/run_supplement_v2.py','--mode','sensitivity','--workers','16'],
            ['scripts/time_supplement_intervals.py','--scope','original'],
            ['scripts/time_supplement_intervals.py','--scope','application'],
            ['scripts/time_supplement_intervals.py','--scope','fixed_development'],
            ['scripts/time_supplement_intervals.py','--scope','fixed_application'],
            ['scripts/analyze_supplement_v2.py','--kind','s1'],
            ['scripts/analyze_supplement_v2.py','--kind','s2'],
            ['scripts/analyze_supplement_v2.py','--kind','s3']]
    receipts=[];started=datetime.now(timezone.utc).isoformat()
    try:
        replay=r/'results/supplement_v2/s1_replay/s1_complete.receipt.json'
        while not replay.exists():
            running=state/'s1_complete.lock'
            if not running.exists() or not psutil.pid_exists(int(running.read_text(encoding='ascii'))):
                raise RuntimeError('S1 stopped without complete receipt; inspect preserved evidence')
            write_json(status,{'status':'WAITING_FOR_S1','pid':os.getpid(),'started_utc':started})
            time.sleep(10)
        assert json.loads(replay.read_text(encoding='utf-8'))['status']=='COMPLETE'
        for i,args in enumerate(stages,1):
            progress={'status':'RUNNING','stage':i,'command':[sys.executable,*args],'pid':os.getpid(),
                      'started_utc':started,'stage_started_utc':datetime.now(timezone.utc).isoformat(),'completed_stages':receipts}
            write_json(status,progress);print(json.dumps(progress),flush=True)
            log=state/f'chain_stage_{i:02d}.log'
            with log.open('x',encoding='utf-8') as output:
                child=subprocess.run([sys.executable,'-X','utf8',*args],cwd=r,stdout=output,stderr=subprocess.STDOUT)
            receipt={'stage':i,'command':args,'exit_code':child.returncode,'log':log.relative_to(r).as_posix(),
                     'log_sha256':sha_file(log),'completed_utc':datetime.now(timezone.utc).isoformat()}
            receipts.append(receipt)
            if child.returncode:raise RuntimeError(f'Stage {i} failed; inspect {log}')
        write_json(status,{'status':'SUPPLEMENT_EXPERIMENTS_ANALYZED','started_utc':started,
                          'finished_utc':datetime.now(timezone.utc).isoformat(),'completed_stages':receipts})
        print('All supplementary experiments and all-case analyses completed.',flush=True)
    except Exception as exc:
        write_json(status,{'status':'STOPPED_REQUIRES_TECHNICAL_AUDIT','started_utc':started,
                          'error':str(exc),'completed_stages':receipts})
        raise
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':main()

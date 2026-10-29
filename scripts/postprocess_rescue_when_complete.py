"""One-shot dependent workflow, not a launcher/restart loop."""
import _bootstrap
import json
import subprocess
import sys
import time
from rqmc.common import root, write_json


def main():
    r=root();start=time.monotonic();limit=48*3600
    print('Waiting for the existing frozen confirmation pool; no experiment retries.',flush=True)
    while (r/'state/rescue_v1/RUN.lock').exists():
        if time.monotonic()-start>limit:raise TimeoutError('Postprocessing wait exceeded compute budget')
        time.sleep(30)
    commands=[['scripts/analyze_rescue.py','--phase','confirmation'],['scripts/assess_rescue_confirmation.py']]
    for command in commands:
        subprocess.run([sys.executable,*command],cwd=r,check=True)
    decision=json.loads((r/'handoff/rescue_confirmation_decision.json').read_text(encoding='utf-8'))
    if decision['status']=='CONFIRMATION_SUPPORTED_REQUIRES_DRAFT_AUDIT':
        for command in [['scripts/build_rescue_artifacts.py'],['scripts/benchmark_rescue_latency.py'],['scripts/reproduce_rescue.py','--workers','16']]:
            subprocess.run([sys.executable,*command],cwd=r,check=True)
    write_json(r/'state/rescue_v1/postprocessing_receipt.json',{'status':'NUMERICAL_POSTPROCESSING_COMPLETE','decision':decision['status'],
        'wait_and_work_wall_s':time.monotonic()-start,'next':'Inspect all results, draft or close according to evidence; actual final manuscript/PDF review and package remain manual agent work.'})
    print('Postprocessing complete; scientific decision and verification receipts saved.',flush=True)


if __name__=='__main__':main()

import _bootstrap
import json,shutil,platform,subprocess
import psutil
from rqmc.common import root,write_json,environment

def main():
    r=root(); mem=psutil.virtual_memory(); out={'environment':environment(),
       'processor_reported':platform.processor(),'physical_cores':psutil.cpu_count(logical=False),
       'logical_threads':psutil.cpu_count(),'ram_total_gib':round(mem.total/2**30,2),
       'ram_available_gib':round(mem.available/2**30,2),'free_disk_gib':round(shutil.disk_usage(r).free/2**30,2),
       'latex':{x:shutil.which(x) for x in ['pdflatex','bibtex','latexmk']},
       'recommended_start_workers':12 if mem.available>=16*2**30 else 4,
       'note':'Hardware detection only, NOT a runtime prediction or scientific validation.'}
    write_json(r/'state/environment.json',out)
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

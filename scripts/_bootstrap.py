from pathlib import Path
import os,sys
# Set before importing numpy/scipy; not setdefault (the user's base may have 32).
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
os.environ['OMP_DYNAMIC']='FALSE'
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
sys.path.insert(0,str(ROOT))

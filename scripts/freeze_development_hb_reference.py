"""Prospective secondary HBCI reference, learned only from existing development."""
import _bootstrap
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from rqmc.common import root,write_json,sha_file

r=root();target=r/'state/supplement_v2/development_hb_reference.json'
if (r/'results/supplement_v2/profile/profile.jsonl').exists():
    raise SystemExit('Must register before any S2 profiling/confirmation')
if target.exists():raise SystemExit('Reference already frozen; do not change it')
path=r/'results/rescue_v1/analysis/development/summary.csv';df=pd.read_csv(path)
g=df[(df.ci=='hbci')&df.method.str.startswith('fixed_')].copy()
assert len(g)==42 and set(g['case'])=={'d_smooth1','d_ridge'} and set(g.budget)=={4096,16384,65536}
assert (g.attempted==200).all() and (g.failures==0).all()
scores=g.groupby('method').mean_width.apply(lambda x:float(np.exp(np.log(x).mean())))
winner=min(scores.index,key=lambda m:(scores[m],int(m.split('_')[1])))
write_json(target,{'type':'PROSPECTIVE_SECONDARY_REFERENCE_NOT_NEW_METHOD','selected_reference':winner,
    'interval':'hbci','selection':'Smallest geometric mean of the six development-cell mean widths; ties choose smaller n',
    'development_cases':['d_smooth1','d_ridge'],'budgets':[4096,16384,65536],'repetitions_per_cell':200,
    'all_fixed_scores':scores.to_dict(),'development_summary_sha256':sha_file(path),
    'sealed_utc':datetime.now(timezone.utc).isoformat(),'new_integrand_calls':0,
    'all_seven_fixed_references_retained':True,'original_primary_reference_unchanged':True,
    'scope':'Only two development families had HBCI; this is a common deployable reference, not a cellwise oracle.'})
print(json.dumps({'selected_hb_reference':winner,'all_fixed_scores':scores.to_dict()},indent=2))

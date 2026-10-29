import _bootstrap
import json
from datetime import datetime, timezone
from rqmc.common import root, write_json, sha_file

r=root()
folder=r/'results/supplement_v2/profiles'
rows=[json.loads((folder/f's1_w{w}.receipt.json').read_text()) for w in (12,8,16)]
assert all(x['total_tasks']==108 and x['errors']==0 for x in rows)
best=max(rows,key=lambda x:x['tasks_per_s'])
write_json(r/'state/supplement_v2/worker_selection.json', {
    'selected_workers':best['workers'],'profiles':rows,
    'selection_criterion':'Highest observed end-to-end tasks/s including startup; RAM-safe 8/12/16 candidates.',
    'small_sample_runtime_only':True,'selected_utc':datetime.now(timezone.utc).isoformat(),
    'protocol_sha256':sha_file(r/'docs/SUPPLEMENT_V2_PROTOCOL.md'),
    'estimated_s1_pool_hours':108000/best['tasks_per_s']/3600,
    'all_profile_repeated_integrand_calls':sum(x['repeated_integrand_calls_new'] for x in rows)})
print(best['workers'])

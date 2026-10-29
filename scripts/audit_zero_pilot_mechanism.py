"""Finite deterministic selector diagnostic, zero integrand evaluations."""
import _bootstrap
import json
import numpy as np
from rqmc.common import root,write_json,sha_file
from rqmc.rescue_allocation import choose_rescue

r=root();old=json.loads((r/'config/rescue_v1.json').read_text(encoding='utf-8'));profiles=old.pop('rescue_profiles');old.pop('rescue_controls')
rows=[]
for method in ('A02','PLUGIN_STAGE'):
    for K in (8,16,32):
        for N in (16384,65536):
            spec=dict(profiles[method],pilot_replicates=K)
            n,reps,diag=choose_rescue(np.zeros((K,3)),[1,2,4],N,4*K,method,old,spec)
            rows.append({'method':method,'pilot_count':K,'budget':N,'all_zero_initial_pilot':True,
                         'selected_n':n,'production_reps':reps,'charged_pilot_calls':4*K,
                         'stops_at_initial_depth':n<=2,'scores':diag['selection_scores']})
assert all(x['selected_n']==1 and x['stops_at_initial_depth'] for x in rows)
write_json(r/'state/supplement_v2/zero_pilot_mechanism.json',{
    'type':'DETERMINISTIC_SELECTOR_AND_A_PRIORI_PROBABILITY_DIAGNOSTIC_NOT_SIMULATION',
    'integrand_calls':0,'rows':rows,
    'miss_probability_lower_bound':'max(0,1-K*h0*p); union bound requires uniform point marginals, not within-net independence',
    'default_K16_h4_bounds':{'p_1e-3':.936,'p_1e-4':.9936},
    'finite_grid_qualification':'Use grid event probability for literal finite-grid statement; continuous threshold probability is the ideal model quantity.',
    'scope':'Declared two budgets and pilot counts8/16/32, no claim for arbitrary settings or future integrands',
    'selector_source_sha256':sha_file(r/'rqmc/rescue_allocation.py')})
print(json.dumps({'zero_integrand_calls':True,'checked_selector_settings':len(rows),'all_selected_n1':True}))

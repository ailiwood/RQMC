import _bootstrap
import math,json
from rqmc.common import root,load_config,write_json

def main():
    cfg=load_config();rows=[]
    for N in cfg['budgets']:
        nmax=cfg['pilot_nmax'][str(N)];K=sum(n<=nmax for n in cfg['fixed_n'])
        pairs=cfg['pilot_replicates']//2
        add=.5*math.sqrt(math.log(K/cfg['pilot_beta'])/(2*pairs))
        rows.append({'budget':N,'pilot_calls':cfg['pilot_replicates']*nmax,
             'pilot_fraction':cfg['pilot_replicates']*nmax/N,'candidates':K,'pairs':pairs,
             'B_Hoeffding_addition':add,'B_always_saturates':add>=.25,
             'action':'Analytically retire this B setting before expensive experiments; record deviation, no hidden replacement.'
                      if add>=.25 else 'Check upper-bound saturation and selected n in development.'})
    report={'type':'ANALYTICAL_PREFLIGHT_NOT_EMPIRICAL_RESULT','rows':rows,
            'note':'No automatic method change. Codex must record any route retirement before freezing; this is not evidence for A.'}
    write_json(root()/'state/design_preflight.json',report)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()

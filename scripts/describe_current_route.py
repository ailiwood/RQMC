"""Descriptive review of existing evidence, no new integrand calls or primary tests."""
import _bootstrap
import json
import numpy as np
import pandas as pd
from rqmc.common import root, write_json


def main():
    r=root();out=r/'review/2026-10-29';out.mkdir(parents=True,exist_ok=True)
    s=pd.read_csv(r/'results/rescue_v1/analysis/confirmation/summary.csv')
    eb=s[s.ci=='ebci'];fw=eb[eb.method=='fixed_4'][['case','budget','mean_width']]
    ratios={}
    for method in ['A','A01','A02','PLUGIN','PLUGIN_MATCH','PLUGIN_STAGE']:
        pair=eb[eb.method==method].merge(fw,on=['case','budget'],suffixes=('_m','_f'))
        ratios[method]=float(np.exp(np.log(pair.mean_width_m/pair.mean_width_f).mean()))
    a=eb[eb.method=='A02'][['case','budget','mean_width','coverage']]
    hb=s[(s.ci=='hbci')&(s.method=='fixed_4')][['case','budget','mean_width','coverage']]
    cross=a.merge(hb,on=['case','budget'],suffixes=('_A02_EB','_fixed4_HB'))
    cross['width_ratio']=cross.mean_width_A02_EB/cross.mean_width_fixed4_HB
    cross.to_csv(out/'cross_interval_diagnostic.csv',index=False)
    shares=[]
    for method in ['A02','fixed_4']:
        for line in (r/f'results/rescue_v1/confirmation/{method}.jsonl').open(encoding='utf-8'):
            x=json.loads(line)
            if 'hbci' not in x.get('intervals',{}):continue
            shares.append({'method':method,'case':x['case_id'],'budget':x['budget'],
                           'ebci_s':x['primary_ci_s'],'hbci_s':x['hbci_s']})
    times=pd.DataFrame(shares).groupby(['method','case','budget']).median().reset_index()
    times.to_csv(out/'concurrent_interval_timing_diagnostic.csv',index=False)
    result={'source':'Complete frozen confirmation summaries/raw durations',
        'new_integrand_calls':0,'primary_decision_changed':False,
        'common_reference_ratios':ratios,
        'A01_over_original_A':ratios['A01']/ratios['A'],
        'A02_over_A01':ratios['A02']/ratios['A01'],
        'A02_EB_over_fixed4_HB':{'cells':len(cross),'geometric_mean':float(np.exp(np.log(cross.width_ratio).mean())),
                               'min':float(cross.width_ratio.min()),'max':float(cross.width_ratio.max()),
                               'all_above_one':bool((cross.width_ratio>1).all())},
        'limits':['Cross-interval comparison is post hoc and descriptive, over only two prespecified HBCI families.',
                  'Original primary comparisons use the same EBCI; they are not invalidated or replaced.',
                  'The recorded interval timings came from the concurrent pool, not isolated EB-only/HB-only task timings.',
                  'The score change and the adaptive-policy bundle can be compared; no separate smoothing claim.']}
    write_json(out/'existing_evidence_diagnostic.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

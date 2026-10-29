"""Apply only the decision rules sealed before confirmation."""
import _bootstrap
import json
import pandas as pd
from rqmc.common import root, write_json, sha_file


def main():
    r = root()
    folder = r/'results/rescue_v1/analysis/confirmation'
    receipt = json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    frozen = json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
    assert receipt['tasks'] == frozen['expected_tasks'] == 324000
    assert receipt['intervals'] == frozen['expected_intervals'] == 414000
    summary = pd.read_csv(folder/'summary.csv')
    contrasts = pd.read_csv(folder/'contrasts.csv')
    aggregates = pd.read_csv(folder/'aggregate.csv')
    candidate = summary[(summary.method=='A02') & (summary.ci=='ebci')]
    assert len(candidate) == 18 and candidate.attempted.eq(1000).all()
    primary = aggregates[(aggregates.method=='A02') & (aggregates.ci=='ebci') &
                         aggregates.reference.isin(['fixed_4','BUDGET_FIXED'])]
    assert len(primary) == 2
    cell = contrasts[(contrasts.method=='A02') & (contrasts.reference=='fixed_4') &
                     (contrasts.ci=='ebci')].merge(candidate,on=['case','budget','method','ci'],validate='one_to_one')
    gain = cell[(cell.mean_width_ratio<=.90) & (cell.holm_p<.05) &
                (cell.coverage>=.95) & (cell.coverage_wilson_lo>=.93)]
    checks = {
        'complete_matrix':receipt['tasks']==324000 and receipt['intervals']==414000,
        'no_numerical_failures':receipt['failures']==0,
        'both_bonferroni_aggregate_upper_bounds_below_one':bool(primary.ratio_hi.lt(1).all()),
        'all_candidate_cell_coverage_at_least_point94':bool(candidate.coverage.ge(.94).all()),
        'two_function_families_with_useful_gain_and_coverage_guard':gain['case'].nunique()>=2,
    }
    document = {'status':'CONFIRMATION_SUPPORTED_REQUIRES_DRAFT_AUDIT' if all(checks.values()) else 'CONFIRMATION_DID_NOT_SUPPORT_PRIMARY_CLAIM',
                'freeze_signature':frozen['signature'],'checks':checks,
                'primary_aggregate_comparisons':primary.to_dict(orient='records'),
                'qualifying_gain_cells':gain[['case','budget','mean_width_ratio','ratio_lo','ratio_hi','holm_p','coverage','coverage_wilson_lo','coverage_wilson_hi']].to_dict(orient='records'),
                'candidate_min_coverage':float(candidate.coverage.min()),
                'candidate_empty_intervals':int(candidate.empty_count.sum()),
                'failure_count_all_methods':receipt['failures'],
                'source_tables_sha256':{p.name:sha_file(p) for p in [folder/'summary.csv',folder/'contrasts.csv',folder/'aggregate.csv',folder/'receipt.json']},
                'limits':['One frozen confirmation look; secondary ablations cannot replace the primary outcome.',
                          'A supported simulation claim is not journal acceptance or a universal efficiency theorem.',
                          'Draft, reference/claim audit, PDF page review and isolated reproduction remain required.']}
    write_json(r/'handoff/rescue_confirmation_decision.json',document)
    print(json.dumps(document,indent=2))


if __name__=='__main__':
    main()

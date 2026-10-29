import _bootstrap
import json
import zipfile
from datetime import datetime, timezone
from rqmc.common import root, sha_file, write_json, environment, source_hashes, digest
from run_rescue import runtime_sources


def main():
    r = root()
    state = r/'state/rescue_v1'
    dest = state/'confirmation_freeze.json'
    if dest.exists():
        raise SystemExit('Already frozen; never overwrite')
    if list((r/'results/rescue_v1/confirmation').glob('*.jsonl')):
        raise SystemExit('Confirmation data already exist')
    receipt_path = r/'results/rescue_v1/analysis/development/receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    cfgpath = r/'config/rescue_v1.json'
    cfg = json.loads(cfgpath.read_text(encoding='utf-8'))
    profiles, controls = cfg.pop('rescue_profiles'), cfg.pop('rescue_controls')
    methods = sorted(set(controls + ['A01','A02','PLUGIN_STAGE']))
    assert set(receipt['methods']) == set(methods) and len(methods) == 18
    assert receipt['tasks'] == 43200 and receipt['failures'] == 0 and receipt['empty_intervals'] == 0
    assert receipt['selected_fixed_baseline'] == 'fixed_4'
    for method, expected in receipt['raw_sha256'].items():
        assert sha_file(r/f'results/rescue_v1/development/{method}.jsonl') == expected
    a = next(x for x in receipt['aggregates'] if x['method']=='A02' and x['reference']=='fixed_4' and x['ci']=='ebci')
    assert a['geometric_mean_ratio'] < 1 and len(a['families_with_10pct_gain']) >= 2
    schedule = next(x for x in receipt['aggregates'] if x['method']=='A02' and x['reference']=='BUDGET_FIXED' and x['ci']=='ebci')
    assert schedule['ratio_hi'] < 1
    cfg['primary_method'], cfg['primary_fixed_baseline'] = 'A02','fixed_4'
    full = dict(cfg,rescue_profiles=profiles,rescue_controls=controls)
    write_json(cfgpath,full)
    manifest = source_hashes()
    additions = ['.project-root','config/rescue_v1.json','docs/RESCUE_AUTHORIZATION.md',
                 'docs/RESCUE_CONFIRMATION_PROTOCOL.md','AGENTS.md','研究设计_原文.md',
                 '研究设计_72小时执行补充.md','docs/EXECUTION.md','docs/MATH_AUDIT.md']
    manifest.update({rel:sha_file(r/rel) for rel in additions})
    snapshot = state/'confirmation_source.zip'
    with zipfile.ZipFile(snapshot,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(manifest):
            z.write(r/rel,rel)
    protocol_paths = ['docs/RESCUE_CONFIRMATION_PROTOCOL.md','docs/RESCUE_AUTHORIZATION.md',
                      'results/rescue_v1/analysis/development/receipt.json']
    freeze = {'status':'FROZEN_BEFORE_CONFIRMATION','utc':datetime.now(timezone.utc).isoformat(),
              'config':cfg,'profiles':profiles,'methods':methods,'primary_method':'A02',
              'primary_baseline':'fixed_4','budget_fixed':profiles['BUDGET_FIXED'],
              'runtime_sources':runtime_sources(r),'full_source_manifest':manifest,
              'protocol_hashes':{rel:sha_file(r/rel) for rel in protocol_paths},
              'environment':environment(),'source_snapshot':'state/rescue_v1/confirmation_source.zip',
              'source_snapshot_sha256':sha_file(snapshot),'expected_tasks':324000,
              'expected_intervals':414000,'scientific_interventions_used':2,
              'development_comparisons':{'primary':a,'stronger_schedule':schedule}}
    freeze['signature'] = digest(freeze)
    write_json(dest,freeze)
    print(json.dumps({k:freeze[k] for k in ['status','utc','primary_method','expected_tasks','expected_intervals','signature']},indent=2))


if __name__ == '__main__':
    main()

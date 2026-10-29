from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime,timezone
from .common import root,load_config,write_json,source_hashes,digest,environment,sha_file,safe_relative

def verify_freeze():
    r=root();p=r/'state/freeze.json'
    if not p.exists():raise RuntimeError('Confirmation is locked: freeze after development review')
    f=json.loads(p.read_text(encoding='utf-8'))
    if digest(load_config())!=f['config_hash']:raise RuntimeError('Frozen config changed')
    if source_hashes()!=f['source_hashes']:raise RuntimeError('Frozen code changed; do not retune confirmation')
    env=environment()
    if env['packages']!=f['environment']['packages'] or env['python']!=f['environment']['python']:
        raise RuntimeError('Frozen Python/dependencies changed')
    if env.get('installed')!=f['environment'].get('installed'):
        raise RuntimeError('Frozen complete installed dependency set changed')
    return f

def freeze(winner,baseline):
    r=root();p=r/'state/freeze.json'
    if p.exists():raise RuntimeError('Already frozen; no overwrite')
    if winner not in ('A','B') or baseline not in [f'fixed_{n}' for n in load_config()['fixed_n']]:
        raise ValueError('Invalid winner/baseline')
    review=json.loads((r/'state/research_review.json').read_text(encoding='utf-8'))
    for key in ['continue_research','intervals_checked','sampler_checked','nearest_neighbors_checked','runtime_feasible']:
        if review.get(key) is not True:raise RuntimeError(f'Missing passed review: {key}')
    if review.get('scientific_route_count',0)>2:raise RuntimeError('Scientific route budget exceeded')
    evidence={}
    for rel in review.get('evidence_files',[]):
        q=safe_relative(r,rel)
        if not q.is_file() or q.stat().st_size<20:raise RuntimeError('Missing evidence: '+rel)
        evidence[rel]=sha_file(q)
    if len(evidence)<3:raise RuntimeError('Need math, development and runtime evidence')
    raw=r/'results/raw/development.jsonl'
    if not raw.is_file() or raw.stat().st_size<20:raise RuntimeError('No actual development results')
    cfg=load_config();cfg['primary_method']=winner;cfg['primary_fixed_baseline']=baseline
    write_json(r/'config/experiment.json',cfg)
    f={'created_utc':datetime.now(timezone.utc).isoformat(),'config_hash':digest(cfg),
       'config':cfg,'source_hashes':source_hashes(),'environment':environment(),
       'development_results_sha256':sha_file(raw),'review':review,'evidence_sha256':evidence}
    write_json(p,f)
    return f

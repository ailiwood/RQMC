import json
import pytest
from rqmc import freeze as fz
from rqmc.common import write_json,load_config

def prepare(tmp_path,monkeypatch):
    cfg=load_config();write_json(tmp_path/'config/experiment.json',cfg)
    monkeypatch.setattr(fz,'root',lambda:tmp_path)
    monkeypatch.setattr(fz,'load_config',lambda:json.loads((tmp_path/'config/experiment.json').read_text()))
    monkeypatch.setattr(fz,'source_hashes',lambda:{'code.py':'testhash'})
    monkeypatch.setattr(fz,'environment',lambda:{'python':'3.test','packages':{'numpy':'test'}})
    return cfg

def test_confirm_locked(tmp_path,monkeypatch):
    prepare(tmp_path,monkeypatch)
    with pytest.raises(RuntimeError):fz.verify_freeze()

def test_cannot_freeze_false_review(tmp_path,monkeypatch):
    prepare(tmp_path,monkeypatch);write_json(tmp_path/'state/research_review.json',{'continue_research':False})
    with pytest.raises(RuntimeError):fz.freeze('A','fixed_4')

def test_freeze_and_changed_config(tmp_path,monkeypatch):
    prepare(tmp_path,monkeypatch);ev=[]
    for n in ['math','dev','runtime']:
        p=tmp_path/f'handoff/{n}.md';p.parent.mkdir(exist_ok=True);p.write_text('Evidence test fixture, not a real review.'*2);ev.append(p.relative_to(tmp_path).as_posix())
    raw=tmp_path/'results/raw/development.jsonl';raw.parent.mkdir(parents=True);raw.write_text('test fixture - never scientific data\n')
    write_json(tmp_path/'state/research_review.json',dict(continue_research=True,intervals_checked=True,
       sampler_checked=True,nearest_neighbors_checked=True,runtime_feasible=True,scientific_route_count=2,evidence_files=ev))
    fz.freeze('A','fixed_4');assert fz.verify_freeze()['config']['primary_method']=='A'
    with pytest.raises(RuntimeError):fz.freeze('B','fixed_8')
    cfg=json.loads((tmp_path/'config/experiment.json').read_text());cfg['alpha']=.1
    write_json(tmp_path/'config/experiment.json',cfg)
    with pytest.raises(RuntimeError):fz.verify_freeze()

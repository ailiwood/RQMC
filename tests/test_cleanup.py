import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from safe_clean import candidates

def test_clean_preserves_research_files(tmp_path):
    for rel in ['results/raw/development.jsonl','paper/manuscript.pdf','paper/manuscript.tex','config/experiment.json','研究设计_原文.md']:
        p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('keep')
    b=tmp_path/'paper/build';b.mkdir();(b/'.rqmc-generated').write_text('marker');(b/'manuscript.aux').write_text('drop')
    found=[p.relative_to(tmp_path).as_posix() for p in candidates(tmp_path)]
    assert found==['paper/build/manuscript.aux']

def test_no_marker_no_delete(tmp_path):
    b=tmp_path/'paper/build';b.mkdir(parents=True);(b/'manuscript.aux').write_text('keep')
    assert candidates(tmp_path)==[]

def test_do_not_follow_cleanup_link(tmp_path):
    import pytest
    out=tmp_path.parent/'outside_clean';out.mkdir(exist_ok=True);(out/'x.aux').write_text('keep')
    b=tmp_path/'paper/build';b.mkdir(parents=True);(b/'.rqmc-generated').write_text('marker')
    try:(b/'linked').symlink_to(out,target_is_directory=True)
    except (OSError,NotImplementedError):pytest.skip('no symlinks')
    assert candidates(tmp_path)==[] and (out/'x.aux').exists()

import numpy as np
import pytest
from scipy.special import ndtr
from supplement.integrands import genz_upper


def test_independent_gaussian_rectangle_is_constant():
    u=np.random.default_rng(57).random((3,8,15))
    assert np.allclose(genz_upper(u,16,0,.5),ndtr(.5)**16,rtol=0,atol=1e-16)


def test_gaussian_transform_endpoints_and_domain():
    u=np.vstack([np.zeros(31),np.full(31,np.nextafter(1.,0.))])
    values=genz_upper(u,32,.7,.5)
    assert np.isfinite(values).all() and np.all((values>=0)&(values<=1))
    assert values[0]==ndtr(.5)
    with pytest.raises(ValueError):genz_upper(np.ones((2,31)),32,.7,.5)


def test_isolated_interval_modes_retain_matched_production_and_calls():
    import json
    from rqmc.common import root
    from supplement.runtime import execute
    cfg=json.loads((root()/'config/rescue_v1.json').read_text())
    profiles=cfg.pop('rescue_profiles');cfg.pop('rescue_controls')
    case=cfg['development_cases'][0]
    for method in ('fixed_4','A02','PLUGIN_STAGE'):
        task=(cfg,'supplement_v2_interval_isolation_test',case,4096,method,0,profiles.get(method))
        both=execute((*task,'both'));eb=execute((*task,'ebci'));hb=execute((*task,'hbci'))
        assert both['status']==eb['status']==hb['status']=='ok'
        assert set(eb['intervals'])=={'ebci'} and set(hb['intervals'])=={'hbci'}
        assert eb['hbci_s']==0 and hb['primary_ci_s']==0
        assert both['production_means_digest']==eb['production_means_digest']==hb['production_means_digest']
        assert both['calls_used']==eb['calls_used']==hb['calls_used']==4096
        assert both['intervals']['ebci']==eb['intervals']['ebci']
        assert both['intervals']['hbci']==hb['intervals']['hbci']

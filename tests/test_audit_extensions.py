import numpy as np
import pytest
from rqmc.allocation import choose
from rqmc.common import load_config
from rqmc.intervals import ebci,hbci
from rqmc.sampling import blocks

@pytest.mark.parametrize('budget',[4096,16384])
def test_B_always_picks_one_even_without_complete_saturation(budget):
    cfg=load_config();ns=[n for n in cfg['fixed_n'] if n<=cfg['pilot_nmax'][str(budget)]]
    # Worst case for n=1, best case for every other candidate.
    pilot=np.zeros((16,len(ns)));pilot[1::2,0]=1
    n,R,_=choose(pilot,ns,budget,16*max(ns),'B',cfg)
    assert n==1 and 16*max(ns)+R==budget

@pytest.mark.parametrize('ci',[ebci,hbci])
def test_empty_set_is_preserved(ci):
    ans=ci(np.r_[np.zeros(512),np.ones(512)])
    assert ans['empty'] and ans['lower']>ans['upper'] and ans['width']==0

def test_one_point_grid_is_52_bit_uniform_and_chunk_invariant():
    a=np.concatenate(list(blocks(8,1,64,[871],chunk=7)))
    b=np.concatenate(list(blocks(8,1,64,[871],chunk=11)))
    assert np.array_equal(a,b)
    assert np.equal(a*2**52,np.floor(a*2**52)).all()

def test_qmcpy_nested_prefixes_and_determinism():
    pytest.importorskip('qmcpy')
    a=np.concatenate(list(blocks(8,64,16,[551],backend='qmcpy',chunk=8)))
    b=np.concatenate(list(blocks(8,64,16,[551],backend='qmcpy',chunk=8)))
    assert np.array_equal(a,b)
    for n in [1,2,4,8,16,32,64]:
        assert np.array_equal(np.sort((a[:,:n,0]*n).astype(int),axis=1),np.tile(np.arange(n),(16,1)))

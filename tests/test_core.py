import json,math
import numpy as np
import pytest
from scipy.integrate import quad
from rqmc.common import seed_words,load_config,digest,safe_relative
from rqmc.integrands import evaluate,truth
from rqmc.sampling import batch_means,blocks
from rqmc.intervals import ebci,hbci,hb_capital,mp09,t_interval
from rqmc.allocation import choose,proxy_width
from rqmc.experiment import execute_task

@pytest.mark.parametrize('stage',['pilot','production','other'])
def test_seed_stable(stage):
    assert seed_words(7,'A',stage)==seed_words(7,'A',stage)
    assert seed_words(7,'A',stage)!=seed_words(7,'B',stage)

def test_seed_domain_separation():
    assert len({tuple(seed_words(1,i,s)) for i in range(20) for s in ['pilot','production']})==40

@pytest.mark.parametrize('kind,extras',[('smooth1',{}),('step',{'threshold':.31}),('exp',{'lam':2}),('ridge',{'threshold':.5}),('smoothridge',{'a':.4}),('product',{})])
def test_integrals_known(kind,extras):
    c={'id':'test','kind':kind,'d':1,**extras}
    fn=lambda u:float(evaluate(c,np.array([[u]]))[0])
    points=[.31] if kind=='step' else None
    val,err=quad(fn,0,1,epsabs=1e-8,points=points,limit=250)
    assert val==pytest.approx(truth(c),abs=max(1e-7,5*err))

@pytest.mark.parametrize('case',load_config()['confirmation_cases'])
def test_function_range(case):
    u=np.random.default_rng(9).random((3,17,case['d']))
    x=evaluate(case,u)
    assert x.shape==(3,17) and np.isfinite(x).all() and x.min()>=0 and x.max()<=1

@pytest.mark.parametrize('kind,kwargs',[('ridge',{'threshold':0}),('smoothridge',{'a':.5})])
def test_normal_zero_endpoint(kind,kwargs):
    c={'kind':kind,'d':3,**kwargs}
    assert np.array_equal(evaluate(c,np.zeros((2,3))),[0.,0.])

@pytest.mark.parametrize('n',[2,4,16])
def test_scramble_determinism_and_distinctness(n):
    a=np.concatenate(list(blocks(2,n,4,[7,11],chunk=3)))
    b=np.concatenate(list(blocks(2,n,4,[7,11],chunk=2)))
    assert np.array_equal(a,b)
    assert not np.array_equal(a[0],a[1])
    # n-point one-dimensional stratification of each independent Sobol net.
    for row in a: assert sorted(np.floor(row[:,0]*n).astype(int))==list(range(n))

@pytest.mark.parametrize('n',[0,3,12])
def test_bad_net_size(n):
    with pytest.raises(ValueError):next(blocks(2,n,4,[1]))

def test_nested_prefixes_count_actual_evals():
    c={'kind':'smooth1','d':1};p,t=batch_means(c,16,16,[11],prefixes=[1,2,4,8,16])
    assert p.shape==(16,5) and t['calls']==256
    u=np.concatenate(list(blocks(1,16,16,[11])));v=evaluate(c,u)
    assert np.allclose(p[:,1],v[:,:2].mean(axis=1))

def scalar_eb(x,alpha=.05,c=.5):
    mu=.5;var=.25;sumx=0.;res=0.;sw=0.;swy=0.;pen=0.;lo=0.;hi=1.;R=len(x)
    for i,y in enumerate(x,1):
        l=min(c,math.sqrt(2*math.log(2/alpha)/(R*var)))
        pen+=(y-mu)**2*(-math.log1p(-l)-l);sw+=l;swy+=l*y
        rad=(math.log(2/alpha)+pen)/sw;lo=max(lo,swy/sw-rad);hi=min(hi,swy/sw+rad)
        sumx+=y;mu=(.5+sumx)/(i+1);res+=(y-mu)**2;var=(.25+res)/(i+1)
    return lo,hi

@pytest.mark.parametrize('size',[2,16,128,512])
def test_eb_scalar_vector(size):
    x=np.random.default_rng(size).beta(.5,2,size);a=ebci(x);b=scalar_eb(x)
    assert a['lower']==pytest.approx(b[0],abs=1e-12)
    assert a['upper']==pytest.approx(b[1],abs=1e-12)

@pytest.mark.parametrize('value',[0.,.2,1.])
@pytest.mark.parametrize('fn',[ebci,hbci,mp09,t_interval])
def test_constant_coverage(fn,value):
    a=fn(np.full(64,value));assert not a['empty'] and a['lower']<=value<=a['upper']
    assert 0<=a['lower']<=a['upper']<=1

@pytest.mark.parametrize('fn',[ebci,hbci,mp09,t_interval])
def test_bad_ci_input(fn):
    with pytest.raises(ValueError):fn([0.,float('nan')])
    with pytest.raises(ValueError):fn([-.01,.5])
    with pytest.raises(ValueError):fn([.2])

def test_hedged_inversion_monotone_and_grid():
    x=np.random.default_rng(17).beta(2,6,150);out=hbci(x)
    grid=np.linspace(0,1,101);cs=np.array([hb_capital(x,m) for m in grid])
    assert np.all(np.diff(cs[:,0])<=1e-10) and np.all(np.diff(cs[:,1])>=-1e-10)
    ok=(cs<=math.log(2/.05)).all(axis=1)
    assert ok.any()
    assert out['lower']<=grid[ok].min() and out['upper']>=grid[ok].max()
    if out['lower']>1e-8:assert hb_capital(x,out['lower']-1e-7)[0]>math.log(40)
    if out['upper']<1-1e-8:assert hb_capital(x,out['upper']+1e-7)[1]>math.log(40)

@pytest.mark.parametrize('method',['PLUGIN','A','B'])
@pytest.mark.parametrize('budget',[4096,16384])
def test_allocation_budget(method,budget):
    cfg=load_config();nmax=cfg['pilot_nmax'][str(budget)];ns=[n for n in cfg['fixed_n'] if n<=nmax]
    pilot=np.random.default_rng(7).random((16,len(ns)));cost=16*nmax
    n,R,info=choose(pilot,ns,budget,cost,method,cfg)
    assert n in ns and R>=32 and cost+R*n<=budget

def test_B_saturation_is_visible():
    cfg=load_config();ns=cfg['fixed_n'];pilot=np.random.default_rng(7).random((16,7))
    n,R,diag=choose(pilot,ns,16384,1024,'B',cfg)
    assert diag['variance_upper_saturation']==1 and n==1

def test_bad_accounting():
    cfg=load_config()
    with pytest.raises(ValueError):choose(np.zeros((16,3)),[1,2,4],4096,32,'A',cfg)

@pytest.mark.parametrize('method',['fixed_1','fixed_4','PLUGIN','A','B','t_R8'])
def test_end_to_end_small(method):
    cfg=load_config();cfg['budgets']=[256];cfg['pilot_nmax']={'256':4};cfg['fixed_n']=[1,2,4]
    c={'id':'unit','kind':'smooth1','d':1}
    row=execute_task((cfg,'unit',c,256,method,0,True))
    assert row['status']=='ok',row
    assert row['calls_used']<=256 and row['unused_budget']>=0
    for ci in row['intervals'].values():assert np.isfinite(ci['width'])

@pytest.mark.parametrize('bad',['../x','/tmp/x','C:/Windows/file','folder/../../x','folder\\x'])
def test_path_escape(tmp_path,bad):
    with pytest.raises(ValueError):safe_relative(tmp_path,bad)

def test_path_symlink(tmp_path):
    outside=tmp_path.parent/'outside_rqmc';outside.mkdir(exist_ok=True)
    link=tmp_path/'link'
    try:link.symlink_to(outside,target_is_directory=True)
    except (OSError,NotImplementedError):pytest.skip('Symlink not available')
    with pytest.raises(ValueError):safe_relative(tmp_path,'link/test')

def test_optional_qmcpy_api():
    pytest.importorskip('qmcpy')
    a=np.concatenate(list(blocks(2,4,5,[11],backend='qmcpy',chunk=3)))
    assert a.shape==(5,4,2) and not np.array_equal(a[0],a[1])
    for row in a:assert sorted(np.floor(row[:,0]*4).astype(int))==[0,1,2,3]

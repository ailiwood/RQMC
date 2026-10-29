"""Independent transform, reference and frozen-worker equivalence checks."""
import _bootstrap
import json
import math
import sys
from datetime import datetime, timezone
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr,ndtri
from rqmc.common import root,write_json,sha_file,seed_words
from rqmc.rescue_experiment import execute_rescue_task
from supplement.integrands import genz_upper,equicorrelation_cholesky
from supplement.runtime import execute,batch_means

r=root()
wheel=r/'validation_dependencies/mpmath-1.3.0-py3-none-any.whl'
assert sha_file(wheel)=='a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c'
sys.path.insert(0,str(wheel))
import mpmath as mp


def dense(u,m,rho,b):
    cov=(1-rho)*np.eye(m)+rho*np.ones((m,m))
    L=np.linalg.cholesky(cov)
    z=np.zeros((len(u),m-1)); mass=np.full(len(u),ndtr(b/L[0,0])); product=mass.copy()
    for j in range(1,m):
        z[:,j-1]=ndtri(u[:,j-1]*mass)
        conditional=np.sum(L[j,:j]*z[:,:j],axis=1)
        mass=ndtr((b-conditional)/L[j,j]); product*=mass
    return product,L


def hp_reference(m,rho,b,dps):
    with mp.workdps(dps):
        rr=mp.mpf(str(rho)); bb=mp.mpf(str(b))
        phi=lambda z:mp.exp(-z*z/2)/mp.sqrt(2*mp.pi)
        Phi=lambda x:mp.erfc(-x/mp.sqrt(2))/2
        f=lambda z:phi(z)*Phi((bb-mp.sqrt(rr)*z)/mp.sqrt(1-rr))**m
        value=mp.quad(f,[-12,-8,-4,0,4,8,12])
        return mp.nstr(value,dps-5)


def main():
    cfg_all=json.loads((r/'config/rescue_v1.json').read_text())
    cfg=dict(cfg_all); profiles=cfg.pop('rescue_profiles');cfg.pop('rescue_controls')
    new=json.loads((r/'config/supplement_v2.json').read_text())
    rng=np.random.default_rng(79120261029); checks=[]
    for m,rho,b in ((2,.25,0),(16,.25,0),(32,.7,.5),(8,0,.4)):
        u=rng.uniform(.0001,.9999,size=(257,m-1))
        value=genz_upper(u,m,rho,b); reference,L=dense(u,m,rho,b)
        delta=float(np.max(np.abs(value-reference)))
        assert np.allclose(value,reference,rtol=1e-12,atol=2e-14)
        diagonal,below=equicorrelation_cholesky(m,rho)
        assert np.allclose(np.diag(L),diagonal,rtol=1e-14,atol=1e-14)
        for j in range(m-1): assert np.allclose(L[j+1:,j],below[j],rtol=1e-14,atol=1e-14)
        endpoints=np.vstack([np.zeros(m-1),np.full(m-1,np.nextafter(1.,0.))])
        assert np.isfinite(genz_upper(endpoints,m,rho,b)).all()
        checks.append({'check':'independent dense Cholesky recursion and endpoint bounds','dimension':m,
                       'rho':rho,'upper':b,'max_absolute_difference':delta})
    for rho in (.25,.7):
        v,error=quad(lambda x:float(genz_upper(np.array([[x]]),2,rho,0)[0]),0,1,epsabs=1e-12)
        exact=.25+math.asin(rho)/(2*math.pi)
        assert abs(v-exact)<2e-11
        checks.append({'check':'bivariate orthant analytic identity','rho':rho,'error':v-exact,'quad_error':error})
    refs={}
    for case in new['cases'][:2]:
        m,rho,b=case['normal_dimension'],case['rho'],case['upper']
        f=lambda z:math.exp(-z*z/2)/math.sqrt(2*math.pi)*ndtr((b-math.sqrt(rho)*z)/math.sqrt(1-rho))**m
        value,error=quad(f,-12,12,epsabs=1e-14,epsrel=1e-13,limit=500)
        hp50=hp_reference(m,rho,b,50); hp80=hp_reference(m,rho,b,80)
        assert abs(value-float(hp80))<1e-13 and abs(float(hp50)-float(hp80))<1e-14
        radius=max(1e-12,100*error,10*abs(value-float(hp80)))
        refs[case['id']]={'reference':float(hp80),'float64_quad':value,'quad_reported_absolute_error':error,
                         'mpmath_50digits':hp50,'mpmath_80digits':hp80,
                         'truncation_tail_bound':float(2*ndtr(-12)),
                         'coverage_sensitivity_radius':radius,
                         'radius_is_numerical_sensitivity_not_formal_interval_arithmetic_certificate':True}
        means,times=batch_means(case,4096,32,seed_words(20261029,'kernel_validation',case['id']),cfg)
        se=float(means.std(ddof=1)/np.sqrt(len(means))); diff=float(means.mean()-float(hp80))
        assert abs(diff)<6*se+5e-7
        refs[case['id']]['kernel_check']={'scrambles':32,'n':4096,'mean':float(means.mean()),'mcse':se,
                                        'difference':diff,'calls':times['calls'],'not_coverage_evidence':True}
    write_json(r/'state/supplement_v2/application_references.json',{'cases':refs,'mpmath_wheel_sha256':sha_file(wheel)})
    # Old-case worker produces exactly the same production sequence, allocation,
    # and EBCI/HBCI values. Only supplementary diagnostics and runtime differ.
    equivalence=[]
    for case in (cfg['development_cases'][0],cfg['development_cases'][-1]):
        for method in ('fixed_4','A02','PLUGIN_STAGE'):
            spec=profiles.get(method)
            task=(cfg,'supplement_v2_equivalence',case,4096,method,7)
            old=execute_rescue_task((*task,True,spec))
            fresh=execute((*task,spec,'both'))
            assert old['status']==fresh['status']=='ok'
            for key in ('selected_n','production_reps','pilot_calls','calls_used','estimate','seed_digest','production_means_digest'):
                assert old[key]==fresh[key],key
            for ci in ('ebci','hbci'):
                assert all(fresh['intervals'][ci][k]==v for k,v in old['intervals'][ci].items())
            equivalence.append({'case':case['id'],'method':method,'all_original_scientific_fields_checked':True})
    assert new['cases'][2]['threshold']==float(ndtri(1-1e-3))
    assert new['cases'][3]['threshold']==float(ndtri(1-1e-4))
    write_json(r/'state/supplement_v2/kernel_validation.json',{
        'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'worker_equivalence':equivalence,
        'references_sha256':sha_file(r/'state/supplement_v2/application_references.json'),
        'sources':{str(p.relative_to(r)):sha_file(p) for p in (r/'supplement/integrands.py',r/'supplement/runtime.py',r/'scripts/validate_supplement.py')},
        'limitations':['Not an independent human proof or general floating-point certification.',
                      'Known [0,1] range is analytic. Continuum/grid/roundoff distinctions remain as in original sampling audit.']})
    print(json.dumps({'status':'PASS','reference_cases':refs,'worker_equivalence_tasks':len(equivalence)},indent=2))


if __name__=='__main__':main()

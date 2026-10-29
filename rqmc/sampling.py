from __future__ import annotations
from time import perf_counter
import inspect
import numpy as np
from scipy.stats import qmc
from .integrands import evaluate

def _power_two(n): return isinstance(n,(int,np.integer)) and n>0 and n&(n-1)==0

def blocks(d: int,n: int,reps: int,entropy,backend='scipy',chunk=128):
    """Independent LMS+digital-shift scrambles. No splitting of a single net."""
    if not _power_two(n) or reps<1 or chunk<1 or d<1: raise ValueError('Invalid net shape')
    ss=np.random.SeedSequence(entropy)
    # At n=1 use IID uniform on the same 52-bit digital grid as both net backends.
    if n==1:
        rng=np.random.default_rng(ss)
        for a in range(0,reps,chunk):
            yield rng.integers(0,2**52,size=(min(chunk,reps-a),1,d),dtype=np.uint64).astype(np.float64)*2.**-52
        return
    if backend=='scipy':
        children=ss.spawn(reps)
        rng_supported='rng' in inspect.signature(qmc.Sobol).parameters
        for a in range(0,reps,chunk):
            out=np.empty((min(chunk,reps-a),n,d),dtype=np.float64)
            for j,child in enumerate(children[a:a+chunk]):
                rng=np.random.default_rng(child)
                kwargs={'rng':rng} if rng_supported else {'seed':rng}
                engine=qmc.Sobol(d,scramble=True,bits=52,optimization=None,**kwargs)
                out[j]=engine.random_base2(int(n).bit_length()-1)
            yield out
    elif backend=='qmcpy':
        from qmcpy import DigitalNetB2  # optional; no silent fallback
        children=ss.spawn((reps+chunk-1)//chunk)
        for b,a in enumerate(range(0,reps,chunk)):
            size=min(chunk,reps-a)
            engine=DigitalNetB2(dimension=d,replications=size,seed=children[b],
                                randomize='LMS DS',order='GRAY',t=52)
            out=np.asarray(engine.gen_samples(n=n),dtype=np.float64)
            if out.shape!=(size,n,d): raise RuntimeError('QMCPy API/shape changed; validate adapter')
            if not np.isfinite(out).all() or np.any(out<0) or np.any(out>=1):
                raise RuntimeError('QMCPy point range invalid')
            yield out
    else: raise ValueError('Backend must be scipy or qmcpy')

def batch_means(case,n,reps,entropy,backend='scipy',chunk=128,prefixes=None):
    means=[]; sample_s=0.; eval_s=0.
    iterator=iter(blocks(case['d'],n,reps,entropy,backend,chunk))
    while True:
        t=perf_counter()
        try: u=next(iterator)
        except StopIteration: break
        sample_s+=perf_counter()-t
        t=perf_counter(); v=evaluate(case,u)
        if prefixes is None: m=v.mean(axis=1)
        else:
            if any(not _power_two(x) or x>n for x in prefixes): raise ValueError('Bad prefixes')
            c=np.cumsum(v,axis=1)
            m=np.stack([c[:,x-1]/x for x in prefixes],axis=1)
        means.append(m);eval_s+=perf_counter()-t
    return np.concatenate(means,axis=0),{'sampling_s':sample_s,'evaluation_s':eval_s,'calls':int(n*reps)}

from __future__ import annotations
import math
import numpy as np
from scipy.special import ndtr, ndtri

def evaluate(case: dict, u: np.ndarray) -> np.ndarray:
    """Evaluate bounded f. Exact integrals are intentionally in truth(), not here."""
    u=np.asarray(u,dtype=np.float64)
    if u.shape[-1]!=case['d'] or not np.isfinite(u).all() or np.any(u<0) or np.any(u>=1):
        raise ValueError('Expected finite points in [0,1) with the configured dimension')
    kind=case['kind']
    if kind=='smooth1': v=u[...,0]*np.exp(u[...,0]-1)
    elif kind=='step': v=(u[...,0]<case['threshold']).astype(float)
    elif kind=='exp': v=np.exp(-case['lam']*u.mean(axis=-1))
    elif kind in ('ridge','smoothridge'):
        # No clipping. At zero ndtri=-inf; u=1 is excluded, so inf-inf cannot occur.
        z=ndtri(u).sum(axis=-1)/math.sqrt(case['d'])
        v=(z>case['threshold']).astype(float) if kind=='ridge' else ndtr(z+case['a'])
    elif kind=='product': v=np.prod((1+np.cos(2*np.pi*u))/2,axis=-1)
    else: raise ValueError(f'Unknown integrand {kind}')
    if not np.isfinite(v).all() or np.any(v < -1e-14) or np.any(v>1+1e-14):
        raise ArithmeticError('Integrand violated the known [0,1] bounds')
    return v

def truth(case: dict) -> float:
    """Evaluator only; allocation modules must never import this."""
    k=case['kind']
    if k=='smooth1': return math.exp(-1)
    if k=='step': return float(case['threshold'])
    if k=='exp':
        a=case['lam']/case['d']
        return float((-np.expm1(-a)/a)**case['d']) if a else 1.
    if k=='ridge': return float(ndtr(-case['threshold']))
    if k=='smoothridge': return float(ndtr(case['a']/math.sqrt(2)))
    if k=='product': return 2.**(-case['d'])
    raise ValueError(k)

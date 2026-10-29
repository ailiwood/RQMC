"""Bounded application transform; no evaluator reference is accessible here.

Independently written conditional Gaussian transform, natural coordinate order.
For positive equicorrelation, every entry below a given Cholesky diagonal is
constant. Accumulating that column gives the dense recursion in O(d) per point.
"""
from functools import lru_cache
import numpy as np
from scipy.special import ndtr, ndtri
from rqmc.integrands import evaluate as original_evaluate


@lru_cache(maxsize=16)
def equicorrelation_cholesky(d, rho):
    if d < 2 or not 0 <= rho < 1:
        raise ValueError('Require dimension>=2 and nonnegative nonsingular correlation')
    j=np.arange(d,dtype=float)
    diagonal=np.sqrt((1-rho)*(1+j*rho)/(1+(j-1)*rho))
    below=rho*np.sqrt((1-rho)/((1+(j-1)*rho)*(1+j*rho)))
    return diagonal,below


def genz_upper(u, dimension, rho, upper):
    u=np.asarray(u,dtype=float)
    if u.shape[-1] != dimension-1 or not np.isfinite(u).all() or np.any(u<0) or np.any(u>=1):
        raise ValueError('Genz transform requires finite [0,1)^(dimension-1) points')
    diagonal,below=equicorrelation_cholesky(int(dimension),float(rho))
    mass=np.full(u.shape[:-1],ndtr(upper))
    product=mass.copy()
    if rho==0:
        return np.full(u.shape[:-1],float(ndtr(upper)**dimension))
    conditional_sum=np.zeros(u.shape[:-1])
    for j in range(dimension-1):
        # At u=0 use the extended-real lower endpoint exactly. With rho>0,
        # all subsequent conditional masses tend to one; no clipping is needed.
        latent=ndtri(u[...,j]*mass)
        conditional_sum += below[j]*latent
        mass=ndtr((upper-conditional_sum)/diagonal[j+1])
        product*=mass
    if not np.isfinite(product).all() or np.any(product<0) or np.any(product>1):
        raise ArithmeticError('Genz integrand outside a priori [0,1] bounds')
    return product


def evaluate(case,u):
    if case['kind']=='mvn_upper':
        if case['d'] != case['normal_dimension']-1:
            raise ValueError('Integration dimension mismatch')
        return genz_upper(u,case['normal_dimension'],case['rho'],case['upper'])
    return original_evaluate(case,u)

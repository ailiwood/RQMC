from __future__ import annotations
import math
import numpy as np
from scipy.stats import t as student_t

def _validate(x,alpha):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all() or np.any(x<0) or np.any(x>1):
        raise ValueError('Need >=2 finite scramble means in [0,1]')
    if not 0<alpha<1: raise ValueError('Bad alpha')
    return x

def moments(x):
    n=len(x); ts=np.arange(1,n+1,dtype=np.float64)
    mu=(.5+np.cumsum(x))/(ts+1)
    var=(.25+np.cumsum((x-mu)**2))/(ts+1)
    return np.r_[.5,mu[:-1]],np.r_[.25,var[:-1]]

def result(lo,hi):
    lo=float(lo);hi=float(hi)
    if not (math.isfinite(lo) and math.isfinite(hi)): raise ArithmeticError('Nonfinite endpoint')
    return {'lower':lo,'upper':hi,'width':max(0.,hi-lo),'empty':lo>hi}

def ebci(x,alpha=.05,cap=.5):
    """PrPl-EB fixed R, Jain et al. Eqs7/8; running intersection, not proxy."""
    x=_validate(x,alpha)
    if not 0<cap<1: raise ValueError('Invalid cap')
    mu_pre,var_pre=moments(x)
    lam=np.minimum(cap,np.sqrt(2*np.log(2/alpha)/(len(x)*var_pre)))
    sw=np.cumsum(lam); center=np.cumsum(lam*x)/sw
    rad=(np.log(2/alpha)+np.cumsum((x-mu_pre)**2*(-np.log1p(-lam)-lam)))/sw
    return result(max(0.,float(np.max(center-rad))),min(1.,float(np.min(center+rad))))

def hb_capital(x,m,alpha=.05,cap=.5):
    """Return max-prefix log capitals for the two separate martingales."""
    x=_validate(x,alpha)
    if not 0<=m<=1 or not 0<cap<1: raise ValueError('Bad m or cap')
    _,v=moments(x)
    b=np.sqrt(2*np.log(2/alpha)/(len(x)*v))
    lp=np.minimum(b,cap/m) if m>0 else b
    lm=np.minimum(b,cap/(1-m)) if m<1 else b
    plus=np.cumsum(np.log1p(lp*(x-m)))
    minus=np.cumsum(np.log1p(-lm*(x-m)))
    return max(0.,float(np.max(plus))),max(0.,float(np.max(minus)))

def hbci(x,alpha=.05,cap=.5,theta=.5,tol=1e-10):
    """Invert two monotone capital constraints, returning outward numerical bounds."""
    x=_validate(x,alpha)
    if not 0<cap<1 or not 0<theta<1 or not 0<tol<.01: raise ValueError('Invalid parameters')
    _,v=moments(x);b=np.sqrt(2*np.log(2/alpha)/(len(x)*v))
    def plus(m):
        l=np.minimum(b,cap/m) if m>0 else b
        return max(0.,float(np.max(np.cumsum(np.log1p(l*(x-m))))))
    def minus(m):
        l=np.minimum(b,cap/(1-m)) if m<1 else b
        return max(0.,float(np.max(np.cumsum(np.log1p(-l*(x-m))))))
    tp=np.log(1/(alpha*theta));tm=np.log(1/(alpha*(1-theta)))
    if plus(0)<=tp: low=0.
    else:
        a,z=0.,1.
        while z-a>tol:
            m=(a+z)/2
            if plus(m)>tp:a=m
            else:z=m
        low=a # outside the accepted set: conservative expansion
    if minus(1)<=tm: high=1.
    else:
        a,z=0.,1.
        while z-a>tol:
            m=(a+z)/2
            if minus(m)>tm:z=m
            else:a=m
        high=z
    return result(low,high)

def mp09(x,alpha=.05):
    """Diagnostic only: not the primary R01 predictable-plug-in EBCI."""
    x=_validate(x,alpha);n=len(x);l=np.log(4/alpha)
    r=np.sqrt(2*np.var(x,ddof=1)*l/n)+7*l/(3*(n-1))
    return result(max(0.,np.mean(x)-r),min(1.,np.mean(x)+r))

def t_interval(x,alpha=.05):
    x=_validate(x,alpha)
    if np.all(x==x[0]): return result(x[0],x[0]) # exact constant input; asymptotic t comparator only
    r=student_t.ppf(1-alpha/2,len(x)-1)*np.std(x,ddof=1)/np.sqrt(len(x))
    return result(max(0.,np.mean(x)-r),min(1.,np.mean(x)+r))

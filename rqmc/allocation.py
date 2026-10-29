from __future__ import annotations
import numpy as np

def proxy_width(var,reps,alpha=.05):
    """Selection proxy from the user design, NEVER a final confidence bound."""
    var=np.asarray(var,dtype=float);reps=np.asarray(reps,dtype=float)
    if np.any(var<0) or np.any(reps<2): raise ValueError('Bad variance/count')
    l=np.log(2/alpha)
    return 2*(l/(3*reps)+np.sqrt(2*var*l/reps+l*l/(9*reps*reps)))

def choose(pilot,ns,budget,pilot_calls,route,cfg):
    x=np.asarray(pilot,dtype=float);ns=np.asarray(ns,dtype=int)
    if x.shape!=(cfg['pilot_replicates'],len(ns)) or not np.isfinite(x).all():
        raise ValueError('Pilot shape/values')
    if np.any(x<0) or np.any(x>1):raise ValueError('Pilot outside known bounds')
    if pilot_calls!=int(cfg['pilot_replicates']*max(ns)):raise ValueError('Pilot accounting mismatch')
    counts=(budget-pilot_calls)//ns
    valid=counts>=cfg['min_production_replicates']
    if not np.any(valid):raise ValueError('Insufficient production budget')
    raw=np.var(x,axis=0,ddof=1);v=raw.copy(); saturated=0.
    if route=='A':
        # Fixed low-dimensional smoothing, not truth-based model selection.
        z=np.log(np.maximum(raw,cfg['variance_floor']));w=np.log(ns)
        slope=np.polyfit(w,z,1)[0] if len(ns)>1 else -1.
        slope=float(np.clip(slope,*cfg['smooth_slope']))
        intercept=float(np.mean(z-slope*w))
        v=np.clip(np.exp(intercept+slope*w),0,.25)
    elif route=='B':
        if len(x)%2:raise ValueError('Paired pilot needs an even number')
        d=(x[::2]-x[1::2])**2/2
        eps=.5*np.sqrt(np.log(len(ns)/cfg['pilot_beta'])/(2*len(d)))
        unbounded=d.mean(axis=0)+eps
        saturated=float(np.mean(unbounded>=.25));v=np.minimum(.25,unbounded)
    elif route!='PLUGIN':raise ValueError('Only PLUGIN/A/B allowed')
    scores=np.full(len(ns),np.inf)
    scores[valid]=proxy_width(v[valid],counts[valid],cfg['alpha'])
    i=int(np.argmin(scores)) # deterministic ties favor the smallest n
    return int(ns[i]),int(counts[i]),{'raw_zero_variances':int(np.sum(raw==0)),
        'variance_upper_saturation':saturated,'proxy_width':float(scores[i]),
        'pilot_variances':raw.tolist(),'selection_variances':v.tolist(),'candidate_n':ns.tolist()}

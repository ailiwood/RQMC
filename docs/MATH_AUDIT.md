# Required mathematical audit

Primary: Jain et al., Information and Inference 15(1), iaag003 (2026), DOI10.1093/imaiai/iaag003; author text https://arxiv.org/html/2504.18677v2 . Original betting source: Waudby-Smith & Ramdas, JRSSB86(1),1–27, DOI10.1093/jrsssb/qkad009.

Let x_i be independent production scramble means in [0,1], i=1..R. Define m_t=(0.5+sum_{i<=t}x_i)/(t+1), s_t²=(0.25+sum_{i<=t}(x_i-m_i)²)/(t+1); m_0=.5, s_0²=.25. The variance update uses m_i whereas the EBCI squared prediction error uses m_{i-1}; do not conflate.

PrPl-EB: λ_i=min(c,sqrt(2 log(2/α)/(R s_{i-1}²))). Weighted mean at t = sum λ_i x_i / sum λ_i. Radius=[log(2/α)+sum (x_i-m_{i-1})²*(-log(1-λ_i)-λ_i)]/sum λ_i. Intersect over all t≤R and [0,1]. R stays the preselected production size for all intermediate weights. This is NOT the allocation proxy, nor MP09 Eq(6).

HBCI: b_i=sqrt(2 log(2/α)/(R s_{i-1}²)); λ_i^+(m)=min(b_i,c/m), λ_i^-(m)=min(b_i,c/(1-m)). Log capital for plus=sum log1p(λplus*(x-m)); minus=sum log1p(-λminus*(x-m)). Include every prefix and prior capital 1. With θ=.5 retain m when max-prefix logKplus≤log(2/α) AND max-prefix logKminus≤log(2/α). Invert monotone functions separately; round numerical endpoints outwards.

Transcription cautions in author HTML: negative product displays lambda-plus in one place; use the original paper definition to verify minus. The maximum of two martingales is NOT in general a martingale. Coverage follows by applying Ville to two nonnegative processes with risk θα and (1−θ)α (union bound), not by calling their maximum a martingale. Record primary-source verification, don't silently attribute a corrected formula as an exact quote.

Numerical audit: empty intersections are possible on rare paths; retain and count them as noncoverage. Never replace by a point interval or discard. NaN/Inf is numerical failure, not statistical emptiness. EBCI center is weighted, not generally sample mean. HBCI bisection returns conservative outer endpoints. Pilot-upper-bound risk affects selection only; production inference has its own α and no pilot observations. Finite precision changes a continuum into a digital grid: document bits, endpoint behavior, tolerances; no artificial clipping without bias analysis.

Before formal experiment: cross-check vector EBCI against independent scalar loop; HBCI endpoints against direct grid/log capital; constant, all-zero, all-one, Bernoulli and continuous input tests; small external reference check against legally accessible author code where possible. Included tests establish implementation consistency, not the theorem's proof or observed nominal coverage in every research case.

## Pre-experiment route-B degeneracy (analytical, not an experiment result)
With 16 pilot scrambles, 8 pairs, K=7 and beta=.10, the Hoeffding addition alone is 0.5*sqrt(log(70)/16) ≈0.258, exceeding the universal variance bound .25. Thus all upper bounds saturate at .25 for the N=16384 profile and the proxy chooses n=1 regardless of pilot data. This is an exact limitation of this concrete B variant. Codex should document and analytically retire this budget's B route before costly simulation; it may retain B as a diagnostic or drop it from the full matrix BEFORE freeze with an explicit deviation/retirement report. Do not change beta/constants post hoc or disguise a new route as a bug fix. This retirement is a failure of B, not evidence that A works. The package retains B in the default config so the diagnostic is visible and testable.

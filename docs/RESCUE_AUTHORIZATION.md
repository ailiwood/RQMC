# A rescue study amendment — 2026-10-28

The user explicitly authorized starting experiments with up to ten distinct remedial measures, methods or paths, seeking a useful positive contribution and requesting a process review if attempts become repetitive. This later authorization supersedes the earlier prohibition on further development after the first stopping gate and the previous one-revision recommendation. Original design documents and the completed negative study remain immutable evidence. This is not a software-error rerun.

The ceiling is ten scientific interventions, not ten seeds or ten confirmation looks. Each intervention is registered before evaluation, counted permanently, and must state a mechanism distinct from previous attempts. Engineering fixes do not count as new scientific attempts but invalidate affected data if necessary. B remains retired; PLUGIN remains a baseline. Work remains centered on A and the original bounded-integrand RQMC allocation question. No unrelated project, GPU, cloud spending, or publication action is authorized.

## Development and confirmation separation

Use new `rescue_v1_development` streams on the four original development cases. Budgets are 4096, 16384 and the originally planned 65536. Each method receives 200 full repetitions per cell, with the same complete-case matrix. EBCI remains primary; HBCI remains a predeclared secondary comparison on smooth1 and ridge. All seven fixed n methods, fixed-R t methods, original PLUGIN, original A/B diagnostics and an objective-matched raw-variance PLUGIN control are retained. No control receives artificial pilot charges.

The initial pilot rule is 16 independent scrambles with nested powers-of-two prefixes through min(64, N/256), rounded down to a power of two. Pilot calls are therefore 256, 1024, 1024; the added 65536 budget has a 1.5625% pilot because the complete candidate grid ends at n=64. This rule is fixed before the new experiments and applied equally to original and revised selectors. It is not claimed that an unchanged 6.25% pilot fraction is amortized by a larger budget.

Within development, a method advances only if it has a plausible positive contribution after all costs: at least two development function families with >=10% mean-width improvement against the common fixed baseline, geometric-mean width ratio below one over all cells, no explanation based on invalid coverage, and a useful explanation/ablation relative to PLUGIN. The common fixed baseline minimizes equal-cell geometric mean EBCI width on development. The complete fixed grid must be shown, including unfavourable cases. These are exploratory screening criteria, not confirmation tests or journal acceptance standards. Candidate comparisons to an objective-matched PLUGIN must be disclosed even if unfavourable; smoothing is not claimed beneficial without evidence.

Once a mechanism and exact definition pass development, stop tuning, record all attempted methods, freeze configuration/source/dependencies and run independent confirmation. No revised algorithm may read a true integral or a true variance. Confirmation families/parameters remain unopened; they cannot be recycled for iterative method selection. One confirmation stage is intended. A failed confirmation closes this rescue study rather than authorizing ten test-set looks.

Before confirmation, specify the exact primary claim, contrasts, multiplicity handling, repeat counts and effect-size criteria. A paper requires a substantive positive contribution, complete coverage qualifications, independent confirmation, nearest-neighbor audit, reproducible raw-to-table analysis, compiled manuscript and page review. A software/CI/budget failure is not a publishable efficiency gain.

## Attempt 1 — expected-moment finite-R EBCI objective

Keep original A's bounded log-linear variance smoothing and pilot budget. Replace its Bennett-style ranking proxy with a deterministic expected-moment surrogate derived from the actual EBCI formula, including its 0.5/0.25 initialization, predictable variance, lambda cap and prefix intersection. Estimate the common mean from the largest pilot prefix; use no integrand identity or truth in the selector. This surrogate is not itself a confidence interval and is not asserted to equal expected actual width. An objective-matched raw-variance PLUGIN is included to isolate the role of smoothing.

For IID scramble means with mean mu and variance v, writing delta=mu-0.5:

E[(X_i-m_i)^2] = v(i^2+i-1)/(i+1)^2 + delta^2/(i+1)^2.

E[(X_i-m_(i-1))^2] = v(1+(i-1)/i^2) + delta^2/i^2.

With H_i=sum_(j=1)^i 1/j and H2_i=sum_(j=1)^i 1/j^2,

E[s_(i-1)^2] = [0.25 + v(i+1-H_i-H2_i) + delta^2(H2_i-1)]/i.

Insert these expectations into the EBCI betting weights and penalty. Center the surrogate at mu, clip the predicted interval to [0,1], and take its running intersection. Exactness holds for constant samples; randomness in the weights/center prevents a general equality to expected interval width. Validate the moment identities by exact finite Bernoulli enumeration, and validate the constant limit against the actual interval implementation before running experiments.

## Stop and record

### Attempt 2 registration (after complete attempt 1 development)

A01 completed 2400 tasks alongside all controls. The common fixed baseline became fixed_4 on the expanded three-budget matrix. A01's geometric ratio is 0.9330 against fixed_4, 0.8168 against original PLUGIN and 0.9938 against the objective-matched raw PLUGIN. Only exp reaches the 10% family screen; step at N=65536 has ratio 0.9016. This is a useful objective correction but does not yet pass the advancement gate.

A02 uses the same finite-R objective and original log smoothing, with an adaptive-depth pilot. Generate a single bounded block of 16 cap-length randomized nets, initially evaluate only their first 4 points, and extend by disjoint dyadic suffixes only when the selected n exceeds half the currently observed depth. Stop at the original cap in all events. At each stage use the current actual cumulative pilot charge in remaining production counts. Candidate n values are limited to observed powers of two. All generated points incur sampling time; only evaluated points incur integrand calls. Production streams remain independent of the complete adaptive pilot history. `PLUGIN_STAGE` uses exactly this policy with raw rather than smoothed variances. Prefix equality and disjoint evaluation accounting are checked before execution. This is a new pilot policy, not a bug fix to A01.

Preserve all raw outputs, failures, source snapshots, costs and attempt decisions. Stop before ten if evidence supports a final frozen candidate or if new proposals merely repeat an exhausted mechanism. Reaching ten without useful evidence ends experimentation and produces a process/lessons/next-step report. Resource or session failure is recorded as resumable, never as scientific evidence.

# Rescue confirmation protocol — registered before any confirmation task

Date: 2026-10-28. Final candidate A02. Scientific interventions used: 2 of at most 10. No additional method tuning after this protocol is sealed. Full definitions are in `docs/RESCUE_AUTHORIZATION.md`, `config/rescue_v1.json` and the runtime source snapshot. The original negative study and every rescue development method remain reported.

## Claim and scope

Evaluate whether calibrating the allocation objective to finite-R EBCI behavior and adaptively limiting pilot depth produces useful interval-width reductions with a fully charged independent pilot. The intended contribution is the allocation criterion and pilot policy, not EBCI/HBCI themselves, conditional coverage, generic log-slope fitting, or parallel sampling. The raw-variance objective-matched and stage-matched PLUGIN variants are ablations/baselines, not renamed innovations. No independent claim that smoothing is beneficial will be made unless its own contrasts support that claim.

Independent confirmation uses six already specified cases: smooth1; step threshold sqrt(2)/4; exp d=32, lambda=3; normal ridge d=32, threshold=1.5; smooth normal ridge d=8, a=.5; cosine product d=8. The last two function families have not been used in development. Budgets are 4096/16384/65536. Repetitions are exactly 1000 complete tasks per case, budget and method. Fixed seed 20261028 with the new `rescue_v1_confirmation` domain; production and complete adaptive pilot history have separate hash-derived entropy. Methods have independent streams; pairing by repetition index is not common random numbers.

The complete 18-method matrix is: fixed_n for n=1,2,4,8,16,32,64; original A, original B diagnostic, original PLUGIN; PLUGIN_MATCH; PLUGIN_STAGE; A01; A02; BUDGET_FIXED; t_R8, t_R16, t_R32. EBCI is primary for all 15 non-t methods. HBCI is secondary for c_smooth1 and c_ridge, applied to all 15 methods. Fixed-R t intervals remain practical/asymptotic comparators and do not supply distribution-free coverage claims. There are 324000 tasks and 414000 intervals if every task succeeds.

## Fixed references selected solely on development

Primary common baseline: fixed_4, selected by equal-cell geometric mean EBCI mean width across the complete development matrix (4 cases x 3 budgets).

Stronger fixed schedule: BUDGET_FIXED uses n=2 at 4096, n=4 at 16384 and n=4 at 65536. For each budget this minimizes the four-case development geometric mean width. It uses no function identity, no pilot and no truth. It is registered before confirmation, then run with its own independent production streams and zero pilot charge. All individual fixed-n results remain visible.

## Primary statistical assessment

The independent simulation unit is one complete pilot-selection-production repetition. For every case/budget/method report mean, median and 90th-percentile widths, MCSE, coverage with 95% Wilson intervals, empty sets, numerical failures, costs and selection distributions. Failed calculations remain in coverage denominators and have separately reported width summaries. Never infer zero failure probability from zero observed events.

For A02 versus each of fixed_4 and BUDGET_FIXED, report all 18 case/budget mean-width ratios and paired-ID differences. Their streams remain independent. Delta-method ratio influence values use x/mean(x)-y/mean(y); per-cell ratios use t_(999) uncertainty. The equal-cell geometric mean of the 18 mean-width ratios is the aggregate performance measure. Across cells the random streams are independent, so the aggregate log-ratio MC variance is the sum of squared per-cell log-ratio MCSEs divided by 18^2.

Two aggregate superiority comparisons (A02/fixed_4 and A02/BUDGET_FIXED) use one-sided Bonferroni levels .025 each; their upper bounds must both be below 1 for the broad efficiency claim. All 18 primary cellwise A02/fixed_4 differences form one Holm family at .05. A useful positive confirmation additionally requires at least two distinct function families each having a prespecified-budget cell with point mean-width ratio <=.90 and Holm-adjusted superiority p<.05. This criterion does not imply a simultaneous 10% lower effect bound; report actual uncertainty and do not strengthen the statement.

Coverage quality guard: A02's empirical primary coverage must be at least .94 in all 18 cells, and cells used for the useful-gain statement must have coverage >=.95 and Wilson lower bound >=.93. These are diagnostic simulation guards at 1000 repetitions, not a proof of coverage. The finite-sample justification comes from the fixed-n interval theory conditional on the complete independent pilot. Report all observed violations, empty sets and failures even if guards pass elsewhere. Any unexplained numerical issue closes the positive claim until repaired and affected data are explicitly invalidated.

Original PLUGIN and both matched PLUGIN contrasts, A01/A02 ablations, HBCI, t intervals, wall time and per-cell best fixed methods are secondary/descriptive. Do not replace the primary endpoint, switch comparison families, or promote a favourable secondary interval after inspection. A02 need not beat every fixed n on every case. Losses and near-ties are required context.

## Integrity, resource and reproducibility gates

Seal runtime source hashes, exact selected profiles/config, this protocol, dependencies, source snapshot hashes and the complete development receipt before launching. The runner rejects changed configuration, selected profile, runtime sources or environment on confirmation resume. Task IDs cannot be reset; existing results append only missing tasks. A software error invalidates affected confirmation and must be disclosed; scientific retuning is not a bug fix.

All evaluated pilot points are charged once, nested dependence is disclosed, generated-but-unevaluated pilot points incur real sampling time, unused calls are reported, and fixed references receive no artificial pilot. Total observed throughput is not an isolated method latency or a strict wall-time-budget theorem. Measure isolated latency separately on predeclared representative tasks. No sleep-generated gains or hardware-specific innovation claim.

The conditional-coverage argument is elementary and will not be claimed as a new theorem. The expected-moment surrogate is a ranking heuristic, not a confidence interval, not an exact expected width for general distributions, and not a certified finite-budget oracle guarantee. Document approximation failure regimes and smoothing's limited incremental effect.

If confirmation contradicts the primary useful-contribution criteria, close this rescue study and report process, lessons and a next-step research plan. Do not open up to eight further variants on these confirmation outcomes. If it supports the claim, complete nearest-neighbor review, full raw-to-table figures, an English Algorithms-format draft, actual PDF compilation/page review, reference/claim ledger, author questions, disclosure and unsent cover letter, and isolated source/data reproduction. Status is DRAFT_READY_FOR_HUMAN_REVIEW only after these delivery checks.

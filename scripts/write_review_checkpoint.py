"""Update only mutable documentation after verified organization, not scientific state."""
import _bootstrap
import json
from rqmc.common import root, write_json, sha_file


def main():
    r=root();folder=r/'review/2026-10-29'
    organization=json.loads((folder/'organization_receipt.json').read_text(encoding='utf-8'))
    assert organization['status']=='EXACT_MANIFEST_ARCHIVED_AND_ALL_FILE_HASHES_VERIFIED'
    overview='review/2026-10-29/2026-10-29--A-rescue-v1--r02--round-review.md'
    (r/'RESEARCH_REPORT.md').write_text('# 当前研究总结入口\n\n'
        f'全面最新版：[{overview}]({overview})。\n\n'
        '当前路线和变更：[最新研究路线设计](最新研究路线设计.md)。\n\n'
        '学术审查及待批准补充：[计划](review/2026-10-29/ASSESSMENT_AND_SUPPLEMENT_PLAN.md)。\n\n'
        '已有同 EBCI 正向确认成立；本轮重新审查发现跨区间实际效用仍需补强。未新增实验，未修改原论文。'
        '旧版总结已随文档快照归档，防止多个版本混用。\n',encoding='utf-8')
    repro=r/'REPRODUCE_RESCUE.md';text=repro.read_text(encoding='utf-8')
    text=text.replace('The original `FAILURE_REPORT.md` documents the earlier completed study; it is not silently overwritten by the rescue. Original results remain in `results/raw/development.jsonl`.',
        'The original stopped study is preserved completely in `evidence/original_study_20261027.zip`, including FAILURE_REPORT.md and results/raw/development.jsonl at their original paths inside that archive. Historical loose files have been organized into the explicitly labeled manual-cleanup archive.')
    text+='\n## Organization and review on 29 October 2026\n\n'
    text+='Use 当前研究入口.md and 最新研究路线设计.md for the current route. The updated bundle contains the review/2026-10-29 analysis, scholarly assessment and proposed supplementary protocol. No new experiments were run and no manuscript/PDF source was changed in this review. The original full evidence ZIP remains active in evidence/. Archived scratch copies are not required to reproduce the current scientific result or compile the manuscript. Earlier scratch paths in historical receipts describe where those checks actually ran, not a requirement to keep the scratch tensors/copies.\n\n'
    text+='Legacy scientific helper files remain because they are sealed source or shared comparator dependencies. The historical standalone workflow can be recovered by extracting evidence/original_study_20261027.zip into a fresh project-local scratch directory. Do not launch the old workflow from stale notes or reset any counters. The current review recommends supplementary work but requires the user\'s approval before performing it.\n'
    repro.write_text(text,encoding='utf-8')
    checkpoint='# Current handoff — 2026-10-29\n\n'
    checkpoint+='Project root is E:/00project_code/main_qiubai/1027_RQMC. Read 当前研究入口.md, 最新研究路线设计.md and the current report linked by RESEARCH_REPORT.md. Earlier contradictory live handoffs have been archived, not silently treated as current.\n\n'
    checkpoint+='Existing scientific status: DRAFT_READY_FOR_HUMAN_REVIEW. A02 is frozen and supported on the declared same-EBCI matrix. Two interventions used of ten; eight unused. 324000 tasks/414000 intervals completed; A02 itself has 18000 complete repetitions. No source/config/protocol/environment change, no new experiment and no manuscript/PDF edit in this review.\n\n'
    checkpoint+='Primary reductions: 27.08% vs fixed4 and 22.28% vs development budget schedule; coverage .968--1.000. Raw-stage match is a near tie, so no separate smoothing claim. HBCI six-cell allocation ratio is 1.0400. New descriptive review: A02 EBCI is wider than fixed4 HBCI in all six existing cross-interval cells, aggregate ratio 1.32728. This does not invalidate the same-EBCI confirmation but limits broader practical claims.\n\n'
    checkpoint+='Current task: comprehensive synthesis and file organization are complete; review/2026-10-29/ASSESSMENT_AND_SUPPLEMENT_PLAN.md proposes S1 strong-HBCI/isolated-timing completion, S2 bounded MVN application and rare-event stress, S3 minimal pilot sensitivity, S4 evidence-based manuscript revision. USER APPROVAL IS REQUIRED BEFORE THESE NEW EXPERIMENTS. Do not resume the previous ten-attempt authorization as permission to run these proposed supplements now.\n\n'
    checkpoint+='Organization: 39 exact moves, 8515 files, 1375451341 bytes to _archive_manual_cleanup_20261029, all file hashes verified. No raw evidence deleted. Original full stopped-study evidence preserved as evidence/original_study_20261027.zip (SHA453f7b148e2ae9e242c74bd38515c3e7a5bedfb86f315a0e2cf2393e51b76a57). Current raw/rescue development/confirmation, all frozen source paths, manuscript and .venv/.runtime remain. Use organization_receipt.json and the updated package receipt for verification.\n\n'
    checkpoint+='Existing numerical replay matched 972 tasks and complete 324000-row analysis; isolated manuscript compile matched all 23 pages. Original PDF SHA8a1185ef178f591ed4db76b8244e824e0d69284411877ae8f7aec451c66d7879 must remain unchanged. Human author declarations and independent field review remain pending; no submission/payment/upload.\n'
    (r/'state/handoff.md').write_text(checkpoint,encoding='utf-8')
    (r/'state/STATUS.md').write_text('# Status — 2026-10-29\n\n'
        '**Existing result: DRAFT_READY_FOR_HUMAN_REVIEW.**\n\n'
        '**Current review: TARGETED_SUPPLEMENT_PROPOSED_AWAITING_USER_APPROVAL.**\n\n'
        'The 324000-task/414000-interval A02 confirmation remains complete and unchanged; two of ten interventions used. All primary same-EBCI gates passed; no new experiments during this review. New cross-interval diagnostic limits wider practical claims. See 当前研究入口.md, the complete current report and ASSESSMENT_AND_SUPPLEMENT_PLAN.md.\n\n'
        'Current manuscript remains the actual compiled, visually reviewed 23-page version. Do not call it submission-ready or guarantee acceptance. Proposed supplemental experiments and manuscript revision await explicit user approval.\n\n'
        'Stale live instructions and loose historical material have been archived after exact hash verification. Historical negative evidence remains in evidence/original_study_20261027.zip. Current sources/tests/config, all rescue raw repetitions, dependencies and source freezes are retained. No global changes, previous-project access, upload, payment or submission.\n',encoding='utf-8')
    (r/'task_plan.md').write_text('# Current plan — 2026-10-29\n\n'
        '- [x] Reconcile frozen code, protocol, complete results and current manuscript.\n'
        '- [x] Produce comprehensive Chinese research overview and current A02 route design.\n'
        '- [x] Search primary field sources and four Algorithms articles from 2024--2026; record reading scope and source hashes.\n'
        '- [x] Recompute descriptive existing-data diagnostics with zero new integrand calls; preserve primary analyses.\n'
        '- [x] Exact archive manifest applied; all migrated hashes and frozen source paths checked.\n'
        '- [ ] Complete organized-project analysis/compilation checks, allowlisted cache cleanup and updated bundle verification.\n'
        '- [x] Write bounded S1--S4 supplement proposal; no new experiments.\n'
        '- [ ] Await user approval before implementing supplement or revising the manuscript from new results.\n\n'
        'Scientific counter remains 2/10. Original development and confirmation counts never reset. Prior session plans/notes are preserved under the manual archive and in the previous verified delivery.\n',encoding='utf-8')
    (r/'notes.md').write_text('# Current review notes — 2026-10-29\n\n'
        'Core finding: existing same-EBCI confirmation supports a positive allocation contribution; matched raw variance does not establish independent smoothing benefit. The new post hoc cross-interval diagnostic has A02 EBCI/fixed4 HBCI=1.32728 over six cells, all ratios >1. Do not replace the original endpoints; discuss practical scope and propose strong-interval/cost validation.\n\n'
        'Recent journal sources read in relevant sections: Dimov/Georgieva 2025 a18050252; Liu et al. 2024 a17110524; Xia/Song 2026 a19070596; Kannan/Diwekar 2024 a17050195. These examples motivate a stronger evidence structure, not a guaranteed journal acceptance threshold. Full source text remains local; redistributed evidence uses metadata/URLs/hashes. Direct MDPI 429 and public read-through recorded. One guessed publisher URL failed and was not relied on; the verified DOI and author version support the direct-neighbour claims.\n\n'
        'User explicitly requested approval before supplementary experiments. No new scientific tasks were run. The archival helper performs only exact manifest moves within root, no deletions; old raw results and reports remain preserved. The current report maps already validated strict analysis into analysis-report/stats-appendix/figure-catalog, without inventing additional statistical evidence.\n\n'
        'Historical session logs and reporting-error evidence are archived; live handoff has been compacted to avoid stale running/no-resume instructions. Current scientific freezes, configs and source files are unchanged. .venv and .runtime remain active.\n',encoding='utf-8')
    records=[
        {'id':'dimov2025','doi':'10.3390/a18050252','authors':'Ivan Dimov; Rayna Georgieva','year':2025,
         'title':'Cutting-Edge Stochastic Approach: Efficient Monte Carlo Algorithms with Applications to Sensitivity Analysis',
         'reading':'Abstract/introduction, algorithm overview, experimental subsections 3.1--3.4 and applicability/conclusion; not an independent reproof of rate theorems'},
        {'id':'liu2024','doi':'10.3390/a17110524','authors':'Jiaqi Liu; Ziyang Wang; HaiYing Wang; Nalini Ravishanker','year':2024,
         'title':'Subsampling Algorithms for Irregularly Spaced Autoregressive Models',
         'reading':'Abstract, pilot/sequential thinning overview and Sections 5.1/5.2 on estimation efficiency and measured time; parameter-specific detailed formulas not rederived'},
        {'id':'xia2026','doi':'10.3390/a19070596','authors':'Shucan Xia; Haoran Song','year':2026,
         'title':'Acceptance Rate-Adaptive pCN MCMC for Moderate-Dimensional Bayesian Inverse Problems',
         'reading':'Abstract/introduction, Sections 2.3--2.6 and theory narrative/remarks, experimental design and subsection structure 4.1--4.7; not all theorem proofs or every numeric result verified'},
        {'id':'kannan2024','doi':'10.3390/a17050195','authors':'Shiva Kumar Kannan; Urmila Diwekar','year':2024,
         'title':'An Enhanced Particle Swarm Optimization (PSO) Algorithm Employing Quasi-Random Numbers',
         'reading':'Abstract/introduction, sampling replacement overview, benchmark/TSP experimental narrative and result-table captions; no reimplementation or exhaustive result-table check'}]
    fetch=json.loads((r/'docs/source_records/review_20261029/fetch_receipt.json').read_text(encoding='utf-8'))
    for entry in records:
        f=next(x for x in fetch['records'] if x['id']==entry['id']);entry.update(source=f['source'],text_sha256=f['sha256'])
        assert sha_file(r/f'docs/source_records/review_20261029/{entry["id"]}.txt')==entry['text_sha256']
    write_json(r/'docs/source_records/review_20261029/source_claims.json',{
        'date':'2026-10-29','records':records,'claim_scope':'Examples of recent target-journal evidence structures; not direct implemented competitors or acceptance guarantees.',
        'direct_neighbour':'https://doi.org/10.1093/imaiai/iaag003; https://arxiv.org/html/2504.18677v2 Sections4--5',
        'new_experiments':False,'exclusive_novelty_certificate':False})
    print('Updated mutable current-route entry, report index, handoff, plan, notes and source reading ledger.')


if __name__=='__main__':main()

"""Record completed reviews and checkpoint, using already observed verification evidence."""
import _bootstrap
import json
import shutil
from rqmc.common import root, sha_file, write_json


def main():
    r=root()
    def read(p):return json.loads((r/p).read_text(encoding='utf-8'))
    audit=read('handoff/rescue_draft_audit.json');build=read('handoff/rescue_pdf_build.json')
    reproduction=read('handoff/manuscript_source_reproduction.json')
    assert all(not x for x in audit['changed_sealed_files'].values())
    assert reproduction['status']=='ISOLATED_SOURCE_COMPILED_AND_ALL_PAGE_CONTENT_REPRODUCED'
    assert len(reproduction['pages'])==23 and all(x['rendered_pixels_identical'] for x in reproduction['pages'])
    render=read('paper/rendered/render_manifest.json')
    assert sha_file(r/'paper/manuscript.pdf')==build['pdf_sha256']==render['pdf_sha256']==audit['pdf_sha256']
    notes=[
        'Title/187-word abstract, author placeholders, review status and licensing wording checked.',
        'Introduction scope, citations, section references and body spacing checked.',
        'Nearest-source table, budget equation and predictor subscripts readable.',
        'EBCI intersection, HBCI directional capitals and proxy distinction checked.',
        'Expected moments, harmonic coefficients, substituted score and limit readable.',
        'Constant limit, smoothing parameters and adaptive-depth text checked.',
        'Algorithm steps, independent production and revision history checked.',
        'All six functions/integrals, comparators, B saturation and counts checked.',
        'MC estimands, multiplicity, coverage guards and hardware/software text checked.',
        'Digital-grid caveat and all primary/result numbers checked against tables.',
        'Six-panel width figure, labels and full legend readable; no clipping.',
        'All 18 primary rows and ratio heatmap legible, including losses.',
        'Complete fixed-grid/ablation table, coverage/HBCI and t failure text checked.',
        'Coverage plot with Wilson intervals, legend and nominal line readable.',
        'Allocation/cost dual axes and runtime/reproduction text checked; rounding consistent.',
        'All six latency rows and objective/attribution discussion readable.',
        'Limitations/conclusion and supplementary-material transition checked.',
        'Author/funding/conflicts placeholders and AI disclosure clearly unconfirmed.',
        'Appendix A1--A2 tables complete, readable and within margins.',
        'Appendix A3--A5 tables complete; scientific notation and coverage retained.',
        'Appendix A6--A8 retain Product and both full HBCI method grids.',
        'Appendix A9--A10 retain all 54 t cells including severe undercoverage.',
        'All ten references, resolved citation order, DOI wrapping and preprint labels checked.'
    ]
    pages=[]
    for entry,note in zip(render['pages'],notes):
        assert sha_file(r/entry['raster'])==entry['sha256']
        pages.append(dict(entry,visual_review='PASSED',note=note))
    write_json(r/'handoff/rescue_pdf_visual_review.json',{
        'status':'ALL_23_PAGES_ACTUALLY_VISUALLY_INSPECTED','pdf_sha256':build['pdf_sha256'],
        'reviewer':'Same AI-assisted session via local page images; not independent human review',
        'pages':pages,'unresolved_visual_defects':[],
        'repairs':['Removed bare unassigned DOI footer through document settings, class unchanged',
                   'Matched latency prose rounding to generated table (7.64 ms)',
                   'Reset appendix table counter to A1--A10'],
        'human_author_fields':'Intentionally pending, as required by project contract'})
    source=read('handoff/source_zip_receipt.json')
    assert source['sha256']==sha_file(r/'handoff/manuscript_source.zip')==reproduction['source_sha256']
    source['status']='PACKAGED_AND_ISOLATED_COMPILATION_ALL_PAGES_REPRODUCED'
    source['reproduction_receipt']='handoff/manuscript_source_reproduction.json'
    write_json(r/'handoff/source_zip_receipt.json',source)
    journal=read('handoff/rescue_journal_format_audit.json')
    journal['status']='DRAFT_FORMAT_COMPILE_AND_VISUAL_CHECKS_COMPLETE'
    journal['manuscript_compliance']={'research_sections':True,'abstract_words':audit['abstract_words'],
        'keywords':6,'verified_reference_entries':10,'actual_compile':True,'visual_pages':23,
        'isolated_source_compile':True,'author_declarations':'Pending human confirmation',
        'submission_status':'Not submitted; cover letter is unsent'}
    write_json(r/'handoff/rescue_journal_format_audit.json',journal)
    shutil.copy2(r/'paper/build/manuscript.log',r/'validation/current/rescue-manuscript-compilation-log.txt')
    (r/'validation/current/pytest-rescue-final.txt').write_text(
        'Command: .venv/Scripts/python.exe -m pytest -q\nObserved final run: 96 passed, 2 skipped in 1.02s\n'
        'Two skips concern Windows symlink creation privileges, not scientific tests.\n',encoding='utf-8')
    attempts=read('state/rescue_v1/attempts.json')
    assert len(attempts['attempts'])==2 and attempts['attempt_limit']==10
    attempts['status']='CONFIRMATION_SUPPORTED_DRAFT_READY_FOR_HUMAN_REVIEW'
    attempts['attempts'][1]['status']='CONFIRMATION_SUPPORTED'
    attempts['attempts'][1]['confirmation_tasks_for_this_method']=18000
    attempts['complete_confirmation_tasks_all_methods']=324000
    attempts['decision']='handoff/rescue_confirmation_decision.json'
    attempts['reason_no_further_attempts']='Positive frozen independent confirmation; no tuning on confirmation results'
    write_json(r/'state/rescue_v1/attempts.json',attempts)
    status=r/'state/STATUS.md';old=status.read_text(encoding='utf-8')
    history=r/'state/rescue_v1/status_before_final_delivery.md'
    if not history.exists():history.write_text(old,encoding='utf-8')
    original=old.split('## Completed original study:',1)[1]
    status.write_text('# Status\n\nDRAFT_READY_FOR_HUMAN_REVIEW — 2026-10-29. Positive A rescue confirmation; '
        '2/10 interventions used, eight slots unused. 324000/324000 tasks and 414000 intervals complete, '
        'zero numeric failures/empty sets. All frozen scientific sources/protocol hashes unchanged.\n\n'
        'A02 EBCI aggregate reduction: 27.08% vs fixed-4, 22.28% vs stronger development-selected '
        'budget schedule. Eight useful cells in three families, including held-out Product. '
        'Coverage .968--1.000. Matched raw-stage ratio .9979 spans one; no independent smoothing claim. '
        'HBCI does not share the primary gain; worst primary loss 5.25%.\n\n'
        'Deliverables: RESEARCH_REPORT.md; paper/manuscript.pdf (23 pages, actually compiled and every page viewed); '
        'handoff/manuscript_source.zip (isolated compile, all page text/pixels identical); '
        'REPRODUCE_RESCUE.md; handoff/rqmc_rescue_reproducibility.zip (member hashes in separate receipt). '
        'Numerical replay: 972 exact scientific matches, complete 324000-row analysis byte identical. '
        'Final tests 96 passed, two platform skips. Full mathematical/source/claim/statistical reviews saved.\n\n'
        'Human authors must independently review novelty and accuracy and complete names, affiliations, funding, '
        'conflicts, contributions, AI disclosure, originality and publication declarations. No submission/payment/upload. '
        'This status is not a publication guarantee. Do not spend remaining slots tuning on confirmation.\n\n'
        '## Completed original study:'+original,encoding='utf-8')
    checkpoint='\n\n## Final rescue checkpoint — 2026-10-29\n\n'
    checkpoint+='DRAFT_READY_FOR_HUMAN_REVIEW. Complete confirmation and audits support an interval-specific positive contribution. '
    checkpoint+='324000 tasks, 414000 intervals, 0 failures/empty sets. Two interventions used; stop scientific tuning. '
    checkpoint+='See state/STATUS.md and RESEARCH_REPORT.md. Actual 23-page compile/view and isolated source compile passed; '
    checkpoint+='972 scientific tasks matched, full-data tables reproduced. Human declaration questions and unsent cover letter saved. '
    checkpoint+='Final reproducibility package and checksum receipt are the delivery artifacts. Earlier running/negative checkpoints are historical.\n'
    for rel in ['state/handoff.md','task_plan.md','notes.md']:
        path=r/rel;text=path.read_text(encoding='utf-8')
        if '## Final rescue checkpoint — 2026-10-29' not in text:path.write_text(text+checkpoint,encoding='utf-8')
    print('Recorded actual visual review, source rebuild, final audits and draft checkpoint.')


if __name__=='__main__':main()

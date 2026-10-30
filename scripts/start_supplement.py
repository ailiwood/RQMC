"""Record explicit user authorization and retain the previously reviewed paper."""
import _bootstrap
import json
import zipfile
from datetime import datetime, timezone
from rqmc.common import root, sha_file, write_json

r = root()
target = r/'state/supplement_v2'
target.mkdir(parents=True, exist_ok=True)
archive = target/'previous_reviewed_manuscript.zip'
if not archive.exists():
    paths = [p for p in (r/'paper').rglob('*') if p.is_file()
             and not any(x in ('build', 'rendered') for x in p.relative_to(r/'paper').parts)]
    paths += [r/'handoff'/n for n in ('rescue_pdf_build.json', 'rescue_pdf_visual_review.json',
              'rescue_package_receipt.json', 'rescue_reproducibility_receipt.json') if (r/'handoff'/n).exists()]
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(r).as_posix())
    write_json(target/'authorization.json', {
        'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'authorization':'User explicitly approved S1--S4 experiments and targeted manuscript revision on 2026-10-29.',
        'proposal':'review/2026-10-29/ASSESSMENT_AND_SUPPLEMENT_PLAN.md',
        'proposal_sha256':sha_file(r/'review/2026-10-29/ASSESSMENT_AND_SUPPLEMENT_PLAN.md'),
        'experimental_wall_cap_hours':24, 'rescue_interventions_used':2,
        'previous_manuscript_zip_sha256':sha_file(archive),
        'previous_pdf_sha256':sha_file(r/'paper/manuscript.pdf'),
        'authors':[{'name':'Guo Lina','corresponding':True},
                   {'name':'Sun Chengyu','corresponding':False}],
        'affiliation':'Shandong Huayu University of Technology, Dezhou, Shandong Province, China, 253034',
        'blank_backmatter':['Funding','Acknowledgments','Data and Code Availability'],
        'conflicts':'The authors declare no conflicts of interest.'})
print(json.dumps({'archive':str(archive),'sha256':sha_file(archive)}))

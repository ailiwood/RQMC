"""Combine previously checked references with the two actually read additions."""
import _bootstrap
import json
from rqmc.common import root,write_json,sha_file

r=root();old=json.loads((r/'docs/rescue_reference_claim_ledger.json').read_text(encoding='utf-8'))
items=old['items']+[
    {'key':'genz1992','doi':'10.1080/10618600.1992.10477010',
     'claim':'Established conditional transformation for multivariate normal probabilities; not our innovation',
     'read_level':'Publisher metadata and abstract; original full body unavailable; conditional derivation corroborated by Genz/Trinh2016 Section2/2.1',
     'source':'https://www.tandfonline.com/doi/abs/10.1080/10618600.1992.10477010',
     'local_evidence':'docs/SUPPLEMENT_V2_MATH_AUDIT.md; docs/source_records/supplement_v2/fetch_receipt.json'},
    {'key':'genztrinh2016','doi':'10.1007/978-3-319-33507-0_13',
     'claim':'Univariate conditioning background: Cholesky limits, truncated inverse-CDF draws and product weights; bivariate innovations not implemented',
     'read_level':'Publisher author/title/book/pp289--302/year2016 metadata verified; author preprint Section2/2.1 (pp2--3) actually read through browser; not a full14-page proof review',
     'source':'https://people.cs.kuleuven.be/~dirk.nuyens/mcqmc2014_proceedings_preprints/223.pdf',
     'local_evidence':'docs/SUPPLEMENT_V2_MATH_AUDIT.md; state/supplement_v2/kernel_validation.json'}]
assert len(items)==len({x['key'] for x in items})==12
write_json(r/'docs/supplement_reference_claim_ledger.json',{'status':'ALL_12_ENTRIES_VERIFIED_WITH_EXPLICIT_READING_LIMITS',
    'items':items,'original_ledger_sha256':sha_file(r/'docs/rescue_reference_claim_ledger.json'),
    'same_session_not_independent_human_verification':True})
print('Prepared twelve-entry source/claim ledger with explicit reading limits.')

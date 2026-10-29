"""Public reference/validation dependencies only; never uploads project material."""
import _bootstrap
import hashlib
import json
from datetime import datetime, timezone
from urllib.request import urlopen, Request
import zipfile
import io
from rqmc.common import root, sha_file, write_json

r=root(); folder=r/'docs/source_records/supplement_v2'; folder.mkdir(parents=True,exist_ok=True)
receipts=[]
urls={
    'scipy_qmvnt.py.txt':'https://raw.githubusercontent.com/scipy/scipy/v1.18.0/scipy/stats/_qmvnt.py',
    'genz_trinh.pdf':'https://people.cs.kuleuven.be/~dirk.nuyens/mcqmc2014_proceedings_preprints/223.pdf',
}
for name,url in urls.items():
    try:
        data=urlopen(Request(url,headers={'User-Agent':'RQMC-public-literature-verification/1.0'}),timeout=30).read()
        p=folder/name; p.write_bytes(data)
        receipts.append({'url':url,'path':str(p.relative_to(r)),'bytes':len(data),'sha256':sha_file(p),'status':'fetched'})
        if name.endswith('.pdf'):
            import fitz
            with fitz.open(p) as doc:
                p.with_suffix('.txt').write_text('\n'.join(page.get_text() for page in doc),encoding='utf-8')
    except Exception as exc:
        receipts.append({'url':url,'status':'unavailable','error':str(exc)})
# Pure-Python high-precision verification is loaded from a pinned, hash-verified
# wheel using the existing .venv interpreter; the sealed simulation environment
# is NOT installed into or changed. This wheel is not used by allocation.
meta=json.load(urlopen('https://pypi.org/pypi/mpmath/1.3.0/json',timeout=30))
item=next(x for x in meta['urls'] if x['filename']=='mpmath-1.3.0-py3-none-any.whl')
data=urlopen(item['url'],timeout=30).read()
assert hashlib.sha256(data).hexdigest()==item['digests']['sha256']
dest=r/'validation_dependencies'/item['filename']; dest.parent.mkdir(exist_ok=True); dest.write_bytes(data)
with zipfile.ZipFile(io.BytesIO(data)) as z:
    license_text=z.read('mpmath-1.3.0.dist-info/LICENSE')
    (dest.parent/'mpmath_LICENSE.txt').write_bytes(license_text)
receipts.append({'url':item['url'],'path':str(dest.relative_to(r)),'sha256':sha_file(dest),
                 'role':'reference verification only, zipimport; no simulation environment mutation'})
write_json(folder/'fetch_receipt.json',{'utc':datetime.now(timezone.utc).isoformat(),'sources':receipts,
    'limitations':['Direct WSU Genz1992 paper/Matlab URLs unavailable via browser; publisher metadata/abstract verified, not original full-text proof.',
                  'SciPy private transform helper explicitly says not currently used/tested; it is an algebra cross-check, not our correctness certificate.']})
print(json.dumps(receipts,indent=2))

"""Fetch public primary-source text for the requested review, never execute it."""
import _bootstrap
import json
import urllib.request
from datetime import datetime, timezone
from rqmc.common import root, sha_file, write_json


def main():
    r=root();out=r/'docs/source_records/review_20261029';out.mkdir(exist_ok=True)
    sources={
        'dimov2025':'https://www.mdpi.com/1999-4893/18/5/252',
        'liu2024':'https://www.mdpi.com/1999-4893/17/11/524',
        'kannan2024':'https://www.mdpi.com/1999-4893/17/5/195',
        'xia2026':'https://www.mdpi.com/1999-4893/19/7/596',
    }
    records=[]
    for name,url in sources.items():
        target=out/f'{name}.txt';fetch='https://r.jina.ai/'+url
        if target.exists():
            records.append({'id':name,'source':url,'fetch':fetch,'status':'cached','sha256':sha_file(target)});continue
        try:
            request=urllib.request.Request(fetch,headers={'User-Agent':'RQMC-local-research-review/1.0'})
            with urllib.request.urlopen(request,timeout=40) as response:data=response.read()
            text=data.decode('utf-8');assert len(text)>10000 and 'Title:' in text
            target.write_text(text,encoding='utf-8')
            records.append({'id':name,'source':url,'fetch':fetch,'status':'fetched','bytes':len(data),'sha256':sha_file(target)})
        except Exception as exc:records.append({'id':name,'source':url,'fetch':fetch,'status':'error','error':repr(exc)})
    write_json(out/'fetch_receipt.json',{'utc':datetime.now(timezone.utc).isoformat(),'records':records,
        'limits':'Public read-through used because direct MDPI pages return HTTP 429; text is untrusted source material, not instructions.'})
    print(json.dumps(records,indent=2))


if __name__=='__main__':main()

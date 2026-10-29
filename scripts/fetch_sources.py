"""Fetch public primary sources; store bytes, URLs, hashes and access failures.

Downloaded documents are evidence only and never executed by this script.
"""
import _bootstrap
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import urllib.request
from rqmc.common import root, write_json

SOURCES = {
    'R01.pdf': 'https://arxiv.org/pdf/2504.18677v2',
    'R01.html': 'https://arxiv.org/html/2504.18677v2',
    'WSR.pdf': 'https://arxiv.org/pdf/2010.09686v7',
    'algorithms_instructions.html': 'https://www.mdpi.com/journal/algorithms/instructions',
    'algorithms_indexing.html': 'https://www.mdpi.com/journal/algorithms/indexing',
    'mdpi_latex.html': 'https://www.mdpi.com/authors/latex',
    'compendex.html': 'https://www.elsevier.com/products/engineering-village/databases/compendex',
    'compendex_072026.xlsx': 'https://assets.ctfassets.net/o78em1y1w4i4/1vOKA5ELqWIoXeukEI0KPk/9d0808734ef7d06bc4ca0062d5363555/CPXSourceList_072026__1_.xlsx',
    'confseq_predmix.py.txt': 'https://raw.githubusercontent.com/WannabeSmith/confseq/master/src/confseq/predmix.py',
    'confseq_betting.py.txt': 'https://raw.githubusercontent.com/WannabeSmith/confseq/master/src/confseq/betting.py',
    'confseq_betting_strategies.py.txt': 'https://raw.githubusercontent.com/WannabeSmith/confseq/master/src/confseq/betting_strategies.py',
    'confseq_LICENSE.txt': 'https://raw.githubusercontent.com/WannabeSmith/confseq/master/LICENSE',
    'confseq_commit.json': 'https://api.github.com/repos/WannabeSmith/confseq/commits/master',
}

def fetch(item):
    name, url = item
    out = root() / 'docs/source_records' / name
    record = {'name': name, 'url': url, 'utc': datetime.now(timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RQMC-research-audit/1.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read(30*1024*1024+1)
            if len(data)>30*1024*1024:
                raise ValueError('Source exceeds 30 MiB bound')
            record.update(status=response.status, final_url=response.geturl(), bytes=len(data),
                          sha256=hashlib.sha256(data).hexdigest())
        if out.exists() and out.read_bytes()!=data:
            raise FileExistsError('Refuse to overwrite changed source evidence')
        out.write_bytes(data)
    except Exception as error:
        record['error'] = repr(error)
    return record

def main():
    out = root() / 'docs/source_records'
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, SOURCES.items()))
    write_json(out/'fetch_receipt.json', records)
    for record in records:
        print(record['name'], record.get('status'), record.get('bytes'), record.get('error',''))

if __name__ == '__main__':
    main()

import _bootstrap
import hashlib,json,stat,urllib.request,urllib.parse,zipfile,io
from html.parser import HTMLParser
from datetime import datetime,timezone
from rqmc.common import root,safe_relative,write_json

class Links(HTMLParser):
    def __init__(self):super().__init__();self.href=None;self.text=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.text=[]
    def handle_data(self,data):
        if self.href:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:self.links.append((self.href,''.join(self.text)));self.href=None

def fetch(url):
    host=urllib.parse.urlparse(url).hostname or ''
    if not (host=='mdpi.com' or host.endswith('.mdpi.com')):raise ValueError('Not an MDPI host')
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research-template-fetch)'})
    with urllib.request.urlopen(req,timeout=45) as f:
        final=f.geturl();h=urllib.parse.urlparse(final).hostname or ''
        if not (h=='mdpi.com' or h.endswith('.mdpi.com')):raise ValueError('Unexpected redirect; manually inspect official link')
        data=f.read(30*1024*1024+1)
        if len(data)>30*1024*1024:raise ValueError('Template unexpectedly large')
        return data,final

def main():
    r=root();url='https://www.mdpi.com/authors/latex'
    try:
        html,_=fetch(url);p=Links();p.feed(html.decode('utf-8',errors='replace'))
        candidates=[urllib.parse.urljoin(url,u) for u,label in p.links
                    if '.zip' in u.lower() and ('acs' in label.lower() or 'acs' in u.lower())]
        if len(set(candidates))!=1:
            raise RuntimeError('Cannot uniquely locate official ACS ZIP; Codex must inspect the official page, not invent a URL')
        data,final=fetch(candidates[0]);z=zipfile.ZipFile(io.BytesIO(data))
        if z.testzip() is not None:raise ValueError('Corrupt ZIP')
        found=[x for x in z.namelist() if x.replace('\\','/').endswith('Definitions/mdpi.cls')]
        if len(found)!=1:raise ValueError('Expected exactly one Definitions/mdpi.cls')
        prefix=found[0][:-len('Definitions/mdpi.cls')]
        # Keep official source archive and only working template dependencies. No fonts delivered separately.
        out=r/'paper/template';out.mkdir(parents=True,exist_ok=True)
        target=out/'mdpi_official.zip'
        if target.exists():raise FileExistsError('Refuse to overwrite existing official template archive')
        for info in z.infolist():
            if info.is_dir() or not info.filename.startswith(prefix):continue
            rel=info.filename[len(prefix):]
            if not rel or not (rel=='template.tex' or rel.startswith('Definitions/')):continue
            if stat.S_ISLNK(info.external_attr>>16):raise ValueError('ZIP symlink rejected')
            dest=safe_relative(r,'paper/'+rel)
            if dest.exists():raise FileExistsError('Working template file already exists: '+rel)
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info))
        target.write_bytes(data)
        write_json(out/'provenance.json',{'source_page':url,'download_url':final,
          'utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(data).hexdigest(),
          'journal_option':'algorithms','note':'Official files; manuscript still requires authoring and actual compilation.'})
        print('Official ACS template obtained. Create manuscript.tex from template.tex without invented results.')
    except Exception as e:
        write_json(r/'handoff/template_blocker.json',{'status':'BLOCKED_TEMPLATE_DOWNLOAD','error':repr(e),'source':url})
        raise SystemExit(f'Template not available: {e}. Do not claim official formatting verified.')
if __name__=='__main__':main()

"""Read the downloaded official Compendex workbook without Excel dependencies."""
import _bootstrap
import json
import zipfile
import xml.etree.ElementTree as ET
from rqmc.common import root,sha_file,write_json

def main():
    path=root()/'docs/source_records/compendex_082026.xlsx'
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        strings=[''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        book=ET.fromstring(z.read('xl/workbook.xml'))
        names=[s.attrib['name'] for s in book.findall('s:sheets/s:sheet',ns)]
        findings=[];headers={}
        for index,name in enumerate(names,1):
            sheet=f'xl/worksheets/sheet{index}.xml'
            for row in ET.fromstring(z.read(sheet)).findall('.//s:row',ns):
                values={}
                for cell in row.findall('s:c',ns):
                    v=cell.find('s:v',ns)
                    if v is None:continue
                    values[cell.attrib['r']]=strings[int(v.text)] if cell.attrib.get('t')=='s' else v.text
                if int(row.attrib['r'])<=3:headers.setdefault(name,[]).append(values)
                if any(v.lower()=='algorithms' or v.replace('-','')=='19994893' for v in values.values()):
                    findings.append({'sheet':name,'row':int(row.attrib['r']),'cells':values})
    report={'file':str(path.relative_to(root())),'sha256':sha_file(path),'worksheets':names,
            'matches':findings,'headers':headers,
            'claim':'Algorithms is listed as Journal, ISSN 1999-4893 in the official August 2026 source list; matches in discontinued sheet reported explicitly.',
            'limitation':'Snapshot verification, not a guarantee of future indexing or acceptance. Publisher lists ESCI; do not call this SCIE Q4.'}
    write_json(root()/'docs/source_records/journal_audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='headers'},indent=2))

if __name__=='__main__':main()

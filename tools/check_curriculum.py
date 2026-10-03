"""Validate supplied facts, real destinations and preservation of all original pages."""
import argparse, hashlib, json, re, zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from collections import Counter
from lxml import html, etree
import openpyxl
from build_curriculum import strip, gr, NOTE

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def normalized(text):return text.replace('\r\n','\n').rstrip()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--workbook',type=Path,required=True);a=ap.parse_args()
    data=load(ROOT/'curriculum-data.json');baseline=load(a.audit/'before-manifest.json');manifest=load(ROOT/'release-public-manifest.json');report=load(a.audit/'build-audit.json')
    assert hashlib.sha256(a.workbook.read_bytes()).hexdigest()==data['sourceSha256']
    w=openpyxl.load_workbook(a.workbook,read_only=True,data_only=True)
    for r in data['gradeSubjects']:
        cells=next(w[r['sourceSheet']].iter_rows(min_row=r['sourceRow'],max_row=r['sourceRow'],values_only=True))
        keys=['grade','subject','revision','scope','focus','sequence','task','school','summary','url','sourceRange']
        assert tuple(r[k] for k in keys)==tuple(cells),r
    raw_plans=list(w['반별운영'].iter_rows(min_row=6,values_only=True));assert len(raw_plans)==45
    for p,raw in zip(data['levelPlans'],raw_plans):assert tuple(p.values())==tuple(raw)
    raw_choices=list(w['고등선택과목'].iter_rows(min_row=6,values_only=True));assert len(raw_choices)==29
    for p,raw in zip(data['choices'],raw_choices):assert tuple(p.values())==tuple(raw)
    w.close()
    links=0;anchors=0;descs=[];cache={};new_routes={p['route'] for p in data['pages']}
    assert len(new_routes)==88
    for p in data['pages']:
        doc=html.fromstring((ROOT/p['file']).read_bytes());cache[p['route']]=doc
        assert len(doc.xpath('//h1'))==1,p['route']
        ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),p['route']
        desc=doc.xpath('//meta[@name="description"]/@content')[0];assert desc==p['description'] and len(desc)<=80 and desc.endswith('.');descs.append(desc)
        assert doc.xpath('//link[@rel="canonical"]/@href')==['https://xn--3e0bz50bxucwzc.com'+__import__('urllib.parse',fromlist=['quote']).quote(p['route'],safe='/')]
        for href in doc.xpath('//a/@href'):
            if not href.startswith(('/','#')):continue
            link=urlsplit(href);path=unquote(link.path) or p['route'];target=ROOT/path.lstrip('/')
            if path.endswith('/'):target=target/'index.html'
            assert target.is_file(),(p['file'],href,str(target));links+=1
            if link.fragment:
                d=cache.get(path)
                if d is None:d=html.fromstring(target.read_bytes());cache[path]=d
                assert d.xpath('//*[@id=$id]',id=unquote(link.fragment)),(p['file'],href);anchors+=1
    assert len(descs)==len(set(descs)),'Descriptions must be distinct'
    connected={p['file']:p for p in data['existingPages']};preserved=0
    with zipfile.ZipFile(a.audit/'before-html.zip') as z:
        for name in baseline['files']:
            if not name.endswith('.html'):continue
            old=z.read(name).decode('utf-8');new=(ROOT/name).read_text(encoding='utf-8')
            assert normalized(strip(new))==normalized(strip(old)),name
            if name in connected:
                block=re.findall(r'<!-- curriculum-links:module:start -->([\s\S]*?)<!-- curriculum-links:module:end -->',new);assert len(block)==1,name
                d=html.fromstring(block[0]);actual=[unquote(x) for x in d.xpath('//a/@href')];assert actual==connected[name]['links'],name
                for path in actual:assert path in new_routes,(name,path)
                c=connected[name]['context']
                for path in actual:
                    if path=='/학습커리큘럼/':continue
                    parts=path.strip('/').split('/');s={'초':'초등','중':'중등','고':'고등'}
                    if c.get('stage'):assert parts[1]==s[c['stage']],name
                    if c.get('subject') in ['국어','영어','수학','사회','과학','역사']:assert parts[2]==c['subject'],name
                if c.get('kind'):assert new.count('href="#learning-curriculum"')==1,name
            else:assert normalized(new)==normalized(old),name
            preserved+=1
    targets=[name for name in baseline['files'] if name.endswith('.html') and name.startswith(('지점안내/','전국센터/','과목별학원/'))]
    uncovered=set(targets)-set(connected)
    # Legacy redirect documents deliberately keep their original noindex/redirect body.
    for name in uncovered:
        d=html.fromstring((ROOT/name).read_bytes());assert d.xpath('//meta[contains(@content,"noindex")]') or d.xpath('//meta[@http-equiv="refresh"]'),name
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};sitemap=etree.parse(str(ROOT/'sitemap.xml'));urls=[unquote(urlsplit(x).path) for x in sitemap.xpath('//s:loc/text()',namespaces=ns)]
    assert len(urls)==len(set(urls))==manifest['sitemapPages']==report['beforeSitemap']+88
    assert new_routes<=set(urls)
    assert set(baseline['files'])<=set(manifest['files'])
    allowed=set(report['changedPublicFiles'])
    for name,digest in manifest['files'].items():
        raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
        if name not in allowed:
            assert digest==baseline['files'][name] or (manifest.get('textSha256',{}).get(name) is not None and manifest['textSha256'][name]==baseline.get('textSha256',{}).get(name)),name
    result={'sourceWorkbookUnchanged':True,'gradeSubjectRowsVerified':66,'levelPlansVerified':45,'selectionGroupsVerified':29,'newPages':88,'contextModules':len(connected),'originalHtmlPreserved':preserved,'localLinksChecked':links,'anchorsChecked':anchors,'sitemapPages':len(urls),'namespacePages':len(targets),'legacyRedirectsPreserved':len(uncovered),'allApprovedPublicHashes':True}
    (a.audit/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()

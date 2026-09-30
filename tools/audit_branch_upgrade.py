"""Whole-release facts, internal links, source preservation and metadata audit."""
import argparse, collections, hashlib, json, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--3e0bz50bxucwzc.com'
def sha(b):return hashlib.sha256(b).hexdigest()
def plain(el):return ' '.join(el.text_content().split())
def walk(v):
    if isinstance(v,dict):
        yield v
        for child in v.values():yield from walk(child)
    elif isinstance(v,list):
        for child in v:yield from walk(child)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args()
    site=args.root;manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'));baseline=json.loads(args.baseline.read_text(encoding='utf-8'));data=json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'));files=set(manifest['files']);new=[p for p in files if p.endswith('.html') and p.startswith(('지점안내/','학습시스템/'))];fail=[];titles=[];descs=[];urls=[];links=0;faqcount=0;preserved=0
    branches={b['route'].lstrip('/')+'index.html':b for b in data['branches']}
    assert len(branches)==188 and sum(len(b['areas']) for b in data['branches'])==371
    ids={}
    def getids(name):
        if name not in ids:ids[name]=set(html.fromstring((site/name).read_bytes()).xpath('//@id'))
        return ids[name]
    for name in new:
        raw=(site/name).read_bytes();doc=html.fromstring(raw);text=doc.text_content();title=doc.xpath('//title/text()')[0];desc=doc.xpath('//meta[@name="description"]/@content')[0];canonical=doc.xpath('//link[@rel="canonical"]/@href')[0];titles.append(title);descs.append(desc);urls.append(canonical)
        if len(doc.xpath('//h1'))!=1:fail.append([name,'h1'])
        if len(desc)>80 or not desc.endswith('.'):fail.append([name,'description length'])
        if unquote(urlsplit(canonical).path)!='/'+name.removesuffix('index.html'):fail.append([name,'canonical'])
        for channel in ['og:description','twitter:description']:
            if doc.xpath('//meta[@name=$c or @property=$c]/@content',c=channel)!=[desc]:fail.append([name,'meta alignment'])
        nodes=[n for s in doc.xpath('//script[@type="application/ld+json"]/text()') for n in walk(json.loads(s))]
        faqs=[{'q':plain(d.xpath('./summary')[0]),'a':plain(d.xpath('./div')[0])} for d in doc.xpath('//details[@data-faq]')]
        schemas=[n for n in nodes if n.get('@type')=='FAQPage'];faqcount+=len(faqs)
        if len(schemas)!=bool(faqs):fail.append([name,'FAQ count'])
        elif faqs and [{'q':x['name'],'a':x['acceptedAnswer']['text']} for x in schemas[0]['mainEntity']]!=faqs:fail.append([name,'FAQ alignment'])
        if len(doc.xpath('//@id'))!=len(set(doc.xpath('//@id'))):fail.append([name,'duplicate ids'])
        for el in doc.xpath('//a[@href]|//link[@href]|//img[@src]|//script[@src]|//source[@srcset]'):
            refs=[el.get('href') or el.get('src')] if el.tag!='source' else [v.strip().split()[0] for v in el.get('srcset').split(',')]
            for ref in refs:
                full=urlsplit(urljoin(canonical,ref))
                if full.scheme not in ['http','https'] or full.netloc!=urlsplit(DOMAIN).netloc:continue
                target=unquote(full.path).lstrip('/');target=target+'index.html' if target.endswith('/') or not target else target
                links+=1
                if target not in files:fail.append([name,'missing release target',target]);continue
                if full.fragment and target.endswith('.html') and unquote(full.fragment) not in getids(target):fail.append([name,'missing anchor',target,full.fragment])
        if name in branches:
            b=branches[name]
            for c in b['courses']:
                block=doc.xpath('//*[@data-course=$s]',s=c['subject'])
                if len(block)!=1 or block[0].get('data-grades')!=','.join(c['grades']) or block[0].get('data-pending')!=','.join(c['pending']):fail.append([name,'course facts',c['subject']])
                for note in c['notes']:
                    if note not in plain(block[0]):fail.append([name,'missing condition',note])
            for note in b['courseNotes']:
                if note not in text:fail.append([name,'missing center condition',note])
            expected=[table for fee in b['fees'] if fee['kind']=='branch' or not any(f['kind']=='branch' for f in b['fees']) for table in fee['tables']]
            actual=[[[plain(cell) for cell in tr.xpath('./th|./td')] for tr in table.xpath('.//tr')] for table in doc.xpath('//table')]
            if expected!=actual:fail.append([name,'fee tables differ'])
            gallery=doc.xpath('//*[@id="photos"]//img/@src')
            if [unquote(x) for x in gallery]!=[p['small']['src'] for p in b['photos']]:fail.append([name,'gallery mapping'])
            if not doc.xpath('//a[@href=$u]',u=b['feeUrl']):fail.append([name,'fee link'])
            if 'Offers' in text or '★★★★★' in text:fail.append([name,'unverified claim'])
            if any(n.get('@type') in ['Offer','Review','AggregateRating'] for n in nodes):fail.append([name,'unverified schema'])
        if '학습시스템/와와학습코칭/' in name and len(doc.xpath('//*[@data-video-id]'))!=4:fail.append([name,'official videos missing'])
    for key,values in [('titles',titles),('descriptions',descs),('canonical URLs',urls)]:
        if len(values)!=len(set(values)):fail.append(['new pages','duplicate '+key])
    def baseline_check(item):
        name,expected=item;raw=(ROOT/name).read_bytes()
        if name.endswith('.html'):
            text=raw.decode('utf-8')
            text=re.sub(r'<a data-directory-nav\b[^>]*>.*?</a>','',text,flags=re.S)
            text=re.sub(r'<a data-branch-link\b[^>]*>.*?</a>','',text,flags=re.S)
            text=re.sub(r'<section class="bd-entry" data-branch-entry>.*?</section>','',text,flags=re.S)
            text=text.replace('<link rel="stylesheet" href="/assets/branch-directory.css">','')
            return name,sha(text.encode('utf-8'))==expected or sha(text.replace('\r\n','\n').encode('utf-8'))==baseline.get('textSha256',{}).get(name,expected)
        if re.search(r'\.(?:jpg|jpeg|webp|png|gif)$',name,re.I):return name,sha(raw)==expected
        return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(baseline_check,baseline['files'].items()):
            if result:
                name,ok=result
                if not ok:fail.append([name,'protected baseline content changed'])
                else:preserved+=1
    byarea={a['slug']:b['route'] for b in data['branches'] for a in b['areas']};connected=0
    def old_link_check(name):
        parts=name.split('/');slug=parts[2] if parts[0]=='과목별학원' and len(parts)==4 else parts[1] if parts[0]=='전국센터' and len(parts) in [3,4] else None
        if name.endswith('.html') and slug in byarea:
            doc=html.fromstring((site/name).read_bytes());refs=doc.xpath('//a[@data-branch-link]/@href')
            return name,len(refs)==1 and unquote(refs[0])==byarea[slug]
        return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(old_link_check,baseline['files']):
            if result:
                connected+=1
                if not result[1]:fail.append([result[0],'branch navigation wrong'])
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    sitemap=etree.parse(str(site/'sitemap.xml'));routes=[unquote(urlsplit(v).path).lstrip('/')+'index.html' for v in sitemap.xpath('//s:loc/text()',namespaces=ns)]
    if len(routes)!=len(set(routes)) or set(routes)!={f for f in files if f.endswith('.html')}:fail.append(['sitemap','HTML coverage mismatch'])
    for file,expected in data['sourceHashes'].items():
        if sha((args.source/file).read_bytes())!=expected:fail.append([file,'source changed'])
    forbidden=[n for n in files if n.startswith(('tools/','tmp/','.','branch-directory-data')) or re.search(r'\.(?:csv|xlsx|py|md|zip)$',n)]
    if forbidden:fail.append(['private source files in release',forbidden])
    report={'status':'PASS' if not fail else 'FAIL','newPages':len(new),'totalHtml':len(routes),'branchPages':len(branches),'regions':len({b['region'] for b in data['branches']}),'connectedRegionalPages':connected,'internalLinkChecks':links,'visibleFaqAnswers':faqcount,'preservedHtmlAndImages':preserved,'uniqueTitles':len(set(titles)),'uniqueDescriptions':len(set(descs)),'branchFeeTables':sum(any(f['kind']=='branch' for f in b['fees']) for b in data['branches']),'approvedPhotos':sum(len(b['photos']) for b in data['branches']),'branchesWithPhotos':sum(bool(b['photos']) for b in data['branches']),'errors':fail}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));assert not fail
if __name__=='__main__':main()

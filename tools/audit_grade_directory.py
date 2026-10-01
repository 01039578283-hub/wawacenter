"""Audit every new page, canonical alias and protected published source."""
import argparse,collections,hashlib,json,re,zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote,unquote,urljoin,urlsplit
from lxml import html,etree
from grade_editorial import TOPICS
ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--3e0bz50bxucwzc.com'
def plain(el):return ' '.join(el.text_content().split())
def walk(v):
    if isinstance(v,dict):
        yield v
        for child in v.values():yield from walk(child)
    elif isinstance(v,list):
        for child in v:yield from walk(child)
def normalized(raw):return raw.decode('utf-8').replace('\r\n','\n').strip()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);args=ap.parse_args()
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
    before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
    generated=json.loads((args.audit/'generated-pages.json').read_text(encoding='utf-8'))
    data=json.loads((ROOT/'grade-directory-data.json').read_text(encoding='utf-8'))
    branches={b['route']:b for b in json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'))['branches']}
    areas={a['slug']:a for a in json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'))['areas']}
    new=set(generated['newPages']);files=set(manifest['files']);pages={p['route'].lstrip('/')+'index.html':p for p in data['pages']};legacy=generated['legacyCanonical'];reverse={v:k for k,v in legacy.items()}
    assert len(new)==564 and len(pages)==564 and len(legacy)==1113
    removed=set(generated['removedPages']);destinations={**legacy,**generated['movedRoutes'],**{p['previousHub']:p['branch'] for p in data['areaPages']}}
    assert len(removed)==1484 and not removed & files
    assert all(not (ROOT/n).exists() and not (ROOT/'.public-release'/n).exists() for n in removed)
    assert sum(len(p['sources']) for p in data['pages'])==3339
    redirects=json.loads((ROOT/'vercel.json').read_text('utf-8'))['redirects']
    assert {unquote(r['source']).removesuffix('(/)?')+'/':unquote(r['destination']) for r in redirects}==generated['movedRoutes']
    assert all(r['statusCode']==301 for r in redirects)
    failures=[];titles=[];descs=[];linkcount=0;faqcount=0;hashes=collections.defaultdict(list);normalized_hashes=collections.defaultdict(list)
    id_cache={}
    def ids(name):
        if name not in id_cache:id_cache[name]=set(html.fromstring((ROOT/name).read_bytes()).xpath('//@id'))
        return id_cache[name]
    for name in sorted(new|{'과목별학원/'+label+'/index.html' for label in ['초등학생학원','중학생학원','고등학생학원']}):
        raw=(ROOT/name).read_bytes();doc=html.fromstring(raw);title=doc.xpath('//title/text()')[0];desc=doc.xpath('//meta[@name="description"]/@content')[0];canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
        if len(doc.xpath('//h1'))!=1:failures.append([name,'h1'])
        if len(desc)>80 or not desc.endswith('.'):failures.append([name,'description'])
        if name in new:titles.append(title);descs.append(desc)
        if unquote(urlsplit(canonical).path)!='/'+name.removesuffix('index.html'):failures.append([name,'canonical'])
        for channel in ['og:description','twitter:description']:
            if doc.xpath('//meta[@name=$c or @property=$c]/@content',c=channel)!=[desc]:failures.append([name,'meta alignment'])
        nodes=[n for text in doc.xpath('//script[@type="application/ld+json"]/text()') for n in walk(json.loads(text))]
        if [n for n in nodes if n.get('@type') in ['WebPage','CollectionPage']][0]['description']!=desc:failures.append([name,'schema description'])
        if any(n.get('@type') in ['Review','AggregateRating','Offer'] for n in nodes):failures.append([name,'unverified schema'])
        visible=[{'q':plain(d.xpath('./summary')[0]),'a':plain(d.xpath('./div')[0])} for d in doc.xpath('//details[@data-faq]')]
        schemas=[n for n in nodes if n.get('@type')=='FAQPage'];faqcount+=len(visible)
        if len(schemas)!=1 or [{'q':x['name'],'a':x['acceptedAnswer']['text']} for x in schemas[0]['mainEntity']]!=visible:failures.append([name,'FAQ mismatch'])
        if len(doc.xpath('//@id'))!=len(set(doc.xpath('//@id'))):failures.append([name,'duplicate id'])
        if name in pages:
            p=pages[name];b=branches[p['branch']]
            assert len(p['sources'])==3*len(p['areas']) and len({x['archive'] for x in p['sources']})==3
            for c in p['courses']:
                block=doc.xpath('//*[@data-stage-course=$s]',s=c['subject'])
                true=next(x for x in b['courses'] if x['subject']==c['subject'])
                assert c['grades']==[g for g in true['grades'] if g.startswith(p['prefix'])]
                assert c['pending']==[g for g in true['pending'] if g.startswith(p['prefix'])]
                if len(block)!=1 or block[0].get('data-grades')!=','.join(c['grades']) or block[0].get('data-pending')!=','.join(c['pending']):failures.append([name,'grade facts'])
                for note in c['notes']:
                    if note not in plain(block[0]):failures.append([name,'condition'])
            school=doc.xpath('//*[@data-stage-schools]')[0]
            expected=' · '.join(p['schools']) or '제공 자료에 이 학년의 학교명이 없습니다.'
            for a in p['areas']:
                assert a['schools']==areas[a['area']]['schools'][p['prefix']]
                block=doc.xpath('//*[@data-grade-area=$a]/dd',a=a['area'])
                if len(block)!=1 or plain(block[0])!=(' · '.join(a['schools']) or '제공 자료에 이 학년의 학교명이 없습니다.'):failures.append([name,'area reference'])
            if plain(school)!=expected:failures.append([name,'school stage'])
            image=doc.xpath('//img[contains(@src,"6839.webp")]')
            if len(image)!=1 or image[0].get('height')!='16116' or image[0].get('loading')!='eager':failures.append([name,'image'])
            if len(doc.xpath('//source[contains(@srcset,"6839-mobile.webp")]'))!=1:failures.append([name,'mobile image'])
            entries=[f for f in b['fees'] if f['kind']=='branch'] or b['fees']
            expected_tables=[rows for entry in entries for rows in entry['tables'] if rows]
            actual_tables=[[[plain(cell) for cell in row.xpath('./th|./td')] for row in table.xpath('.//tr')] for table in doc.xpath('//table')]
            if actual_tables!=expected_tables:failures.append([name,'tuition source cells'])
            if not any(f['kind']=='branch' for f in b['fees']) and '지점 확정 금액 아님' not in doc.text_content():failures.append([name,'common tuition'])
            body=plain(doc.xpath('//main')[0]);hashes[hashlib.sha256(body.encode()).hexdigest()].append(name)
            stripped=body.replace(p['name'],'').replace(p['area'],'')
            normalized_hashes[hashlib.sha256(stripped.encode()).hexdigest()].append(name)
            for phrase in ['학부모후기','이 원고','학원교재실','★★★★★','성적 보장']:
                if phrase in body:failures.append([name,'draft residue',phrase])
            if not any(c['grades'] for c in p['courses']) and '개설 학년을 제공 자료에서 확인하지 못했습니다' not in body:failures.append([name,'unconfirmed stage'])
    if len(titles)!=len(set(titles)):failures.append(['title duplicates'])
    if len(descs)!=len(set(descs)):failures.append(['description duplicates'])
    duplicates=[x for x in normalized_hashes.values() if len(x)>1]
    if duplicates:failures.append(['area-name-only detail copies',duplicates])
    sitemap=etree.parse(str(ROOT/'sitemap.xml'));routes=[unquote(urlsplit(n.text).path) for n in sitemap.findall('.//{*}loc')]
    if len(routes)!=len(set(routes)):failures.append(['sitemap duplicate'])
    if set(legacy)&set(routes):failures.append(['legacy alias in sitemap'])
    wanted_new={'/'+n.removesuffix('index.html') for n in new}
    if not wanted_new<=set(routes):failures.append(['new URL missing from sitemap'])
    if set(destinations)-set(legacy) & set(routes):failures.append(['obsolete URL in sitemap'])
    for old,new_route in legacy.items():
        doc=html.fromstring((ROOT/(old.lstrip('/')+'index.html')).read_bytes())
        if unquote(urlsplit(doc.xpath('//link[@rel="canonical"]/@href')[0]).path)!=new_route:failures.append([old,'legacy canonical'])
    def check_links(name):
        doc=html.fromstring((ROOT/name).read_bytes());base=DOMAIN+'/'+name.removesuffix('index.html');bad=[];count=0
        for el in doc.xpath('//a[@href]|//link[@href]|//img[@src]|//script[@src]|//source[@srcset]'):
            references=[el.get('href') or el.get('src')] if el.tag!='source' else [v.strip().split()[0] for v in el.get('srcset').split(',')]
            for ref in references:
                full=urlsplit(urljoin(base,ref))
                if full.scheme not in ['http','https'] or full.netloc!=urlsplit(DOMAIN).netloc:continue
                target=unquote(full.path).lstrip('/');target+='index.html' if target.endswith('/') or not target else '';count+=1
                if target not in files:bad.append([name,'missing file',target])
                elif full.fragment and target.endswith('.html'):
                    if unquote(full.fragment) not in ids(target):bad.append([name,'missing anchor',target,full.fragment])
        return count,bad
    with ThreadPoolExecutor(max_workers=8) as pool:
        for count,bad in pool.map(check_links,[n for n in files if n.endswith('.html')]):linkcount+=count;failures.extend(bad)
    protected=0;old_html=0;exempt={'과목별학원/'+label+'/index.html' for label in ['초등학생학원','중학생학원','고등학생학원']}
    with zipfile.ZipFile(args.audit/'before-source.zip') as archive:
        for name,digest in before['files'].items():
            if name in removed:continue
            if name.endswith('.html') and name not in exempt:
                original=normalized(archive.read(name));current=normalized((ROOT/name).read_bytes())
                original=re.sub(r'<!-- grade-entry:start -->.*?<!-- grade-entry:end -->','',original,flags=re.S)
                original=re.sub(r'<p class="gd-legacy-note".*?</p>','',original,flags=re.S)
                original=original.replace('<link rel="stylesheet" href="/assets/grade-directory.css">','')
                current=re.sub(r'<!-- grade-entry:start -->.*?<!-- grade-entry:end -->','',current,flags=re.S)
                current=re.sub(r'<p class="gd-legacy-note".*?</p>','',current,flags=re.S)
                current=current.replace('<link rel="stylesheet" href="/assets/grade-directory.css">','')
                old_route='/'+name.removesuffix('index.html')
                if old_route in legacy:
                    target=DOMAIN+quote(legacy[old_route],safe='/')
                    original=re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")[^"]+',lambda m:m[1]+target,original)
                def approved_link(m):
                    ref=urlsplit(m[2]);route=unquote(ref.path)
                    if ref.netloc and ref.netloc!=urlsplit(DOMAIN).netloc:return m[0]
                    if route not in destinations:return m[0]
                    target=quote(destinations[route],safe='/')
                    valid={'courses','fees','lesson-image','learning','schools','faq','next-stage'}
                    return m[1]+target+(('#'+ref.fragment) if ref.fragment in valid else '')+m[3]
                # Compare the original after only the approved destination migration;
                # fragments removed from old destinations cannot be reversed.
                original=re.sub(r'(\bhref=")([^"]+)(")',approved_link,original)
                if current!=original:failures.append([name,'protected old HTML differed'])
                else:old_html+=1
            elif re.search(r'\.(?:webp|jpg|jpeg|png|gif|svg)$',name):
                if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:failures.append([name,'protected image bytes'])
                else:protected+=1
    for name,expected in data['sourceHashes'].items():
        if hashlib.sha256((args.source/name).read_bytes()).hexdigest()!=expected:failures.append([name,'source changed'])
    report={'status':'FAIL' if failures else 'PASS','newPages':len(new),'gradePages':len(pages),'neighborhoodHubs':0,'removedPages':len(removed),'redirects':len(redirects),'totalHtml':sum(n.endswith('.html') for n in files),'canonicalSitemapPages':len(routes),'legacyRepresentatives':len(legacy),'uniqueTitles':len(set(titles)),'uniqueDescriptions':len(set(descs)),'faqAnswers':faqcount,'internalLinksChecked':linkcount,'preservedOldHtml':old_html,'preservedImageFiles':protected,'sourceDrafts':3339,'topicCombinations':len(set(tuple(p['topics']) for p in data['pages'])),'detailExactDuplicates':sum(len(x)>1 for x in hashes.values()),'detailNameOnlyDuplicates':len(duplicates),'errors':failures}
    (args.audit/'source-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v if k!='errors' else v[:15] for k,v in report.items()},ensure_ascii=False));assert not failures
if __name__=='__main__':main()

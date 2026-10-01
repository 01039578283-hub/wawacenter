"""Check the whole public tree and independently compare all reviewed workbook facts."""
import argparse,hashlib,json,re,zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote,quote
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
HOST='xn--3e0bz50bxucwzc.com';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
def text(el):return ' '.join(el.text_content().split())
def normal(value):return ' '.join(value.split())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--source',type=Path,default=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보\영어수학교재_120종_기초표준심화반_홈페이지용_20261001.xlsx'));args=ap.parse_args()
 data=json.loads((ROOT/'book-library-data.json').read_text(encoding='utf-8'))
 source=json.loads((args.audit/'source-data.json').read_text(encoding='utf-8'))
 generation=json.loads((args.audit/'generated-pages.json').read_text(encoding='utf-8'))
 manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 pages={p['route'].lstrip('/')+'index.html':p for p in data['pages']};books={b['id']:b for b in source['books']}
 allowed={'index.html','학습가이드/index.html','sitemap.xml','rss.xml','llms.txt'}
 protected={n:h for n,h in before['files'].items() if n not in allowed}
 selected=set(manifest['files']);errors=[];ids={};links=[];canonicals={};bodies=[];descriptions=[]
 if set(before['files'])-selected:errors.append(['old public files removed'])
 if selected-set(before['files'])!=set(generation['newFiles']):errors.append(['new inventory differs'])
 if len(pages)!=27 or len(source['books'])!=120 or len(source['classes'])!=18:errors.append(['page or workbook inventory'])
 if source['sha256']!=data['sourceSha256']:errors.append(['workbook SHA mismatch'])
 if hashlib.sha256(args.source.read_bytes()).hexdigest()!=source['sha256']:errors.append(['original workbook changed'])
 for b in data['books']:
  if b['id'] not in books:errors.append(['unknown book',b['id']]);continue
  for key,value in books[b['id']].items():
   if b.get(key)!=value:errors.append(['source fact changed',b['id'],key])
 if data['classes']!=source['classes']:errors.append(['class plan facts changed'])
 if len(set(b['id'] for b in data['books']))!=120:errors.append(['book IDs repeat'])
 def inspect(name):
  raw=(ROOT/name).read_bytes();digest=hashlib.sha256(raw).hexdigest();bad=[]
  if digest!=manifest['files'][name]:bad.append('manifest digest')
  if name in protected and digest!=protected[name]:bad.append('protected bytes changed')
  if not name.endswith('.html'):return name,bad,None
  doc=html.fromstring(raw);all_ids=doc.xpath('//@id');targets=doc.xpath('//@href|//@src')
  for srcset in doc.xpath('//@srcset'):targets.extend(part.strip().split()[0] for part in srcset.split(',') if part.strip())
  if len(all_ids)!=len(set(all_ids)):bad.append('duplicate IDs')
  canonical=doc.xpath('//link[@rel="canonical"]/@href');extra=None
  if name in pages:
   p=pages[name];description=doc.xpath('//meta[@name="description"]/@content')
   if len(doc.xpath('//h1'))!=1:bad.append('one H1 required')
   if canonical!=['https://'+HOST+quote(p['route'],safe='/')]:bad.append('self canonical')
   if description!=[p['description']] or len(p['description'])>80 or not p['description'].endswith('.'):bad.append('description length or sentence')
   for key in ['og:description','twitter:description']:
    if doc.xpath('//meta[@property="'+key+'" or @name="'+key+'"]/@content')!=description:bad.append('social description mismatch')
   graph=json.loads(doc.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
   webpage=next(n for n in graph if n['@id']==canonical[0]+'#webpage')
   if webpage['description']!=p['description']:bad.append('page schema description mismatch')
   visible=text(doc.xpath('//main')[0])
   if re.search(r'편집\s*(원칙|기준)|\b(?:SEO|AEO|GEO)\b|★★★★★|성적\s*보장|실제\s*사용\s*교재입니다',visible):bad.append('unsupported or internal public copy')
   if any(n['@type'] in ['Product','Offer','AggregateRating','Review'] for n in graph if isinstance(n['@type'],str)):bad.append('unverified product schema')
   faq=next(n for n in graph if n['@type']=='FAQPage')['mainEntity']
   actual=[(text(d.xpath('./summary')[0]),text(d.xpath('./div/p')[0])) for d in doc.xpath('//details[@data-faq]')]
   if actual!=[tuple(map(normal,pair)) for pair in p['faqs']] or actual!=[(normal(q['name']),normal(q['acceptedAnswer']['text'])) for q in faq]:bad.append('FAQ content differs')
   if p['article']:
    article=next(n for n in graph if 'Article' in (n['@type'] if isinstance(n['@type'],list) else [n['@type']]))
    if article['datePublished']!=data['updated'] or article['dateModified']!=data['updated']:bad.append('article dates mismatch')
   if p['bookIds']:
    listing=next(n for n in graph if n['@type']=='ItemList')
    expected=[('https://'+HOST+quote('/교재안내/'+books[id]['field']+'/#book-'+id.lower(),safe='/#')) for id in p['bookIds']]
    if listing['numberOfItems']!=len(p['bookIds']) or [i['url'] for i in listing['itemListElement']]!=expected:bad.append('book listing inventory differs')
   if p['route']=='/교재안내/':
    cards=doc.xpath('//*[@data-book-card]')
    if len(cards)!=120:bad.append('static catalog count')
    seen=[]
    for card in cards:
     id=card.get('data-book-id');seen.append(id);b=books[id];facts=json.loads(card.get('data-facts'))
     for key in ['name','publisher','area','student','condition']:
      if facts[key]!=b[key]:bad.append(id+' comparison fact differs: '+key)
     for key in ['field','level']:
      if card.get('data-'+key)!=b[key]:bad.append(id+' classification differs')
     levels=[] if b['additional']=='없음' else [s.strip() for s in b['additional'].split(',')]
     if card.get('data-additional')!=','.join(levels):bad.append(id+' additional classification differs')
    if len(set(seen))!=120:bad.append('static IDs repeated')
   elif len(p['bookIds'])==20:
    cards=doc.xpath('//article[contains(@class,"bk-book-detail")]')
    if [c.get('data-book-id') for c in cards]!=p['bookIds']:bad.append('full book order differs')
    for card in cards:
     b=books[card.get('data-book-id')];visible_card=text(card)
     for key in ['name','publisher','area','student','condition','introduction']:
      if normal(b[key]) not in visible_card:bad.append(b['id']+' source fact missing: '+key)
   elif p['bookIds']:
    plan=next(c for c in source['classes'] if c['field']==p['route'].split('/')[2] and data['levels'][c['level']]==p['route'].split('/')[3])
    expected=re.findall(r'\(([A-Z]{2}\d{2})\)',plan['primary']+' '+plan['supplement'])
    if doc.xpath('//*[@data-plan-book]/@data-plan-book')!=expected:bad.append('plan IDs differ from workbook')
    for key in ['student','goal','condition']:
     if normal(plan[key]) not in visible:bad.append('plan fact missing: '+key)
   else:
    kind=p['route'].split('/')[2];record_url='/assets/book-records/'+kind+'.txt';record=(ROOT/record_url.lstrip('/')).read_bytes()
    if doc.xpath('//a[@download]/@href')!=[quote(record_url,safe='/')]:bad.append('record download target')
    if not record.startswith(b'\xef\xbb\xbf') or b'\n' in record.replace(b'\r\n',b''):bad.append('record encoding/line ending')
   extra={'description':p['description'],'body':hashlib.sha256(visible.encode()).hexdigest()}
  return name,bad,{'ids':set(all_ids),'targets':targets,'canonical':canonical[0] if canonical else None,'extra':extra}
 with ThreadPoolExecutor(max_workers=8) as pool:
  for i,(name,bad,doc) in enumerate(pool.map(inspect,sorted(selected)),1):
   if bad:errors.append([name,bad])
   if doc:
    ids[name]=doc['ids'];links.extend((name,t) for t in doc['targets']);canonicals[name]=doc['canonical']
    if doc['extra']:descriptions.append(doc['extra']['description']);bodies.append(doc['extra']['body'])
   if i%1500==0:print(json.dumps({'checkedFiles':i,'errors':len(errors)}),flush=True)
 internal=0
 for source_name,target in links:
  u=urlsplit(urljoin('https://'+HOST+'/'+source_name,target))
  if u.scheme not in ['http','https'] or u.netloc not in [HOST,'전국수업.com']:continue
  internal+=1;part=unquote(u.path).lstrip('/');name=part+'index.html' if not part or part.endswith('/') else part
  if name not in selected:
   if not Path(name).suffix and name+'/index.html' in selected:name+='/index.html'
   else:errors.append([source_name,'missing target',target]);continue
  if u.fragment and name in ids and unquote(u.fragment) not in ids[name]:errors.append([source_name,'missing fragment',target])
 locs=etree.parse(str(ROOT/'sitemap.xml')).xpath('//s:loc/text()',namespaces=NS)
 if len(locs)!=len(set(locs)) or len(locs)!=5321:errors.append(['sitemap count or duplicates',len(locs)])
 for name in pages:
  if canonicals[name] not in locs:errors.append([name,'missing in sitemap'])
 with zipfile.ZipFile(args.audit/'before-source.zip') as archive:
  for name in data['entryPages']:
   stripped=re.sub(r'<!-- book-entry:start -->[\s\S]*?<!-- book-entry:end -->','',(ROOT/name).read_text(encoding='utf-8'))
   if name=='index.html':
    stripped=re.sub(r'<!-- home-library:([a-z]+):start -->[\s\S]*?<!-- home-library:\1:end -->','',stripped)
    stripped=stripped.replace('"dateModified":"2026-10-01"','"dateModified":"2026-09-28"')
    stripped=stripped.replace('\n        <div class="hero-points"','        <div class="hero-points"').replace('\n    <div class="metric-row"','    <div class="metric-row"')
   if stripped!=archive.read(name).decode('utf-8').replace('\r\n','\n'):errors.append([name,'unrelated content changed'])
  old_sitemap=etree.fromstring(archive.read('sitemap.xml'));old_locs=old_sitemap.xpath('//s:loc/text()',namespaces=NS)
  if set(locs)-set(old_locs)!={canonicals[n] for n in pages}:errors.append(['sitemap added canonical set differs'])
  by_loc={entry.find('s:loc',NS).text:entry for entry in etree.parse(str(ROOT/'sitemap.xml')).getroot()}
  changed={'https://'+HOST+'/','https://'+HOST+quote('/학습가이드/',safe='/')}
  for entry in old_sitemap:
   loc=entry.find('s:loc',NS).text
   if loc not in by_loc:errors.append([loc,'old canonical lost'])
   elif loc not in changed and etree.tostring(entry)!=etree.tostring(by_loc[loc]):errors.append([loc,'unrelated sitemap entry changed'])
  old_items=etree.fromstring(archive.read('rss.xml')).findall('channel/item');items=etree.parse(str(ROOT/'rss.xml')).findall('channel/item')
  if [etree.tostring(i) for i in old_items]!=[etree.tostring(i) for i in items[:len(old_items)]]:errors.append(['old RSS items changed'])
  if len(items)!=len(old_items)+27 or [i.findtext('link') for i in items[len(old_items):]]!=[canonicals[n] for n in pages]:errors.append(['RSS added inventory mismatch'])
 if len(set(descriptions))!=27 or len(set(bodies))!=27:errors.append(['duplicate descriptions or full bodies'])
 home=html.parse(str(ROOT/'index.html'));home_data=json.loads((ROOT/'home-library-data.json').read_text(encoding='utf-8'))
 topic_links=home.xpath('//*[@data-home-topic]/@href');reading_links=home.xpath('//*[@data-home-reading]/@href')
 expected=['https://'+HOST+quote(p['route'],safe='/') for p in home_data['listedPages']]
 nodes=[json.loads(s) for s in home.xpath('//script[@type="application/ld+json"]/text()')]
 listing=next(n for n in nodes if n.get('@id')=='https://'+HOST+'/#home-library-list')
 if len(topic_links)!=6 or len(reading_links)!=12 or [urljoin('https://'+HOST,u) for u in topic_links+reading_links]!=expected or [i['url'] for i in listing['itemListElement']]!=expected:errors.append(['home content links and schema differ'])
 if listing['numberOfItems']!=18:errors.append(['home listing inventory'])
 if any(n in selected for n in ['home-library-data.json','book-library-data.json']):errors.append(['authoring catalog public'])
 if any(n.endswith('.xlsx') or n.startswith('tools/') or n=='book-library-data.json' for n in selected):errors.append(['private sources public'])
 report={'status':'FAIL' if errors else 'PASS','publicFiles':len(selected),'htmlPages':len(ids),'newPages':27,'textbooks':120,'planGuides':18,'blankRecords':2,'protectedPublicFiles':len(protected),'sitemapPages':len(locs),'checkedInternalReferences':internal,'uniqueDescriptions':len(set(descriptions)),'uniqueBodies':len(set(bodies)),'errors':errors,'deployed':False}
 (args.audit/'book-library-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({**report,'errors':errors[:15]},ensure_ascii=False));assert not errors
if __name__=='__main__':main()

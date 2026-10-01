"""Whole-publication preservation and learning-library checks, without deployment."""
import argparse, hashlib, json, re, zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote, quote
from lxml import html, etree
ROOT=Path(__file__).resolve().parents[1]
HOST='xn--3e0bz50bxucwzc.com'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
def text(el):return ' '.join(el.text_content().split())

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 data=json.loads((ROOT/'learning-guide-data.json').read_text(encoding='utf-8'))
 manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 guide_pages={p['route'].lstrip('/')+'index.html':p for p in data['pages']};hub='학습가이드/index.html'
 allowed={hub,*guide_pages,'sitemap.xml','rss.xml','llms.txt'}
 protected={n:h for n,h in before['files'].items() if n not in allowed}
 selected=set(manifest['files']);errors=[];ids={};links=[];canonicals={};descriptions=[];bodies=[]
 if set(before['files'])-selected:errors.append(['public files removed',sorted(set(before['files'])-selected)])
 expected_new={p['record'].lstrip('/') for p in data['pages']}|{'assets/learning-guides.css','assets/learning-guides.js'}|set(guide_pages)-set(before['files'])
 if selected-set(before['files'])!=expected_new:errors.append(['new public inventory differs'])
 def inspect(name):
  raw=(ROOT/name).read_bytes();digest=hashlib.sha256(raw).hexdigest();bad=[]
  if digest!=manifest['files'][name]:bad.append('manifest digest')
  if name in protected and digest!=protected[name]:bad.append('protected public bytes')
  if not name.endswith('.html'):return name,bad,None
  doc=html.fromstring(raw);allids=doc.xpath('//@id')
  if len(allids)!=len(set(allids)):bad.append('duplicate IDs')
  targets=doc.xpath('//@href|//@src')
  for srcset in doc.xpath('//@srcset'):targets.extend(part.strip().split()[0] for part in srcset.split(',') if part.strip())
  canonical=doc.xpath('//link[@rel="canonical"]/@href');extra=None
  if name==hub or name in guide_pages:
   p=guide_pages.get(name,data['hub']);description=doc.xpath('//meta[@name="description"]/@content')
   if len(doc.xpath('//h1'))!=1:bad.append('one H1 required')
   if canonical!=['https://'+HOST+quote(p['route'],safe='/')]:bad.append('self canonical')
   if description!=[p['description']] or len(description[0])>80 or not description[0].endswith('.'):bad.append('description length/sentence')
   for field in ['og:description','twitter:description']:
    if doc.xpath('//meta[@property="'+field+'" or @name="'+field+'"]/@content')!=description:bad.append('social metadata mismatch')
   graph=json.loads(doc.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
   if graph[0]['description']!=p['description']:bad.append('page schema description mismatch')
   visible=text(doc.xpath('//main')[0])
   if re.search(r'편집\s*(원칙|기준)|\b(?:SEO|AEO|GEO)\b|★★★★★',visible):bad.append('policy or implementation copy in public text')
   if name in guide_pages:
    article=next(n for n in graph if 'Article' in ([n['@type']] if isinstance(n['@type'],str) else n['@type']))
    if article['datePublished']!=p['datePublished'] or article['dateModified']!=data['updated']:bad.append('article dates')
    expected_citations=[data['sources'][k][3] for k in p['sources']]
    if article['citation']!=expected_citations or not all(u in targets for u in expected_citations):bad.append('citations missing')
    faq=next(n for n in graph if n['@type']=='FAQPage')['mainEntity']
    actual=[(text(d.xpath('./summary')[0]),text(d.xpath('./div/p')[0])) for d in doc.xpath('//details[@data-faq]')]
    if actual!=[tuple(pair) for pair in p['faq']] or actual!=[(q['name'],q['acceptedAnswer']['text']) for q in faq]:bad.append('FAQ schema and visible content differ')
    if doc.xpath('//a[@download]/@href')!=[quote(p['record'],safe='/')]:bad.append('record download')
    if len(doc.xpath('//li[contains(@class,"lg-step")]'))!=len(p['steps']):bad.append('action steps inventory')
    record=(ROOT/p['record'].lstrip('/')).read_bytes()
    if not record.startswith(b'\xef\xbb\xbf') or b'\n' in record.replace(b'\r\n',b''):bad.append('record encoding/line endings')
    if not all(label+':' in record.decode('utf-8-sig') for label,_ in p['recordFields']):bad.append('record fields missing')
    if p['legacy'] and not {'section-1','section-2','section-3','section-4'}<=set(allids):bad.append('legacy anchors lost')
    extra={'description':p['description'],'body':hashlib.sha256(text(doc.xpath('//article[@data-learning-guide]')[0]).encode()).hexdigest()}
   else:
    cards=doc.xpath('//*[@data-guide-card]');listing=next(n for n in graph if n['@type']=='ItemList')
    if len(cards)!=40 or listing['numberOfItems']!=40:bad.append('static card count')
    listed=[unquote(urlsplit(n['url']).path) for n in listing['itemListElement']]
    if listed!=[p['route'] for p in data['pages']]:bad.append('collection ordering')
  return name,bad,{'ids':set(allids),'targets':targets,'canonical':canonical[0] if canonical else None,'extra':extra}
 with ThreadPoolExecutor(max_workers=8) as pool:
  for i,(name,bad,doc) in enumerate(pool.map(inspect,sorted(selected)),1):
   if bad:errors.append([name,bad])
   if doc:
    ids[name]=doc['ids'];links.extend((name,t) for t in doc['targets']);canonicals[name]=doc['canonical']
    if doc['extra']:descriptions.append(doc['extra']['description']);bodies.append(doc['extra']['body'])
   if i%1500==0:print(json.dumps({'checkedFiles':i,'errors':len(errors)}),flush=True)
 internal=0
 for source,target in links:
  u=urlsplit(urljoin('https://'+HOST+'/'+source,target))
  if u.scheme not in ['http','https'] or u.netloc not in [HOST,'전국수업.com']:continue
  internal+=1;path=unquote(u.path).lstrip('/');name=path+'index.html' if not path or path.endswith('/') else path
  if name not in selected:
   if not Path(name).suffix and name+'/index.html' in selected:name+='/index.html'
   else:errors.append([source,'missing target',target]);continue
  if u.fragment and name in ids and unquote(u.fragment) not in ids[name]:errors.append([source,'missing fragment',target])
 locs=etree.parse(str(ROOT/'sitemap.xml')).xpath('//s:loc/text()',namespaces=NS)
 if len(locs)!=len(set(locs)) or len(locs)!=5294:errors.append(['sitemap duplicates/count',len(locs)])
 for name in [hub,*guide_pages]:
  if canonicals[name] not in locs:errors.append([name,'absent from sitemap'])
 with zipfile.ZipFile(args.audit/'before-source.zip') as archive:
  old_sitemap=etree.fromstring(archive.read('sitemap.xml'));old_locs=old_sitemap.xpath('//s:loc/text()',namespaces=NS)
  if not set(old_locs)<=set(locs):errors.append(['existing canonical removed from sitemap'])
  current=etree.parse(str(ROOT/'sitemap.xml'));by_loc={entry.find('s:loc',NS).text:entry for entry in current.getroot()}
  guide_locs={canonicals[n] for n in [hub,*guide_pages]}
  for entry in old_sitemap:
   loc=entry.find('s:loc',NS).text
   if loc not in guide_locs and etree.tostring(entry)!=etree.tostring(by_loc[loc]):errors.append([loc,'unrelated sitemap entry changed'])
  oldrss=etree.fromstring(archive.read('rss.xml'));rss=etree.parse(str(ROOT/'rss.xml'))
  outside=lambda items:[etree.tostring(i) for i in items if not unquote(urlsplit(i.findtext('link')).path).startswith('/학습가이드/')]
  if outside(oldrss.findall('channel/item'))!=outside(rss.findall('channel/item')):errors.append(['unrelated RSS items changed'])
  rss_routes=[unquote(urlsplit(i.findtext('link')).path) for i in rss.findall('channel/item')]
  if len(rss_routes)!=len(set(rss_routes)) or sum(r.startswith('/학습가이드/') for r in rss_routes)!=41:errors.append(['RSS guide inventory'])
 if len(set(descriptions))!=40 or len(set(bodies))!=40:errors.append(['identical article body or description'])
 report={'status':'FAIL' if errors else 'PASS','publicFiles':len(selected),'htmlPages':len(ids),'guidePages':41,'guideArticles':40,'newArticles':32,'recordForms':40,'protectedPublicFiles':len(protected),'sitemapPages':len(locs),'checkedInternalReferences':internal,'uniqueDescriptions':len(set(descriptions)),'uniqueBodies':len(set(bodies)),'errors':errors,'deployed':False}
 (args.audit/'learning-guide-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({**report,'errors':errors[:12]},ensure_ascii=False));assert not errors

if __name__=='__main__':main()

"""Check the complete publication, all 1,897 directory pages and preserved bytes."""
import argparse,collections,hashlib,json,re,zipfile
from pathlib import Path
from urllib.parse import urlsplit,urljoin,unquote
from concurrent.futures import ThreadPoolExecutor
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
def text(el):return ' '.join(el.text_content().split())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 generated=json.loads((args.audit/'generated-pages.json').read_text(encoding='utf-8'))
 data=json.loads((ROOT/'subject-directory-data.json').read_text(encoding='utf-8'))
 branches={b['route']:b for b in json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'))['branches']}
 pages={p['route'].lstrip('/')+'index.html':p for p in data['pages']}
 updated=set(generated['updatedParents']);directory=updated|set(pages);selected=set(manifest['files']);errors=[]
 allowed=updated|{'sitemap.xml','llms.txt'}
 preserved={n:h for n,h in before['files'].items() if n not in allowed}
 ids={};links=[];canonicals={};descs=[];headings=[];bodies=[];image_counts=0
 def inspect(name):
  raw=(ROOT/name).read_bytes();bad=[]
  if hashlib.sha256(raw).hexdigest()!=manifest['files'][name]:bad.append('manifest digest')
  if name in preserved and hashlib.sha256(raw).hexdigest()!=preserved[name]:bad.append('protected public bytes')
  if not name.endswith('.html'):return name,bad,None
  doc=html.fromstring(raw);allids=doc.xpath('//@id')
  if len(allids)!=len(set(allids)):bad.append('duplicate IDs')
  targets=[(el.get('href') or el.get('src') or el.get('srcset').split()[0]) for el in doc.xpath('//*[@href or @src or @srcset]') if el.get('href') or el.get('src') or el.get('srcset')]
  canonical=doc.xpath('//link[@rel="canonical"]/@href');main=doc.xpath('//main');desc=doc.xpath('//meta[@name="description"]/@content')
  extra=None
  if name in directory:
   if len(doc.xpath('//h1'))!=1:bad.append('heading count')
   if len(desc)!=1 or len(desc[0])>80 or not desc[0].endswith('.'):bad.append('description length/sentence')
   if not canonical or unquote(urlsplit(canonical[0]).path)!='/'+name.removesuffix('index.html'):bad.append('self canonical')
   graphs=[json.loads(s) for s in doc.xpath('//script[@type="application/ld+json"]/text()')]
   graph=graphs[0]['@graph']
   if graph[0]['description']!=desc[0]:bad.append('schema description')
   for field in ['og:description','twitter:description']:
    if doc.xpath('//meta[@property="'+field+'" or @name="'+field+'"]/@content')!=desc:bad.append('meta alignment')
   visible=[{'q':text(el.xpath('./summary')[0]),'a':text(el.xpath('./div/p')[0])} for el in doc.xpath('//details[@data-faq]')]
   schema=next((n for n in graph if n['@type']=='FAQPage'),{'mainEntity':[]})
   if visible!=[{'q':q['name'],'a':q['acceptedAnswer']['text']} for q in schema['mainEntity']]:bad.append('FAQ differs')
   if name in pages:
    p=pages[name];b=branches[p['branch']]
    actual_tables=[[[' '.join(c.text_content().split()) for c in row.xpath('./th|./td')] for row in table.xpath('.//tr')] for table in doc.xpath('//table')]
    fees=[f for f in b['fees'] if f['kind']=='branch'] or b['fees']
    expected=[rows for f in fees for rows in f['tables'] if rows]
    if actual_tables!=expected:bad.append('tuition table cells changed')
    educational=doc.xpath('//section[@data-subject-topic]')
    if len(educational)!=len(p['topics']):bad.append('section inventory')
    if len(educational)<6:bad.append('insufficient meaningful sections')
    img=doc.xpath('//div[contains(@class,"bd-image-panel")]//img')
    if len(img)!=1 or img[0].get('height')!='16116':bad.append('full consultation image')
    bodytext=text(main[0])
    extra={'sections':len(educational),'bodySha256':hashlib.sha256(bodytext.encode()).hexdigest()}
  return name,bad,{'ids':set(allids),'targets':targets,'canonical':canonical[0] if canonical else None,'desc':desc[0] if desc else None,'extra':extra}
 with ThreadPoolExecutor(max_workers=8) as pool:
  for i,(name,bad,doc) in enumerate(pool.map(inspect,sorted(selected)),1):
   if bad:errors.append([name,bad])
   if doc:
    ids[name]=doc['ids'];links.extend((name,target) for target in doc['targets']);canonicals[name]=doc['canonical']
    if name in directory:descs.append(doc['desc'])
    if doc['extra']:headings.append(doc['extra']['sections']);bodies.append(doc['extra']['bodySha256'])
   if i%1500==0:print(json.dumps({'checkedFiles':i,'errors':len(errors)}),flush=True)
 # All publication targets, including old readable aliases and all fragments.
 for source,target in links:
  u=urlsplit(urljoin('https://xn--3e0bz50bxucwzc.com/'+source,target))
  if u.scheme not in ['http','https'] or u.netloc!='xn--3e0bz50bxucwzc.com':continue
  path=unquote(u.path).lstrip('/');name=path+'index.html' if not path or path.endswith('/') else path
  if name not in selected:
   if not Path(name).suffix and name+'/index.html' in selected:name+='/index.html'
   else:errors.append([source,'missing target',target]);continue
  if u.fragment and name in ids and unquote(u.fragment) not in ids[name]:errors.append([source,'missing fragment',target])
 ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};tree=etree.parse(str(ROOT/'sitemap.xml'));locs=tree.xpath('//s:loc/text()',namespaces=ns)
 if len(locs)!=len(set(locs)) or len(locs)!=5262:errors.append(['sitemap','duplicates/count',len(locs)])
 for name in directory:
  if canonicals[name] not in locs:errors.append([name,'absent from sitemap'])
 if len(set(descs))!=len(descs):errors.append(['directory','duplicate descriptions'])
 if len(set(bodies))!=len(bodies):errors.append(['new pages','identical body'])
 # Every pre-existing parent keeps its original content except the authorized
 # new entry, aligned descriptions and semantic separation of concern cards.
 def stripped(s):
  s=s.replace('\r\n','\n')
  s=re.sub(r'<!-- subject-entry:start -->.*?<!-- subject-entry:end -->','',s,flags=re.S)
  s=s.replace('<link rel="stylesheet" href="/assets/subject-directory.css">','').replace('sd-grade-topics','bd-grid gd-topic-grid')
  s=re.sub(r'<section class="bd-card sd-grade-topic" data-editorial-topic="([^"]+)" id="parent-learning-[^"]+">(.*?)</section>',lambda m:'<article class="bd-card" data-editorial-topic="'+m[1]+'">'+m[2]+'</article>',s,flags=re.S)
  s=re.sub(r'(<meta (?:name="description"|name="twitter:description"|property="og:description") content=")[^"]+("[^>]*>)',r'\1__DESCRIPTION__\2',s)
  def schema(m):
   graph=json.loads(m[1]);graph['@graph'][0]['description']='__DESCRIPTION__'
   return json.dumps(graph,ensure_ascii=False,sort_keys=True)
  return re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,s,flags=re.S)
 with zipfile.ZipFile(args.audit/'before-source.zip') as z:
  for name in updated:
   if stripped(z.read(name).decode('utf-8'))!=stripped((ROOT/name).read_text(encoding='utf-8')):errors.append([name,'original parent content changed'])
 sourcefolder=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보')
 info=json.loads((args.audit/'center-source-inspection.json').read_text(encoding='utf-8'))
 for name,f in info.items():
  if hashlib.sha256((sourcefolder/name).read_bytes()).hexdigest()!=f['sha256']:errors.append([name,'center input changed'])
 sources=[s for p in data['pages'] for s in p['sources']]
 if len(sources)!=4452 or len({(s['archive'],s['filename']) for s in sources})!=4452:errors.append(['sources','coverage'])
 drafts=json.loads((args.audit/'manuscript-records.json').read_text(encoding='utf-8'));hashes={(r['archive'],r['filename']):r['sha256'] for r in drafts}
 for s in sources:
  if hashes[s['archive'],s['filename']]!=s['sha256']:errors.append([s['filename'],'source hash mismatch'])
 txt=Path(r'C:\Users\1992k\Desktop\전국수업.com_초중고_영어수학_신규URL_허브순_20261001.txt').read_bytes()
 expected=['https://전국수업.com'+p['route'] for p in sorted(data['pages'],key=lambda p:(len(p['route'].strip('/').split('/')),p['route']))]
 if not txt.startswith(b'\xef\xbb\xbf') or txt.decode('utf-8-sig').splitlines()!=expected or txt.count(b'\r\n')!=1128:errors.append(['URL export','BOM/CRLF/coverage'])
 report={'status':'FAIL' if errors else 'PASS','publicFiles':len(selected),'htmlPages':len(ids),'directoryPages':len(directory),'newPages':len(pages),'updatedParents':len(updated),'sitemapPages':len(locs),'internalReferences':len(links),'protectedPublicFiles':len(preserved),'sourceDrafts':len(sources),'sectionCountRange':[min(headings),max(headings)],'uniqueDescriptions':len(set(descs)),'uniqueNewBodies':len(set(bodies)),'errors':errors}
 (args.audit/'source-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(report,errors=errors[:10]),ensure_ascii=False));assert not errors
if __name__=='__main__':main()

"""Check the full expansion, links, source separation and protected HTML."""
import argparse, hashlib, json, re, zipfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html, etree
import build_education_info as view

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);a=ap.parse_args();out=a.audit;root=view.ROOT
 load=view.load;data=load(root/'education-info-data.json');audit=load(out/'upgrade-audit.json');baseline=load(out/'before-release-public-manifest.json');old=load(out/'before-education-info-data.json');selection=load(out/'source-selection.json')
 fresh=[x for x in data['articles'] if x.get('expansionIndex')];assert len(fresh)==30 and len(data['articles'])==60
 assert len(set(x['route'] for x in data['articles']))==60
 assert [x for x in data['articles'] if not x.get('expansionIndex')]==old['articles'],'Previously published article records changed'
 descendants={n for n in baseline['files'] if n.startswith(('지점안내/','전국센터/','과목별학원/')) and n.endswith('.html')}
 linked={x['file'] for x in data['existingPages'] if x['module']}
 assert descendants<=linked, sorted(descendants-linked)[:5]
 changed=set(audit['changedPublicFiles']);preserved=0;bounded=0
 with zipfile.ZipFile(out/'before-source.zip') as z:
  for name in baseline['files']:
   raw=(root/name).read_bytes()
   if name not in changed:
    digest=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest() if name in baseline['textSha256'] else hashlib.sha256(raw).hexdigest()
    expected=baseline['textSha256'].get(name,baseline['files'][name]);assert digest==expected,name;preserved+=1
   elif name.endswith('.html') and name!='교육정보/index.html':
    norm=lambda s:view.strip(s).replace('\r\n','\n').rstrip()
    assert norm(raw.decode('utf-8'))==norm(z.read(name).decode('utf-8')),name;bounded+=1
 base_dom={};new_text=[];descs=[];links_checked=0;total_bytes=0
 def destination(href):
  u=urlsplit(href)
  if u.netloc and u.netloc!='xn--3e0bz50bxucwzc.com':return
  if u.scheme and u.scheme not in ('http','https'):return
  path=unquote(u.path)
  if not path:path='/'
  if not path.startswith('/'):raise AssertionError(('relative URL',href))
  name=path.lstrip('/')
  if not name or name.endswith('/'):name+='index.html'
  elif not Path(name).suffix:name+='/index.html'
  target=root/name;assert target.exists(),href
  if u.fragment:
   if name not in base_dom:base_dom[name]=html.fromstring(target.read_text(encoding='utf-8'))
   assert base_dom[name].xpath('//*[@id=$fragment]',fragment=unquote(u.fragment)),href
  return name
 for article in fresh:
  name=article['route'].lstrip('/')+'index.html';doc=html.fromstring((root/name).read_text(encoding='utf-8'));base_dom[name]=doc
  assert doc.xpath('//h1/text()')==[article['title']]
  desc=doc.xpath('//meta[@name="description"]/@content')[0];assert desc==article['description'] and len(desc)<=80 and desc.endswith('.');descs.append(desc)
  assert unquote(urlsplit(doc.xpath('//link[@rel="canonical"]/@href')[0]).path)==article['route']
  assert doc.xpath('//meta[@name="robots"]/@content')==['index,follow']
  for i,(heading,paragraph) in enumerate(article['sections'],1):
   parts=doc.xpath('//section[@id=$id]',id='part-'+str(i));assert len(parts)==1
   assert parts[0].xpath('./h2/text()')==[heading]
   rendered=' '.join(p.text_content() for p in parts[0].xpath('./p[not(@class)]'));assert rendered==paragraph,(article['title'],heading)
  photos=doc.xpath('//figure[@class="ei-photo"]/img');assert len(photos)==3
  assert len({x.get('src') for x in photos})==3
  for im,row in zip(photos,article['images']):
   assert im.get('src')==row['src'] and im.get('alt')==row['alt'] and im.get('loading')=='lazy'
   assert max(row['width'],row['height'])<=1200
   asset=root/row['src'].lstrip('/');size=asset.stat().st_size;total_bytes+=size;assert size<400_000,(row['src'],size)
  for href in doc.xpath('//a/@href'):
   # Empty paths are anchors within the current article.
   if href.startswith('#'):assert doc.xpath('//*[@id=$id]',id=unquote(href[1:])),href
   else:destination(href)
   links_checked+=1
  own=' '.join(p for _,p in article['sections']);new_text.append(own)
  manuscript=selection['pages'][article['expansionIndex']-1]['text'];source=re.sub(r'\s+','',manuscript);rewrite=re.sub(r'\s+','',own)
  match=SequenceMatcher(None,source,rewrite,autojunk=False).find_longest_match();assert match.size<100,(article['title'],'long unrewritten source passage',match.size)
  assert article['title']!=article['sourceTitle']
 assert len(set(descs))==30
 hub=html.fromstring((root/'교육정보/index.html').read_text(encoding='utf-8'));assert len(hub.xpath('//*[@data-education-card]'))==60
 ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};tree=etree.parse(str(root/'sitemap.xml'));locations=tree.xpath('//s:loc/text()',namespaces=ns);assert len(locations)==len(set(locations))==baseline['sitemapPages']+30
 for article in data['articles']:assert view.ui.url(article['route']) in locations
 rss=etree.parse(str(root/'rss.xml'));rsslinks=rss.xpath('//item/link/text()');assert len(rsslinks)==len(set(rsslinks))
 for article in fresh:assert view.ui.url(article['route']) in rsslinks
 counts=Counter()
 for item in data['existingPages']:
  if not item['module']:continue
  doc=html.fromstring((root/item['file']).read_text(encoding='utf-8'));block=doc.xpath('//*[@id="home-education" or @id="education-reading"]');assert len(block)==1
  hrefs={unquote(urlsplit(v).path) for v in block[0].xpath('.//a/@href')}
  assert set(item['module']['links'])<=hrefs and '/교육정보/' in hrefs,item['file']
  stage=item['module'].get('context',{}).get('stage');subject=item['module'].get('context',{}).get('subject')
  for route in item['module']['links']:
   counts[route]+=1;target=next(x for x in data['articles'] if x['route']==route)
   assert not stage or stage in target['stages'],(item['file'],target['title'])
   assert not subject or not target['subjects'] or subject in target['subjects'],(item['file'],target['title'])
 for article in fresh:assert counts[article['route']]>0
 duplicate_pairs=[]
 comparison=[('prior:'+x['slug'],' '.join(p for _,p in x['sections'])) for x in old['articles']]
 for index,article in enumerate(fresh):
  current=set(re.sub(r'\s+','',new_text[index])[i:i+30] for i in range(max(0,len(re.sub(r'\s+','',new_text[index]))-29)))
  for label,text in comparison:
   compact=re.sub(r'\s+','',text);other={compact[i:i+30] for i in range(max(0,len(compact)-29))};ratio=len(current&other)/max(1,len(current|other))
   if ratio>.12:duplicate_pairs.append([article['slug'],label,ratio])
  comparison.append((article['slug'],new_text[index]))
 assert not duplicate_pairs,duplicate_pairs
 result={'articles':60,'newArticles':30,'protectedFilesUnchanged':preserved,'boundedHtmlUpdates':bounded,'localDestinationsCovered':len(descendants),'newArticleLinksChecked':links_checked,'newImageBytes':total_bytes,'articleDescriptionsUnique':True,'sitemapPages':len(locations),'allNewArticlesHaveContextLinks':True,'nearDuplicatePairs':duplicate_pairs}
 view.save(out/'validation.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()

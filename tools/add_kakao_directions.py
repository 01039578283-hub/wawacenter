"""Add the reviewed Kakao maps after existing map images without rewriting content."""
import argparse,json,re,hashlib
from pathlib import Path
from html import escape
from urllib.parse import urljoin,urlsplit,unquote,quote
from datetime import datetime,timezone,timedelta
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
START='<!-- kakao-directions:start -->';END='<!-- kakao-directions:end -->'
NAVSTART='<!-- kakao-directions:jump:start -->';NAVEND='<!-- kakao-directions:jump:end -->'
CSS='<link rel="stylesheet" href="/assets/kakao-directions.css">'
def escaped(s):return escape(str(s),quote=True)
def frame_html(branch):
 return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>'+escaped(branch['name'])+' 위치 지도</title><link rel="stylesheet" href="/assets/kakao-map-frame.css"></head><body data-map-state="loading"><div id="daumRoughmapContainer'+branch['timestamp']+'" class="root_daum_roughmap root_daum_roughmap_landing" data-kakao-map data-timestamp="'+branch['timestamp']+'" data-key="'+branch['key']+'"></div><p class="kd-frame-status" data-map-status>위치 지도를 불러오고 있습니다.</p><script src="/assets/kakao-map-frame.js"></script><script charset="UTF-8" class="daum_roughmap_loader_script" src="https://t1.kakaocdn.net/kakaomapweb/roughmap/loader/prod/roughmapLoader.js"></script></body></html>')
def section_html(branch,route):
 b=escaped(branch['name'])
 body=START+'<section class="kd-section" id="directions" aria-labelledby="directions-title" data-kakao-directions data-kakao-branch="'+b+'" data-kakao-route="'+escaped(route)+'"><h2 id="directions-title">찾아오시는 길</h2><p class="kd-intro">'+b+'의 위치와 주변 교통편을 확인하세요.</p><div class="kd-panel"><iframe class="kd-map" src="'+branch['frame']+'" title="'+b+' 카카오맵 위치 지도" loading="lazy" width="640" height="400" sandbox="allow-scripts" referrerpolicy="strict-origin-when-cross-origin"></iframe><p class="kd-address"><strong>'+b+' 방문 주소</strong>'+escaped(branch['address'])+'</p><div class="kd-transport">'
 if branch['subways']:
  body+='<section aria-labelledby="directions-subway-title"><h3 id="directions-subway-title">주변 지하철</h3><ul class="kd-list">'+''.join('<li><span class="kd-line">'+escaped(x['line'])+'</span><span>'+escaped(x['name'])+'</span></li>' for x in branch['subways'])+'</ul></section>'
 if branch['busStops']:
  body+='<section aria-labelledby="directions-stops-title"><h3 id="directions-stops-title">주변 정류장</h3><ul class="kd-list">'+''.join('<li><span class="kd-stop-number">'+str(x['number'])+'</span><span>'+escaped(x['name'])+'</span></li>' for x in branch['busStops'])+'</ul></section>'
 if branch['busGroups']:
  body+='<section aria-labelledby="directions-buses-title"><h3 id="directions-buses-title">주변 버스</h3><dl class="kd-buses">'+''.join('<div><dt><span class="kd-bus-type">'+escaped(x['type'])+'</span></dt><dd>'+''.join('<span>'+escaped(n)+'</span>' for n in x['routes'])+'</dd></div>' for x in branch['busGroups'])+'</dl></section>'
 if not any(branch[k] for k in ('subways','busStops','busGroups')):
  body+='<section><h3>교통편 안내</h3><p class="kd-note">제공된 지도에는 주변 교통정보가 등록되어 있지 않습니다. 방문 전 이용할 교통편의 최신 운행 정보를 확인해 주세요.</p></section>'
 body+='</div></div><p class="kd-note">카카오맵 약도에 등록된 위치와 교통정보입니다. 노선·정차 여부는 달라질 수 있으니 방문 전 확인해 주세요.</p></section>'+END
 return body
def patch_page(text,branch,route):
 section=section_html(branch,route)
 if START in text:
  text=re.sub(re.escape(START)+r'[\s\S]*?'+re.escape(END),lambda _:section,text,count=1)
 else:
  if '<!-- branch-map:end -->' in text:
   text=text.replace('<!-- branch-map:end -->','<!-- branch-map:end -->'+section,1)
  else:
   pattern=r'<section\b[^>]*class="[^"]*\bimage-first-location\b[^"]*"[^>]*>[\s\S]*?</section>'
   match=re.search(pattern,text);assert match and 'assets/maps/' in match[0],route
   text=text[:match.end()]+section+text[match.end():]
 if CSS not in text:
  shell='<link rel="stylesheet" href="/assets/site-shell.css">';assert shell in text
  text=text.replace(shell,CSS+shell,1)
 if NAVSTART not in text:
  nav=re.search(r'<nav class="(?:bd-jump|image-first-nav)"[^>]*>[\s\S]*?</nav>',text);assert nav,route
  pos=nav.end()-6;text=text[:pos]+NAVSTART+'<a href="#directions">찾아오시는 길</a>'+NAVEND+text[pos:]
 return text
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--report',required=True);args=parser.parse_args()
 data=json.loads((ROOT/'kakao-directions-data.json').read_text('utf-8'));maps=json.loads((ROOT/'branch-map-data.json').read_text('utf-8'));manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8'))
 srcs={v['image']['src']:v for v in maps['areas'].values()};changed=[];pages=[];held=[];hubs=[];newassets=[]
 for name in list(manifest['files']):
  if not name.endswith('.html'):continue
  path=ROOT/name;before=path.read_bytes();text=before.decode('utf-8');entries=[]
  for src in re.findall(r'<img\b[^>]*src="([^"]+)"[^>]*>',text):
   key=unquote(urlsplit(urljoin('https://전국수업.com/'+name,src)).path)
   if key in srcs:entries.append(srcs[key])
  if entries:
   assert len(entries)==1,name
   entry=entries[0];route=entry['branch'];branch=data['branches'][route];record={'file':name,'area':entry['area'],'branch':route,'name':branch['name'],'frame':branch['frame']}
   if not branch['approved']:held.append(record);continue
   nexttext=patch_page(text,branch,route);pages.append(record)
  elif name=='지점안내/index.html' or re.fullmatch(r'지점안내/[^/]+/index\.html',name):
   def card(m):
    c=m[0];href=re.search(r'<h3><a href="([^"]+)"',c);assert href,name
    route=unquote(urlsplit(href[1]).path);branch=data['branches'].get(route)
    if not branch or not branch['approved'] or 'data-kakao-hub-link' in c:return c
    link='<p class="kd-hub-link" data-kakao-hub-link><a href="'+quote(route,safe='/')+'#directions">'+escaped(branch['name'])+' 찾아오시는 길</a></p>'
    return c.removesuffix('</article>')+link+'</article>'
   nexttext=re.sub(r'<article\b[^>]*\bdata-branch-card\b[^>]*>[\s\S]*?</article>',card,text)
   if nexttext!=text:
    if CSS not in nexttext:nexttext=nexttext.replace('<link rel="stylesheet" href="/assets/site-shell.css">',CSS+'<link rel="stylesheet" href="/assets/site-shell.css">',1)
    hubs.append(name)
  else:continue
  if nexttext!=text:
   changed.append(name)
   if args.apply:path.write_bytes(nexttext.encode('utf-8'))
 for route,b in data['branches'].items():
  if not b['approved']:continue
  name=b['frame'].lstrip('/');newassets.append(name)
  if args.apply:
   path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(frame_html(b).encode('utf-8'))
 if args.apply:
  sitemap=ROOT/'sitemap.xml';raw=sitemap.read_bytes();tree=etree.fromstring(raw);changedset=set(changed)
  for node in tree:
   loc=node.find('{*}loc');route=unquote(urlsplit(loc.text).path);name=route.lstrip('/')+'index.html' if route.endswith('/') else route.lstrip('/')
   if name in changedset:
    last=node.find('{*}lastmod')
    if last is None:last=etree.SubElement(node,'{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
    last.text='2026-10-16'
  sitemap.write_bytes(etree.tostring(tree,encoding='utf-8',xml_declaration=True,pretty_print=True))
  for name in changed+newassets+['assets/kakao-directions.css','assets/kakao-map-frame.css','assets/kakao-map-frame.js','sitemap.xml']:
   raw=(ROOT/name).read_bytes();manifest['files'][name]=hashlib.sha256(raw).hexdigest()
   manifest.setdefault('textSha256',{})[name]=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
  manifest['createdAt']=datetime.now(timezone(timedelta(hours=9))).isoformat()
  (ROOT/'release-public-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf-8')
 result={'pages':pages,'hubs':hubs,'held':held,'changed':changed,'assets':newassets,'targetCount':len(pages)+len(held),'applied':args.apply}
 Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
 print(json.dumps({'mappedPages':len(pages),'hubs':len(hubs),'held':len(held),'changedHtml':len(changed),'frameAssets':len(newassets),'apply':args.apply}))
if __name__=='__main__':main()

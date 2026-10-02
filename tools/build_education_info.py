"""Publish revised educational articles and narrowly insert contextual links."""
import argparse,hashlib,json,re,zipfile,shutil
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from urllib.parse import unquote,urlsplit
from html import escape
from lxml import etree
import build_branch_upgrade as ui
from build_site_shell import header,NAV
from education_articles import ARTICLES,GROUPS,SOURCES

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-02'
ui.DAY=DAY
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,value):ui.save(path,value)
def route(name):return '/' if name=='index.html' else '/'+name.removesuffix('index.html')
def marked(kind,body):return '<!-- education-links:'+kind+':start -->'+body+'<!-- education-links:'+kind+':end -->'
def strip(text):
 text=re.sub(r'<!-- education-links:([a-z]+):start -->[\s\S]*?<!-- education-links:\1:end -->','',text)
 return re.sub(r'<!-- education-style:start -->[\s\S]*?<!-- education-style:end -->','',text)
def style(text):
 return text.replace('<link rel="stylesheet" href="/assets/site-shell.css">','<!-- education-style:start --><link rel="stylesheet" href="/assets/education-info.css"><!-- education-style:end --><link rel="stylesheet" href="/assets/site-shell.css">',1)
def actions(items):return '<div class="ei-actions">'+''.join('<a'+(' class="ei-primary"' if len(x)>2 and x[2] else '')+' href="'+ui.href(x[0])+'">'+ui.e(x[1])+'</a>' for x in items)+'</div>'
def section(id,title,body,cls=''):
 return '<section class="ei-section '+cls+'" id="'+id+'" aria-labelledby="'+id+'-title"><h2 id="'+id+'-title">'+ui.e(title)+'</h2>'+body+'</section>'
def finder(regions):
 return section('local-learning','우리 지역의 수업과 지점도 확인해 보세요',
  '<p>읽은 내용을 바탕으로 학생에게 필요한 도움을 정했다면, 통학할 지역의 수업과 교육비 자료를 함께 살펴보세요. 동네 이름과 실제 등원 주소는 다를 수 있습니다.</p>'
  '<div class="ei-finder" data-education-finder><div class="ei-finder-fields" data-finder-fields hidden>'
  '<label>지역<select name="region"><option value="">지역 선택</option></select></label>'
  '<label>지점<select name="branch" disabled><option value="">지점 선택</option></select></label>'
  '<label>동네<select name="area" disabled><option value="">동네 선택</option></select></label></div>'
  '<p data-finder-status role="status" aria-live="polite">아래 지역별 목록에서도 지점을 찾을 수 있습니다.</p>'
  '<div class="ei-actions"><a data-finder-branch href="'+ui.href('/지점안내/')+'">전체 지점 정보</a><a data-finder-area href="'+ui.href('/전국센터/')+'">동네별 수업 안내</a></div>'
  '<details><summary>지역별 지점 목록 바로가기</summary><nav class="ei-region-fallback" aria-label="지역별 수업 지점">'+''.join(ui.link('/지점안내/'+r+'/',r+' 지점') for r in regions)+'</nav></details></div>')
def enrich_shell(name):
 text=(ROOT/name).read_text(encoding='utf-8');text,n=re.subn(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:header(route(name)),text,count=1);assert n==1
 text=text.replace('<body class="general-page bd-page">','<body class="general-page bd-page ei-page" data-site-shell="1">',1)
 if name!='교육정보/index.html':text=text.replace('<meta property="og:type" content="website">','<meta property="og:type" content="article">',1)
 text=text.replace('</head>','<link rel="stylesheet" href="/assets/education-info.css"><link rel="stylesheet" href="/assets/site-shell.css"><script defer src="/assets/education-info.js"></script></head>',1)
 ui.write(ROOT/name,text)
def card(a):
 return '<article class="ei-card" data-education-card data-group="'+ui.e(a['group'])+'" data-stages="'+''.join(a['stages'])+'" data-search="'+ui.e(' '.join([a['title'],a['description'],*a['subjects']]))+'"><span class="ei-kicker">'+ui.e(a['group'])+'</span><h3>'+ui.link(a['route'],a['title'])+'</h3><p>'+ui.e(a['description'])+'</p>'+ui.link(a['route'],'내용과 점검표 읽기 →')+'</article>'
def related(items,title='함께 읽으면 도움이 되는 교육정보',id='education-reading'):
 return '<section class="ei-related" id="'+id+'" aria-labelledby="'+id+'-title" data-education-related><h2 id="'+id+'-title">'+ui.e(title)+'</h2><p>지금 어려운 과제와 생활 일정에 맞는 내용을 골라 보세요.</p><div class="ei-related-grid">'+''.join(ui.link(a['route'],a['title']) for a in items)+'</div>'+actions([('/교육정보/','교육정보 전체 보기')])+'</section>'
def pick(c,name):
 stage=c.get('stage');subject=c.get('subject');kind=c.get('kind')
 preferred=[12,17,27,2,22] if subject=='수학' else [2,22,25,17,27] if subject=='영어' else [23,30,20,7,21,18] if stage=='초' else [24,6,29,15,19,16,8] if stage=='중' else [6,16,29,15,14,5,19] if stage=='고' else [4,10,13,28,30,3]
 if kind=='hub':preferred=[4,13,30,23,7]
 seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
 candidates=[ARTICLES[i-1] for i in preferred if not stage or stage in ARTICLES[i-1]['stages']]
 offset=seed%len(candidates);return (candidates[offset:]+candidates[:offset])[:3]

IMAGE_ALTS='''책상 앞에서 생각하는 두 학생|알파벳과 함께 놓인 책|자료를 보며 대화하는 학생들|책을 들고 서 있는 학생|확인 항목을 표시하는 손|책을 펼친 교실의 학생|교실에서 필기하는 학생|공부와 관련된 그림과 노트|헤드폰을 쓰고 책을 보는 학생|펼친 책에 필기하는 모습|책상 앞에서 생각하는 학생들|책을 들고 서 있는 세 학생|노트북과 책을 보는 학생|교실에서 손을 든 학생|일정을 표시한 벽면의 자료|시간을 보여 주는 시계|책을 읽으며 공부하는 학생|교실에서 책을 보는 학생들|책과 태블릿을 펼친 책상|칠판 앞에서 설명하는 아이들|문제 풀이를 적는 모습|책상에서 쉬고 있는 학생|생각하는 모습을 표현한 세 학생|책을 펼친 학생의 손|함께 자료를 보는 학생들|칠판 앞에서 대화하는 학생들|교재 옆에서 생각하는 학생|책에 필기하는 학생의 손|펼친 교재에 문제를 푸는 학생|교복을 입고 서 있는 두 학생|침대에서 휴식하는 모습|테이블에서 공부 이야기를 나누는 모습|책과 컴퓨터로 공부하는 학생들|교실 책상에 앉은 학생들|자료를 함께 보는 두 학생|책상에서 손을 든 학생|테이블에서 자료를 검토하는 학생들|책과 함께 앉아 있는 세 학생|책과 태블릿이 놓인 학습 공간|학습 자료 앞에서 웃는 아이|생각하는 모습을 표현한 두 학생|선생님과 과제를 확인하는 학생|교실에서 공부하는 학생들|펼친 책을 읽는 학생|교실에 함께 있는 학생들|펼쳐진 책의 여러 페이지|혼자 책을 읽는 학생|여러 학생의 학습을 살펴보는 모습|칠판에 글을 쓰는 학생|칠판 앞에 서 있는 두 학생|쌓인 책 옆에서 생각하는 학생|색 표시가 있는 책과 필기구|교재를 읽는 학생|필기 자료를 함께 보는 모습|테이블에서 대화하는 학생들|수학 내용이 있는 칠판 앞 학생|과제를 함께 확인하는 두 학생|책을 보며 필기하는 학생|책상에서 학습하는 학생|책과 태블릿이 펼쳐진 책상|책과 컴퓨터가 놓인 학습 공간|계획표에 표시하는 손|책상에서 손을 든 두 학생|교실의 앞쪽에 앉은 학생|파일을 들고 서 있는 학생|책상 앞에 앉은 두 학생|태블릿과 필기 자료가 놓인 책상|필기구와 작은 노트|교실에서 필기하는 학생의 손|컴퓨터 앞에서 공부하는 모습|책상에서 읽고 쓰는 학생|벽면의 일정을 확인하는 모습|노트에 글을 적는 손|책 위에 놓인 작은 시계|생각하며 앉아 있는 두 학생|책을 읽으며 확인하는 학생|책상 앞에서 이야기를 나누는 모습|책상에서 혼자 공부하는 아이|교재에 문제 풀이를 쓰는 학생|교실에서 책을 보는 여러 학생|책을 들고 서 있는 두 학생|교실에서 학습 자료를 보는 모습|가족이 함께 책을 보는 모습|책과 노트에 필기하는 학생|교실에서 글을 쓰는 학생|책상에 앉아 공부하는 학생들|자료를 함께 확인하는 학생들|책상 앞에서 생각하는 학생|침대에서 잠든 모습|책과 노트를 함께 보는 학생들'''.split('|')
assert len(IMAGE_ALTS)==90

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args();audit=args.audit
 baseline=load(audit/'before-manifest.json');selected_sources=load(audit/'source-selection.json');images=load(audit/'selected-images.json')
 assert len(selected_sources['pages'])==30 and len(images)==90
 snapshot=audit/'before-source.zip'
 if not snapshot.exists():
  with zipfile.ZipFile(snapshot,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
   for name,digest in baseline['files'].items():
    if not name.endswith('.html') and name not in ['sitemap.xml','rss.xml','llms.txt']:continue
    raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name;archive.writestr(name,raw)
 # Two visually similar random photos are separated between articles.
 images[58],images[74]=images[74],images[58];alts=IMAGE_ALTS[:];alts[58],alts[74]=alts[74],alts[58]
 new_assets=[]
 for i,img in enumerate(images):
  raw=Path(img['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==img['sha256']
  name='assets/education-info/photo-'+f'{i+1:03}'+Path(img['file']).suffix.lower();dest=ROOT/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists() or dest.read_bytes()!=raw:dest.write_bytes(raw)
  img['src']='/'+name;img['alt']=alts[i];new_assets.append(name)
 for i,a in enumerate(ARTICLES):
  a['route']='/교육정보/'+a['slug']+'/';a['images']=[{k:im[k] for k in ['src','alt','width','height','sha256']} for im in images[i*3:i*3+3]]
  a['sourceTitle']=selected_sources['pages'][a['sourceIndex']]['sourceTitle']
 branches=ui.BRANCHES;regions=ui.REGIONS
 centers={'regions':regions,'branches':[{'name':b['name'],'region':b['region'],'route':b['route'],'areas':[{'slug':a['slug'],'name':a['name'],'route':'/전국센터/'+a['slug']+'/'} for a in b['areas']]} for b in branches]}
 save(ROOT/'assets/education-centers.json',centers)
 for a in ARTICLES:
  tags=[a['group'],'·'.join({'초':'초등','중':'중등','고':'고등'}[s] for s in a['stages'])]
  body='<section class="ei-hero"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h1>'+ui.e(a['title'])+'</h1><p>'+ui.e(a['lead'])+'</p><div class="ei-tags">'+''.join('<span>'+ui.e(x)+'</span>' for x in tags)+'</div>'+actions([('/교육정보/','교육정보 목록'),('#local-learning','우리 지역 수업 찾기')])+'</section><div class="ei-reading">'
  titles=[(f'part-{i}',h) for i,(h,_) in enumerate(a['sections'],1)]+[('practice',a['task'][0]),('questions','자주 묻는 질문')]
  body+='<details class="ei-toc" open><summary>이 글에서 확인할 내용</summary><ol>'+''.join('<li>'+ui.link('#'+id,h)+'</li>' for id,h in titles)+'</ol></details>'
  for i,(h,p) in enumerate(a['sections'],1):
   # Each paragraph is split at a sentence boundary for easier mobile reading.
   sentences=re.split(r'(?<=\.) ',p);cut=max(1,len(sentences)//2)
   content='<p>'+ui.e(' '.join(sentences[:cut]))+'</p><p>'+ui.e(' '.join(sentences[cut:]))+'</p>'
   cited='motivation' if a['sourceIndex']==2 and i==2 else 'sleep' if a['sourceIndex']==4 and i==1 else 'fees' if a['sourceIndex']==3 and i==4 else 'learning' if a['sourceIndex']==21 and i==2 else 'support' if a['sourceIndex']==10 and i==6 else 'wawa' if a['sourceIndex']==27 and i==4 else None
   if cited:content+='<p class="ei-ref">참고: '+ui.link(SOURCES[cited][1],SOURCES[cited][0],True)+'</p>'
   body+=section('part-'+str(i),h,content)
   if i in [2,4,6]:
    im=a['images'][i//2-1];body+='<figure class="ei-photo"><img src="'+im['src']+'" alt="'+ui.e(im['alt'])+'" width="'+str(im['width'])+'" height="'+str(im['height'])+'" loading="lazy" decoding="async"><figcaption>학습 주제를 설명하기 위한 이미지입니다.</figcaption></figure>'
  body+=section('practice',a['task'][0],'<ul>'+''.join('<li>'+ui.e(x)+'</li>' for x in a['task'][1])+'</ul>','ei-task')
  body+=section('questions','자주 묻는 질문',ui.faqs_markup(a['faq']))
  guide='초등학생공부습관' if a['stages']==['초'] else '중학생내신공부법' if a['stages']==['중'] else '고등학생과목별공부법' if a['stages']==['고'] else '학습플래너작성법' if a['group']=='계획·시간 관리' else '학부모상담체크리스트' if a['group'] in ['학원·코칭','생활·학부모'] else '학습질문만들기'
  body+=section('more-help','공부 방법과 교재를 이어서 살펴보세요',actions([('/학습가이드/'+guide+'/','관련 학습가이드'),('/교재안내/','영어·수학 교재 후보'),('/학습시스템/','학습코칭과 공식 영상')]))
  if a['sources']:body+=section('references','참고 자료','<ul class="ei-sources">'+''.join('<li>'+ui.link(SOURCES[k][1],SOURCES[k][0],True)+'</li>' for k in a['sources'])+'</ul>')
  others=[x for x in ARTICLES if x['group']==a['group'] and x!=a][:3]
  body+=related(others,id='related-articles')+finder(regions)+'</div>'
  node={'@type':'Article','@id':ui.url(a['route'])+'#article','headline':a['title'],'description':a['description'],'inLanguage':'ko-KR','datePublished':DAY,'dateModified':DAY,'author':{'@type':'Organization','name':'전국수업.com','url':ui.url('/')},'publisher':{'@type':'Organization','name':'전국수업.com','url':ui.url('/')},'image':[ui.DOMAIN+im['src'] for im in a['images']],'mainEntityOfPage':{'@id':ui.url(a['route'])+'#webpage'},'articleSection':a['group'],'citation':[SOURCES[k][1] for k in a['sources']]}
  ui.shell(a['route'],a['title'],a['description'],body,[('교육정보','/교육정보/'),(a['title'],a['route'])],faqs=a['faq'],nodes=[node]);enrich_shell(a['route'].lstrip('/')+'index.html')
 hubdesc='시험 준비·공부 계획·복습·동기·학원 선택·생활 관리에 관한 교육정보 30편과 실천 점검표를 찾아봅니다.'
 hub='<section class="ei-hero"><p class="ei-kicker">교육정보</p><h1>공부와 생활의 고민,<br>필요한 정보부터 찾아보세요</h1><p>학생이 혼자 공부하다 막혔을 때, 부모가 수업과 일정을 고민할 때 읽을 수 있는 글입니다. 과제·질문·생활을 나눠 보고 각 글의 점검표로 다음 행동을 정해 보세요.</p>'+actions([('/학습가이드/','학년·과목별 학습가이드'),('/지점안내/','우리 지역 지점 찾기')])+'</section>'
 hub+='<nav class="ei-groups" aria-label="교육정보 주제">'+''.join('<a href="#article-list" data-education-group="'+ui.e(g)+'">'+ui.e(g)+'</a>' for g in GROUPS)+'</nav>'
 hub+='<form class="ei-filter" data-education-filter role="search"><label>궁금한 내용 검색<input name="q" type="search" placeholder="예: 복습, 수면, 학원 등록"></label><label>주제<select name="group"><option value="">모든 주제</option>'+''.join('<option>'+ui.e(g)+'</option>' for g in GROUPS)+'</select></label><label>대상<select name="stage"><option value="">모든 학년</option><option value="초">초등</option><option value="중">중등</option><option value="고">고등</option></select></label><button class="ei-btn" type="reset">전체 보기</button></form><p data-education-status role="status" aria-live="polite">30개 교육정보 글이 있습니다.</p><noscript><p>검색 기능을 사용하지 않아도 아래에서 모든 글을 읽을 수 있습니다.</p></noscript><div class="ei-empty" data-education-empty hidden>검색한 글이 없습니다. 검색어를 줄이거나 다른 주제를 선택해 보세요.</div><section id="article-list" aria-label="교육정보 글 목록"><div class="ei-list">'+''.join(card(a) for a in ARTICLES)+'</div></section>'+finder(regions)
 node={'@type':'ItemList','@id':ui.url('/교육정보/')+'#articles','name':'학생과 학부모를 위한 교육정보','numberOfItems':30,'itemListElement':[{'@type':'ListItem','position':i,'name':a['title'],'url':ui.url(a['route'])} for i,a in enumerate(ARTICLES,1)]}
 ui.shell('/교육정보/','학생과 학부모를 위한 교육정보',hubdesc,hub,[('교육정보','/교육정보/')],nodes=[node],kind='CollectionPage');enrich_shell('교육정보/index.html')
 changes=[];contexts={p['file']:p['context'] for p in load(ROOT/'contextual-links-data.json')['pages']}
 with zipfile.ZipFile(snapshot) as archive:
  for name in baseline['files']:
   if not name.endswith('.html'):continue
   original=archive.read(name).decode('utf-8');text=original
   text,count=re.subn(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:header(route(name)),text,count=1);assert count==1,name
   expected=None
   if name in contexts:
    c=contexts[name];items=pick(c,name);block=marked('module',related(items,(c['subject']+' ' if c.get('subject') else '')+'공부와 수업 선택에 도움이 되는 교육정보'))
    if '<!-- contextual-links:module:end -->' in text:text=text.replace('<!-- contextual-links:module:end -->','<!-- contextual-links:module:end -->'+block,1)
    else:raise AssertionError('missing reviewed resource insertion point: '+name)
    jump=marked('jump','<nav class="ei-jump" aria-label="교육정보 바로가기">'+ui.link('#education-reading','관련 교육정보 읽기')+ui.link('/교육정보/','교육정보 목록')+'</nav>')
    text=text.replace('<!-- contextual-links:jump:end -->','<!-- contextual-links:jump:end -->'+jump,1);text=style(text)
    expected={'context':c,'links':[a['route'] for a in items]}
   elif name=='index.html':
    featured=[next(a for a in ARTICLES if a['group']==g) for g in GROUPS]
    block='<section class="ei-home" id="home-education" aria-labelledby="home-education-title"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h2 id="home-education-title">공부 계획부터 학원 선택까지</h2><p>시험 준비, 과목별 공부, 동기와 생활 관리에서 지금 필요한 내용을 찾아보세요. 글마다 바로 써볼 수 있는 질문과 점검표를 담았습니다.</p><div class="ei-related-grid">'+''.join(ui.link(a['route'],a['title']) for a in featured)+'</div>'+actions([('/교육정보/','교육정보 30편 전체 보기',True)])+'</section>'
    assert '<!-- home-library:content:end -->' in text;text=text.replace('<!-- home-library:content:end -->','<!-- home-library:content:end -->'+marked('home',block),1)
    text=text.replace('<!-- home-library:jump:end -->','<!-- home-library:jump:end -->'+marked('jump','<nav class="ei-jump" aria-label="교육정보 글 바로가기">'+ui.link('#home-education','학생·학부모 교육정보 읽기')+'</nav>'),1);text=style(text)
    expected={'links':[a['route'] for a in featured]}
   ui.write(ROOT/name,text);changes.append({'file':name,'route':route(name),'module':expected})
 # Preserve prior URL entries; only add the new canonical documents.
 sitemap=etree.fromstring(archive_bytes(snapshot,'sitemap.xml'));ns='http://www.sitemaps.org/schemas/sitemap/0.9';existing={unquote(urlsplit(u.find('{'+ns+'}loc').text).path) for u in sitemap}
 for p in ['/교육정보/',*[a['route'] for a in ARTICLES]]:
  assert p not in existing;entry=etree.SubElement(sitemap,'{'+ns+'}url');etree.SubElement(entry,'{'+ns+'}loc').text=ui.url(p);etree.SubElement(entry,'{'+ns+'}lastmod').text=DAY
 content_changed={p['route'] for p in changes if p['module']}
 for entry in sitemap:
  if unquote(urlsplit(entry.find('{'+ns+'}loc').text).path) in content_changed:
   date=entry.find('{'+ns+'}lastmod')
   if date is None:date=etree.SubElement(entry,'{'+ns+'}lastmod')
   date.text=DAY
 (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
 rss=etree.fromstring(archive_bytes(snapshot,'rss.xml'));channel=rss.find('channel');channel.find('lastBuildDate').text='Fri, 02 Oct 2026 12:00:00 +0900'
 for a in reversed(ARTICLES):
  item=etree.Element('item');etree.SubElement(item,'title').text=a['title'];etree.SubElement(item,'link').text=ui.url(a['route']);etree.SubElement(item,'guid',isPermaLink='true').text=ui.url(a['route']);etree.SubElement(item,'description').text=a['description'];etree.SubElement(item,'pubDate').text='Fri, 02 Oct 2026 12:00:00 +0900';channel.insert(5,item)
 (ROOT/'rss.xml').write_bytes(etree.tostring(rss,encoding='utf-8',xml_declaration=True,pretty_print=True))
 llms=archive_bytes(snapshot,'llms.txt').decode('utf-8');llms+='\n\n## 교육정보\n\n- 학생과 학부모를 위한 교육정보: '+ui.DOMAIN+'/교육정보/\n'+''.join('- '+a['title']+': '+ui.DOMAIN+a['route']+'\n' for a in ARTICLES);ui.write(ROOT/'llms.txt',llms)
 save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
 shell_data=load(ROOT/'site-shell-data.json');shell_data['nav']=NAV;shell_data['pages']=sorted(set(shell_data['pages'])|set(ui.NEW));save(ROOT/'site-shell-data.json',shell_data)
 public={**baseline['files']};textsha={**baseline['textSha256']}
 names=[p['file'] for p in changes]+ui.NEW+new_assets+['assets/education-info.css','assets/education-info.js','assets/education-centers.json','assets/site-shell.css','sitemap.xml','rss.xml','llms.txt']
 for name in names:
  raw=(ROOT/name).read_bytes();public[name]=hashlib.sha256(raw).hexdigest()
  if name.endswith(('.html','.css','.js','.json','.xml','.txt')):textsha[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
 manifest={**baseline,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':len(sitemap),'files':dict(sorted(public.items())),'textSha256':dict(sorted(textsha.items()))};save(ROOT/'release-public-manifest.json',manifest)
 # Source provenance is kept outside public output.
 report={'version':1,'selectedFolders':30,'articles':ARTICLES,'newPages':ui.NEW,'existingPages':changes,'images':[{'src':i['src'],'alt':i['alt'],'width':i['width'],'height':i['height'],'sha256':i['sha256']} for i in images]}
 save(ROOT/'education-info-data.json',report)
 print(json.dumps({'articles':30,'newPages':31,'images':90,'menusUpdated':len(changes),'relatedModules':sum(bool(p['module']) for p in changes),'publicFiles':len(public),'sitemapPages':len(sitemap)},ensure_ascii=False))
def archive_bytes(snapshot,name):
 with zipfile.ZipFile(snapshot) as archive:return archive.read(name)
if __name__=='__main__':main()

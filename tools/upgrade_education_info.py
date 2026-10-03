"""Expand the existing library without regenerating protected local pages."""
import argparse, hashlib, json, re, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import etree
from PIL import Image, ImageOps
import build_education_info as view

ROOT = view.ROOT
ui = view.ui
DAY = '2026-10-04'
ui.DAY = DAY
SOURCES = {
 'styles': ('EEF 학습 유형 근거 검토', 'https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/learning-styles'),
 'listening': ('British Council 수준별 영어 듣기 자료', 'https://learnenglish.britishcouncil.org/free-resources/listening'),
 'keep': ('Google Keep 체크리스트 공식 도움말', 'https://support.google.com/keep/answer/6395451?hl=ko'),
 'learning': view.SOURCES['learning'], 'support': view.SOURCES['support'], 'wawa': view.SOURCES['wawa'],
}
REFERENCES = {1:(2,'styles'), 2:(1,'listening'), 3:(1,'keep'), 7:(1,'wawa'), 8:(6,'support'), 20:(5,'learning'), 21:(6,'support'), 22:(5,'learning'), 30:(2,'support')}
ALTS = '''학습 자료를 들고 설명하는 학생|펼친 책 옆에서 노트에 필기하는 손|교실에서 학습 자료를 함께 확인하는 학생들|노트와 영어 알파벳이 놓인 책상|벽면 달력에 일정을 표시하는 모습|교실에서 책을 펼친 학생|컴퓨터와 필기구가 놓인 학습 공간|수학 내용이 적힌 칠판 앞의 학생들|휴식용품이 놓인 수영장 가장자리|책상에 앉아 자료를 보는 네 학생|펼친 교재를 함께 확인하는 두 사람|노트북과 책이 놓인 책상|문항과 확인 표시가 있는 영어 자료|컴퓨터와 책을 펼치고 생각하는 학생|영상 화면과 펼친 교재가 놓인 책상|태블릿과 교재를 함께 보는 학생|교실 책상 앞에서 질문을 표현하는 두 학생|교실에서 함께 있는 네 학생|달력에 메모를 붙이는 손|책을 들고 서 있는 두 학생|노트와 필기구, 운동 소품이 놓인 책상|함께 모여 웃는 학생들|교실에서 교재를 읽는 학생|책상에서 손을 들고 질문하는 학생|야외에서 책을 들고 서 있는 두 학생|책을 펼치고 혼자 필기하는 학생|칠판 앞에서 설명을 나누는 모습|태블릿과 교재를 펼쳐 공부하는 책상|학습 자료를 들어 보이는 두 학생|조명이 켜진 책상에서 혼자 공부하는 모습|펼친 책 옆에서 생각하는 학생|책상에서 책을 읽는 아이|노트와 노트북으로 함께 공부하는 모습|야외에서 책을 들고 있는 학생|교실 책상에서 필기하는 손|컴퓨터와 책을 펼쳐 놓고 공부하는 모습|책과 자료를 확인하는 세 학생|교실에서 책을 들고 함께 서 있는 학생들|소파에 앉아 책을 보는 보호자와 아이|교실 책상에서 자료에 표시하는 손|가족이 함께 책을 읽는 모습|펼쳐진 책의 여러 페이지|햇빛이 들어오는 교실의 책상과 칠판|복도에서 학습 자료를 함께 보는 학생들|쌓인 책과 읽는 사람들을 표현한 그림|칠판에 도형을 그리며 이야기하는 두 학생|노트북과 교재를 함께 확인하는 두 사람|컴퓨터와 시계, 노트가 놓인 책상|태블릿과 교재로 공부하는 학생|책상에서 손을 들고 질문하는 학생|교실에서 학생의 학습을 살펴보는 모습|교재 옆에서 노트에 필기하는 손|책상에서 혼자 교재를 읽는 학생|책상 앞에서 질문을 표현하는 아이들|교재를 펼쳐 필기하는 학생의 손|책상에 앉아 공부하는 사람을 표현한 그림|쌓인 책 옆에서 생각하는 학생|책 더미에 기대어 생각하는 학생|태블릿과 책을 펼쳐 공부하는 학생|책을 펼치고 내용을 함께 확인하는 두 사람|문제에 도형을 그리며 공부하는 아이|책에 기대어 쉬고 있는 학생|펼친 책과 작은 시계가 놓인 책상|책과 태블릿을 펼치고 함께 공부하는 모습|책을 펼쳐 두고 필기하는 학생|노트북과 교재로 공부하는 학생|벽면 달력에서 날짜를 확인하는 모습|학습 자료에 표시하며 함께 공부하는 학생들|자료를 들고 함께 서 있는 학생들|책을 읽으며 단어 자료를 확인하는 학생|벽면 일정표에 내용을 적는 모습|책상에서 학생과 상담하는 모습|교재를 들고 서 있는 두 학생|교실에서 함께 학습 자료를 확인하는 학생들|책상에 앉아 책을 읽는 아이|책상에서 글을 쓰는 아이들|여러 교재를 펼쳐 놓고 읽는 학생|펼친 책을 함께 보는 보호자와 아이|노트에 내용을 기록하는 손|학습 내용을 함께 확인하는 두 사람|책상에서 교재에 필기하는 손|교재 옆의 노트에 글을 쓰는 손|태블릿과 책을 함께 확인하는 학습 모습|펼친 책 옆에서 질문을 생각하는 학생|칠판 앞에서 함께 책을 보는 학생들|교재와 태블릿으로 공부하는 학생|침대에 앉아 휴대전화를 보는 모습|책과 함께 소파에 앉아 있는 아이들|책상에 기대어 생각하는 학생|강단에서 내용을 설명하는 사람'''.split('|')
assert len(ALTS) == 90

def read_articles():
 blocks=(ROOT/'tools/education_expansion.txt').read_text(encoding='utf-8').split('@@ ')[1:]
 result=[]
 for block in blocks:
  lines=block.strip().splitlines(); n,slug,title,desc,group,stages,subjects=lines[0].split('|')
  a=dict(expansionIndex=int(n),sourceIndex=29+int(n),slug=slug,title=title,description=desc,group=view.GROUPS[int(group)],stages=list(stages),subjects=subjects.split('·') if subjects else [],lead=lines[1],sections=[],task=None,faq=[],sources=[])
  for line in lines[2:]:
   if line.startswith('## '):a['sections'].append([line[3:],''])
   elif line.startswith('>> '):a['task']=[line[3:],[]]
   elif line.startswith('- '):a['task'][1].append(line[2:])
   elif line.startswith('?? '):a['faq'].append(line[3:].split('|'))
   elif line.strip():a['sections'][-1][1]+=line
  assert len(a['sections'])==6 and len(a['task'][1])==4 and len(a['faq'])==2, n
  assert len(desc)<=80 and desc.endswith('.') and all(len(p)>=80 for _,p in a['sections']),n
  if int(n) in REFERENCES:a['sources']=[REFERENCES[int(n)][1]]
  a['route']='/교육정보/'+slug+'/'
  result.append(a)
 assert len(result)==30 and len({a['route'] for a in result})==30
 return result

def recommend(articles,context,name,limit=3):
 stage=context.get('stage'); subject=context.get('subject')
 def allowed(a):
  return (not stage or stage in a['stages']) and (not subject or not a['subjects'] or subject in a['subjects'])
 pool=[a for a in articles if allowed(a)]
 # Subject pages always include one topic directly addressing that subject.
 seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
 fresh=[a for a in pool if a.get('expansionIndex')]; prior=[a for a in pool if not a.get('expansionIndex')]
 rotate=lambda xs: xs[seed%len(xs):]+xs[:seed%len(xs)] if xs else []
 result=rotate([a for a in fresh if subject in a['subjects']])[:1] if subject else []
 for a in rotate(fresh)+rotate(prior):
  if a not in result:result.append(a)
  if len(result)==limit:break
 assert len(result)==limit
 return result

def article(a,all_articles):
 tags=[a['group'],'·'.join({'초':'초등','중':'중등','고':'고등'}[s] for s in a['stages'])]
 body='<section class="ei-hero"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h1>'+ui.e(a['title'])+'</h1><p>'+ui.e(a['lead'])+'</p><div class="ei-tags">'+''.join('<span>'+ui.e(t)+'</span>' for t in tags)+'</div>'+view.actions([('/교육정보/','교육정보 목록'),('#local-learning','우리 지역 수업 찾기')])+'</section><div class="ei-reading">'
 toc=[('part-'+str(i),h) for i,(h,_) in enumerate(a['sections'],1)]+[('practice',a['task'][0]),('questions','자주 묻는 질문'),('local-learning','우리 지역 수업과 지점')]
 body+='<details class="ei-toc" open><summary>이 글에서 확인할 내용</summary><ol>'+''.join('<li>'+ui.link('#'+id,h)+'</li>' for id,h in toc)+'</ol></details>'
 for i,(h,p) in enumerate(a['sections'],1):
  sentences=re.split(r'(?<=\.) ',p);cut=max(1,len(sentences)//2)
  contents=''.join('<p>'+ui.e(t)+'</p>' for t in [' '.join(sentences[:cut]),' '.join(sentences[cut:])] if t)
  if a['expansionIndex'] in REFERENCES and REFERENCES[a['expansionIndex']][0]==i:
   label,url=SOURCES[REFERENCES[a['expansionIndex']][1]];contents+='<p class="ei-ref">참고: '+ui.link(url,label,True)+'</p>'
  body+=view.section('part-'+str(i),h,contents)
  if i in [2,4,6]:
   im=a['images'][i//2-1]
   body+='<figure class="ei-photo"><img src="'+im['src']+'" alt="'+ui.e(im['alt'])+'" width="'+str(im['width'])+'" height="'+str(im['height'])+'" loading="lazy" decoding="async"><figcaption>글의 이해를 돕는 소개용 이미지입니다.</figcaption></figure>'
 body+=view.section('practice',a['task'][0],'<ul>'+''.join('<li>'+ui.e(t)+'</li>' for t in a['task'][1])+'</ul>','ei-task')
 body+=view.section('questions','자주 묻는 질문',ui.faqs_markup(a['faq']))
 guide='영어독해근거찾기' if a['subjects']==['영어'] else '수학오답관리' if a['subjects']==['수학'] else '학습플래너작성법' if a['group']=='계획·시간 관리' else '학부모상담체크리스트' if a['group'] in ['학원·코칭','생활·학부모'] else '초등학생공부습관' if a['stages']==['초'] else '학습질문만들기'
 body+=view.section('more-help','공부 방법과 지역 정보를 이어서 살펴보세요',view.actions([('/학습가이드/'+guide+'/','관련 학습가이드'),('/교재안내/','영어·수학 교재 살펴보기'),('/선생님찾기/','지점별 선생님 소개'),('/지점안내/','지역별 지점 정보'),('/전국센터/','동네별 수업 안내')]))
 if a['sources']:body+=view.section('references','참고 자료','<ul class="ei-sources">'+''.join('<li>'+ui.link(SOURCES[k][1],SOURCES[k][0],True)+'</li>' for k in a['sources'])+'</ul>')
 others=sorted([b for b in all_articles if b['route']!=a['route']],key=lambda b:(b['group']!=a['group'],not bool(set(b['stages'])&set(a['stages'])),not bool(set(b['subjects'])&set(a['subjects'])),b['route']))[:3]
 body+=view.related(others,id='related-articles')+view.finder(ui.REGIONS)+'</div>'
 node={'@type':'Article','@id':ui.url(a['route'])+'#article','headline':a['title'],'description':a['description'],'inLanguage':'ko-KR','datePublished':DAY,'dateModified':DAY,'author':{'@type':'Organization','name':'전국수업.com','url':ui.url('/')},'publisher':{'@type':'Organization','name':'전국수업.com','url':ui.url('/')},'image':[ui.DOMAIN+im['src'] for im in a['images']],'mainEntityOfPage':{'@id':ui.url(a['route'])+'#webpage'},'articleSection':a['group'],'citation':[SOURCES[k][1] for k in a['sources']]}
 ui.shell(a['route'],a['title'],a['description'],body,[('교육정보','/교육정보/'),(a['title'],a['route'])],faqs=a['faq'],nodes=[node]);view.enrich_shell(a['route'].lstrip('/')+'index.html')

def hub(articles):
 count=len(articles);desc=f'시험 준비·공부 계획·과목별 복습·학부모 지도에 관한 교육정보 {count}편을 주제와 학년으로 찾고 실천 점검표를 읽습니다.'
 body='<section class="ei-hero"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h1>오늘의 공부 고민,<br>필요한 정보부터 찾아보세요</h1><p>영어 듣기가 막힐 때, 시험 계획이 밀릴 때, 아이에게 어떤 도움을 줄지 고민될 때 읽어 보세요. 글마다 공부 순서와 확인 질문을 담아 학생의 실천과 학부모의 대화를 돕습니다.</p>'+view.actions([('#article-list','교육정보 '+str(count)+'편 살펴보기',True),('/학습가이드/','학년·과목별 학습가이드'),('#local-learning','우리 지역 지점 찾기')])+'</section>'
 body+='<nav class="ei-groups" aria-label="교육정보 주제">'+''.join('<a href="#article-list" data-education-group="'+ui.e(g)+'">'+ui.e(g)+' <span>'+str(sum(a['group']==g for a in articles))+'</span></a>' for g in view.GROUPS)+'</nav>'
 body+='<form class="ei-filter" data-education-filter role="search"><label>궁금한 내용 검색<input name="q" type="search" placeholder="예: 영어 듣기, 기말고사, 학부모"></label><label>주제<select name="group"><option value="">모든 주제</option>'+''.join('<option>'+ui.e(g)+'</option>' for g in view.GROUPS)+'</select></label><label>대상<select name="stage"><option value="">모든 학년</option><option value="초">초등</option><option value="중">중등</option><option value="고">고등</option></select></label><button class="ei-btn" type="reset">전체 보기</button></form><p data-education-status role="status" aria-live="polite">'+str(count)+'개 교육정보 글이 있습니다.</p><noscript><p>검색 기능을 사용하지 않아도 아래에서 모든 글을 읽을 수 있습니다.</p></noscript><div class="ei-empty" data-education-empty hidden>검색한 글이 없습니다. 검색어를 줄이거나 다른 주제를 선택해 보세요.</div><section id="article-list" aria-label="교육정보 글 목록"><div class="ei-list">'+''.join(view.card(a) for a in articles)+'</div></section>'+view.finder(ui.REGIONS)
 node={'@type':'ItemList','@id':ui.url('/교육정보/')+'#articles','name':'학생과 학부모를 위한 교육정보','numberOfItems':count,'itemListElement':[{'@type':'ListItem','position':i,'name':a['title'],'url':ui.url(a['route'])} for i,a in enumerate(articles,1)]}
 ui.shell('/교육정보/','학생과 학부모를 위한 교육정보',desc,body,[('교육정보','/교육정보/')],nodes=[node],kind='CollectionPage');view.enrich_shell('교육정보/index.html')

def replace_block(text,kind,body):
 pattern=r'<!-- education-links:'+kind+r':start -->[\s\S]*?<!-- education-links:'+kind+':end -->'
 result,n=re.subn(pattern,lambda _:view.marked(kind,body),text)
 assert n==1,(kind,n)
 assert re.sub(pattern,'',text)==re.sub(pattern,'',result)
 return result

def refresh_manifest(baseline,names):
 public=dict(baseline['files']);normalized=dict(baseline['textSha256'])
 for name in names:
  raw=(ROOT/name).read_bytes();public[name]=hashlib.sha256(raw).hexdigest()
  if name.endswith(('.html','.css','.js','.mjs','.json','.xml','.txt','.svg')):normalized[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
 sitemap=etree.parse(str(ROOT/'sitemap.xml'))
 view.save(ROOT/'release-public-manifest.json',{**baseline,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':len(sitemap.getroot()),'files':dict(sorted(public.items())),'textSha256':dict(sorted(normalized.items()))})

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--refresh-only',action='store_true');args=ap.parse_args();out=args.audit
 baseline=view.load(out/'before-release-public-manifest.json')
 if args.refresh_only:
  audit=view.load(out/'upgrade-audit.json');refresh_manifest(baseline,audit['changedPublicFiles']);return
 previous=view.load(out/'before-education-info-data.json');selected=view.load(out/'source-selection.json');photos=view.load(out/'selected-images.json');fresh=read_articles()
 assert len(previous['articles'])==30 and len(photos)==90
 assert not any((ROOT/(a['route'].lstrip('/')+'index.html')).exists() for a in fresh),'Already published; use --refresh-only'
 snapshot=out/'before-source.zip'
 if not snapshot.exists():
  with zipfile.ZipFile(snapshot,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
   for name in baseline['files']:
    if name.endswith('.html'):z.writestr(name,(ROOT/name).read_bytes())
 assets=[];image_rows=[]
 for i,p in enumerate(photos):
  source=Path(p['file']);assert hashlib.sha256(source.read_bytes()).hexdigest()==p['sha256']
  dest='assets/education-info/learning-'+str(i+1).zfill(3)+'.webp';(ROOT/dest).parent.mkdir(parents=True,exist_ok=True)
  with Image.open(source) as original:
   im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((1200,1200),Image.Resampling.LANCZOS);im.save(ROOT/dest,'WEBP',quality=82,method=6)
   row=dict(src='/'+dest,alt=ALTS[i],width=im.width,height=im.height,sha256=hashlib.sha256((ROOT/dest).read_bytes()).hexdigest())
  image_rows.append(row);assets.append(dest)
 for i,a in enumerate(fresh):
  a['sourceTitle']=selected['pages'][i]['sourceTitle'];a['images']=image_rows[i*3:i*3+3]
  assert len({im['sha256'] for im in a['images']})==3,a['title']
 all_articles=fresh+previous['articles']
 for a in fresh:article(a,all_articles)
 hub(all_articles)
 modules=[];usage=Counter();changed=[]
 with zipfile.ZipFile(snapshot) as z:
  for item in previous['existingPages']:
   item=json.loads(json.dumps(item,ensure_ascii=False));name=item['file'];module=item['module']
   if not module:modules.append(item);continue
   old=z.read(name).decode('utf-8')
   if name=='index.html':
    featured=[next(a for a in fresh if a['group']==g) for g in view.GROUPS]
    body='<section class="ei-home" id="home-education" aria-labelledby="home-education-title"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h2 id="home-education-title">공부 계획부터 학원 선택까지</h2><p>영어 듣기와 시험 준비, 공부 습관과 학부모의 대화에서 지금 필요한 내용을 찾아보세요. 공부 순서와 실천 점검표를 담았습니다.</p><div class="ei-related-grid">'+''.join(ui.link(a['route'],a['title']) for a in featured)+'</div>'+view.actions([('/교육정보/','교육정보 '+str(len(all_articles))+'편 살펴보기',True)])+'</section>'
    text=replace_block(old,'home',body);module['links']=[a['route'] for a in featured]
   else:
    context=module['context'];featured=recommend(all_articles,context,name)
    title=(context.get('subject','')+' ' if context.get('subject') else '')+'공부와 수업 선택에 도움이 되는 교육정보'
    text=replace_block(old,'module',view.related(featured,title));module['links']=[a['route'] for a in featured]
   assert view.strip(old)==view.strip(text),name
   usage.update(module['links']);ui.write(ROOT/name,text);changed.append(name);modules.append(item)
 assert all(usage[a['route']]>0 for a in fresh)
 ns='http://www.sitemaps.org/schemas/sitemap/0.9';sitemap=etree.parse(str(out/'before-sitemap.xml')).getroot();seen={unquote(urlsplit(e.find('{'+ns+'}loc').text).path) for e in sitemap}
 for a in fresh:
  assert a['route'] not in seen;e=etree.SubElement(sitemap,'{'+ns+'}url');etree.SubElement(e,'{'+ns+'}loc').text=ui.url(a['route']);etree.SubElement(e,'{'+ns+'}lastmod').text=DAY
 modified={view.route(name) for name in changed}|{'/교육정보/'}
 for e in sitemap:
  if unquote(urlsplit(e.find('{'+ns+'}loc').text).path) in modified:
   date=e.find('{'+ns+'}lastmod')
   if date is None:date=etree.SubElement(e,'{'+ns+'}lastmod')
   date.text=DAY
 (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
 rss=etree.parse(str(out/'before-rss.xml')).getroot();channel=rss.find('channel');channel.find('lastBuildDate').text='Sun, 04 Oct 2026 00:00:00 +0900'
 for a in reversed(fresh):
  item=etree.Element('item');etree.SubElement(item,'title').text=a['title'];etree.SubElement(item,'link').text=ui.url(a['route']);etree.SubElement(item,'guid',isPermaLink='true').text=ui.url(a['route']);etree.SubElement(item,'description').text=a['description'];etree.SubElement(item,'pubDate').text='Sun, 04 Oct 2026 00:00:00 +0900';channel.insert(5,item)
 (ROOT/'rss.xml').write_bytes(etree.tostring(rss,encoding='utf-8',xml_declaration=True,pretty_print=True))
 llms=(out/'before-llms.txt').read_text(encoding='utf-8');llms+='\n\n## 공부와 학부모 지원 정보\n\n'+''.join('- '+a['title']+': '+ui.DOMAIN+a['route']+'\n' for a in fresh);ui.write(ROOT/'llms.txt',llms)
 view.save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
 shell=view.load(ROOT/'site-shell-data.json');shell['pages']=sorted(set(shell['pages'])|set(ui.NEW));view.save(ROOT/'site-shell-data.json',shell)
 report={**previous,'version':2,'selectedFolders':60,'articles':all_articles,'newPages':sorted(set(previous['newPages'])|set(ui.NEW)),'existingPages':modules,'images':previous['images']+image_rows,'expansion':{'date':DAY,'selectedFolders':30,'routes':[a['route'] for a in fresh]}}
 view.save(ROOT/'education-info-data.json',report)
 names=sorted(set(changed+ui.NEW+assets+['assets/education-info.css','assets/education-info.js','sitemap.xml','rss.xml','llms.txt']))
 audit={'date':DAY,'articlesAdded':len(fresh),'articleTotal':len(all_articles),'imagesAdded':len(assets),'sourceSeed':selected['seed'],'relatedModules':len(changed),'incomingLinks':dict(usage),'changedPublicFiles':names,'newRoutes':[a['route'] for a in fresh]}
 view.save(out/'upgrade-audit.json',audit);refresh_manifest(baseline,names)
 print(json.dumps({k:audit[k] for k in ['articlesAdded','articleTotal','imagesAdded','relatedModules']},ensure_ascii=False))

if __name__=='__main__':main()

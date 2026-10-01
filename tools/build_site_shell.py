"""Unify the site shell and expand the three reviewed official program guides."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
from html import escape
from urllib.parse import quote,unquote,urlsplit
from lxml import etree,html
import build_branch_upgrade as ui
ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-02'
NAV=[('홈','/'),('지점안내','/지점안내/'),('학습시스템','/학습시스템/'),('학습가이드','/학습가이드/'),('교재안내','/교재안내/'),('과목별학원','/과목별학원/'),('전국학원','/전국센터/'),('상담문의','/상담문의/')]
SOURCE={'와와학습코칭':'https://www.wawacenter.com/brand/wawacenter','개별맞춤관리':'https://www.wawacenter.com/intro/coachingSystem','AI학습':'https://www.wawacenter.com/intro/AISystem'}
DESCS={
 '/학습시스템/':'와와 공식 소개 영상과 학습코칭·개별 맞춤 관리·AI 프로그램을 살펴보고, 지점별 수업 조건과 상담 자료를 확인합니다.',
 '/학습시스템/와와학습코칭/':'와와 공식 영상과 개별 진도·학습코칭의 방향을 살펴보고, 아이의 공부 기록과 지점별 수업 조건을 확인합니다.',
 '/학습시스템/개별맞춤관리/':'계획·학습·생활 관리의 역할과 플래너·오답·백지노트 활용을 살펴보고, 학생별 피드백과 지점에서 확인할 질문을 정리합니다.',
 '/학습시스템/AI학습/':'AI 영어·수학·국어·독서의 공식 대상 학년과 학습 구성을 살펴보고, 진단·연습·기록의 활용 및 지점별 조건을 확인합니다.',
}
def href(p):return quote(p,safe='/#-')
def links(items):return '<div class="pg-links">'+''.join('<a href="'+href(p)+'">'+escape(t)+'</a>' for p,t in items)+'</div>'
def section(id,title,content,lead=''):
 return '<section class="pg-section" id="'+id+'" aria-labelledby="'+id+'-title"><h2 id="'+id+'-title">'+escape(title)+'</h2>'+('<p class="pg-lead">'+escape(lead)+'</p>' if lead else '')+content+'</section>'
def cards(rows,two=False):
 body='<div class="pg-grid'+(' pg-two' if two else '')+'">'
 for i,(h,p,items) in enumerate(rows,1):body+='<article class="pg-card"><span class="pg-number">'+f'{i:02}'+'</span><h3>'+escape(h)+'</h3><p>'+escape(p)+'</p>'+('<ul>'+''.join('<li>'+escape(x)+'</li>' for x in items)+'</ul>' if items else '')+'</article>'
 return body+'</div>'
def marked(kind,body):return '<!-- program-review:'+kind+':start -->'+body+'<!-- program-review:'+kind+':end -->'
def header(route):
 current=next((p for _,p in NAV[1:] if route.startswith(p)),'/' if route=='/' else None)
 menu=''.join('<a href="'+href(p)+'"'+(' aria-current="page"' if current==p else '')+(' data-directory-nav' if p=='/지점안내/' else '')+'>'+t+'</a>' for t,p in NAV)
 return '<header class="site-header" data-site-header="1"><div class="header-inner"><a class="brand" href="/" aria-label="전국수업.com 홈"><span class="brand-mark" aria-hidden="true">W</span><span class="brand-copy"><strong>전국수업.com</strong><small>와와센터 학습코칭</small></span></a><nav class="nav" aria-label="상단 메뉴">'+menu+'</nav><a class="header-cta" href="'+ui.FORM+'" target="_blank" rel="noopener noreferrer">상담 신청</a></div></header>'
def hero_end(s):
 start=re.search(r'<section\b[^>]*class="[^"]*(?:bd-hero|\bhero\b)[^"]*"[^>]*>',s);assert start
 depth=0
 for t in re.finditer(r'</?section\b[^>]*>',s[start.start():]):
  depth+=-1 if t.group().startswith('</') else 1
  if not depth:return start.start()+t.end()
 raise AssertionError('unclosed hero')
def add_after_hero(s,body):
 end=hero_end(s);return s[:end]+body+s[end:]
def add_before(s,id,body):
 m=re.search(r'<section\b[^>]*\bid="'+id+r'"[^>]*>',s);assert m,id
 return s[:m.start()]+body+s[m.start():]
def program_content(route,s):
 if route=='/학습시스템/':
  body=section('official-introduction','공식 영상으로 살펴보는 와와 학습코칭','<div class="pg-panel pg-video-grid"><div><h3>아이에게 필요한 관리부터 찾아보세요</h3><p>수업의 방향은 소개 영상으로, 구체적인 확인 항목은 아래 세 가지 안내로 살펴보세요.</p>'+links([('/학습시스템/와와학습코칭/','영상과 학습코칭 안내'),('/학습시스템/개별맞춤관리/','계획·학습·생활 관리'),('/학습시스템/AI학습/','과목별 AI 학습 구성')])+'</div><div>'+ui.video('59Tna9pZWrk','와와학습코칭센터 공식 소개')+'</div></div>')
  return add_after_hero(s,marked('hub',body))
 if route=='/학습시스템/와와학습코칭/':
  body=section('individual-study','같은 학년이어도 공부할 내용은 다를 수 있습니다',cards([
   ('개별 진도와 설명','브랜드는 학생의 현재 학습 상태에 맞춰 진도와 설명을 연결하는 방향을 안내합니다. 같은 교재를 쓰는지보다 어떤 부분을 혼자 해결하고 어디서 도움받는지 함께 살펴보세요.',[]),
   ('공부 방법을 익히는 코칭','문제를 완료한 뒤 계획·실행·점검을 돌아보는 과정을 생각해 보세요. 다음 공부를 학생이 설명할 수 있는지 기록하면 상담 질문을 구체화하기 좋습니다.',[]),
   ('지점에서 확인할 수업 구성','브랜드의 공통 설명과 실제 등록 조건은 구분해 확인하세요. 과목별 학년, 지도 방식, 시간과 교육비를 희망 지점의 자료에서 함께 살펴볼 수 있습니다.',[]),
  ]))
  body+=section('family-check','학생의 기록으로 수업을 비교해 보세요','<div class="pg-panel"><p>최근 풀이·학교 자료·주간 일정을 준비하고, 혼자 한 부분과 설명이 필요한 부분을 표시해 보세요. 첫 목표와 다시 확인할 자료가 무엇인지 상담에서 물어볼 수 있습니다.</p>'+links([('/학습시스템/개별맞춤관리/','관리 항목 자세히 보기'),('/학습가이드/학부모상담체크리스트/','상담 준비 자료'),('/지점안내/','지점별 수업·교육비 확인')])+'</div>')
  return add_before(s,'flow',marked('brand',body))
 if route=='/학습시스템/개별맞춤관리/':
  body=section('management-areas','계획·학습·생활, 관리의 역할을 나누어 보세요',cards([
   ('플랜 관리: 가능한 계획 세우기','공식 안내는 학생과 목표·우선순위를 정하고 시간과 분량을 관리하는 과정을 설명합니다. 계획한 과제와 실제 한 결과를 나란히 놓아 보세요.',['오늘 확인할 목표','혼자 공부할 수 있는 시간','끝낸 범위와 다음 수정']),
   ('학습 관리: 막힌 단계 찾기','학생의 이해에 맞춘 교재와 공부 방법, 오답노트·백지노트·마인드맵 등의 도구를 다룹니다. 기록 방식은 필요한 내용을 확인하는 데 맞춰 고를 수 있습니다.',['틀린 원인과 중간 풀이','답을 가리고 설명한 내용','관련 개념을 연결한 기록']),
   ('생활 관리: 공부 밖의 조건 살피기','공식 설명에는 학생·학부모와의 소통을 통해 습관과 생활 리듬을 함께 살피는 내용이 있습니다. 학교 일정과 과제 부담을 공부 기록과 함께 이야기해 보세요.',['귀가·휴식·학교 일정','계속 남는 과제의 이유','필요한 도움과 공유 방식']),
  ]))
  body+=section('learning-space','공부 공간과 선생님의 역할도 확인하세요','<div class="pg-panel"><p>공식 안내의 ‘둥지 시스템’은 학생들이 선생님을 중심으로 공부하는 구조를 설명합니다. 개별 진도 안내를 항상 일대일 수업으로 읽기보다, 희망 지점의 실제 인원과 설명·질문 시간을 확인해 주세요.</p>'+links([('/지점안내/','지점별 사진·방문 정보'),('/학습가이드/학습질문만들기/','질문을 준비하는 방법')])+'</div>')
  body+=section('study-tools','학습 도구는 어떤 확인에 쓰는지 살펴보세요',cards([
   ('오답노트','틀린 줄과 이유, 다시 풀 결과를 함께 남깁니다. 답을 베껴 적은 것과 혼자 다시 해결한 것을 구분해 보세요.',[]),
   ('백지노트','보지 않고 꺼내 본 개념과 설명을 남기고, 빠진 부분을 원자료와 대조해 보세요.',[]),
   ('마인드맵','중심 개념과 연결한 개념의 관계를 짧게 설명해 보세요. 보기 좋은 그림보다 연결의 이유를 확인할 자료가 됩니다.',[]),
  ]))+links([('/학습가이드/수학오답관리/','수학 오답 복습'),('/학습가이드/인출연습과간격복습/','답을 보지 않는 복습'),('/학습가이드/학습대화방법/','학생과 공부 대화하기')])
  return add_before(s,'planner',marked('management',body))
 if route=='/학습시스템/AI학습/':
  notice='<p class="pg-scope">아래는 공식 프로그램의 설명입니다. 실제 도입 여부·개설 과목·등록 학년·교재와 추가 비용은 지점별로 확인해 주세요.</p>'
  body=section('ai-english','AI 영어: 소리·문장·읽기·듣기를 연결하기','<div class="pg-panel"><span class="pg-range">공식 대상 범위 · 초1~고3</span><p>초등 구성은 파닉스와 영역별 온라인 학습, AI 말하기 연습·워크북을 연결합니다. 중·고등 구성은 독해·구문·듣기·교과서 기반 학습을 다룹니다.</p>'+links([('/교재안내/초등영어/','초등 영어 교재 비교'),('/교재안내/중등영어/','중등 영어 교재 비교'),('/교재안내/고등영어/','고등 영어 교재 비교')])+'</div>')
  body+=section('ai-math','AI 수학: 성취도와 오답을 다음 문제에 반영하기','<div class="pg-panel"><span class="pg-range">공식 대상 범위 · 초1~고3</span><p>성취도에 맞춘 문제·시험지 구성, 오답 클리닉과 유사·변형 문제 연습을 설명합니다. 종이 교재와 앱의 연결도 안내하므로 사용 방식은 희망 지점에서 확인하세요.</p>'+links([('/학습가이드/수학오답관리/','오답 기록과 재풀이'),('/교재안내/','학년별 수학 교재 찾기')])+'</div>')
  body+=section('ai-korean','AI 국어: 읽은 근거와 취약 영역을 확인하기','<div class="pg-panel"><span class="pg-range">공식 대상 범위 · 중1~고3</span><p>독서·문학·문법, 어휘·어법과 학교 자료에 맞춘 연습을 다룹니다. 분석 결과와 맞춤 문제·해설을 학생의 실제 답안과 함께 살펴보세요.</p>'+links([('/학습가이드/국어비문학읽기/','국어 비문학 읽기'),('/학습가이드/국어서술형답안/','국어 서술형 답안 점검')])+'</div>')
  body+=section('ai-reading','AI 독서: 책 선택과 활동 기록을 연결하기','<div class="pg-panel"><span class="pg-range">공식 대상 범위 · 초1~중2</span><p>읽기 지수와 진로·흥미 검사를 활용한 도서 추천, 독서 활동 기록과 포트폴리오를 안내합니다. 읽은 양과 내용을 설명한 기록을 함께 볼 수 있습니다.</p>'+links([('/학습가이드/독서내용요약/','읽은 내용 요약하기'),('/학습가이드/학습변화기록/','학습 변화 기록하기')])+'</div>')
  return add_before(s,'use',marked('ai',notice+body))
 return s

def update_description(s,route,catalog):
 if route not in DESCS:return s
 desc=DESCS[route];assert len(desc)<=80 and desc.endswith('.')
 for attr,value in [('name','description'),('property','og:description'),('name','twitter:description')]:
  pattern=r'(<meta '+attr+'="'+value+r'" content=")[^"]*(")';s,count=re.subn(pattern,lambda m:m[1]+escape(desc,quote=True)+m[2],s,count=1);assert count==1
 m=re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>',s);graph=json.loads(m[1]);graph['@graph'][0]['description']=desc;graph['@graph'][0]['dateModified']=DAY
 s=s[:m.start(1)]+ui.j(graph)+s[m.end(1):]
 item=catalog['pages'][route.rstrip('/')];item['description']=desc;item['sources']=list(dict.fromkeys([*item.get('sources',[]),desc]))
 return s

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args();before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 catalog=json.loads((ROOT/'seo-descriptions.json').read_text(encoding='utf-8-sig'))
 pages=[]
 with zipfile.ZipFile(args.audit/'before-source.zip') as archive:
  for name in before['files']:
   if not name.endswith('.html'):continue
   s=archive.read(name).decode('utf-8');route='/'+name.removesuffix('index.html');route='/' if name=='index.html' else route
   s,count=re.subn(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:header(route),s,count=1);assert count==1,name
   s,count=re.subn(r'<body\b([^>]*)>',lambda m:'<body'+m[1]+' data-site-shell="1">',s,count=1);assert count==1
   s=s.replace('</head>','<link rel="stylesheet" href="/assets/site-shell.css"></head>',1)
   if route.startswith('/학습시스템/'):
    s=program_content(route,s)
    if route!='/학습시스템/':
     jumps=[('official-video','공식 소개 영상'),('individual-study','개별 진도와 코칭')] if route.endswith('/와와학습코칭/') else [('management-areas','계획·학습·생활'),('study-tools','학습 도구')] if route.endswith('/개별맞춤관리/') else [('ai-english','AI 영어'),('ai-math','AI 수학'),('ai-korean','AI 국어'),('ai-reading','AI 독서')]
     jump='<nav class="pg-jump" aria-label="학습시스템 내용 바로가기">'+''.join('<a href="#'+id+'">'+t+'</a>' for id,t in jumps)+'</nav>'
     s=add_after_hero(s,marked('jump',jump))
    s=update_description(s,route,catalog)
   if name=='index.html':
    jump='<nav class="pg-jump pg-home-links" aria-label="와와 소개와 학습시스템 바로가기"><a href="'+href('/학습시스템/와와학습코칭/#official-video')+'">와와 공식 소개 영상</a><a href="'+href('/학습시스템/개별맞춤관리/')+'">개별 맞춤 관리</a><a href="'+href('/학습시스템/AI학습/')+'">AI 학습 구성</a></nav>'
    # Keep the existing home hero and conversion content in their current order.
    m=re.search(r'<nav class="hl-jump"[\s\S]*?</nav>',s);assert m
    s=s[:m.end()]+marked('home',jump)+s[m.end():]
   b=s.encode('utf-8');p=ROOT/name
   if p.read_bytes()!=b:p.write_bytes(b)
   pages.append(name)
  # Only the content-expanded hub and guides get a new sitemap content date.
  sitemap=etree.fromstring(archive.read('sitemap.xml'));ns='http://www.sitemaps.org/schemas/sitemap/0.9'
  for u in sitemap:
   route=unquote(urlsplit(u.find('{'+ns+'}loc').text).path)
   if route in DESCS or route=='/':u.find('{'+ns+'}lastmod').text=DAY
  (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
 ui.save(ROOT/'seo-descriptions.json',catalog)
 selected=set(before['files'])|{'assets/site-shell.css'};files=dict(before['files']);text_hashes=dict(before['textSha256'])
 for name in pages+['assets/site-shell.css','sitemap.xml']:
  b=(ROOT/name).read_bytes();files[name]=hashlib.sha256(b).hexdigest();text_hashes[name]=hashlib.sha256(b.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
 ui.save(ROOT/'release-public-manifest.json',{**before,'createdAt':'2026-10-02T00:00:00+09:00','files':dict(sorted(files.items())),'textSha256':dict(sorted(text_hashes.items()))})
 ui.save(ROOT/'site-shell-data.json',{'version':1,'reviewed':DAY,'nav':NAV,'pages':pages,'sources':SOURCE,'descriptions':DESCS,'videoIds':['59Tna9pZWrk','avpJfW7eIV0','f_skFu40U04','UIXUaBZdNXU'],'aiRanges':{'영어':'초1~고3','수학':'초1~고3','국어':'중1~고3','독서':'초1~중2'}})
 report={'unifiedPages':len(pages),'programPages':4,'publicFiles':len(selected),'sitemapPages':before['sitemapPages'],'newUrls':0,'deployed':False};ui.save(args.audit/'generation-summary.json',report);print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()

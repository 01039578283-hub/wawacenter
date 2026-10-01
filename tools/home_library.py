"""Add a compact, visible path from the homepage to academy and education content."""
import json,re
import build_branch_upgrade as ui
TOPICS=[
 ('/지점안내/','우리 동네 지점 찾기','주소·과목별 학년·교육비 자료·사진을 보고 방문할 지점을 확인하세요.','지점 안내 보기','학원 찾기'),
 ('/학습시스템/','학습코칭 알아보기','진단·계획·학습 점검과 AI 학습을 어떤 순서로 살펴볼지 정리했습니다.','학습 방식 살펴보기','학원 정보'),
 ('/학습가이드/','학생·학부모 학습가이드','시험 준비, 과목별 공부, 공부 습관과 학부모 상담에 필요한 글을 모았습니다.','학습가이드 40편 읽기','교육 정보'),
 ('/교재안내/','영어·수학 교재 찾기','초·중·고 120종의 학습 영역과 권·단계 조건을 비교하고 교재의 역할을 정하세요.','교재 검색·비교하기','교재 선택'),
 ('/과목별학원/','학년·과목별 수업 안내','영어·수학·국어 안내에서 학년별로 확인할 학습 내용과 수업 질문을 살펴보세요.','학년·과목 안내 보기','수업 선택'),
 ('/상담문의/','상담 전 준비하기','최근 학습 자료와 궁금한 점을 정리하고 상담 흐름과 신청 방법을 확인하세요.','상담 준비 확인하기','학부모 준비'),
]
GROUPS=[
 ('학년과 시험 준비','현재 학년에서 확인할 공부와 학교의 평가 범위를 연결하세요.',[
  ('초등학생공부습관','초등학생 공부 습관'),('중학생내신공부법','중학생 내신 공부법'),('고등학생과목별공부법','고등학생 과목별 공부 계획'),('시험4주학습계획','시험 4주 학습 계획')]),
 ('과목별 공부와 복습','틀린 원인과 읽기의 근거를 찾아 다음 과제를 정해 보세요.',[
  ('수학오답관리','수학 오답 관리'),('영어문장구조읽기','영어 문장 구조 읽기'),('국어비문학읽기','국어 비문학 읽기'),('학습플래너작성법','학습 플래너 작성법')]),
 ('학부모의 수업 선택과 대화','상담에서 묻고 비교할 항목을 같은 기준으로 확인하세요.',[
  ('학원수업비교','학원 수업 비교'),('교육비확인','교육비 확인'),('학부모상담체크리스트','학부모 상담 체크리스트'),('학습대화방법','공부 대화 방법')]),
]
def enhance(root):
 file=root/'index.html';source=file.read_text(encoding='utf-8')
 source=re.sub(r'<!-- home-library:([a-z]+):start -->[\s\S]*?<!-- home-library:\1:end -->','',source)
 styles='<!-- home-library:styles:start --><link rel="stylesheet" href="/assets/home-library.css"><!-- home-library:styles:end -->'
 source=source.replace('</head>',styles+'</head>')
 jump='<!-- home-library:jump:start --><nav class="hl-jump" aria-label="학원·학습 정보 바로가기">'+ui.link('#home-library','학원·학습 자료 한눈에 보기 ↓')+ui.link('#home-reading','주제별 교육 정보글 읽기 ↓')+'</nav><!-- home-library:jump:end -->'
 anchor='        <div class="hero-points" aria-label="핵심 안내">'
 assert source.count(anchor)==1;source=source.replace(anchor,jump+'\n'+anchor)
 cards=''.join('<a class="hl-card" data-home-topic href="'+ui.href(route)+'"><span class="hl-label">'+ui.e(label)+'</span><h3>'+ui.e(title)+'</h3><p>'+ui.e(desc)+'</p><span class="hl-card-action">'+ui.e(action)+' <span aria-hidden="true">→</span></span></a>' for route,title,desc,action,label in TOPICS)
 groups=''.join('<section class="hl-group" aria-labelledby="home-group-'+str(i)+'"><h3 id="home-group-'+str(i)+'">'+ui.e(title)+'</h3><p>'+ui.e(desc)+'</p><ul>'+''.join('<li><a data-home-reading href="'+ui.href('/학습가이드/'+slug+'/')+'">'+ui.e(label)+' <span aria-hidden="true">→</span></a></li>' for slug,label in links)+'</ul></section>' for i,(title,desc,links) in enumerate(GROUPS,1))
 entry='<!-- home-library:content:start --><section class="home-library" id="home-library" aria-labelledby="home-library-title"><div class="hl-heading"><p class="eyebrow">학원 안내 · 교육 정보 · 교재 선택</p><h2 id="home-library-title">필요한 정보를 한곳에서 찾아보세요</h2><p>학원을 알아보는 중이라면 지점과 수업부터, 공부 방법이 궁금하다면 학습가이드와 교재 안내부터 살펴보세요.</p></div><nav class="hl-topic-grid" aria-label="주제별 정보 페이지">'+cards+'</nav><section class="hl-reading" id="home-reading" aria-labelledby="home-reading-title"><div class="hl-reading-heading"><h2 id="home-reading-title">지금 고민에 맞는 교육 정보글</h2>'+ui.link('/학습가이드/','학습가이드 40편 전체 보기 →')+'</div><div class="hl-reading-grid">'+groups+'</div></section></section><!-- home-library:content:end -->'
 marker='    <div class="metric-row" aria-label="학습코칭 핵심 관리">'
 assert source.count(marker)==1;source=source.replace(marker,entry+'\n'+marker)
 listed=[{'route':route,'title':title} for route,title,*_ in TOPICS]+[{'route':'/학습가이드/'+slug+'/','title':label} for _,_,links in GROUPS for slug,label in links]
 node={'@context':'https://schema.org','@type':'ItemList','@id':ui.url('/')+'#home-library-list','name':'학원 안내와 교육 정보','numberOfItems':len(listed),'itemListElement':[{'@type':'ListItem','position':i,'name':p['title'],'url':ui.url(p['route'])} for i,p in enumerate(listed,1)]}
 schema='<!-- home-library:schema:start --><script type="application/ld+json">'+ui.j(node)+'</script><!-- home-library:schema:end -->'
 source=source.replace('</head>',schema+'</head>').replace('"dateModified":"2026-09-28"','"dateModified":"'+ui.DAY+'"')
 ui.write(file,source);ui.save(root/'home-library-data.json',{'updated':ui.DAY,'topics':[{'route':r,'title':t,'description':d,'action':a,'label':l} for r,t,d,a,l in TOPICS],'readingGroups':GROUPS,'listedPages':listed})

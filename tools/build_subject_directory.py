"""Render grade/subject children and enrich every actual branch-directory parent."""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import unquote,urlsplit,quote
from concurrent.futures import ThreadPoolExecutor
from lxml import etree
import build_branch_upgrade as ui
from grade_editorial import STAGE_GUIDES
from subject_editorial import BY_ID,UNITS,SUMMARY_TOPICS
from branch_maps import insert_map
ROOT=ui.ROOT
DATA=json.loads((ROOT/'subject-directory-data.json').read_text(encoding='utf-8'))
PAGES=DATA['pages'];BRANCHES={b['route']:b for b in ui.BRANCHES}
GRADES=json.loads((ROOT/'grade-directory-data.json').read_text(encoding='utf-8'))['pages']
LABELS={'초':'초등학생학원','중':'중학생학원','고':'고등학생학원'}
NAMES={'초':'초등학생','중':'중학생','고':'고등학생'}
e,link,section=ui.e,ui.link,ui.section

def overview(p):
 c=p['course'];scope=ui.grade_label(c['grades']) or '개설 학년 확인 필요'
 return scope+(' · 별도 확인 '+ui.grade_label(c['pending']) if c['pending'] else '')

def child_card(p):
 b=BRANCHES[p['branch']];focus=BY_ID[p['topics'][0]][3]
 return '<article class="bd-card sd-choice"><p class="bd-kicker">'+e(b['name']+' · '+NAMES[p['stage']])+'</p><h3>'+link(p['route'],p['areas'][0]['name']+' '+NAMES[p['stage']]+' '+p['subject']+'학원 안내')+'</h3><p>'+e(overview(p))+'</p><p>'+e(focus)+'</p>'+link(p['route'],'학습 점검·교육비·상담 질문 보기 →')+'</article>'

def child_description(p):
 b=BRANCHES[p['branch']];topic=SUMMARY_TOPICS[p['topics'][0]]
 desc=f'{b["region"]} {p["areas"][0]["name"]} {b["name"]} {NAMES[p["stage"]]} {p["subject"]}학원의 안내 학년·교육비와 {topic} 점검 방법을 확인합니다.'
 if len(desc)>80:desc=f'{p["areas"][0]["name"]} {b["name"]} {NAMES[p["stage"]]} {p["subject"]}학원의 안내 학년·교육비와 {topic} 점검 방법을 확인합니다.'
 assert len(desc)<=80,desc
 return desc

def grade_description(p):
 b=BRANCHES[p['branch']];topic=SUMMARY_TOPICS[p['topics'][0]]
 desc=f'{p["name"]} {NAMES[p["prefix"]]} 학원 선택을 위해 {b["name"]}의 과목별 학년·교육비·학교 자료와 {topic} 상담 기준을 확인합니다.'
 assert len(desc)<=80,desc
 return desc

def child(p):
 b=BRANCHES[p['branch']];stage=NAMES[p['stage']];subject=p['subject'];c=p['course'];focus=BY_ID[p['topics'][0]]
 desc=child_description(p)
 title=f'{b["region"]} '+('·'.join(a['name'] for a in p['areas'][:2]))+f' {stage} {subject}학원 | {b["name"]} 학습 점검·교육비'
 areas=' · '.join(a['name'] for a in p['areas'])
 hero=f'<section class="bd-hero"><p class="bd-kicker">{e(b["region"])} · {e(b["district"])} / {stage} {subject}</p><h1>{e(p["name"])} {stage}<br>{subject}학원 선택과 학습 안내</h1><p>{e(areas)}에서 {stage} {subject} 수업을 찾는 가정을 위해, <strong>{e(focus[3])}</strong>부터 살펴볼 질문을 정리했습니다. 연결 지점은 {e(b["name"])}입니다. 학생의 현재 자료와 아래 지점 정보를 함께 비교해 보세요.</p><p class="gd-answer"><strong>{e(b["displayName"])}</strong><br>{e(b["address"])}</p>'+ui.actions([(ui.FORM,stage+' '+subject+' 상담 신청',True,True),(p['parent'],p['name']+' '+stage+' 과목 전체 안내')])+'</section>'
 jump='<nav class="bd-jump" aria-label="과목 안내 바로가기">'+''.join(link('#'+k,n) for k,n in [('lesson-image','상세 이미지'),('subject-course','안내 학년'),('learning','학습 점검'),('local-focus','동네별 질문'),('fees','교육비'),('schools','학교·위치'),('faq','질문')])+'</nav>'
 image=b['bodyImage'];picture=f'<div class="bd-image-panel"><picture><source media="(max-width:800px)" srcset="{ui.href(image["mobile"])}"><img src="{ui.href(image["src"])}" width="918" height="16116" loading="eager" decoding="async" alt="와와 학습코칭의 수업과 학습 관리 상세 안내"></picture></div>'
 body=hero+jump+section('lesson-image','학습코칭 수업을 자세히 살펴보세요',picture,'공통 수업 안내입니다. 이 지점의 과목별 학년과 수강 조건은 아래에서 따로 확인해 주세요.')
 course=f'<article class="bd-card" data-subject-course="{subject}" data-grades="{e(",".join(c["grades"]))}" data-pending="{e(",".join(c["pending"]))}"><h3>{e(b["name"])} {stage} {subject}</h3><div class="bd-grade">{e(ui.grade_label(c["grades"]) or "개설 학년 확인 필요")}</div>'
 if not c['grades']:course+='<p class="bd-pending">제공 자료만으로 이 학년의 '+subject+' 개설 여부를 확정하지 못했습니다. 현재 등록 가능 여부를 지점에서 확인해 주세요.</p>'
 if c['pending']:course+='<p class="bd-pending">별도 확인 학년: '+e(ui.grade_label(c['pending']))+'. 표와 운영 조건을 함께 확인해 주세요.</p>'
 course+=''.join('<p class="bd-course-note">'+e(n)+'</p>' for n in c['notes'])+'</article>'
 course+=''.join('<p class="bd-notice">'+e(n)+'</p>' for n in p['courseNotes'])
 body+=section('subject-course',b['name']+' '+stage+' '+subject+' 안내 학년과 조건',course,'자료상 안내 범위입니다. 상담 가능 여부와 모집 상태·시간표는 별도로 확인해야 합니다.')
 body+=section('learning',stage+' '+subject+' 상담에서 먼저 확인할 것',f'<p class="gd-answer">{e(areas)}의 {stage} {subject} 상담은 '+link('#learning-'+focus[0],focus[3])+'부터 살펴볼 수 있습니다. 현재 교재에서 혼자 해결한 부분과 설명이 필요한 부분을 표시해 준비해 주세요.</p><p>아래 내용은 학생의 학습을 살펴보는 방법과 수업을 비교할 질문입니다. 지점에서 모든 과정을 운영한다는 뜻은 아니며 실제 지도 방식은 상담에서 확인해 주세요.</p>')
 for i,key in enumerate(p['topics'],1):
  t=BY_ID[key]
  topic='<p>'+e(t[5])+'</p><div class="sd-task"><h3>학생 자료에서 해 볼 점검</h3><p>'+e(t[6])+'</p></div><p class="sd-question"><strong>상담에서 물어볼 질문</strong><br>'+e(t[7])+'</p>'
  body+=section('learning-'+key,t[3],topic,class_name='sd-editorial') .replace('<section ',f'<section data-subject-topic="{key}" ',1)
 units='<div class="sd-unit-list">'+''.join('<article class="bd-card"><h3>'+e(h)+'</h3><p>'+e(copy)+'</p></article>' for h,copy in UNITS[p['stage'],subject])+'</div>'
 body+=section('stage-process',stage+' '+subject+'의 영역별 점검',units,'학생이 현재 배우는 범위에 해당하는 항목부터 살펴보세요. 아래 영역 목록은 이 지점의 개설 과정표가 아닙니다.')
 local=''
 for a in p['areas']:
  picks=[BY_ID[k] for k in a['topics'][:3]]
  local+='<article class="bd-card sd-area" data-subject-area="'+e(a['slug'])+'"><h3>'+e(a['name'])+'에서 준비하는 '+stage+' '+subject+' 상담</h3><p>학교 참고 정보: '+e(' · '.join(a['schools']) or '제공 자료에 이 학년의 학교명이 없습니다.')+'</p><ul>'+''.join('<li><strong>'+e(t[3])+'</strong><br>'+e(t[7])+'</li>' for t in picks)+'</ul></article>'
 body+=section('local-focus',p['name']+' 학교 자료와 학습 질문',local,'이 동네의 원고에서 확인한 학습 고민을 상담 준비 항목으로 정리했습니다. 학교명은 제휴·재원 학생·학교별 전용반을 나타내지 않습니다.')
 body+=section('weekly-plan',subject+' 복습과 다른 과목의 일정을 맞추기','<div class="bd-card"><h3>한 주의 실제 시간부터 적어 보세요</h3><p>'+e('초등학생은 학교 활동과 귀가 후 쉬는 시간까지 함께 적고, 짧게 혼자 해 볼 과제를 먼저 골라 보세요.' if p['stage']=='초' else '학교 수업·과제·평가 일정을 먼저 적고, 새 진도와 오답 복습에 쓸 시간을 따로 확보할 수 있는지 확인하세요.')+'</p><p>'+e(subject)+'에서는 '+e('어휘를 떠올리는 시간과 문장을 읽고 쓰는 시간' if subject=='영어' else '개념을 설명하는 시간과 문제를 풀고 검토하는 시간')+'을 나누어 적으면 미완료 이유를 구체적으로 상담하기 좋습니다. 실제 요일과 횟수는 지점에서 확인해 주세요.</p></div>')
 checklist=['현재 교재와 최근에 배운 범위','정답을 지우지 않은 최근 오답과 중간 기록','학교에서 받은 진도·평가·과제 안내','혼자 공부할 수 있는 요일과 과제 부담','희망 과목·학년 및 수업 구성에 관한 질문']
 body+=section('consultation',b['name']+' '+stage+' '+subject+' 상담 준비 목록','<ol class="sd-checklist">'+''.join('<li>'+e(x)+'</li>' for x in checklist)+'</ol><p>점수만 전달하기보다 혼자 한 부분과 도움받은 부분을 표시해 주세요. 진단 결과에 따라 무엇을 먼저 복습할지, 다음 확인 자료는 무엇인지 질문할 수 있습니다.</p>')
 body+=section('fees',b['name']+' 교육비 자료와 '+subject+' 수업 구성', '<p>'+e(stage)+' '+subject+'에 해당하는 행과 횟수·시간을 함께 확인하세요. 다른 과목 또는 추가 프로그램을 포함한 표도 있으므로 한 과목의 확정 금액으로 읽지 않아야 합니다.</p>'+ui.tables(b))
 schoolcard='<article class="bd-card"><h3>'+stage+' 학교 참고 정보</h3><p data-stage-schools>'+e(' · '.join(p['schools']) or '제공 자료에 이 학년의 학교명이 없습니다.')+'</p><p>학생이 실제로 받은 교과서·배부 자료·평가 안내를 준비해 주세요. 학교별 시험 방식이나 재원 현황을 학교명만으로 판단할 수는 없습니다.</p></article>'
 location='<article class="bd-card"><h3>'+e(b['name'])+' 실제 방문 정보</h3><dl class="bd-facts"><div><dt>주소</dt><dd>'+e(b['address'])+'</dd></div><div><dt>등록 학원명</dt><dd>'+e(b['registeredName'])+'</dd></div><div><dt>등록번호</dt><dd>'+e(b['registration'])+'</dd></div></dl>'+link('https://map.naver.com/p/search/'+quote(b['address'],safe=''),'네이버 지도에서 주소 확인',True)+'<p>연결 동네와 실제 소재지는 다를 수 있습니다. 출발 위치에서 하교·식사·귀가까지 포함한 이동 시간을 직접 확인해 주세요.</p></article>'
 if b['addressPending']:location+='<p class="bd-notice">주소 자료가 서로 달라 방문 전 현재 위치를 확인해야 합니다.</p>'
 body+=section('schools','학교 자료와 실제 등원 위치','<div class="bd-grid bd-two">'+schoolcard+location+'</div><p>'+link(b['route']+'#photos',b['name']+' 제공 사진과 공간 안내 확인')+'</p>')
 faq=[(b['name']+'에서 '+stage+' '+subject+' 수업을 등록할 수 있나요?', '제공 자료의 '+subject+' 안내 범위는 '+overview(p)+('입니다. ' if c['grades'] else '입니다. 자료가 비어 있어 수업이 없다고 단정할 수는 없습니다. ')+'현재 모집 여부와 수업 시간, 별도 조건은 지점에서 확인해 주세요.'),(b['name']+' '+subject+' 수업료는 어디서 확인하나요?', '위 교육비 표와 연결된 '+b['name']+' 교습비 자료에서 학년·과목·횟수·시간을 함께 확인하세요. 공통 참고 금액은 지점의 확정 수강료가 아니며, 교재와 추가 프로그램의 포함 여부도 상담해야 합니다.'),(stage+' '+subject+' 상담에는 무엇을 가져가면 좋나요?',focus[6]+' 현재 교재와 최근 오답, 실제 학교 자료를 함께 준비하면 시작 범위와 다음 확인 방법을 구체적으로 상담할 수 있습니다.'),(p['areas'][0]['name']+' 페이지의 학교명은 전용반을 뜻하나요?','학교명은 제공 자료의 상담 참고 정보입니다. 제휴·재원 학생·학교별 전용반을 뜻하지 않습니다. 학교 진도와 준비 범위는 학생이 직접 받은 자료로 확인해 주세요.'),('틀린 문제를 다시 맞히면 복습이 끝난 건가요?','답을 기억해 맞힌 것인지, 조건을 설명하고 풀이를 다시 만든 것인지 구분해 보세요. 새 조건에서도 적용할 수 있는지와 다음 확인 시점은 상담에서 물어볼 기준입니다. 결과나 성적 변화를 보장하는 설명은 아닙니다.'),('학습코칭 이미지의 과정이 모두 '+b['name']+'에서 운영되나요?','이미지는 공통 안내입니다. 이 페이지의 '+subject+' 과목별 학년과 조건을 우선 확인하고, 실제 교재·인원·지도 방식·추가 프로그램 사용 여부는 지점에 문의해 주세요.')]
 body+=section('faq',b['name']+' '+stage+' '+subject+' 자주 묻는 질문',ui.faqs_markup(faq))
 siblings=[x for x in PAGES if x['area']==p['area'] and (x['stage']==p['stage'] or x['subject']==subject) and x['route']!=p['route']]
 body+=section('related','같은 지점의 과목과 학년을 이어서 보기','<div class="bd-grid sd-choice-grid">'+''.join(child_card(x) for x in siblings)+'</div><p>'+link(p['parent'],stage+' 전체 과목·학년 안내')+' · '+link(b['route'],b['name']+' 종합 안내')+' · '+link(STAGE_GUIDES[p['stage']][1],STAGE_GUIDES[p['stage']][0])+'</p>')
 body+='<p class="bd-source">자료 반영일: '+ui.DAY+'. 개설 학년과 교육비는 제공 센터 자료의 안내이며 현재 모집·시간표 확인일과 다릅니다.</p>'
 crumbs=[('지점안내','/지점안내/'),(b['region'],'/지점안내/'+b['region']+'/'),(b['name'],b['route']),(p['name']+' '+LABELS[p['stage']],p['parent']),(subject,p['route'])]
 nodes=[{'@type':'LearningResource','@id':ui.url(p['route'])+'#learning-guide','name':b['name']+' '+stage+' '+subject+' 학습 점검','description':focus[5],'inLanguage':'ko-KR','educationalLevel':stage,'learningResourceType':'학습 점검과 상담 준비 안내','about':{'@type':'Thing','name':subject},'isPartOf':{'@id':ui.url(p['route'])+'#webpage'}}]
 # Decorate the rendered document before the single final write. This also
 # avoids an intermediate unstyled file while the large collection is built.
 rendered=[];saved_write=ui.write
 try:
  ui.write=lambda path,value:rendered.append((path,value))
  body=insert_map(body,b,p['area'])
  ui.shell(p['route'],title,desc,body,crumbs,faq,nodes=nodes,branch=True)
 finally:ui.write=saved_write
 assert len(rendered)==1
 file,text=rendered[0]
 text=text.replace('<body class="general-page bd-page">',f'<body class="general-page bd-page gd-page sd-page" data-subject-branch="{p["branch"]}" data-stage="{p["stage"]}" data-subject="{subject}" data-neighborhood="{p["area"]}">')
 text=text.replace('</head>','<link rel="stylesheet" href="/assets/grade-directory.css"><link rel="stylesheet" href="/assets/subject-directory.css"></head>')
 ui.write(file,text)

def description(text,route,desc):
 assert len(desc)<=80 and desc.endswith('.'),desc
 old=re.search(r'<meta name="description" content="([^"]+)"',text)[1]
 for attr in ['name="description"','property="og:description"','name="twitter:description"']:
  text=re.sub('(<meta '+attr+' content=")[^"]+("[^>]*>)',lambda m:m[1]+e(desc)+m[2],text)
 def schema(m):
  graph=json.loads(m[1]);graph['@graph'][0]['description']=desc
  return '<script type="application/ld+json">'+ui.j(graph)+'</script>'
 text=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,text,count=1,flags=re.S)
 profile=ui.DESCRIPTIONS['pages'].get(route.rstrip('/'),{})
 ui.DESCRIPTIONS['pages'][route.rstrip('/')]=dict(profile,description=desc,sources=list(dict.fromkeys([*profile.get('sources',[]),old,desc])))
 return text

def enrich_parents():
 paths=['/지점안내/']+['/지점안내/'+r+'/' for r in ui.REGIONS]+[p['route'] for p in GRADES]
 changed=[];bygrade={p['route']:p for p in GRADES}
 for route in paths:
  file=ROOT/(route.lstrip('/')+'index.html');text=file.read_text(encoding='utf-8');old=text
  grade=bygrade.get(route);branch=BRANCHES.get(route)
  if grade:
   group=[p for p in PAGES if p['parent']==route];b=BRANCHES[grade['branch']];stage=NAMES[grade['prefix']]
   block=section('subject-choice',grade['name']+' '+stage+' 영어·수학 선택 안내','<div class="bd-grid sd-choice-grid">'+''.join(child_card(p) for p in group)+'</div>','과목마다 안내 학년이 다를 수 있습니다. 각 페이지의 학년·조건을 먼저 확인하고 학생 자료에 맞는 학습 질문을 살펴보세요.')
   # Separate the original concern cards without altering their factual order.
   text=text.replace('bd-grid gd-topic-grid','sd-grade-topics')
   text=re.sub(r'<article class="bd-card" data-editorial-topic="([^"]+)">(.*?)</article>',lambda m:'<section class="bd-card sd-grade-topic" data-editorial-topic="'+m[1]+'" id="parent-learning-'+m[1]+'">'+m[2]+'</section>',text,flags=re.S)
   desc=grade_description(grade)
   marker='<section class="bd-section " id="courses"'
  elif branch:
   group=[p for p in PAGES if p['branch']==route];b=branch
   block=section('subject-choice',b['name']+' 학년·과목별 학습 점검','<div class="bd-grid sd-choice-grid">'+''.join(child_card(p) for p in group)+'</div>','초·중·고 영어와 수학을 나누어 안내합니다. 희망 과목의 학년과 수강 조건, 학생의 실제 학습 기록을 함께 확인해 주세요.')
   desc=f'{b["region"]} {b["district"]} {b["name"]}의 초·중·고 영어·수학 안내와 과목별 학년, 주소·교육비·방문 자료를 확인합니다.'
   marker='<section class="bd-section " id="courses"'
  else:
   region=route.strip('/').split('/')[-1] if route!='/지점안내/' else None
   bb=[b for b in ui.BRANCHES if not region or b['region']==region];scope=region or '전국'
   rows=[]
   for stage in '초중고':
    cells=[]
    for subject in ['영어','수학']:
     count=sum(any(c['subject']==subject and any(g.startswith(stage) for g in c['grades']) for c in b['courses']) for b in bb)
     cells.append('<td>'+str(count)+'개 지점</td>')
    rows.append('<tr><th scope="row">'+NAMES[stage]+'</th>'+''.join(cells)+'</tr>')
   block=section('subject-choice',scope+' 학년·과목별 지점 찾는 순서','<div class="bd-grid">'+''.join('<article class="bd-card"><h3>'+e(h)+'</h3><p>'+e(copy)+'</p></article>' for h,copy in [('1. 실제 지점과 주소 선택','동네 이름이나 학교명으로 검색하고 연결된 지점의 실제 소재지를 확인하세요.'),('2. 초·중·고 학년 안내 선택','지점 페이지에서 학생의 학년 안내를 열어 과목별 표와 별도 확인 조건을 비교하세요.'),('3. 영어·수학 학습 질문 확인','선택한 학년 아래 영어와 수학 페이지에서 학습 점검·학교 자료·교육비·상담 준비 내용을 확인하세요.')])+'</div><div class="bd-table-wrap"><table class="bd-table"><caption>'+e(scope)+' 자료상 안내 학년이 있는 지점 수</caption><thead><tr><th scope="col">학년</th><th scope="col">영어</th><th scope="col">수학</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p>제공 자료에 해당 학년이 기재된 지점 수입니다. 현재 모집 상태나 반 수를 뜻하지 않으며 자료가 비어 있는 지점은 개설 여부를 별도로 확인해야 합니다.</p>')
   desc=f'{scope} {len(bb)}개 실제 지점에서 초·중·고 영어·수학 안내를 찾고 과목별 학년, 주소·교육비·학교 자료를 확인합니다.'
   marker='<section class="bd-section " id="how-to-choose"'
  assert marker in text,route
  # Repeatable builder replaces its own section only.
  text=re.sub(r'<!-- subject-entry:start -->.*?<!-- subject-entry:end -->','',text,flags=re.S)
  text=text.replace(marker,'<!-- subject-entry:start -->'+block+'<!-- subject-entry:end -->'+marker,1)
  if '/assets/subject-directory.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/assets/subject-directory.css"></head>')
  text=description(text,route,desc)
  ui.write(file,text);changed.append(route.lstrip('/')+'index.html')
 return changed

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 for i,p in enumerate(PAGES,1):
  child(p)
  if i%200==0:print(json.dumps({'renderedSubjectPages':i}),flush=True)
 parents=enrich_parents()
 ui.save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
 new=[p['route'].lstrip('/')+'index.html' for p in PAGES]
 selected=set(before['files'])|set(new)|{'assets/subject-directory.css'}
 ns='http://www.sitemaps.org/schemas/sitemap/0.9';tree=etree.parse(str(ROOT/'sitemap.xml'));root=tree.getroot()
 existing={unquote(urlsplit(n.find('{'+ns+'}loc').text).path):n for n in root}
 for name in [*new,*parents]:
  route='/'+name.removesuffix('index.html');node=existing.get(route)
  if node is None:node=etree.SubElement(root,'{'+ns+'}url');etree.SubElement(node,'{'+ns+'}loc').text=ui.url(route);existing[route]=node
  lm=node.find('{'+ns+'}lastmod')
  if lm is None:lm=etree.SubElement(node,'{'+ns+'}lastmod')
  lm.text=ui.DAY
 tree.write(str(ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True)
 llms=ROOT/'llms.txt';text=llms.read_text(encoding='utf-8');text=re.sub(r'\n## 지점별 학년·과목 안내[\s\S]*$','',text)
 text+='\n## 지점별 학년·과목 안내\n\n188개 실제 지점의 초·중·고 학년 안내 아래 영어·수학 페이지 1,128개를 연결했습니다.\n주소 구조는 /지점안내/지역/실제지점/초등학생학원·중학생학원·고등학생학원/수학·영어/ 입니다.\n각 페이지는 과목별 안내 학년·별도 확인 조건, 학습 점검 질문, 연결 동네의 학교 참고 정보, 교육비 자료와 실제 방문 정보를 설명합니다.\n학습 점검은 교육적 확인 기준이며 실제 과정 개설·운영·모집·성과를 보장하지 않습니다. 학교명은 제휴·재원·전용반을 뜻하지 않습니다. 공통 교육비는 지점 확정 금액과 구분합니다.\n'
 ui.write(llms,text)
 def digest(name):
  raw=(ROOT/name).read_bytes();h=hashlib.sha256(raw).hexdigest()
  normalized=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest() if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name) else None
  return name,h,normalized
 with ThreadPoolExecutor(max_workers=8) as pool:hashes=list(pool.map(digest,sorted(selected)))
 manifest=dict(before,files={n:h for n,h,_ in hashes},textSha256={n:h for n,_,h in hashes if h},sitemapPages=len(root),createdAt=datetime.now(timezone.utc).isoformat())
 ui.save(ROOT/'release-public-manifest.json',manifest)
 report={'newPages':new,'updatedParents':parents,'allDirectoryPages':len(new)+len(parents),'sourceDrafts':4452,'sitemapPages':len(root),'publicFiles':len(selected)}
 ui.save(args.audit/'generated-pages.json',report)
 routes=sorted([p['route'] for p in PAGES],key=lambda p:(len(p.strip('/').split('/')),p))
 dest=Path(r'C:\Users\1992k\Desktop')/'전국수업.com_초중고_영어수학_신규URL_허브순_20261001.txt'
 dest.write_bytes(('\r\n'.join('https://전국수업.com'+r for r in routes)+'\r\n').encode('utf-8-sig'))
 print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()},ensure_ascii=False))
if __name__=='__main__':main()

"""Create a searchable textbook library and selection guides from reviewed rows."""
import argparse,hashlib,json,re,zipfile
from datetime import datetime,timezone,timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote,unquote,urlsplit
from lxml import etree
import build_branch_upgrade as ui
import home_library
from book_library_content import HUB,LEVELS,FIELDS,ACTIVITIES,MOE
ROOT=ui.ROOT;E=ui.e;NEW=[];PAGES=[];BOOKS=[];CLASSES=[];BY_ID={}
HUB_TITLE='영어·수학 교재 찾기와 선택 안내'
HUB_DESC='초·중·고 영어·수학 교재 120종의 학습 영역과 수준별 선택 조건을 비교하고 교재 선택·자기주도학습 방법을 살펴봅니다.'
NOTICE='기초·표준·심화는 학생의 현재 학습 상태에 따른 선택 참고 분류입니다. 지점의 개설 반이나 공식 사용 교재, 교재 순위를 뜻하지 않습니다.'

def source_link(b):return ui.link(b['publicSourceUrl'],b['sourceLabel'],True)
def book_route(b):return HUB+b['field']+'/#book-'+b['id'].lower()
GUIDE_TITLES={p['slug']:p['title'] for p in json.loads((ROOT/'learning-guide-data.json').read_text(encoding='utf-8'))['pages']}
def guide_link(slug):return ui.link('/학습가이드/'+slug+'/',GUIDE_TITLES[slug])
def list_html(values):return '<ul>'+''.join('<li>'+E(v)+'</li>' for v in values)+'</ul>'
def facts(values):return '<dl class="bk-facts">'+''.join(f'<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>' for k,v in values)+'</dl>'
def hero(title,lead,kicker='교재안내'):
 return f'<header class="bd-hero"><p class="bd-kicker">{E(kicker)}</p><h1>{E(title)}</h1><p>{E(lead)}</p></header>'
def answer(value):return '<div class="bk-answer"><strong>선택의 출발점</strong><p>'+E(value)+'</p></div>'
def notice():return '<p class="bk-notice" data-book-qualification>'+E(NOTICE)+'</p>'
def toc(items):return '<nav class="bk-toc" aria-label="페이지 목차">'+''.join(ui.link('#'+k,n) for k,n in items)+'</nav>'
def section(id,title,body,lead=''):return ui.section(id,title,body,lead)

def save_page(route,title,description,body,crumbs,faqs=(),book_ids=(),article=False):
 assert len(description)<=80 and description.endswith('.'),(route,description)
 nodes=[]
 if article:nodes.append({'@type':['Article','LearningResource'],'@id':ui.url(route)+'#article','url':ui.url(route),'headline':title,'description':description,'inLanguage':'ko-KR','datePublished':ui.DAY,'dateModified':ui.DAY,'author':{'@type':'Organization','name':'와와센터 학습코칭','url':ui.url('/')},'publisher':{'@type':'Organization','name':'와와센터 학습코칭','url':ui.url('/')},'mainEntityOfPage':{'@id':ui.url(route)+'#webpage'},'learningResourceType':'교재 선택 가이드'})
 if book_ids:nodes.append({'@type':'ItemList','@id':ui.url(route)+'#books','name':title+' 교재 후보','numberOfItems':len(book_ids),'itemListElement':[{'@type':'ListItem','position':i,'name':BY_ID[id]['name'],'url':ui.url(book_route(BY_ID[id]))} for i,id in enumerate(book_ids,1)]})
 capture={};write=ui.write;ui.write=lambda path,text:capture.update(path=path,text=text)
 try:ui.shell(route,title,description,body,crumbs,faqs=faqs,nodes=nodes,kind='WebPage' if article else 'CollectionPage')
 finally:ui.write=write
 rendered=capture['text'].replace('</head>','<link rel="stylesheet" href="/assets/book-library.css"><script defer src="/assets/book-library.js"></script></head>').replace('class="general-page bd-page"','class="general-page bd-page bk-page'+(' bk-reading' if article else '')+'"')
 if article:rendered=rendered.replace('property="og:type" content="website"','property="og:type" content="article"')
 write(capture['path'],rendered);NEW.append(route.lstrip('/')+'index.html')
 PAGES.append(dict(route=route,title=title,description=description,bookIds=list(book_ids),faqs=faqs,article=article))

def book_card(b,full=False):
 label=LEVELS[b['level']];additional=' · '.join(LEVELS[l] for l in b['additionalLevels']) or '없음'
 if full:
  return f'<article class="bk-book-detail" id="book-{b["id"].lower()}" data-book-id="{b["id"]}" data-level="{E(b["level"])}" data-additional="{E(",".join(b["additionalLevels"]))}"><p class="bk-meta">{E(b["publisher"])} · {E(b["area"])}</p><h3>{E(b["name"])}</h3><p>{E(b["introduction"])}</p>'+facts([('살펴볼 학생',b['student']),('권·단계 조건',b['condition']),('선택 참고 분류','주분류 '+label+' / 추가 '+additional)])+'<p class="bk-source-link">'+source_link(b)+'</p></article>'
 data={'name':b['name'],'field':FIELDS[b['field']]['label'],'publisher':b['publisher'],'area':b['area'],'student':b['student'],'condition':b['condition'],'level':label,'additional':[LEVELS[l] for l in b['additionalLevels']],'route':book_route(b)}
 search=' '.join([b['id'],b['field'],FIELDS[b['field']]['label'],b['name'],b['publisher'],b['area'],b['student'],b['condition']])
 return f'<article class="bk-book-card" data-book-card data-book-id="{b["id"]}" data-field="{E(b["field"])}" data-level="{E(b["level"])}" data-additional="{E(",".join(b["additionalLevels"]))}" data-search="{E(search)}" data-facts="{E(ui.j(data))}"><p class="bk-meta">{E(FIELDS[b["field"]]["label"])} · {E(b["publisher"])}</p><h3>{ui.link(book_route(b),b["name"])}</h3><p class="bk-area">{E(b["area"])}</p><p>{E(b["student"])}</p><div class="bk-tags"><span>주분류 {E(label)}</span>'+(''.join(f'<span>추가 {E(LEVELS[l])}</span>' for l in b['additionalLevels']))+'</div><div class="bk-card-actions">'+ui.link(book_route(b),'선택 조건 자세히 보기')+f'<label class="bk-compare-control" data-compare-control hidden><input type="checkbox" data-book-compare value="{b["id"]}"><span>{E(b["name"])} 비교목록에 추가</span></label></div></article>'

def category_card(field):
 f=FIELDS[field];return '<article class="bd-card"><p class="bk-meta">20종 · '+E(f['focus'])+'</p><h3>'+ui.link(HUB+field+'/',f['label']+' 교재')+'</h3><p>'+E(f['answer'])+'</p><div class="bk-level-links">'+''.join(ui.link(HUB+field+'/'+label+'/',label+' 선택 안내') for label in LEVELS.values())+'</div></article>'

def render_hub():
 body=hero('우리에게 필요한\n영어·수학 교재 찾기','과목과 학습 영역을 고르고, 현재 학생의 수행과 권·단계 조건을 비교해 보세요. 초·중·고 6개 분야의 교재 120종을 한곳에 모았습니다.','TEXTBOOK LIBRARY')+notice()
 form='<form class="bk-search" data-book-search role="search"><label class="bk-query" for="book-query">교재명·출판사·학습 영역 검색<input id="book-query" type="search" name="q" placeholder="예: 파닉스, 문장제, 개념원리" autocomplete="off"></label><div class="bk-search-filters"><label for="book-field">학년·과목<select id="book-field" name="field"><option value="">전체 분야</option>'+''.join(f'<option value="{E(field)}">{E(f["label"])}</option>' for field,f in FIELDS.items())+'</select></label><label for="book-level">학습 상태<select id="book-level" name="level"><option value="">전체 수준</option>'+''.join(f'<option value="{E(level)}">{E(label)} 학습</option>' for level,label in LEVELS.items())+'</select></label><button class="bd-btn" type="reset">검색 초기화</button></div><label class="bk-check"><input type="checkbox" name="additional" checked>추가 분류에 포함된 교재도 보기</label></form><p class="bk-result" data-book-status role="status" aria-live="polite">120종의 교재를 볼 수 있습니다.</p><noscript><p>아래 전체 목록과 과목별 페이지는 그대로 볼 수 있습니다. 검색·비교 기능은 자바스크립트를 켜면 이용할 수 있습니다.</p></noscript>'
 body+=form+'<nav class="bk-shortcuts" aria-label="교재 선택 방법">'+ui.link(HUB+'교재선택/','교재 선택 체크리스트')+ui.link(HUB+'자기주도학습/','혼자 공부하는 활용 방법')+ui.link('#categories','학년·과목별 안내')+'</nav>'
 body+='<section class="bd-section bk-compare-panel" data-book-comparison hidden aria-labelledby="compare-title"><h2 id="compare-title">선택한 교재 비교</h2><p class="bd-lead">학습 영역과 살펴볼 학생, 권·단계 조건을 같은 기준으로 읽어 보세요. 검색 조건을 바꾸어도 비교목록은 유지됩니다.</p><div class="bk-comparison-grid" data-comparison-grid></div><button type="button" class="bd-btn" data-comparison-clear>비교목록 비우기</button><p data-comparison-status role="status" aria-live="polite"></p></section>'
 body+=section('book-results','교재 후보와 선택 조건','<div class="bk-empty" data-book-empty hidden><h3>검색 결과가 없습니다.</h3><p>검색어를 짧게 입력하거나 학년·과목·학습 상태를 전체로 바꿔 보세요.</p></div><div class="bk-cards">'+''.join(book_card(b) for b in BOOKS)+'</div>')
 body+=section('categories','과목의 목표와 20종 전체 설명을 살펴보세요','<div class="bd-grid">'+''.join(category_card(field) for field in FIELDS)+'</div>')
 faqs=[('교재 120종이 모두 지점의 사용 교재인가요?','교재 선정 후보를 정리한 자료입니다. 지점별 사용 현황과 개설 과정은 포함되어 있지 않습니다. 실제 사용 여부는 해당 지점에서 확인하세요.'),('기초·표준·심화 분류만으로 교재를 정해도 되나요?','분류는 현재 학습 상태를 생각하기 위한 참고 기준입니다. 같은 시리즈의 권·단계에 따라 활용 범위가 달라지므로 학생의 실제 수행과 선택 조건을 함께 보세요.'),('한 번에 여러 교재를 시작해야 하나요?','현재 목표를 맡길 주교재를 먼저 정하고 부족한 영역만 보강할 수 있습니다. 목록과 편성 예시는 모두 동시에 사용하라는 뜻이 아닙니다.')]
 body+=section('faq','교재 목록을 볼 때 자주 묻는 질문',ui.faqs_markup(faqs))
 body+='<aside class="bk-compare-dock" data-comparison-dock hidden aria-label="비교목록 이동"><a href="#compare-title"><span data-comparison-count>선택한 교재 비교 보기</span><span aria-hidden="true"> ↑</span></a></aside>'
 save_page(HUB,HUB_TITLE,HUB_DESC,body,[('교재안내',HUB)],faqs,[b['id'] for b in BOOKS])

def edition_section(field):
 f=FIELDS[field]
 body='<div class="bk-edition"><p>'+E(f['edition'])+'</p><p>2026년 기준 2022 개정 교육과정은 초등 전 학년과 중1·중2, 고1·고2에 적용됩니다. 중3·고3 적용은 2027년부터입니다. 현재 학교의 적용 교육과정과 해당 권을 함께 확인하세요.</p><p>'+ui.link(MOE,'교육부 고시의 학년별 적용 일정',True)+'</p></div>'
 return section('edition','권·단계·판본을 함께 확인하세요',body)

def render_category(field):
 f=FIELDS[field];route=HUB+field+'/';books=[b for b in BOOKS if b['field']==field];classes=[c for c in CLASSES if c['field']==field]
 body=hero(f['label']+' 교재 20종과 선택 기준',f['focus']+'을 나누어 지금 필요한 교재의 역할을 정해 보세요.')+answer(f['answer'])+notice()+toc([('check','학습 상태'),('levels','수준별 선택'),('book-list','20종 설명'),('edition','판본 확인'),('guides','공부 방법'),('faq','질문')])
 body+=section('check','같은 과목에서도 막힌 부분을 나누어 보세요','<div class="bd-grid">'+''.join('<div class="bd-card"><h3>'+E(h)+'</h3><p>'+E(p)+'</p></div>' for h,p in f['checks'])+'</div>')
 body+=section('levels','현재 수행에 맞는 선택 안내','<div class="bd-grid">'+''.join('<article class="bd-card"><h3>'+ui.link(route+LEVELS[c['level']]+'/',LEVELS[c['level']]+' 학습 교재 선택')+'</h3><p>'+E(c['student'])+'</p><p class="bk-goal">학습 목표 · '+E(c['goal'])+'</p></article>' for c in classes)+'</div>')
 body+=section('book-list',f['label']+' 20종의 소개와 선택 조건','<div class="bk-book-details">'+''.join(book_card(b,True) for b in books)+'</div>','교재마다 살펴볼 학생과 권·단계 조건을 함께 읽어 보세요. 추가 분류가 있더라도 현재 권이 학생에게 맞는지 별도 확인해야 합니다.')
 body+=edition_section(field)
 body+=section('guides','교재를 정했다면 공부 방법도 연결해 보세요','<div class="bk-guide-links">'+''.join(guide_link(slug) for slug in f['guides'])+'</div><p>'+ui.link(HUB+'자기주도학습/','교재로 혼자 공부하는 순서')+' · '+ui.link(HUB+'교재선택/','교재 선택 체크리스트')+'</p>')
 faqs=[(f['label']+' 교재의 수준은 학년으로 정하나요?',f['answer']),('주분류와 추가 분류는 어떻게 읽나요?','주분류는 자료에서 대표적으로 검토한 학습 상태입니다. 추가 분류는 다른 상태에서도 권·단계 조건에 따라 검토할 수 있다는 뜻이며 자동으로 적합하다는 판단은 아닙니다.'),('이 목록의 판본을 그대로 구매하면 되나요?',f['edition']+' 출판사 자료에서 현재 권의 서지와 제공 자료를 확인하세요.')]
 body+=section('faq',f['label']+' 교재 선택 질문',ui.faqs_markup(faqs))
 save_page(route,f['label']+' 교재 20종과 선택 기준',f['description'],body,[('교재안내',HUB),(f['label'],route)],faqs,[b['id'] for b in books])

def reference_cards(ids,roles):
 return '<div class="bk-candidate-grid">'+''.join('<article class="bd-card" data-plan-book="'+id+'"><p class="bk-meta">'+E(role)+'</p><h3>'+ui.link(book_route(BY_ID[id]),BY_ID[id]['name'])+'</h3><p>'+E(BY_ID[id]['area'])+'</p><p>'+E(BY_ID[id]['condition'])+'</p>'+source_link(BY_ID[id])+'</article>' for id,role in zip(ids,roles))+'</div>'

def render_level(c):
 field=c['field'];f=FIELDS[field];label=LEVELS[c['level']];parent=HUB+field+'/';route=parent+label+'/'
 primary=re.findall(r'\(([A-Z]{2}\d{2})\)',c['primary']);supplement=re.findall(r'\(([A-Z]{2}\d{2})\)',c['supplement']);ids=primary+supplement
 assert all(id in BY_ID and BY_ID[id]['field']==field for id in ids)
 title=f['label']+' '+label+' 학습 교재 선택과 활용'
 description=f['label']+' '+label+' 학습의 '+c['goal']+' 목표와 주교재·보강 후보, 권·단계 조건 및 학습 확인 방법을 살펴봅니다.'
 h,example,adjust,flow=ACTIVITIES[(field,c['level'])]
 body=hero(title,c['introduction'])+answer(c['student']+'이라면 '+c['goal']+'을 확인할 과제부터 정해 보세요.')+notice()+toc([('state','현재 상태'),('roles','교재 역할'),('candidates','편성 예시'),('practice','활용 예시'),('check','다음 점검'),('edition','판본'),('faq','질문')])
 body+=section('state','이런 수행을 먼저 확인하세요','<div class="bk-panel">'+facts([('학생 상태 예시',c['student']),('확인할 목표',c['goal']),('선택·진행 조건',c['condition'])])+'</div>')
 steps=[('주교재의 역할 정하기',c['goal']+'을 확인할 주교재 후보를 고르고 실제 목차와 샘플 과제를 살펴봅니다.'),('필요한 보강만 더하기',adjust),('권·단계와 분량 고르기',c['condition']+' 한 번에 진행할 범위는 실제 과제 시간과 도움의 필요에 맞춰 조정합니다.'),('혼자 한 결과 다시 보기','풀이·읽기·쓰기에서 도움받은 부분과 혼자 한 결과를 나누어 남기고, 다음 자료에서 같은 수행이 가능한지 확인하세요.')]
 body+=section('roles','교재를 고르는 순서와 역할','<ol class="bk-steps">'+''.join('<li><h3>'+E(a)+'</h3><p>'+E(b)+'</p></li>' for a,b in steps)+'</ol>')
 body+=section('candidates','주교재와 보강의 편성 예시',reference_cards(ids,['주교재 후보']*len(primary)+['보강·다음 단계 후보']*len(supplement)),'아래 조합은 검토할 후보입니다. 모든 교재의 동시 사용이나 실제 지점의 수업 편성을 의미하지 않습니다.')
 body+=section('practice','실제 과제에 적용할 연습 예시','<div class="bk-example"><h3>'+E(h)+'</h3><p>'+E(example)+'</p><p class="bk-flow">'+E(flow)+'</p></div>')
 body+=section('check','다음 단계보다 먼저 남길 확인 기록','<div class="bk-panel">'+facts([('자료와 범위','교재명·권·단원·실제 과제'),('혼자 한 것',c['goal']+' 중 도움 없이 한 수행'),('필요한 도움','막힌 조건·문장·계산과 받은 설명'),('다음 확인','같은 목표를 다른 자료에서 확인할 시점')])+'<p>'+E(adjust)+'</p></div>')
 body+=edition_section(field)
 faqs=[(f['label']+' '+label+' 분류에 바로 맞추면 되나요?',c['student']+'은 선택을 생각하기 위한 상태 예시입니다. '+c['condition']+' 실제 샘플의 수행과 도움의 범위를 확인해 조정하세요.'),('주교재와 보강 후보를 모두 시작해야 하나요?',c['goal']+'을 맡길 중심 교재를 먼저 정하고 부족한 영역만 보강할 수 있습니다. 보강·다음 단계 후보에는 나중에 검토할 교재도 포함됩니다.'),('혼자 공부할 때 무엇을 남기면 좋나요?',h+' 활동에서 혼자 가능한 부분과 막힌 지점을 구분해 기록하세요. 답을 본 뒤 완성한 결과와 해설 없이 다시 한 결과를 나누어 다음 범위를 정합니다.')]
 body+=section('faq','교재 편성과 활용에 관한 질문',ui.faqs_markup(faqs))
 body+=section('related','전체 설명과 공부 방법도 살펴보세요','<div class="bk-guide-links">'+ui.link(parent,f['label']+' 전체 20종')+ui.link(HUB+'자기주도학습/','혼자 공부하는 활용 방법')+''.join(guide_link(slug) for slug in f['guides'][:2])+'</div>')
 save_page(route,title,description,body,[('교재안내',HUB),(f['label'],parent),(label+' 학습',route)],faqs,ids,True)

def render_howto(kind):
 if kind=='교재선택':
  title='교재 선택 체크리스트와 비교 기록';desc='교재 선택 전에 학습 목표·현재 수행·권·단계·판본과 보강 목적을 확인하고 비교 기록으로 선택 이유를 남깁니다.'
  lead='학생이 필요한 도움과 교재의 역할을 같은 기준으로 비교해 보세요.'
  sections=[('goal','먼저 해결할 한 가지를 정하세요','개념을 설명하기 어려운지, 계산 오류가 반복되는지, 긴 문장에서 연결이 어려운지 최근 자료를 보고 정합니다. 공부 시간이나 학년만으로 교재 난도를 확정하지 않습니다.'),('sample','목차와 샘플 과제로 현재 수행을 보세요','목차에서 필요한 단원을 찾고 공개된 미리보기나 실제 책의 짧은 과제를 읽어 봅니다. 혼자 가능한 부분, 설명이 필요한 부분과 답을 보고 한 부분을 구분해 기록하세요.'),('role','주교재와 보강 교재의 역할을 나누세요','주교재는 중심 목표와 흐름을 맡기고, 보강은 부족한 영역을 좁혀 정합니다. 같은 단원·문법·어휘를 여러 교재에서 반복하는 경우 현재 목표에 필요한 반복인지 먼저 확인합니다.'),('edition','권·단계와 학교 판본을 대조하세요','시리즈 이름 외에 권·Level·학년·학기·학교 과목·개정 교육과정·응시 학년도를 확인합니다. 발행 연도와 적용 교육과정, 발행 연도와 수능 응시 학년도는 서로 다른 항목입니다.'),('support','혼자 사용할 자료와 확인 방법을 살펴보세요','현재 권에 정답·해설·음원·온라인 자료가 어떻게 제공되는지 출판사 안내에서 확인합니다. 오래된 판본의 제공 자료와 최신 판본의 조건이 같다고 가정하지 않습니다.'),('decide','선택 이유와 다음 확인을 함께 남기세요','선택한 책의 이름만 적기보다 해결할 목표, 첫 범위, 도움받을 부분과 다음 확인을 남깁니다. 실제 과제에서 계속 막히면 교재를 더 사기 전에 권·단계·분량과 설명의 필요를 다시 살펴봅니다.')]
  record=[('현재 목표',''),('최근 자료와 혼자 가능한 수행',''),('후보 교재·권·단계·판본',''),('학습 영역과 주교재·보강 역할',''),('샘플에서 막힌 지점과 필요한 도움',''),('선택 이유와 첫 범위',''),('다음 확인 날짜와 자료','')]
  example='영어 지문에서 단어는 알지만 긴 수식 부분 때문에 뜻이 끊긴다면, 어휘 목록을 더 늘리는 것과 문장 구조를 보강하는 것을 구분해 볼 수 있습니다. 최근 문장에서 주어·동사·수식 부분을 나눈 결과를 보고 후보의 샘플 과제를 비교하세요.'
  faqs=[('교재가 유명하면 먼저 사도 되나요?','알려진 이름보다 현재 필요한 목표와 실제 권의 목차·샘플·지원 자료를 확인하세요. 교재의 인지도만으로 학생에게 맞는 단계를 정할 수 없습니다.'),('기초·표준·심화는 출판사의 공식 등급인가요?','이 자료의 분류는 학생 상태에 따른 교재 검토를 위한 참고 기준입니다. 출판사의 공식 반 분류나 공인 난도 등급을 뜻하지 않습니다.'),('지점에서 사용하는 교재도 확인할 수 있나요?','이 자료에는 지점별 사용 현황이 없습니다. 지점의 실제 학년·과목과 사용 교재는 해당 지점의 안내를 확인하세요.')]
 else:
  title='교재로 혼자 공부하는 계획과 점검';desc='교재의 첫 과제·채점·질문·재확인을 학습 계획에 연결하고 혼자 한 수행과 도움의 범위를 기록하는 방법입니다.'
  lead='진도와 함께 실제 수행을 남기면 다음 분량과 필요한 도움을 정하기 좋습니다.'
  sections=[('start','오늘 남길 결과부터 정하세요','“교재 공부” 대신 풀 문제의 범위와 남길 설명·근거·문장을 적습니다. 페이지 수만으로 완료를 정하지 말고 현재 목표의 수행을 같이 정하세요.'),('try','정답을 보기 전에 자신의 시도를 남기세요','모르는 단어, 문제의 조건과 써 본 식을 표시합니다. 막혔을 때 시도를 지우지 않으면 필요한 설명을 구체적으로 질문하기 좋습니다.'),('check','채점과 수정 이유를 연결하세요','맞고 틀림을 확인한 뒤 처음 오류가 생긴 줄이나 근거를 놓친 문장을 찾습니다. 해설을 옮기는 것과 수정 이유를 자신의 말로 설명하는 것을 나누어 기록합니다.'),('ask','질문을 자료와 시도로 좁히세요','교재·권·단원·문항이나 문장의 위치, 마지막으로 이해한 부분과 막힌 연결을 적습니다. 도움받은 뒤에는 직접 다시 해 본 결과를 남기세요.'),('again','시간을 두고 다시 확인하세요','답을 가리고 같은 내용의 설명이나 새 조건의 문제를 확인해 봅니다. 복습 날짜와 분량은 실제 결과와 일정에 맞춰 조정하고 모든 항목에 같은 간격을 강제하지 않습니다.'),('adjust','분량·단계·도움을 같이 조정하세요','끝내지 못한 이유를 시간 부족과 내용 어려움으로 나누어 보세요. 교재를 계속 추가하기보다 가능한 분량, 필요한 이전 개념과 설명받을 범위를 먼저 조정할 수 있습니다.')]
  record=[('교재·권·단원과 오늘 범위',''),('완료 기준과 남길 결과',''),('혼자 한 범위',''),('첫 오류와 수정 이유',''),('질문할 위치와 내 시도',''),('도움받은 뒤 직접 한 결과',''),('재확인 날짜·자료·다음 조정','')]
  example='수학 문항 열 개 중 네 개가 남았다면 “시간이 없어 못 본 두 개 / 조건을 식으로 옮기다가 멈춘 두 개”처럼 나눕니다. 앞의 과제는 일정과 분량을, 뒤의 과제는 설명과 질문을 먼저 정할 자료가 됩니다. 열 개는 권장 분량이 아닌 기록의 예시입니다.'
  faqs=[('혼자 공부하면 질문 없이 끝내야 하나요?','독립 수행과 필요한 도움을 구분해 보세요. 질문할 자료와 자신의 시도를 남기고 설명 뒤 다시 혼자 해 본 결과를 확인할 수 있습니다.'),('교재 진도가 밀리면 분량을 늘려야 하나요?','남은 이유를 먼저 확인하세요. 실제 일정, 과제 난도와 필요한 설명을 함께 보고 가능한 범위를 조정합니다.'),('한 번 다시 맞히면 복습이 끝난 건가요?','답을 기억한 것과 새로운 조건에 적용한 것을 나누어 확인하세요. 같은 목표를 다른 자료에서도 수행하는지 보고 다음 복습을 정할 수 있습니다.')]
 route=HUB+kind+'/'
 body=hero(title,lead)+answer(sections[0][2])+toc([(id,h) for id,h,_ in sections]+[('record','빈 기록 양식'),('faq','질문')])
 body+=''.join(section(id,h,'<div class="bk-panel"><p>'+E(p)+'</p></div>') for id,h,p in sections)
 body+=section('example','상황에 맞춰 적용하는 연습 예시','<div class="bk-example"><p>'+E(example)+'</p></div>')
 record_url='/assets/book-records/'+kind+'.txt';lines=[title+' — 빈 기록 양식','작성 날짜:','']
 for label,_ in record:lines+=[label+':','','']
 lines+=['가이드: https://전국수업.com'+route]
 record_file=ROOT/record_url.lstrip('/');record_file.parent.mkdir(parents=True,exist_ok=True);record_file.write_bytes(('\r\n'.join(lines)+'\r\n').encode('utf-8-sig'));NEW.append(record_url.lstrip('/'))
 body+=section('record','직접 적어 볼 기록 양식','<div class="bk-panel">'+list_html([r[0] for r in record])+'<a class="bd-btn bd-btn-primary" href="'+ui.href(record_url)+'" download="'+E(kind+'-기록양식.txt')+'">빈 기록 양식 내려받기 (TXT)</a></div>')
 body+=section('faq','교재 선택과 학습에 관한 질문',ui.faqs_markup(faqs))
 body+=section('related','교재 목록과 학습가이드를 연결해 보세요','<div class="bk-guide-links">'+ui.link(HUB,'전체 120종 교재 찾기')+ui.link('/학습가이드/학습플래너작성법/','학습 플래너 작성법')+ui.link('/학습가이드/학습질문만들기/','학습 질문 만들기')+ui.link('/학습가이드/피드백활용법/','피드백 활용법')+'</div>')
 save_page(route,title,desc,body,[('교재안내',HUB),(title,route)],faqs,article=True)

def integrate(audit):
 with zipfile.ZipFile(audit/'before-source.zip') as archive:
  home=archive.read('index.html').decode('utf-8');guides=archive.read('학습가이드/index.html').decode('utf-8')
 entry='<!-- book-entry:start --><section class="bd-entry" id="book-discovery" data-book-entry><p class="bd-kicker">교재 선택과 공부 방법</p><h2>지금 필요한 영어·수학 교재를 찾아보세요</h2><p>초·중·고 120종의 학습 영역과 권·단계 조건을 살펴보고, 주교재와 보강의 역할을 정해 보세요.</p><div class="bd-entry-links">'+ui.link(HUB,'전체 교재 찾기')+ui.link(HUB+'교재선택/','교재 선택 체크리스트')+ui.link(HUB+'자기주도학습/','혼자 공부하는 활용 방법')+'</div></section><!-- book-entry:end -->'
 assert home.count('</main>')==1;ui.write(ROOT/'index.html',home.replace('</main>',entry+'</main>'))
 guide_entry='<!-- book-entry:start -->'+section('book-discovery','공부 방법에 맞는 교재도 찾아보세요','<div class="lg-next"><p>필요한 학습 영역과 학생의 수행을 확인했다면 교재의 역할과 권·단계 조건을 비교해 보세요.</p><div class="bd-actions">'+ui.button(HUB,'영어·수학 교재 120종 찾기',True)+ui.button(HUB+'교재선택/','교재 선택 체크리스트')+'</div></div>')+'<!-- book-entry:end -->'
 assert guides.count('<section class="bd-section " id="start"')==1
 guides=guides.replace('<section class="bd-section " id="start"',guide_entry+'<section class="bd-section " id="start"',1);ui.write(ROOT/'학습가이드/index.html',guides)

def update_feeds(audit):
 ns='http://www.sitemaps.org/schemas/sitemap/0.9'
 with zipfile.ZipFile(audit/'before-source.zip') as archive:
  sitemap=etree.fromstring(archive.read('sitemap.xml'));rss=etree.fromstring(archive.read('rss.xml'));llms=archive.read('llms.txt').decode('utf-8-sig')
 modified={ui.url('/'),ui.url('/학습가이드/')}
 for node in sitemap:
  if node.find('{'+ns+'}loc').text in modified:node.find('{'+ns+'}lastmod').text=ui.DAY
 for p in PAGES:
  node=etree.SubElement(sitemap,'{'+ns+'}url');etree.SubElement(node,'{'+ns+'}loc').text=ui.url(p['route']);etree.SubElement(node,'{'+ns+'}lastmod').text=ui.DAY
 (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
 channel=rss.find('channel');stamp=format_datetime(datetime.now(timezone(timedelta(hours=9))));channel.find('lastBuildDate').text=stamp
 for p in PAGES:
  item=etree.SubElement(channel,'item')
  for key,value in [('title',p['title']),('link',ui.url(p['route'])),('guid',ui.url(p['route'])),('description',p['description']),('pubDate',stamp)]:
   element=etree.SubElement(item,key);element.text=value
   if key=='guid':element.set('isPermaLink','true')
 (ROOT/'rss.xml').write_bytes(etree.tostring(rss,encoding='utf-8',xml_declaration=True,pretty_print=True))
 llms+='\n## 교재 안내와 선택 자료\n\n'+HUB_DESC+'\n\n'
 llms+='\n'.join('- '+p['title']+': '+ui.url(p['route']) for p in PAGES)+'\n'
 ui.write(ROOT/'llms.txt',llms)
 return len(sitemap)

def public_source(b):
 url=b['sourceUrl'];label='출판사 교재·참고 자료'
 if b['id']=='ME01':return 'https://www.nebooks.co.kr/pages/book/view.asp?c=BB04010007','NE능률 현재 시리즈와 자료'
 if 'brand_' in url and 'chunjae.co.kr' in url:return 'https://book.chunjae.co.kr/','천재교육 교재 검색'
 if 't-book.visang.com' in url:return 'https://book.visang.com/main','비상교육 교재 검색'
 if 'sinsago.co.kr' in url:return 'https://truebook.sinsago.co.kr/main/main.aspx','좋은책신사고 교재 검색'
 if 'ALIST_PriceRevision.pdf' in url:return 'https://www.alist.co.kr/','에이리스트 교재·수업 자료'
 if b['id']=='EE12':return 'https://www.oupjapan.co.jp/en/gradedreaders/ort/index.shtml','Oxford Reading Tree 시리즈 자료'
 if 'oupjapan.co.jp' in url:return 'https://www.oupjapan.co.jp/ja/products/list/2251','Oxford 영어 교재 목록'
 if 'youtube.com' in url:label='출판사 교재 소개 영상'
 elif b['publisher']=='EBS':label='EBS 교재·학습 자료'
 elif urlsplit(url).path in ['/','/main/','/pages/']:label=b['publisher']+' 교재 검색'
 return url,label

def main():
 global BOOKS,CLASSES,BY_ID
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--source',type=Path,default=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보\영어수학교재_120종_기초표준심화반_홈페이지용_20261001.xlsx'));args=ap.parse_args()
 data=json.loads((args.audit/'source-data.json').read_text(encoding='utf-8'));assert hashlib.sha256(args.source.read_bytes()).hexdigest()==data['sha256'],'Workbook changed since review'
 BOOKS=data['books'];CLASSES=data['classes']
 for b in BOOKS:
  b['additionalLevels']=[] if b['additional']=='없음' else [s.strip() for s in b['additional'].split(',')]
  assert b['level'] in LEVELS and all(l in LEVELS for l in b['additionalLevels'])
  b['publicSourceUrl'],b['sourceLabel']=public_source(b)
 BY_ID={b['id']:b for b in BOOKS}
 render_hub()
 for field in FIELDS:render_category(field)
 for c in CLASSES:render_level(c)
 for kind in ['교재선택','자기주도학습']:render_howto(kind)
 assert len(PAGES)==27 and len({p['description'] for p in PAGES})==27
 integrate(args.audit);sitemap_count=update_feeds(args.audit);home_library.enhance(ROOT);NEW.append('assets/home-library.css')
 ui.save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
 ui.save(ROOT/'book-library-data.json',{'updated':ui.DAY,'sourceSha256':data['sha256'],'fields':FIELDS,'levels':LEVELS,'qualification':NOTICE,'books':BOOKS,'classes':CLASSES,'pages':PAGES,'entryPages':['index.html','학습가이드/index.html']})
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 selected=set(before['files'])|set(NEW)|{'assets/book-library.css','assets/book-library.js'}
 files={};normalized={}
 for name in sorted(selected):
  raw=(ROOT/name).read_bytes();files[name]=hashlib.sha256(raw).hexdigest()
  if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name):normalized[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
 ui.save(ROOT/'release-public-manifest.json',{**before,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':sitemap_count,'files':files,'textSha256':normalized})
 ui.save(args.audit/'generated-pages.json',{'pages':PAGES,'newFiles':sorted(set(NEW)|{'assets/book-library.css','assets/book-library.js'}),'updatedEntries':['index.html','학습가이드/index.html']})
 summary={'books':len(BOOKS),'fields':6,'levelGuides':18,'howToGuides':2,'newPages':27,'publicFiles':len(selected),'htmlPages':sum(n.endswith('.html') for n in selected),'sitemapPages':sitemap_count,'deployed':False}
 ui.save(args.audit/'generation-summary.json',summary);print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()

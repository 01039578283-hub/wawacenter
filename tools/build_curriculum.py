"""Create study-planning references from the supplied workbook, not branch offerings."""
import argparse, hashlib, json, re, zipfile
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
from collections import Counter
import openpyxl
from lxml import etree
import build_branch_upgrade as ui
from build_site_shell import header
from build_education_info import finder

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-04'
ui.DAY = DAY
BASE = '/학습커리큘럼/'
STAGES = {'초': '초등', '중': '중등', '고': '고등'}
LONG = {'초': '초등학교', '중': '중학교', '고': '고등학교'}
NAMES = {'초': '초등학생', '중': '중학생', '고': '고등학생'}
NOTE = '학교 교과서와 실제 진도에 맞춰 조정하는 공부 계획 참고 자료입니다. 지점별 개설 학년·과목·교재는 해당 지점에서 확인하세요.'
MOE = 'https://www.moe.go.kr/boardCnts/viewRenew.do?boardID=141&boardSeq=93458&lev=0'

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, v): ui.save(p, v)
def route(name): return '/' if name == 'index.html' else '/' + name.removesuffix('index.html')
def marked(kind, text): return f'<!-- curriculum-links:{kind}:start -->{text}<!-- curriculum-links:{kind}:end -->'
def strip(text): return re.sub(r'<!-- curriculum-links:([a-z]+):start -->[\s\S]*?<!-- curriculum-links:\1:end -->', '', text)
def sr(s): return BASE + STAGES[s] + '/'
def pr(s, sub): return sr(s) + sub + '/'
def gr(row): return pr(row['grade'][0], row['subject']) + row['grade'] + '/'
def grade_name(g): return LONG[g[0]] + ' ' + g[1:] + '학년'
def actions(items): return '<div class="cu-actions">' + ''.join('<a href="'+ui.href(p)+'">'+ui.e(t)+'</a>' for p,t in items) + '</div>'
def section(id, title, text): return '<section class="cu-section" id="'+id+'" aria-labelledby="'+id+'-title"><h2 id="'+id+'-title">'+ui.e(title)+'</h2>'+text+'</section>'
def para(text): return '<p>'+ui.e(text)+'</p>'
def steps(text): return '<ol class="cu-steps">'+''.join('<li><span>'+ui.e(x.strip())+'</span></li>' for x in text.split('→'))+'</ol>'
def bullets(items): return '<ul>'+''.join('<li>'+ui.e(x)+'</li>' for x in items)+'</ul>'
def hero(title, lead, tags=()): return '<section class="cu-hero"><p class="cu-kicker">학생과 학부모를 위한 공부 커리큘럼</p><h1>'+ui.e(title)+'</h1>'+para(lead)+'<div class="cu-tags">'+''.join('<span>'+ui.e(t)+'</span>' for t in tags)+'</div></section>'
def style(text): return text.replace('<link rel="stylesheet" href="/assets/site-shell.css">', marked('style','<link rel="stylesheet" href="/assets/curriculum.css">')+'<link rel="stylesheet" href="/assets/site-shell.css">',1)
def refs(url, segment=''):
    return section('references','학습 범위를 확인할 자료', '<p>'+ui.link(url, '교육과정 원문과 관련 안내', True)+((' · '+ui.e(segment)) if segment else '')+'</p><p>학년군 기준과 학생의 실제 학년·학기 진도는 다를 수 있습니다. 위 범위에 맞춰 공부 순서와 확인 과제를 정리했습니다.</p>')

def emit(p, title, description, body, crumbs, faqs=(), nodes=(), kind='WebPage'):
    ui.shell(p,title,description,body,crumbs,faqs=faqs,nodes=nodes,kind=kind)
    name=p.lstrip('/')+'index.html'; text=(ROOT/name).read_text(encoding='utf-8')
    text=re.sub(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:header(p),text,count=1)
    text=text.replace('<body class="general-page bd-page">','<body class="general-page bd-page cu-page" data-site-shell="1">',1)
    text=text.replace('</head>','<link rel="stylesheet" href="/assets/education-info.css"><link rel="stylesheet" href="/assets/curriculum.css"><link rel="stylesheet" href="/assets/site-shell.css"><script defer src="/assets/education-info.js"></script><script defer src="/assets/curriculum.js"></script></head>',1)
    ui.write(ROOT/name,text)
    return dict(file=name,route=p,title=title,description=description,faqs=list(faqs))

def card(row):
    title=grade_name(row['grade'])+' '+row['subject']
    special=' · 선택 활동' if row['grade'] in ['초1','초2'] and row['subject']=='영어' else ' · 통합교과 연계' if row['grade'] in ['초1','초2'] and row['subject'] in ['사회','과학'] else ''
    search=' '.join([title,row['grade'],row['subject'],row['focus']])
    return '<article class="cu-card" data-curriculum-card data-stage="'+STAGES[row['grade'][0]]+'" data-grade="'+row['grade']+'" data-subject="'+row['subject']+'" data-search="'+ui.e(search)+'"><p class="cu-kicker">'+ui.e(row['grade']+' · '+row['revision']+special)+'</p><h3>'+ui.link(gr(row),title)+'</h3>'+para(row['focus'])+ui.link(gr(row),'공부 순서와 확인 과제 보기 →')+'</article>'

def list_items(rows, title):
    return {'@type':'ItemList','name':title,'numberOfItems':len(rows),'itemListElement':[{'@type':'ListItem','position':i,'name':grade_name(r['grade'])+' '+r['subject'],'url':ui.url(gr(r))} for i,r in enumerate(rows,1)]}

def filter_cards(rows, stage=None, subject=None):
    grades=list(dict.fromkeys(r['grade'] for r in rows));subjects=list(dict.fromkeys(r['subject'] for r in rows))
    form='<form class="cu-filter" data-curriculum-filter role="search"><label>학년·내용 검색<input type="search" name="q" placeholder="예: 중2, 함수, 분수" autocomplete="off"></label>'
    if not stage: form+='<label>학교급<select name="stage"><option value="">초·중·고 전체</option>'+''.join('<option>'+s+'</option>' for s in STAGES.values())+'</select></label>'
    form+='<label>학년<select name="grade"><option value="">전체 학년</option>'+''.join('<option value="'+g+'" data-stage="'+STAGES[g[0]]+'">'+grade_name(g)+'</option>' for g in grades)+'</select></label>'
    if not subject: form+='<label>과목<select name="subject"><option value="">전체 과목</option>'+''.join('<option>'+s+'</option>' for s in subjects)+'</select></label>'
    form+='<button type="reset">전체 보기</button></form><p class="cu-status" data-curriculum-status role="status" aria-live="polite">'+str(len(rows))+'개 학년·과목 안내가 있습니다.</p><p data-curriculum-empty hidden>조건에 맞는 안내가 없습니다. 검색어를 줄이거나 학년·과목을 바꿔 보세요.</p><noscript><p>검색을 사용하지 않아도 아래의 모든 학년·과목 링크를 열 수 있습니다.</p></noscript>'
    return form+'<div class="cu-grid">'+''.join(card(r) for r in rows)+'</div>'

def level_section(stage, subject, plans, compact=False):
    shared='사회' if subject=='역사' else subject
    items=[p for p in plans if p['stage']==NAMES[stage] and p['subject']==shared]
    note='<p>기초·표준·심화는 공부 방법을 고르는 참고 구분입니다. 공식 성취등급이나 지점의 실제 반 편성을 뜻하지 않으며, 과목 안에서도 영역별로 출발점이 다를 수 있습니다.</p>'
    if subject=='역사':note+='<p>자료의 사회·역사 공통 학습 계획을 활용합니다. 역사 범위는 현재 이수하는 과목과 사료에 맞춰 조정하세요.</p>'
    body=note+'<div class="cu-level-grid">'
    for i,p in enumerate(items):
        label=p['level'].removesuffix('반');body+='<article class="cu-level" id="level-'+str(i+1)+'"><span class="cu-kicker">'+label+' 학습</span><h3>'+['개념부터 다시 연결하기','배운 내용을 과제에 적용하기','조건과 근거를 비교하며 확장하기'][i]+'</h3><dl><dt>이런 도움이 필요할 때</dt><dd>'+ui.e(p['target'])+'</dd>'
        if not compact:body+='<dt>공부 순서 예시</dt><dd>'+ui.e(p['sequence'])+'</dd>'
        body+='<dt>확인할 수행</dt><dd>'+ui.e(p['task'])+'</dd><dt>다음 단계로 갈 때</dt><dd>'+ui.e(p['next'])+'</dd>'
        if not compact:body+='<dt>교재·자료 후보</dt><dd>'+ui.e(p['materials'])+'</dd>'
        body+='</dl></article>'
    body+='</div>'
    if compact:body+=actions([(pr(stage,subject)+'#levels',STAGES[stage]+' '+subject+' 수준별 공부 순서·자료 보기')])
    else:body+='<p class="cu-note">교재명은 후보입니다. 학년·학기·개정판과 현재 수준을 확인하고, 실제 사용 교재는 지점에 문의하세요.</p>'
    return section('levels','기초·표준·심화, 지금 필요한 연습은 무엇일까요?',body)

EVIDENCE={'국어':['지문에서 찾은 근거','내가 쓴 요약·답안','고쳐 쓴 문장과 이유'],'영어':['어휘·표현의 뜻과 쓰임','문장의 구조와 내용','직접 말하거나 쓴 표현'],'수학':['문제의 조건과 단위','식·그림·그래프를 연결한 풀이','틀린 단계와 다시 해결한 결과'],'사회':['자료의 출처와 시점','개념으로 설명한 사례','사실·의견과 판단의 근거'],'과학':['관찰·측정한 사실과 단위','변인·모형·그래프의 관계','자료가 뒷받침하는 결론'],'역사':['사료의 시대·지역·관점','사건의 배경·전개·결과','자료로 설명한 변화와 인과']}

def detail(row, overview, plans):
    stage=row['grade'][0];sub=row['subject'];g=row['grade'];title=grade_name(g)+' '+sub+' 공부 커리큘럼';special=g in ['초1','초2'] and sub in ['영어','사회','과학']
    if special:title=grade_name(g)+' '+sub+(' 선택 활동' if sub=='영어' else ' 통합교과 연계 활동')
    description=row['summary'];body=hero(title,description,['2026 학습 범위',row['revision'],row['scope']])
    body+=actions([(pr(stage,sub),STAGES[stage]+' '+sub+' 학년별로 비교'),('#study-order','공부 순서'),('#practice','확인 과제')])
    body+='<p class="cu-note">'+NOTE+'</p><div class="cu-reading">'
    contents=[('focus','학습 내용'),('study-order','공부 순서'),('practice','확인 과제'),('school-check','학교 자료 확인'),('parent-check','학부모 질문')]
    if not special:contents.insert(3,('levels','수준별 학습'))
    body+='<nav class="cu-toc" aria-label="커리큘럼 본문 바로가기">'+''.join(ui.link('#'+id,h) for id,h in contents)+'</nav>'
    scope=para(row['focus'])+'<div class="cu-callout"><h3>이 학년에서 함께 살필 부분</h3>'+para(overview[g]['priority'])+'</div>'
    if special:scope+='<p class="cu-note">'+('초1·2 영어는 정규 영어 교과가 아닌 선택 활동입니다. 노래·그림·인사 활동을 흥미에 맞춰 선택하며 선행 필수 과정으로 정하지 않습니다.' if sub=='영어' else '초1·2의 '+sub+'는 독립된 정규 '+sub+' 과목 안내가 아닙니다. 슬기로운 생활과 연결한 관찰·생활 활동으로 살펴보세요.')+'</p>'
    if stage=='고' and g!='고1':scope+='<p class="cu-note">고2·고3 범위는 실제 선택·이수 과목에 따른 예시입니다. 아래 과목이 모든 학교에서 같은 학년에 개설되는 것은 아닙니다.</p>'
    body+=section('focus','어떤 내용을 공부하고 무엇을 연결할까요?',scope)
    body+=section('study-order',g+' '+sub+' 공부 순서',steps(row['sequence'])+'<p>학교에서 이미 배운 부분과 혼자 설명하기 어려운 부분을 표시하세요. 필요한 단계부터 시작하고 실제 교과서 순서에 맞춰 조정합니다.</p>')
    body+=section('practice','이 과제로 이해한 내용을 확인해 보세요','<div class="cu-task"><p class="cu-kicker">'+g+' '+sub+' 확인 과제</p><h3>'+ui.e(row['task'])+'</h3>'+bullets(EVIDENCE[sub])+'</div><p>먼저 자료를 보며 익힌 뒤, 혼자 설명하거나 해결한 결과를 남겨 보세요. 빠진 근거와 막힌 단계를 원자료와 대조하면 다음 연습을 정하기 좋습니다.</p>')
    if not special:body+=level_section(stage,sub,plans,compact=True)
    body+=section('school-check','우리 학교의 실제 진도와 맞추기',para(row['school'])+bullets(['교과서의 과목명·출판사·학년·학기와 현재 단원','학교가 안내한 평가 범위·서술형 및 수행 과제','혼자 해결한 학습 자료와 설명이 필요한 부분']))
    if g in ['중3','고3']:body+='<p class="cu-note">2026년 '+g+'은 2015 개정 기준입니다. 2027년부터는 2022 개정 적용 범위로 다시 확인해야 합니다.</p>'
    questions=['“'+row['task']+'”에서 혼자 한 부분은 어디까지인가요?','답을 확인하기 전 어떤 근거나 방법을 사용했나요?','다음에 다시 확인할 내용은 무엇이며 어떤 자료로 볼까요?']
    body+=section('parent-check','학부모가 함께 물어볼 질문',bullets(questions)+'<p>완료한 문제 수와 함께 학생이 설명한 내용을 보세요. 다음 과제의 양과 기간은 현재 학습 공백, 학교 일정과 가능한 공부 시간에 맞춰 정합니다.</p>')
    related=[(sr(stage),STAGES[stage]+' 전체 과목'),('/학습가이드/','공부 방법·복습 학습가이드')]
    if sub in ['영어','수학']:related.append(('/교재안내/'+STAGES[stage]+sub+'/',STAGES[stage]+' '+sub+' 교재 후보'))
    if stage=='고' and g!='고3':related.append((BASE+'고등선택과목/#subject-'+sub,'고등 '+sub+' 과목 선택과 준비 개념'))
    body+=section('next-reading','공부 방법과 자료를 이어서 찾아보세요',actions(related))
    faq=[(g+' '+sub+' 공부는 어디부터 시작하면 좋을까요?','이 자료의 공부 순서는 “'+row['sequence']+'”입니다. 현재 교과서와 진도를 먼저 확인하고, 혼자 설명하기 어려운 단계부터 조정해 보세요.'),('이 커리큘럼이 우리 지점의 실제 수업인가요?','학생과 학부모를 위한 공부 계획 참고 자료입니다. 지점의 실제 운영 과목·학년·교재·시간표는 지점 안내와 상담에서 따로 확인하세요.')]
    if special:faq.insert(1,('초1·2에서 이 활동을 정규 교과로 배우나요?','영어는 정규 교과 밖의 선택 활동이며, 사회·과학 연계 내용은 슬기로운 생활과 연결한 활동입니다. 학교의 실제 편제를 기준으로 확인하세요.'))
    body+=section('questions','자주 묻는 질문',ui.faqs_markup(faq))+refs(row['url'],row['sourceRange'])+finder(ui.REGIONS)+'</div>'
    crumbs=[('학습커리큘럼',BASE),(STAGES[stage],sr(stage)),(sub,pr(stage,sub)),(g+' '+sub,gr(row))]
    node={'@type':'Article','headline':title,'description':description,'inLanguage':'ko-KR','author':{'@type':'Organization','name':'전국수업.com'},'datePublished':DAY,'dateModified':DAY,'mainEntityOfPage':{'@id':ui.url(gr(row))+'#webpage'},'citation':[row['url']]}
    return {**emit(gr(row),title,description,body,crumbs,faq,[node]),'type':'grade-subject','grade':g,'subject':sub,'sourceSheet':row['sourceSheet'],'sourceRow':row['sourceRow']}

def hubs(rows, overviews, plans):
    pages=[]
    for stage,label in STAGES.items():
        group=[r for r in rows if r['grade'].startswith(stage)];subjects=list(dict.fromkeys(r['subject'] for r in group))
        title=label+' 학년·과목별 공부 커리큘럼';description=label+'의 학년·과목별 학습 범위와 공부 순서, 확인 과제를 찾아보고 현재 수준과 학교 진도에 맞춰 계획합니다.'
        body=hero(title,'현재 학년의 내용을 살펴보고, 필요한 과목에서 공부 순서와 확인 과제를 골라 보세요. 기초·표준·심화 계획은 학습 도움을 정하는 참고 기준입니다.',[str(len(group))+'개 학년·과목 안내'])+actions([(pr(stage,sub),label+' '+sub) for sub in subjects])+para(NOTE)
        body+=section('grade-focus','학년이 바뀌면 함께 확인할 것','<div class="cu-grid">'+''.join('<article class="cu-card"><h3>'+grade_name(g)+'</h3>'+para(o['priority'])+para(o['check'])+'</article>' for g,o in overviews.items() if g.startswith(stage))+'</div>')
        body+=section('curriculum-list','우리 학년과 과목 찾아보기',filter_cards(group,stage))+actions([(BASE,'초·중·고 전체 커리큘럼')])+finder(ui.REGIONS)
        pages.append({**emit(sr(stage),title,description,body,[('학습커리큘럼',BASE),(label,sr(stage))],nodes=[list_items(group,title)],kind='CollectionPage'),'type':'stage'})
        for sub in subjects:
            selected=[r for r in group if r['subject']==sub];title=label+' '+sub+' 학년별 공부 커리큘럼';description=label+' '+sub+'의 학년별 학습 중점과 공부 순서를 비교하고, 기초·표준·심화 연습 및 확인 과제를 살펴봅니다.'
            body=hero(title,'어느 학년에서 무엇을 연결할지 먼저 확인하세요. 아래의 수준별 계획은 학교급·과목별 예시이므로 현재 학년의 과제와 함께 조정합니다.',[str(len(selected))+'개 학년 안내'])+actions([(gr(r),r['grade']+' '+sub) for r in selected])+para(NOTE)
            if stage=='초' and sub in ['영어','사회','과학']:body+='<p class="cu-note">초1·2 영어는 선택 활동이며 사회·과학은 통합교과 연계 활동입니다. 아래 학교급 공통 교재와 연습은 해당 과목을 이수하는 학년·수준에 맞춰 선택하세요.</p>'
            body+=section('curriculum-list','학년별 내용과 확인 과제',filter_cards(selected,stage,sub))+level_section(stage,sub,plans)
            body+=section('planning','학교와 학생에 맞춰 계획을 조정하세요',bullets(['현재 학교의 교과서·단원 순서·평가 범위를 우선 확인합니다.','학년과 점수 하나로 수준을 고정하지 않고 실제 설명·풀이·산출물을 확인합니다.','필요한 개념을 보완하고 익숙하지 않은 자료에도 적용하는지 확인합니다.']))
            links=[(sr(stage),label+' 다른 과목'),('/학습가이드/','공부 방법과 복습')]
            if sub in ['영어','수학']:links.append(('/교재안내/'+label+sub+'/',label+' '+sub+' 교재 안내'))
            if stage=='고':links.append((BASE+'고등선택과목/#subject-'+sub,'2022 개정 선택과목 준비 개념'))
            body+=actions(links)+refs(selected[0]['url'],selected[0]['sourceRange'])+finder(ui.REGIONS)
            pages.append({**emit(pr(stage,sub),title,description,body,[('학습커리큘럼',BASE),(label,sr(stage)),(sub,pr(stage,sub))],nodes=[list_items(selected,title)],kind='CollectionPage'),'type':'stage-subject','stage':stage,'subject':sub})
    return pages

def selection_page(rows):
    title='고등 공통·선택과목, 학습 범위와 준비 개념';description='2022 개정 고등 공통·선택과목 29개 묶음의 학습 범위와 준비 개념을 비교하고 학교의 실제 개설·선이수 관계를 확인합니다.'
    body=hero(title,'과목명과 준비 개념을 함께 보고 학교의 실제 개설 학년·학기와 이수 계획을 확인하세요. 2022 개정 기준의 주요 과목 묶음으로, 전체 선택과목 목록은 아닙니다.',['2022 개정 기준','29개 과목 묶음'])
    body+='<p class="cu-note">2026년 고1·고2의 과목 선택에 참고하세요. 2026년 고3은 2015 개정 기준이므로 아래 과목명·범위를 그대로 적용하지 않습니다.</p>'
    body+=actions([('#subject-'+sub,sub) for sub in ['국어','수학','영어','사회','역사','과학']])
    for sub in ['국어','수학','영어','사회','역사','과학']:
        content='<div class="cu-grid">'
        for r in [r for r in rows if r['subject']==sub]:
            content+='<article class="cu-card"><p class="cu-kicker">'+ui.e(r['category'])+'</p><h3>'+ui.e(r['name'])+'</h3><dl><dt>다루는 내용</dt><dd>'+ui.e(r['scope'])+'</dd><dt>먼저 확인할 개념</dt><dd>'+ui.e(r['prerequisite'])+'</dd><dt>공부 연결 예시</dt><dd>'+ui.e(r['connection'])+'</dd></dl></article>'
        content+='</div>'+actions([(pr('고',sub),'고등 '+sub+' 학년별 공부 계획')]);body+=section('subject-'+sub,sub+' 공통·선택과목',content)
    body+=section('school-check','선택 전에 학교에서 확인할 것',bullets(['입학 연도와 적용 교육과정, 실제 개설 학년·학기','공통과목 대체 편성 여부와 선택과목 선이수 관계','학교 이수 과목과 해당 응시 연도의 공식 시험 범위']))+refs(MOE,'각 교과의 공통·선택과목 내용 체계')+finder(ui.REGIONS)
    return {**emit(BASE+'고등선택과목/',title,description,body,[('학습커리큘럼',BASE),('고등선택과목',BASE+'고등선택과목/')],kind='CollectionPage'),'type':'selection'}

def root_page(rows):
    title='초·중·고 학년·과목별 공부 커리큘럼';description='초1부터 고3까지 국어·영어·수학·사회·과학·역사의 학습 범위와 공부 순서를 찾고 기초·표준·심화 연습 및 확인 과제를 살펴봅니다.'
    body=hero('우리 아이의 공부,\n무엇부터 연결할까요?','학년과 과목을 고르면 배울 내용, 공부 순서, 이해를 확인할 과제를 볼 수 있습니다. 기초부터 다시 연결할 때와 배운 내용을 넓힐 때 필요한 연습도 함께 살펴보세요.',['초1~고3','66개 학년·과목 안내','기초·표준·심화 계획'])
    body+=actions([(sr(s),label+' 커리큘럼') for s,label in STAGES.items()]+[(BASE+'고등선택과목/','고등 선택과목 준비')])
    body+='<p class="cu-note">'+NOTE+'</p>'
    body+=section('curriculum-list','학년과 과목에 맞는 공부 계획 찾기',filter_cards(rows))
    body+=section('how-to-start','공부 계획은 이렇게 골라 보세요','<div class="cu-grid">'+''.join('<article class="cu-card"><span class="cu-kicker">'+str(i)+'단계</span><h3>'+h+'</h3>'+para(p)+'</article>' for i,(h,p) in enumerate([('학년과 실제 교과서 확인','학교급과 학년을 고르고 현재 교과서의 단원·진도를 확인합니다. 초1·2의 영어 선택 활동과 사회·과학 연계 활동은 정규 독립 과목과 구분합니다.'),('혼자 설명할 수 있는 부분 찾기','확인 과제를 보고 학생이 이해한 부분과 도움을 받은 부분을 나눕니다. 과목마다, 같은 과목의 영역마다 필요한 학습 수준이 다를 수 있습니다.'),('공부 순서를 정하고 다시 확인하기','현재 필요한 개념부터 공부하고 자신의 말·글·풀이로 확인합니다. 다음 단계는 점수 하나보다 실제 수행을 함께 보고 조정합니다.')],1))+'</div>')
    body+=section('school-year','학교 교육과정과 맞춰 볼 부분','<p>2026년에는 초1~6·중1~2·고1~2에 2022 개정이 적용됩니다. 중3·고3은 2015 개정 기준이며, 2027년부터 2022 개정 적용 범위로 다시 확인해야 합니다.</p><p>중학교 사회·역사의 이수 학년과 고등 선택과목의 개설 학년·학기는 학교마다 다릅니다. 학생이 사용하는 교과서와 학교 안내를 기준으로 범위를 정하세요.</p>'+ui.link(MOE,'교육부 교육과정 안내 확인',True))
    body+=section('related-learning','공부 방법·교재·수업을 함께 찾아보세요',actions([('/학습가이드/','과목별 공부 방법과 복습'),('/교재안내/','영어·수학 교재 비교'),('/교육정보/','학생·학부모 교육정보'),('/지점안내/','지점별 수업·교육비 확인')]))+finder(ui.REGIONS)
    return {**emit(BASE,title,description,body,[('학습커리큘럼',BASE)],nodes=[list_items(rows,title)],kind='CollectionPage'),'type':'root'}

def recommendations(context):
    stage=context.get('stage');subject=context.get('subject','');stages=context.get('stages') or list(STAGES)
    if stage:
        if subject in ['국어','영어','수학','사회','과학','역사']:links=[(pr(stage,subject),STAGES[stage]+' '+subject+' 학년별 공부 순서')]
        else:links=[(sr(stage),STAGES[stage]+' 학년·과목별 공부 계획'),(pr(stage,'수학'),STAGES[stage]+' 수학 커리큘럼'),(pr(stage,'영어'),STAGES[stage]+' 영어 커리큘럼')]
    elif subject in ['국어','영어','수학','사회','과학','역사']:links=[(pr(s,subject),STAGES[s]+' '+subject+' 학년별 공부 계획') for s in stages]
    else:links=[(sr(s),STAGES[s]+' 학년·과목별 공부 계획') for s in stages]
    return links+[(BASE,'전체 학습커리큘럼 찾기')]

def module(context):
    label=(STAGES[context['stage']]+' ' if context.get('stage') else '')+context.get('subject','')
    return '<section class="cu-related" id="learning-curriculum" aria-labelledby="learning-curriculum-title"><p class="cu-kicker">학생·학부모 학습 자료</p><h2 id="learning-curriculum-title">'+ui.e((label.strip()+' ' if label.strip() else '')+'공부, 무엇부터 확인할까요?')+'</h2><p>학년별 학습 내용과 공부 순서, 기초·표준·심화 연습을 살펴보고 지금 필요한 과제를 골라 보세요.</p>'+actions(recommendations(context))+'<p class="cu-related-note">학습 계획 참고 자료이며, 실제 수업의 학년·과목·교재는 지점에서 확인하세요.</p></section>'

def refresh_manifest(baseline, added):
    public=sorted(set(baseline['files'])|set(added));files={};texts={}
    for name in public:
        raw=(ROOT/name).read_bytes();files[name]=hashlib.sha256(raw).hexdigest()
        if re.search(r'\.(html|css|js|mjs|json|xml|txt|svg|webmanifest)$',name):texts[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
    count=len(etree.parse(str(ROOT/'sitemap.xml')).getroot())
    save(ROOT/'release-public-manifest.json',{**baseline,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':count,'files':files,'textSha256':texts})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workbook',type=Path);ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--refresh-manifest',action='store_true');a=ap.parse_args();out=a.audit;out.mkdir(parents=True,exist_ok=True)
    if a.refresh_manifest:refresh_manifest(load(out/'before-manifest.json'),load(out/'build-audit.json')['addedPublicFiles']);return
    assert a.workbook and a.workbook.is_file()
    assert not (ROOT/'curriculum-data.json').exists(), 'Already generated; do not replace reviewed content'
    w=openpyxl.load_workbook(a.workbook,read_only=True,data_only=True);data={s.title:[list(r) for r in s.iter_rows(values_only=True)] for s in w};w.close()
    rows=[]
    keys=['grade','subject','revision','scope','focus','sequence','task','school','summary','url','sourceRange']
    for sheet in ['초등과목','중등과목','고등과목']:
        for i,row in enumerate(data[sheet][5:],6):rows.append({**dict(zip(keys,row)),'sourceSheet':sheet,'sourceRow':i})
    overviews={r[1]:dict(stage=r[0],revision=r[2],subjects=r[3],priority=r[4],check=r[5],url=r[6]) for r in data['학년별개요'][5:]}
    plans=[dict(zip(['stage','subject','level','target','sequence','task','next','materials','adjustment','url'],r)) for r in data['반별운영'][5:]]
    choices=[dict(zip(['subject','category','name','scope','prerequisite','connection','school','url','sourceRange'],r)) for r in data['고등선택과목'][5:]]
    assert len(rows)==66 and len(overviews)==12 and len(plans)==45 and len(choices)==29
    baseline=load(ROOT/'release-public-manifest.json');save(out/'before-manifest.json',baseline)
    for f in ['seo-descriptions.json','site-shell-data.json','sitemap.xml','rss.xml','llms.txt']:(out/('before-'+f)).write_bytes((ROOT/f).read_bytes())
    with zipfile.ZipFile(out/'before-html.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name in baseline['files']:
            if name.endswith('.html'):z.writestr(name,(ROOT/name).read_bytes())
    pages=[detail(r,overviews,plans) for r in rows]+hubs(rows,overviews,plans)+[selection_page(choices),root_page(rows)]
    contexts=load(ROOT/'contextual-links-data.json')['pages'];existing=[]
    for item in contexts:
        if item['context']['kind']=='system':continue
        name=item['file'];old=(ROOT/name).read_text(encoding='utf-8');text=old
        text=text.replace('<!-- contextual-links:module:end -->','<!-- contextual-links:module:end -->'+marked('module',module(item['context'])),1)
        jump='<nav class="cu-jump" aria-label="학습커리큘럼 바로가기">'+ui.link('#learning-curriculum','학년·과목별 공부 커리큘럼 보기')+'</nav>'
        text=text.replace('<!-- contextual-links:jump:end -->','<!-- contextual-links:jump:end -->'+marked('jump',jump),1);text=style(text)
        assert text!=old and strip(text)==strip(old),name
        ui.write(ROOT/name,text);existing.append({'file':name,'context':item['context'],'links':[p for p,_ in recommendations(item['context'])]})
    for name in ['index.html','학습가이드/index.html','교재안내/index.html','교육정보/index.html']:
        old=(ROOT/name).read_text(encoding='utf-8');block=marked('module',module({'stages':list(STAGES)}))
        if name=='index.html':text=old.replace('<!-- home-library:content:end -->','<!-- home-library:content:end -->'+block,1)
        else:
            main=old.index('<main');tag=re.search(r'<(?:section|header)\b[^>]*class="[^"]*(?:bd-hero|ei-hero)[^"]*"[^>]*>',old[main:]);assert tag,name
            start=main+tag.start();kind=tag.group().split()[0][1:];end=old.index('</'+kind+'>',start)+len('</'+kind+'>');text=old[:end]+block+old[end:]
        text=style(text);assert text!=old and strip(text)==strip(old),name;ui.write(ROOT/name,text)
        existing.append({'file':name,'context':{},'links':[p for p,_ in recommendations({})]})
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';sitemap=etree.parse(str(out/'before-sitemap.xml')).getroot();seen={unquote(urlsplit(x.find('{'+ns+'}loc').text).path) for x in sitemap}
    for p in pages:
        assert p['route'] not in seen,p['route'];entry=etree.SubElement(sitemap,'{'+ns+'}url');etree.SubElement(entry,'{'+ns+'}loc').text=ui.url(p['route']);etree.SubElement(entry,'{'+ns+'}lastmod').text=DAY
    changed={route(p['file']) for p in existing}
    for entry in sitemap:
        if unquote(urlsplit(entry.find('{'+ns+'}loc').text).path) in changed:
            date=entry.find('{'+ns+'}lastmod')
            if date is None:date=etree.SubElement(entry,'{'+ns+'}lastmod')
            date.text=DAY
    (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
    llms=(out/'before-llms.txt').read_text(encoding='utf-8')+'\n\n## 학년·과목별 공부 커리큘럼\n\n'
    llms+='공부 계획 참고 자료이며 실제 지점 운영을 확정하지 않습니다.\n'+''.join('- '+p['title']+': '+ui.DOMAIN+p['route']+'\n' for p in pages);ui.write(ROOT/'llms.txt',llms)
    save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS);shell=load(ROOT/'site-shell-data.json');shell['pages']=sorted(set(shell['pages'])|set(ui.NEW));save(ROOT/'site-shell-data.json',shell)
    result={'version':1,'sourceWorkbook':a.workbook.name,'sourceSha256':hashlib.sha256(a.workbook.read_bytes()).hexdigest(),'note':NOTE,'gradeSubjects':rows,'levelPlans':plans,'choices':choices,'pages':pages,'existingPages':existing}
    save(ROOT/'curriculum-data.json',result)
    added=[p['file'] for p in pages]+['assets/curriculum.css','assets/curriculum.js']
    report={'pagesCreated':len(pages),'gradeSubjectPages':len(rows),'levelPlans':len(plans),'choiceGroups':len(choices),'contextModules':len(existing),'changedPublicFiles':[p['file'] for p in existing]+added+['sitemap.xml','llms.txt'],'addedPublicFiles':added,'beforeSitemap':len(seen)}
    save(out/'build-audit.json',report);refresh_manifest(baseline,added);print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},ensure_ascii=False))

if __name__=='__main__':main()

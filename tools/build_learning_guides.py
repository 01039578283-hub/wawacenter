"""Render the researched learning library while preserving every other public page.

Use --audit with the captured baseline folder; do not deploy as part of generation.
"""
import argparse, hashlib, json, re, zipfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import etree
import build_branch_upgrade as ui
import build_site_shell as common
from learning_guides import PAGES, GROUPS, SOURCES, LEVELS

ROOT=ui.ROOT
E=ui.e
GROUP_NAMES={g:n for g,n,_ in GROUPS}
BY_SLUG={p['slug']:p for p in PAGES}
HUB='/학습가이드/'
HUB_TITLE='학생·학부모를 위한 학습가이드'
COUNT=len(PAGES)
HUB_DESCRIPTION=f'학생·학부모를 위한 {COUNT}개 학습가이드에서 과목별 공부 방법과 시험 준비 순서를 찾고 실천 기록을 작성합니다.'
SECTION_NAMES=[('check','먼저 확인'),('steps','실행 순서'),('example','연습 예시'),('record','기록 양식'),('mistakes','주의할 점'),('next','다음 점검'),('faq','자주 묻는 질문'),('sources','참고 자료'),('related','함께 볼 가이드')]

def card(p,filterable=False):
    attrs=f' data-guide-card data-category="{p["group"]}" data-levels="{" ".join(p["levels"])}" data-search="{E(" ".join([p["title"],p["description"],p["audience"],p["tags"]]))}"' if filterable else ''
    badge='<span class="lg-new">새 가이드</span>' if p.get('isNew') else ''
    return f'<article class="bd-card lg-guide-card"{attrs}>{badge}<p class="lg-card-audience">{E(p["audience"])}</p><h3>{ui.link(p["route"],p["title"])}</h3><p class="lg-card-desc">{E(p["description"])}</p>'+f'<a class="lg-card-link" href="{ui.href(p["route"])}" aria-label="{E(p["title"])} 자세히 읽기">가이드 읽기 <span aria-hidden="true">→</span></a></article>'

def shell(route,title,description,body,crumbs,nodes,faqs=(),article=False):
    captured={};original=ui.write
    ui.write=lambda path,text:captured.update(path=path,text=text)
    try:ui.shell(route,title,description,body,crumbs,faqs=faqs,nodes=nodes,kind='WebPage' if article else 'CollectionPage')
    finally:ui.write=original
    text=captured['text'].replace('</head>','<link rel="stylesheet" href="/assets/learning-guides.css"><script type="module" src="/assets/learning-guides.js"></script><link rel="stylesheet" href="/assets/site-shell.css"></head>')
    text=re.sub(r'<header\b[^>]*>.*?</header>',lambda _:common.header(route),text,count=1,flags=re.S)
    text=text.replace('<body ', '<body data-site-shell="1" ',1)
    text=text.replace('class="general-page bd-page"','class="general-page bd-page lg-page'+(' lg-article' if article else ' lg-hub')+'"')
    if article:text=text.replace('property="og:type" content="website"','property="og:type" content="article"')
    original(captured['path'],text)

def record_editor(p):
    fields=''.join(f'<label for="record-field-{i}">{E(label)}<textarea id="record-field-{i}" name="field-{i}" rows="3" maxlength="1600" placeholder="{E(value)}" data-record-field data-label="{E(label)}"></textarea></label>' for i,(label,value) in enumerate(p['record'],1))
    return '<div class="lg-editor" data-guide-record hidden data-title="'+E(p['title'])+'" data-url="'+E(ui.url(p['route']))+'" data-filename="'+E(p['slug']+'-실천기록.txt')+'"><fieldset><legend>페이지에서 직접 실천 기록 작성하기</legend><p class="lg-record-note">작성 내용은 사이트에 전송되지 않습니다. 파일로 저장하기 전에 페이지를 떠나면 지워집니다.</p><label for="record-date">작성 날짜<input type="date" id="record-date" name="record-date" data-record-date></label><div class="lg-editor-fields">'+fields+'</div></fieldset><div class="bd-actions"><button class="bd-btn bd-btn-primary" type="button" data-record-download disabled>작성한 기록 TXT 저장</button><button class="bd-btn" type="button" data-record-print disabled>작성한 기록 인쇄</button></div><p data-record-status role="status" aria-live="polite">한 항목 이상 작성하면 기록을 저장하거나 인쇄할 수 있습니다.</p></div>'

def render_article(p,legacy,published):
    route=p['route']
    body=f'<article data-learning-guide="{E(p["slug"])}"><header class="bd-hero"><p class="bd-kicker">학습가이드 / {E(GROUP_NAMES[p["group"]])}</p><h1>{E(p["title"])}</h1><p class="lg-audience">{E(p["audience"])}</p><div class="lg-dates"><span>처음 게시 <time datetime="{published}">{published}</time></span><span>내용 업데이트 <time datetime="{ui.DAY}">{ui.DAY}</time></span></div></header>'
    body+=f'<div class="lg-answer" data-guide-answer><strong>먼저 알아둘 답</strong><p>{E(p["answer"])}</p></div>'
    body+='<nav class="lg-toc" aria-label="가이드 목차">'+''.join(ui.link('#'+k,n) for k,n in SECTION_NAMES)+'</nav>'
    def section(id,title,content,lead='',alias=None):
        return (f'<span class="lg-legacy" id="section-{alias}" aria-hidden="true"></span>' if legacy and alias else '')+ui.section(id,title,content,lead)
    body+=section('check','지금 상황을 먼저 확인하세요','<div class="lg-checks">'+''.join(f'<div class="bd-card"><h3>{E(h)}</h3><p>{E(t)}</p></div>' for h,t in p['checks'])+'</div>',alias=1)
    body+=section('steps','이 순서로 직접 해 보세요','<ol class="lg-steps">'+''.join(f'<li class="lg-step"><span class="lg-step-number" aria-hidden="true">{i:02}</span><div><h3>{E(h)}</h3><p>{E(t)}</p></div></li>' for i,(h,t) in enumerate(p['steps'],1))+'</ol>',alias=2)
    h,paragraphs=p['example']
    body+=section('example','자료에 적용하는 연습 예시',f'<div class="lg-example"><h3>{E(h)}</h3>'+''.join(f'<p>{E(t)}</p>' for t in paragraphs)+'</div>',alias=3)
    record='/assets/learning-records/'+p['slug']+'.txt'
    body+=section('record','기록 항목을 실제 과제에 적용하세요','<div class="lg-record"><dl>'+''.join(f'<div><dt>{E(label)}</dt><dd>{E(value)}</dd></div>' for label,value in p['record'])+'</dl><p class="lg-record-note">위 내용은 기록할 항목의 예시입니다. 빈 양식을 내려받거나 이 페이지에서 자신의 과제에 맞게 작성해 보세요.</p><div class="bd-actions"><a class="bd-btn bd-btn-primary" href="'+ui.href(record)+'" download="'+E(p['slug']+'-기록양식.txt')+'">빈 기록 양식 내려받기 (TXT)</a></div></div>'+record_editor(p),alias=4)
    body+='<section class="lg-print-record" hidden aria-label="인쇄할 실천 기록"><h2>작성한 실천 기록</h2><pre data-record-output></pre></section>'
    body+=section('mistakes','이 점은 구분해서 보세요','<div class="lg-mistakes"><ul>'+''.join(f'<li>{E(t)}</li>' for t in p['avoid'])+'</ul></div>')
    body+=section('next','다음 자료에서 다시 점검하세요','<div class="lg-next"><p>'+E(p['nextCheck'])+'</p></div>')
    body+=section('faq','자주 묻는 질문',ui.faqs_markup(p['faq']))
    bibliography=''
    for key in p['sources']:
        org,title,year,url,note=SOURCES[key]
        bibliography+='<li>'+ui.link(url,org+' · '+title,True)+f'<small>{E(year)} · {E(note)}</small></li>'
    body+=section('sources','더 살펴볼 참고 자료','<p class="lg-reference-note">아래 자료의 학습 원리를 참고해 실행 순서와 연습 예시를 구성했습니다. 예시의 일정·문장·문제는 적용 연습용이며 학교 평가 기준이나 특정 학생의 실제 결과가 아닙니다.</p><ul class="lg-sources">'+bibliography+'</ul>')
    extra=ui.link('/교재안내/','학년·영역별 교재 선택 자료')+' · '+ui.link('/교재안내/교재선택/','교재 선택 기준') if p['slug']=='교재선택복습' else ui.link('/교재안내/','교재 선택 자료')
    body+=section('related','다음 질문도 함께 살펴보세요','<div class="lg-related">'+''.join(card(BY_SLUG[slug]) for slug in p['related'])+'</div><p class="lg-bottom">'+ui.link(HUB+'#group-'+p['group'],GROUP_NAMES[p['group']]+' 가이드 전체')+' · '+ui.link(HUB,f'전체 {COUNT}개 가이드')+' · '+extra+'</p>')+'</article>'
    organization={'@type':'Organization','name':'와와센터 학습코칭','url':ui.url('/')}
    resource={'@type':['Article','LearningResource'],'@id':ui.url(route)+'#article','url':ui.url(route),'headline':p['title'],'description':p['description'],'inLanguage':'ko-KR','datePublished':published,'dateModified':ui.DAY,'author':organization,'publisher':organization,'mainEntityOfPage':{'@id':ui.url(route)+'#webpage'},'learningResourceType':'학습 가이드','audience':{'@type':'EducationalAudience','audienceType':p['audience']},'articleSection':GROUP_NAMES[p['group']],'citation':[SOURCES[k][3] for k in p['sources']]}
    shell(route,p['title'],p['description'],body,[('학습가이드',HUB),(p['title'],route)],[resource],p['faq'],True)
    lines=[p['title']+' — 빈 기록 양식','작성 날짜:','학생과 함께 볼 자료:','']
    for label,_ in p['record']:lines.extend([label+':','', ''])
    lines+=['다음 확인 날짜:','추가 질문:','', '가이드: https://전국수업.com'+route]
    file=ROOT/record.lstrip('/');file.parent.mkdir(parents=True,exist_ok=True)
    data=('\r\n'.join(lines)+'\r\n').encode('utf-8-sig')
    if not file.exists() or file.read_bytes()!=data:file.write_bytes(data)
    return record.lstrip('/')

def render_hub(book_entry):
    body=f'<section class="bd-hero"><p class="bd-kicker">LEARNING GUIDES</p><h1>학생과 학부모의 질문에서<br>시작하는 학습가이드</h1><p>학생의 지금 상황에 맞는 글을 찾고, 오늘 할 일을 정해 보세요.<br>과목별 연습·시험 준비·학부모 상담을 다루는 {COUNT}개 가이드와 실천 기록을 모았습니다.</p><div class="bd-tags"><span>6개 주제</span><span>{COUNT}개 가이드</span><span>실천 기록 작성·저장</span></div><div class="bd-actions">'+ui.button('#guide-results','대상·주제로 가이드 찾기',True)+ui.button('#reading-paths','어떤 순서로 읽을까요?')+'</div></section>'
    starts=[('시험이 2주 남았어요','시험2주준비','남은 범위와 우선순위'),('고등학교 준비가 막막해요','중등고등학년전환','현재 수행과 학교 안내'),('수학 해설을 봐야 풀려요','해설의존줄이기','막힌 줄과 필요한 도움'),('영어 글을 고쳐도 반복해서 틀려요','영어쓰기수정기록','초안과 수정 이유'),('방학에 무엇부터 복습할까요?','방학복습계획','한 가지 목표와 재확인'),('학원 상담 전에 볼 것은요?','학부모상담체크리스트','자료와 확인할 질문')]
    body+=ui.section('start','지금 필요한 질문부터 골라 보세요','<div class="lg-start">'+''.join(f'<a href="{ui.href(BY_SLUG[slug]["route"])}"><strong>{E(question)}</strong><span>{E(label)} <span aria-hidden="true">→</span></span></a>' for question,slug,label in starts)+'</div>')
    body+='<form id="guide-results" class="lg-search" data-guide-search role="search"><h2>지금 필요한 가이드 찾기</h2><div class="lg-search-row"><label for="guide-level">읽는 대상<select id="guide-level" name="level"><option value="">전체 대상</option>'+''.join(f'<option value="{key}">{name}</option>' for key,name in LEVELS)+'</select></label><label for="guide-query">찾고 싶은 내용<input id="guide-query" name="q" type="search" maxlength="100" placeholder="예: 단어, 수행평가, 숙제, 상담" autocomplete="off"></label><button class="bd-btn" type="reset">검색 초기화</button></div><div class="lg-filters" role="group" aria-label="가이드 주제 필터"><button type="button" data-guide-filter="" aria-pressed="true">전체 '+str(COUNT)+'</button>'+''.join(f'<button type="button" data-guide-filter="{key}" aria-pressed="false">{E(name)}</button>' for key,name,_ in GROUPS)+'</div></form><p class="lg-result" data-guide-status role="status" aria-live="polite">'+str(COUNT)+'개 가이드를 볼 수 있습니다.</p><noscript><p>검색 필터와 페이지 내 기록 작성은 자바스크립트를 켜면 사용할 수 있습니다. 아래 전체 목록과 빈 기록 양식은 그대로 이용할 수 있습니다.</p></noscript><nav class="bd-region-links" aria-label="주제별 가이드 바로가기">'+''.join(ui.link('#group-'+key,name) for key,name,_ in GROUPS)+'</nav><div class="lg-empty" data-guide-empty hidden><h2>검색 결과가 없습니다.</h2><p>검색어를 짧게 입력하거나 대상을 바꿔 보세요. 검색 초기화를 누르면 전체 가이드를 다시 볼 수 있습니다.</p></div>'
    for key,name,lead in GROUPS:
        pages=sorted([p for p in PAGES if p['group']==key],key=lambda p:not p.get('isNew'))
        body+=f'<section class="bd-section" id="group-{key}" data-guide-group aria-labelledby="group-{key}-title"><div class="lg-group-heading"><h2 id="group-{key}-title">{E(name)}</h2><span data-group-count>{len(pages)}개</span></div><p class="bd-lead">{E(lead)}</p><div class="lg-cards">'+''.join(card(p,True) for p in pages)+'</div></section>'
    paths=[('초등학생의 기초와 습관',['초등학생공부습관','수학문장제읽기','방학복습계획'],'작은 과제 한 가지를 혼자 끝낸 범위부터 확인합니다.'),('중학생의 시험 준비',['중학생내신공부법','시험2주준비','시험후학습점검'],'학교 범위·현재 수행·시험 뒤 수정할 행동을 연결합니다.'),('고등학생의 학습 계획',['중등고등학년전환','고등학생과목별공부법','고등수학모의고사분석'],'학교 안내와 과목별 어려움을 다른 목록으로 봅니다.'),('수학 풀이가 막힐 때',['수학기초점검','수학풀이비교','해설의존줄이기'],'필요한 개념·전략·도움의 범위를 구분합니다.'),('영어를 읽고 쓸 때',['영어문장구조읽기','영어지시어연결어','영어쓰기수정기록'],'문장 구조와 연결 관계를 수정 기록까지 이어갑니다.'),('보호자가 함께 도울 때',['학습대화방법','온라인학습점검','교재선택복습'],'관찰한 수행과 필요한 도움을 학생과 함께 정합니다.')]
    body+=ui.section('reading-paths','같은 고민의 가이드를 순서대로 읽어 보세요','<div class="lg-paths">'+''.join('<article class="bd-card"><h3>'+E(title)+'</h3><p>'+E(lead)+'</p><ol>'+''.join('<li>'+ui.link(BY_SLUG[s]['route'],BY_SLUG[s]['title'])+'</li>' for s in slugs)+'</ol></article>' for title,slugs,lead in paths)+'</div>')
    body+=book_entry
    body+=ui.section('use','가이드를 읽고 실제 자료에 적용해 보세요','<div class="lg-next"><p>글 하나를 고르고 실제 과제에 적용하세요. 글의 기록 항목에 혼자 한 부분과 남은 질문을 적고 TXT로 저장할 수 있습니다. 빈 양식은 입력 없이 내려받아 사용할 수 있습니다.</p><p>학교 평가의 범위·일정·답안 조건은 현재 학교 안내를 먼저 확인하세요. 수업의 학년·과목·시간·교육비는 '+ui.link('/지점안내/','실제 지점안내')+'와 해당 지점의 안내 조건을 함께 살펴보세요.</p></div>')
    ordered=[p for key,_,_ in GROUPS for p in sorted([p for p in PAGES if p['group']==key],key=lambda p:not p.get('isNew'))]
    listing={'@type':'ItemList','@id':ui.url(HUB)+'#guides','name':HUB_TITLE,'numberOfItems':COUNT,'itemListElement':[{'@type':'ListItem','position':i,'name':p['title'],'url':ui.url(p['route'])} for i,p in enumerate(ordered,1)]}
    shell(HUB,HUB_TITLE,HUB_DESCRIPTION,body,[('학습가이드',HUB)],[listing])

def update_feeds(audit,legacy):
    ns='http://www.sitemaps.org/schemas/sitemap/0.9'
    with zipfile.ZipFile(audit/'before-source.zip') as archive:
        root=etree.fromstring(archive.read('sitemap.xml'));rss=etree.fromstring(archive.read('rss.xml'));llms=archive.read('llms.txt').decode('utf-8-sig')
    routes={HUB,*[p['route'] for p in PAGES]};found=set()
    for entry in root:
        route=unquote(urlsplit(entry.find('{'+ns+'}loc').text).path)
        if route in routes:
            found.add(route);modified=entry.find('{'+ns+'}lastmod')
            if modified is None:modified=etree.SubElement(entry,'{'+ns+'}lastmod')
            modified.text=ui.DAY
    for route in sorted(routes-found):
        entry=etree.SubElement(root,'{'+ns+'}url');etree.SubElement(entry,'{'+ns+'}loc').text=ui.url(route);etree.SubElement(entry,'{'+ns+'}lastmod').text=ui.DAY
    (ROOT/'sitemap.xml').write_bytes(etree.tostring(root,encoding='utf-8',xml_declaration=True,pretty_print=True))
    channel=rss.find('channel')
    for item in list(channel.findall('item')):
        if unquote(urlsplit(item.findtext('link')).path).startswith(HUB):channel.remove(item)
    stamp=format_datetime(datetime.now(timezone(timedelta(hours=9))))
    channel.find('lastBuildDate').text=stamp
    for p in [dict(route=HUB,title=HUB_TITLE,description=HUB_DESCRIPTION),*PAGES]:
        item=etree.SubElement(channel,'item')
        for k,v in [('title',p['title']),('link',ui.url(p['route'])),('guid',ui.url(p['route'])),('description',p['description']),('pubDate',stamp)]:
            element=etree.SubElement(item,k);element.text=v
            if k=='guid':element.set('isPermaLink','true')
    (ROOT/'rss.xml').write_bytes(etree.tostring(rss,encoding='utf-8',xml_declaration=True,pretty_print=True))
    # Replace obsolete titles for the eight existing links, retain unrelated guidance.
    # Replace this bounded catalog; keep book and neighborhood sections intact.
    llms=re.sub(r'(?m)^## 학습가이드 전체 목록\n[\s\S]*?(?=^## |\Z)','',llms)
    lines=[]
    for line in llms.splitlines():
        match=re.search(r'https://[^\s]+',line)
        if match:
            route=unquote(urlsplit(match.group()).path)
            p=next((p for p in PAGES if p['route']==route),None)
            if p:line='- '+p['title']+': '+ui.url(route)
        lines.append(line)
    lines+=['','## 학습가이드 전체 목록','',HUB_DESCRIPTION,'']
    for key,name,_ in GROUPS:
        lines+=['### '+name,'']
        lines+=['- '+p['title']+': '+ui.url(p['route']) for p in PAGES if p['group']==key]
        lines+=['']
    ui.write(ROOT/'llms.txt','\n'.join(lines))
    return len(root)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args();audit=args.audit
    baseline=json.loads((audit/'before-manifest.json').read_text(encoding='utf-8-sig'))
    ui.DAY='2026-10-02';ui.NEW.clear()
    previous=json.loads((audit/'before-guides.json').read_text(encoding='utf-8'))
    old={p['route']:p for p in previous['pages']}
    legacy={p['route'] for p in previous['pages'] if p['legacy']}
    for p in PAGES:p['isNew']=p['route'] not in old
    dates={p['route']:old[p['route']]['datePublished'] if p['route'] in old else ui.DAY for p in PAGES}
    with zipfile.ZipFile(audit/'before-source.zip') as archive:
        original_hub=archive.read('학습가이드/index.html').decode('utf-8')
        book_entry=re.search(r'<!-- book-entry:start -->.*?<!-- book-entry:end -->',original_hub,re.S)[0]
    records=[render_article(p,p['route'] in legacy,dates[p['route']]) for p in PAGES];render_hub(book_entry)
    sitemap_count=update_feeds(audit,legacy)
    ui.save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
    data={'updated':ui.DAY,'hub':{'route':HUB,'title':HUB_TITLE,'description':HUB_DESCRIPTION},'groups':GROUPS,'levels':LEVELS,'sources':SOURCES,'pages':[{**p,'recordFields':p['record'],'datePublished':dates[p['route']],'record':'/assets/learning-records/'+p['slug']+'.txt','legacy':p['route'] in legacy} for p in PAGES]}
    ui.save(ROOT/'learning-guide-data.json',data)
    selected=set(baseline['files'])|set(ui.NEW)|set(records)|{'assets/learning-guides.css','assets/learning-guides.js','assets/learning-guide-tools.mjs'}
    shell_data=json.loads((ROOT/'site-shell-data.json').read_text(encoding='utf-8'))
    ui.save(ROOT/'site-shell-data.json',{**shell_data,'pages':sorted(n for n in selected if n.endswith('.html'))})
    files={};normalized={}
    for name in sorted(selected):
        raw=(ROOT/name).read_bytes();files[name]=hashlib.sha256(raw).hexdigest()
        if re.search(r'\.(html|css|js|mjs|json|xml|txt|svg|webmanifest)$',name):normalized[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')).hexdigest()
    manifest={**baseline,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':sitemap_count,'files':files,'textSha256':normalized}
    ui.save(ROOT/'release-public-manifest.json',manifest)
    summary={'guideArticles':COUNT,'existingImproved':len(old),'newArticles':sum(p['isNew'] for p in PAGES),'hubPages':1,'recordForms':COUNT,'groups':dict(Counter(p['group'] for p in PAGES)),'publicFiles':len(files),'htmlPages':sum(n.endswith('.html') for n in files),'sitemapPages':sitemap_count,'deployed':False}
    ui.save(audit/'generation-summary.json',summary);ui.save(audit/'source-register.json',{'checkedOn':ui.DAY,'sources':SOURCES})
    ui.write(audit/'preview-routes.json',json.dumps([HUB,*[p['route'] for p in PAGES]],ensure_ascii=False))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()

"""Build neighborhood hubs and one consolidated manuscript per area/stage."""
import argparse,hashlib,json,re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,unquote,urlsplit
from lxml import etree,html
import build_branch_upgrade as shared
from grade_editorial import TOPICS,STAGE_GUIDES
ROOT=shared.ROOT
DAY='2026-10-01'
DATA=json.loads((ROOT/'grade-directory-data.json').read_text(encoding='utf-8'))
PAGES=DATA['pages'];BYPATH={p['route']:p for p in PAGES}
BRANCHES={b['route']:b for b in shared.BRANCHES}
AREAS={a['slug']:a for a in json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'))['areas']}
TOPIC={x[0]:x for x in TOPICS}
LABELS={'초':'초등학생학원','중':'중학생학원','고':'고등학생학원'}
NAMES={'초':'초등학생','중':'중학생','고':'고등학생'}
ALLHUBS={p['hub']:p['area'] for p in PAGES}
LEGACY={f'/과목별학원/{p["category"]}/{p["area"]}/':p['route'] for p in PAGES}
MODIFIED=set()
e,link,section,write,url=shared.e,shared.link,shared.section,shared.write,shared.url
def object_particle(text):
    last=ord(text[-1]);return '을' if 0xAC00<=last<=0xD7A3 and (last-0xAC00)%28 else '를'

def scope(p):
    known=[c['subject']+' '+shared.grade_label(c['grades']) for c in p['courses'] if c['grades']]
    return ' / '.join(known) or '자료상 안내 학년을 확인하지 못했습니다. 개설 여부를 먼저 문의해 주세요.'

def cards(p):
    markup='<div class="bd-grid gd-course-grid">'
    for c in p['courses']:
        markup+=f'<article class="bd-card" data-stage-course="{e(c["subject"])}" data-grades="{e(",".join(c["grades"]))}" data-pending="{e(",".join(c["pending"]))}"><h3>{e(c["subject"])}</h3><div class="bd-grade">'+e(shared.grade_label(c['grades']) or '개설 학년 확인 필요')+'</div>'
        if c['pending']:markup+='<p class="bd-pending">별도 확인: '+e(shared.grade_label(c['pending']))+'. 운영 조건과 함께 상담해 주세요.</p>'
        if not c['grades'] and not c['pending']:markup+='<p>제공 자료에 이 학년의 개설 범위가 없습니다. 수업이 없다는 뜻은 아니며, 현재 안내를 확인해야 합니다.</p>'
        markup+=''.join('<p class="bd-course-note">'+e(n)+'</p>' for n in c['notes'])+'</article>'
    return markup+'</div>'

def photo(b):
    if not b['photos']:return '<p>지점 사진과 공간 안내는 '+link(b['route']+'#photos',b['name']+' 사진 안내')+'에서 확인해 주세요.</p>'
    image=b['photos'][0];large=image['large'];small=image['small']
    return f'<figure class="bd-photo gd-branch-photo"><a href="{shared.href(b["route"]+"#photos")}"><img src="{shared.href(small["src"])}" width="{large["width"]}" height="{large["height"]}" loading="lazy" decoding="async" alt="{e(b["name"])} 제공 공간 사진"></a><figcaption>'+e(b['name'])+'에서 제공한 사진입니다. 현재 배치는 상담에서 확인해 주세요.</figcaption></figure>'

def details(p):
    b=BRANCHES[p['branch']];a=AREAS[p['area']];stage=NAMES[p['prefix']];focus=TOPIC[p['topics'][0]]
    title=p['name']+' '+p['category']+' | '+b['name']+' 학년·교육비와 상담 기준'
    desc=f'{p["name"]} {stage} 학습을 위해 {b["name"]}의 과목별 안내 학년과 교육비 자료, 학교 정보 및 상담 질문을 확인합니다.'
    assert len(desc)<=80,(p['area'],desc)
    known=any(c['grades'] for c in p['courses'])
    intro=f'{p["name"]}에서 {p["category"]}을 알아볼 때는 학생의 학년과 희망 과목을 먼저 맞춰 보세요. 이 동네와 연결된 {b["name"]}의 자료를 바탕으로 개설 학년과 교육비 확인 경로, 상담에서 물어볼 내용을 정리했습니다.'
    hero=f'<section class="bd-hero gd-hero"><p class="bd-kicker">{e(b["region"])} · {e(b["district"])} / {stage} 학습 안내</p><h1>{e(p["name"])} {stage} 학습과<br>수업 선택 안내</h1><p>{e(intro)}</p><p class="gd-answer"><strong>연결 지점: {e(b["displayName"])}</strong><br>{e(b["address"])}</p>'+shared.actions([(shared.FORM,stage+' 학습 상담',True,True),(p['branch'],b['name']+' 종합 안내',False)])+'</section>'
    if not known:hero+='<p class="bd-notice gd-status">'+e(b['name'])+'의 '+stage+' 개설 학년을 제공 자료에서 확인하지 못했습니다. 등록 가능 여부와 과목을 먼저 상담해 주세요.</p>'
    if b['addressPending']:hero+='<p class="bd-notice">주소 자료가 서로 달라 현재 위치를 방문 전에 확인해야 합니다.</p>'
    jump='<nav class="bd-jump" aria-label="학년 안내 바로가기">'+''.join(link('#'+key,label) for key,label in [('lesson-image','상세 안내'),('courses','과목·학년'),('learning','상담 기준'),('fees','교육비'),('schools','학교·위치'),('faq','질문')])+'</nav>'
    image=b['bodyImage'];picture=f'<div class="bd-image-panel"><picture><source media="(max-width:800px)" srcset="{shared.href(image["mobile"])}"><img src="{shared.href(image["src"])}" width="918" height="16116" alt="와와 학습코칭의 수업과 학습 관리 상세 안내" loading="eager" decoding="async"></picture></div>'
    body=hero+jump+section('lesson-image','학습코칭 수업을 자세히 살펴보세요',picture,'공통 수업 안내입니다. 실제 개설 과목과 학년은 아래 지점 자료를 함께 확인해 주세요.')
    body+=section('courses',b['name']+' '+stage+' 과목별 안내 학년',cards(p)+''.join('<p class="bd-notice">'+e(n)+'</p>' for n in p['courseNotes']),'안내 학년과 별도 확인 학년을 구분했습니다. 모집 상태와 시간표는 상담에서 확인해 주세요.')
    learning=f'<p class="gd-answer">{e(p["name"])} {stage} 상담에서는 <strong>{e(focus[1])}</strong>부터 점검할 수 있습니다. 아래 질문은 수업을 비교할 때 사용할 기준입니다. 현재 지점이 제공하는 과정이나 실제 학생의 성과를 뜻하지 않습니다.</p><div class="bd-grid gd-topic-grid">'
    for index,key in enumerate(p['topics'],1):
        t=TOPIC[key]
        learning+=f'<article class="bd-card" data-editorial-topic="{e(key)}"><span class="bd-number">{index:02}</span><h3>{e(t[1])}</h3><p>{e(t[3])}</p><p class="gd-question"><strong>물어볼 질문</strong><br>{e(t[5])}</p><p class="bd-source">준비할 기록: {e(t[4])}</p></article>'
    guide=STAGE_GUIDES[p['prefix']]
    learning+='</div><p>'+e(guide[2])+' '+link(guide[1],guide[0])+'에서 공통 학습 방법을 더 살펴볼 수 있습니다.</p>'
    body+=section('learning',p['name']+' '+stage+' 상담에서 비교할 학습 과정',learning)
    fees=shared.tables(b)
    fees='<p>'+e(stage)+' 항목과 수업 횟수·시간을 함께 읽어 주세요. 아래 자료에 다른 학년의 항목이 포함될 수 있으므로 학생에게 적용되는 구성인지 확인해야 합니다.</p>'+fees
    body+=section('fees',b['name']+' 교육비 자료와 확인 항목',fees,'제공된 표의 학년·과목·수업 구성을 기준으로 확인하고, 현재 적용 금액과 추가 항목은 상담에서 정해 주세요.')
    schools=' · '.join(p['schools'])
    local='<div class="bd-grid bd-two"><div class="bd-card"><h3>'+stage+' 학교 참고 정보</h3><p data-stage-schools>'+e(schools or '제공 자료에 이 학년의 학교명이 없습니다.')+'</p><p>학교명은 상담 준비를 위한 참고 정보입니다. 제휴, 재원 학생, 학교별 전용반을 뜻하지 않습니다.</p>'
    if p['schools']:local+='<p>'+e(p['schools'][0])+' 등 학생이 다니는 학교의 실제 진도와 과제 일정을 준비해, 안내 과목·학년과 맞는지 상담에서 비교해 주세요.</p>'
    local+='</div><div class="bd-card"><h3>'+e(b['name'])+' 방문 정보</h3><dl class="bd-facts"><div><dt>등원 주소</dt><dd>'+e(b['address'])+'</dd></div><div><dt>등록 학원명</dt><dd>'+e(b['registeredName'])+'</dd></div><div><dt>등록번호</dt><dd>'+e(b['registration'])+'</dd></div></dl>'+link('https://map.naver.com/p/search/'+quote(b['address'],safe=''),'네이버 지도에서 주소 확인',True)+'<p>동네 이름과 실제 등원 주소는 다를 수 있습니다. 하교 후 이동·식사·귀가를 포함한 일정을 가족이 직접 확인해 주세요.</p></div></div>'+photo(b)
    body+=section('schools',p['name']+' 학교 정보와 실제 등원 위치',local)
    faq=[(p['name']+' '+stage+' 수업에서 어떤 과목과 학년을 확인할 수 있나요?',b['name']+' 자료의 안내 범위는 '+scope(p)+('입니다. ' if known else ' ')+ '별도 확인 항목과 운영 조건을 읽고 현재 등록 가능 여부를 문의해 주세요.'),(p['name']+' '+stage+' 교육비는 어떻게 확인하나요?',b['name']+' 교습비 자료와 위의 교육비 안내에서 학년, 과목, 수업 시간과 횟수를 함께 확인하세요. 공통 참고 금액은 지점의 확정 수강료가 아니며, 교재와 추가 프로그램 포함 여부도 상담해야 합니다.'),(p['name']+' 상담 전에 어떤 학습 기록을 준비하면 좋나요?',focus[4]+object_particle(focus[4])+' 준비해 보세요. “'+focus[5]+'”라는 질문으로 학생의 막힌 단계와 다음 점검 방법을 구체적으로 확인할 수 있습니다.'),(p['name']+' 페이지의 학교명은 무엇을 기준으로 안내하나요?',(schools+'는 제공 자료에서 확인한 상담 참고 정보입니다. ' if schools else '제공 자료에 이 학년의 학교명이 없습니다. ')+'이 안내는 제휴 학교나 재원 학생, 학교별 수업을 나타내는 자료가 아닙니다. 실제 준비 범위는 학생의 학교 자료로 확인해 주세요.')]
    body+=section('faq',p['name']+' '+stage+' 상담 질문',shared.faqs_markup(faq))
    body+=section('next-stage','같은 동네의 다른 학년 안내','<div class="bd-grid">'+''.join(stage_card(x) for x in PAGES if x['area']==p['area'] and x['prefix']!=p['prefix'])+'</div><p>'+link(p['hub'],p['name']+' 학년별 안내 전체')+' · '+link(p['branch'],b['name']+' 전체 과목·사진 안내')+'</p>')
    body+='<p class="bd-source">자료 반영일: '+DAY+'. 개설 학년과 교육비는 제공 센터 자료를 기준으로 정리했으며 현재 모집 상태의 확인일과 다릅니다.</p>'
    crumbs=[('지점안내','/지점안내/'),(b['region'],f'/지점안내/{b["region"]}/'),(p['name'],p['hub']),(stage+' 안내',p['route'])]
    shared.shell(p['route'],title,desc,body,crumbs,faq,branch=True)
    decorate(p['route'],f'data-grade-page="{p["area"]}" data-stage="{p["prefix"]}"')

def decorate(route,attrs):
    file=ROOT/(route.lstrip('/')+'index.html');text=file.read_text(encoding='utf-8')
    text=text.replace('<body class="general-page bd-page">',f'<body class="general-page bd-page gd-page" {attrs}>')
    text=text.replace('<script type="application/ld+json">','<link rel="stylesheet" href="/assets/grade-directory.css"><script type="application/ld+json">',1)
    write(file,text)

def stage_card(p):
    b=BRANCHES[p['branch']];stage=NAMES[p['prefix']]
    return '<article class="bd-card"><p class="bd-card-meta">'+e(b['name'])+' 연결</p><h3>'+link(p['route'],p['name']+' '+stage+' 학습 안내')+'</h3><p>'+e(scope(p))+'</p><p>상담 기준: '+e(TOPIC[p['topics'][0]][1])+'</p>'+link(p['route'],'학년·교육비·상담 기준 살펴보기 →')+'</article>'

def neighborhood_hub(route,slug):
    group=[p for p in PAGES if p['area']==slug];p=group[0];b=BRANCHES[p['branch']]
    title=p['name']+' 초·중·고 학습 안내 | '+b['name']+' 연결'
    desc=f'{p["name"]}의 초등학생·중학생·고등학생 학습 안내에서 {b["name"]} 과목별 학년과 교육비 자료, 학교 정보 및 상담 기준을 확인합니다.'
    body=f'<section class="bd-hero"><p class="bd-kicker">{e(b["region"])} · {e(b["district"])} / 동네별 학습 안내</p><h1>{e(p["name"])}<br>초·중·고 학습 안내</h1><p>{e(p["name"])}에서 학습 상담을 알아볼 때 연결되는 지점은 {e(b["displayName"])}입니다. 학생의 학교 단계에 맞는 페이지에서 실제 과목별 학년과 상담 기준을 확인해 보세요.</p><p class="bd-address">{e(b["address"])}</p>'+shared.actions([(b['route'],b['name']+' 전체 과목·교육비·사진',True),(shared.FORM,'학습 상담',False,True)])+'</section>'
    body+=section('stage-links',p['name']+' 학년별 수업 선택','<div class="bd-grid">'+''.join(stage_card(x) for x in group)+'</div>','모든 과목이 같은 학년까지 개설되는 것은 아닙니다. 별도 확인 항목을 함께 읽어 주세요.')
    body+=section('school-reference',p['name']+' 학교 단계별 참고 정보','<div class="bd-grid">'+''.join('<article class="bd-card"><h3>'+NAMES[x['prefix']]+'</h3><p>'+e(' · '.join(x['schools']) or '제공 자료에 학교명이 없습니다.')+'</p></article>' for x in group)+'</div>','제공 자료의 학교명이며 재원·제휴·학교별 전용반을 뜻하지 않습니다.')
    faq=[(p['name']+'와 '+b['name']+'은 같은 주소인가요?',p['name']+'는 안내를 찾는 동네 이름이고, 실제 등원 위치는 '+b['address']+'입니다. 실제 이동 시간과 방문 일정은 별도로 확인해 주세요.'),(p['name']+' 학년별 페이지는 어떻게 다른가요?','초등학생은 학습 시작과 기초 확인, 중학생은 학교 진도·과제와 복습 계획, 고등학생은 누적 범위와 과목별 우선순위를 중심으로 읽을 수 있습니다. '+b['name']+'의 과목별 안내 학년과 조건은 각 페이지에 구분했습니다.'),(p['name']+' 교육비와 지점 사진은 어디에서 보나요?',b['name']+' 종합 안내에 제공된 교습비 자료와 지점 사진을 연결했습니다. 학년별 페이지에서도 같은 지점의 교육비 확인 경로를 안내하며, 공통 금액과 지점별 금액을 구분합니다.')]
    body+=section('faq',p['name']+' 학습 안내 질문',shared.faqs_markup(faq))
    related=[x for x in ALLHUBS if x!=route and any(q['hub']==x and q['branch']==p['branch'] for q in PAGES)]
    if related:body+=section('related-areas',b['name']+'와 연결된 다른 동네','<div class="bd-region-links">'+''.join(link(h,ALLHUBS[h]) for h in related)+'</div>')
    body+=section('learning-system','학습 방식과 상담 준비',shared.guide_cards())
    nodes=[{'@type':'ItemList','@id':url(route)+'#stages','numberOfItems':3,'itemListElement':[{'@type':'ListItem','position':i,'name':x['name']+' '+NAMES[x['prefix']]+' 학습 안내','url':url(x['route'])} for i,x in enumerate(group,1)]}]
    shared.shell(route,title,desc,body,[('지점안내','/지점안내/'),(b['region'],f'/지점안내/{b["region"]}/'),(p['name'],route)],faq,nodes,kind='CollectionPage')
    decorate(route,f'data-neighborhood-hub="{slug}"')

def category_hub(prefix,label):
    route=f'/과목별학원/{label}/';group=[p for p in PAGES if p['prefix']==prefix];stage=NAMES[prefix]
    title=stage+' 학원 선택과 지역별 학습 안내'
    desc=f'371개 동네의 {stage} 학습 안내에서 실제 지점의 과목별 학년과 교육비 자료를 확인하고, 학교 정보와 상담 질문을 살펴봅니다.'
    guide=STAGE_GUIDES[prefix]
    body=f'<section class="bd-hero"><p class="bd-kicker">학년별 학습 안내</p><h1>{stage} 학원 선택과<br>지역별 학습 안내</h1><p>{e(guide[2])} 아래 지역별 페이지에는 실제 지점 자료의 과목·학년과 교육비 확인 경로를 함께 정리했습니다.</p>'+shared.actions([('/지점안내/','실제 지점부터 찾기',True),(guide[1],guide[0])])+'</section>'
    form='<form class="bd-search" data-branch-search data-count-label="개 지역 안내" role="search"><label>동네·지점·학교 검색<input type="search" name="q" placeholder="예: 명일동, 명일점, 명일중" autocomplete="off"></label><label>지역<select name="region"><option value="">전국 전체</option>'+''.join('<option value="'+e(r)+'">'+e(r)+'</option>' for r in shared.REGIONS)+'</select></label><button class="bd-btn" type="reset">검색 초기화</button></form><p class="bd-result" data-search-status role="status" aria-live="polite">371개 지역 안내가 있습니다.</p><div class="bd-empty" data-search-empty hidden><p>검색 결과가 없습니다. 동네 이름이나 지역을 바꾸어 보세요.</p></div>'
    listing='<div class="bd-grid">'
    for p in group:
        b=BRANCHES[p['branch']];search=' '.join([p['name'],b['name'],b['region'],b['district'],*p['schools']])
        listing+=stage_card(p).replace('<article class="bd-card">',f'<article class="bd-card" data-branch-card data-region="{e(b["region"])}" data-search="{e(search)}">')
    body+=section('region-guide',stage+' 동네별 학습 안내',form+listing+'</div>')
    faq=[(stage+' 학원은 모든 과목을 같은 학년까지 안내하나요?','아닙니다. 지점과 과목에 따라 안내 학년과 별도 확인 조건이 다릅니다. 지역별 페이지의 과목·학년 표를 읽고 현재 개설과 등록 가능 여부를 문의해 주세요.'),(stage+' 학습 상담 전 무엇을 준비하면 좋나요?',guide[2]+' 최근 과제와 풀이 기록, 학교 일정, 희망 과목을 함께 준비하면 상담 질문을 더 구체적으로 정리할 수 있습니다.')]
    body+=section('faq',stage+' 학습 안내 질문',shared.faqs_markup(faq))
    shared.shell(route,title,desc,body,[('과목별학원','/과목별학원/'),(label,route)],faq,kind='CollectionPage')
    decorate(route,f'data-stage-collection="{prefix}"');MODIFIED.add(route.lstrip('/')+'index.html')

def insert_block(name,block):
    path=ROOT/name;text=path.read_text(encoding='utf-8');old=text
    text=re.sub(r'<!-- grade-entry:start -->.*?<!-- grade-entry:end -->','',text,flags=re.S)
    text=text.replace('</main>','<!-- grade-entry:start -->'+block+'<!-- grade-entry:end --></main>',1)
    if text!=old:write(path,text);MODIFIED.add(name)

def connect_hubs():
    for region in [None,*shared.REGIONS]:
        route=f'/지점안내/{region}/' if region else '/지점안내/'
        body='<div class="bd-grid">'+''.join('<article class="bd-card"><h3>'+link(f'/과목별학원/{label}/',NAMES[p]+' 지역별 안내')+'</h3><p>'+e(STAGE_GUIDES[p][2])+'</p></article>' for p,label in LABELS.items())+'</div>'
        if region:
            hubs=[(h,s) for h,s in ALLHUBS.items() if h.split('/')[2]==region]
            body+='<h3>'+region+' 동네별 학년 안내</h3><div class="bd-region-links">'+''.join(link(h,AREAS[s]['area']) for h,s in hubs)+'</div>'
        insert_block(route.lstrip('/')+'index.html',section('grade-guide', (region+' ' if region else '')+'초·중·고 학년별로 확인하기',body,'실제 지점의 과목별 학년과 동네별 상담 기준을 함께 살펴보세요.').replace('id="grade-guide"','id="grade-guide" data-grade-entry'))
    for route,b in BRANCHES.items():
        body='<div class="bd-grid bd-two">'
        for area in b['areas']:
            p=next(x for x in PAGES if x['area']==area['slug'])
            body+='<article class="bd-card"><h3>'+link(p['hub'],area['name']+' 초·중·고 안내')+'</h3><ul class="bd-link-list">'+''.join('<li>'+link(x['route'],NAMES[x['prefix']]+' 학습 안내')+'</li>' for x in PAGES if x['area']==area['slug'])+'</ul></article>'
        insert_block(route.lstrip('/')+'index.html',section('grade-guide',b['name']+' 동네별 학년 안내',body+'</div>').replace('id="grade-guide"','id="grade-guide" data-grade-entry'))
    for name in ['index.html','전국센터/index.html','과목별학원/index.html']:
        block='<section class="bd-entry" id="grade-discovery" data-grade-entry><p class="bd-kicker">학교 단계에 맞춰 살펴보기</p><h2>초·중·고 학습과 수업 선택</h2><p>동네별 실제 지점의 안내 학년과 교육비 자료, 학교 정보와 상담 기준을 확인하세요.</p><div class="bd-entry-links">'+''.join(link(f'/과목별학원/{label}/',NAMES[p]+' 지역별 안내') for p,label in LABELS.items())+'</div></section>'
        insert_block(name,block)
    for slug,a in AREAS.items():
        p=next(x for x in PAGES if x['area']==slug)
        insert_block(f'전국센터/{slug}/index.html','<section class="bd-entry" id="neighborhood-grade-guide" data-grade-entry><h2>'+e(a['area'])+' 학년별 학습 안내</h2><p>'+link(p['hub'],a['area']+' 초등학생·중학생·고등학생 안내')+'</p></section>')

def migrate_links(public_files):
    changed=0
    def process(name):
        if not name.endswith('.html') or name in shared.NEW:return None
        path=ROOT/name;old=path.read_text(encoding='utf-8');text=old
        legacy_route='/'+name.removesuffix('index.html')
        if legacy_route in LEGACY:
            target=url(LEGACY[legacy_route])
            text=re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")[^"]+',lambda m:m[1]+target,text)
            # Keep the existing readable page for old bookmarks, with an explicit
            # link to its enriched representative. No script or meta redirect.
            text=re.sub(r'<p class="gd-legacy-note".*?</p>','',text,flags=re.S)
            note='<p class="gd-legacy-note">'+link(LEGACY[legacy_route],'최신 학년·교육비와 상담 기준 안내 보기')+'</p>'
            text=re.sub(r'(</h1>)',lambda m:m[1]+note,text,count=1)
            if '/assets/grade-directory.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/assets/grade-directory.css"></head>',1)
        def href_replace(m):
            ref=m[2];split=urlsplit(ref);path_ref=unquote(split.path)
            if split.netloc and split.netloc!=urlsplit(shared.DOMAIN).netloc:return m[0]
            if path_ref not in LEGACY:return m[0]
            target=shared.href(LEGACY[path_ref])
            valid={'courses','fees','lesson-image','learning','schools','faq','next-stage'}
            return m[1]+target+(('#'+split.fragment) if split.fragment in valid else '')+m[3]
        text=re.sub(r'(\bhref=")([^"]+)(")',href_replace,text)
        if text!=old:write(path,text);return name
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name in pool.map(process,public_files):
            if name:MODIFIED.add(name);changed+=1
    return changed

def manifest_update(manifest):
    selected=set(manifest['files'])|set(shared.NEW)|{'assets/grade-directory.css'}
    tree=etree.parse(str(ROOT/'sitemap.xml'));ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};root=tree.getroot()
    existing={unquote(urlsplit(n.find('s:loc',ns).text).path):n for n in root}
    for route in LEGACY:
        if route in existing:root.remove(existing.pop(route))
    for name in set(shared.NEW)|MODIFIED:
        route='/'+name.removesuffix('index.html')
        if route in LEGACY:continue
        node=existing.get(route)
        if node is None:
            node=etree.SubElement(root,'{'+ns['s']+'}url');etree.SubElement(node,'{'+ns['s']+'}loc').text=url(route);existing[route]=node
        lm=node.find('s:lastmod',ns)
        if lm is None:lm=etree.SubElement(node,'{'+ns['s']+'}lastmod')
        lm.text=DAY
    tree.write(str(ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True)
    llms=ROOT/'llms.txt';text=llms.read_text(encoding='utf-8')
    text=re.sub(r'\n## 동네별 학년 안내[\s\S]*$','',text)
    text+='\n## 동네별 학년 안내\n\n지점안내의 지역 아래 동네별 허브에서 초등학생·중학생·고등학생 안내로 연결됩니다.\n동네는 새 지점의 주소를 뜻하지 않습니다. 실제 지점의 개설 학년과 별도 확인 조건을 우선합니다.\n기존 학년별 지역 주소는 새 지점안내 하위 주소를 대표 URL로 가리킵니다.\n교육비는 지점별 자료와 공통 참고표를 구분하며, 일반 학습 점검 질문은 제공 수업이나 실제 후기를 뜻하지 않습니다.\n'
    write(llms,text)
    def digest(name):
        raw=(ROOT/name).read_bytes();normalized=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode()).hexdigest() if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name) else None
        return name,hashlib.sha256(raw).hexdigest(),normalized
    with ThreadPoolExecutor(max_workers=8) as pool:hashes=list(pool.map(digest,sorted(selected)))
    manifest.update({'files':{n:h for n,h,_ in hashes},'textSha256':{n:h for n,_,h in hashes if h},'sitemapPages':len(root),'createdAt':datetime.now(timezone.utc).isoformat()})
    shared.save(ROOT/'release-public-manifest.json',manifest)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',action='store_true');ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
    original=set(manifest['files']);baseline=set(json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))['files'])
    for p in PAGES:details(p)
    for h,s in ALLHUBS.items():neighborhood_hub(h,s)
    for prefix,label in LABELS.items():category_hub(prefix,label)
    connect_hubs();migrate_links(original)
    shared.DESCRIPTIONS['canonicalAliases']={old.rstrip('/'):new.rstrip('/') for old,new in LEGACY.items()}
    shared.save(ROOT/'seo-descriptions.json',shared.DESCRIPTIONS)
    if args.manifest:manifest_update(manifest)
    report={'newPages':[n for n in shared.NEW if n not in baseline],'generatedPages':shared.NEW,'modifiedPages':sorted(MODIFIED),'legacyCanonical':LEGACY,'gradePages':len(PAGES),'neighborhoodHubs':len(ALLHUBS)}
    shared.save(args.audit/'generated-pages.json',report)
    print(json.dumps({k:len(v) if isinstance(v,(list,dict)) else v for k,v in report.items()},ensure_ascii=False))
if __name__=='__main__':main()

"""Generate unique branch destinations and editorial guides from reviewed facts.

Existing neighborhood/subject routes remain canonical and receive navigation only.
Run locally, inspect the output, then --manifest to approve those exact public bytes.
"""
import argparse, hashlib, json, re
from datetime import datetime, timezone
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from lxml import etree, html
from branch_maps import insert_map

ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--3e0bz50bxucwzc.com'
DAY='2026-10-01'
FORM='https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform'
DATA=json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'))
BRANCHES=DATA['branches']
DESCRIPTIONS=json.loads((ROOT/'seo-descriptions.json').read_text(encoding='utf-8-sig'))
REGIONS=[r for r in ['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주'] if any(b['region']==r for b in BRANCHES)]
NEW=[]
def e(v):return escape(str(v),quote=True)
def j(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
def href(p):return quote(p,safe='/#-') if p.startswith('/') else e(p)
def url(p):return DOMAIN+quote(p,safe='/#-')
def link(p,label,external=False):return f'<a href="{href(p)}"'+(' target="_blank" rel="noopener noreferrer"' if external else '')+f'>{e(label)}</a>'
def button(p,label,primary=False,external=False):return f'<a class="bd-btn'+(' bd-btn-primary' if primary else '')+f'" href="{href(p)}"'+(' target="_blank" rel="noopener noreferrer"' if external else '')+f'>{e(label)}</a>'
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True); data=(s.rstrip()+'\n').encode('utf-8')
    if not p.exists() or p.read_bytes()!=data:p.write_bytes(data)
def save(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2))
def grade_label(grades):
    result=[]
    for prefix in ['초','중','고']:
        nums=sorted({int(g[1:]) for g in grades if g.startswith(prefix)})
        if nums:result.append(f'{prefix}{nums[0]}~{prefix}{nums[-1]}' if len(nums)>1 and nums==list(range(nums[0],nums[-1]+1)) else '·'.join(prefix+str(n) for n in nums))
    return ' / '.join(result)
def section(id,title,body,lead='',class_name=''):
    return f'<section class="bd-section {class_name}" id="{id}" aria-labelledby="{id}-title"><h2 id="{id}-title">{e(title)}</h2>'+ (f'<p class="bd-lead">{e(lead)}</p>' if lead else '')+body+'</section>'
def actions(items):return '<div class="bd-actions">'+''.join(button(*x) for x in items)+'</div>'
def faqs_markup(faqs):return ''.join(f'<details class="bd-details" data-faq><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q,a in faqs)
def source_note(page,label):return '<p class="bd-source">공식 설명 참고: '+link('https://www.wawacenter.com/'+page,label,True)+'. 이 페이지는 내용을 학부모의 확인 순서에 맞게 재구성했습니다.</p>'
def shell(route,title,desc,body,crumbs,faqs=(),nodes=(),kind='WebPage',branch=False):
    assert len(desc)<=80 and desc.endswith('.'),(route,desc)
    breadcrumbs=[('홈','/'),*crumbs]
    graph=[{'@type':kind,'@id':url(route)+'#webpage','url':url(route),'name':title,'description':desc,'inLanguage':'ko-KR','dateModified':DAY,'isPartOf':{'@id':url('/')+'#website'},'breadcrumb':{'@id':url(route)+'#breadcrumb'}},{'@type':'BreadcrumbList','@id':url(route)+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':n,'item':url(p)} for i,(n,p) in enumerate(breadcrumbs,1)]},*nodes]
    if branch and nodes:graph[0]['mainEntity']={'@id':nodes[0]['@id']}
    if faqs:graph.append({'@type':'FAQPage','@id':url(route)+'#faq','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faqs]})
    nav=[('홈','/'),('지점안내','/지점안내/'),('학습시스템','/학습시스템/'),('학습가이드','/학습가이드/'),('과목별학원','/과목별학원/'),('상담문의','/상담문의/')]
    html_text=f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | 전국수업.com</title>
<meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{url(route)}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)} | 전국수업.com"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url(route)}"><meta property="og:site_name" content="전국수업.com"><meta property="og:locale" content="ko_KR"><meta property="og:image" content="{DOMAIN}/assets/generated/site6-hero.webp">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)} | 전국수업.com"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{DOMAIN}/assets/generated/site6-hero.webp">
<link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/site-modern.css"><link rel="stylesheet" href="/assets/branch-directory.css">
<script type="application/ld+json">{j({'@context':'https://schema.org','@graph':graph})}</script><script defer src="/assets/branch-directory.js"></script></head>
<body class="general-page bd-page"><a class="skip-link" href="#main">본문 바로가기</a><header class="site-header"><div class="header-inner"><a class="brand" href="/" aria-label="전국수업.com 홈"><span class="brand-mark">W</span><span class="brand-copy"><strong>전국수업.com</strong><small>와와센터 학습코칭</small></span></a><nav class="nav" aria-label="상단 메뉴">{''.join(f'<a href="{href(p)}"'+(' aria-current="page"' if p==route else '')+f'>{e(n)}</a>' for n,p in nav)}</nav><a class="header-cta" href="{FORM}" target="_blank" rel="noopener">상담 신청</a></div></header>
<main id="main"><nav class="bd-breadcrumb" aria-label="현재 위치">{'<span aria-hidden="true">/</span>'.join(link(p,n) if i<len(breadcrumbs)-1 else f'<span aria-current="page">{e(n)}</span>' for i,(n,p) in enumerate(breadcrumbs))}</nav>{body}</main>
<footer class="footer"><div class="footer-inner"><div><strong>전국수업.com</strong><br>지역별 수업과 학습코칭 안내<br>{link('/지점안내/','지점안내')} · {link('/학습시스템/','학습시스템')}</div><div>학습 상담 {link('tel:01068398283','010-6839-8283')}<br><small>학교·학년·희망 지점을 알려 주세요.</small></div></div></footer>
{('<aside class="bd-sticky-contact" aria-label="학습 상담">'+button('tel:01068398283','전화 상담')+button(FORM,'상담 신청',True,True)+'</aside>') if branch else ''}
</body></html>'''
    file=route.lstrip('/')+'index.html';write(ROOT/file,html_text);NEW.append(file)
    old=DESCRIPTIONS['pages'].get(route.rstrip('/'),{})
    DESCRIPTIONS['pages'][route.rstrip('/')]={'description':desc,'sources':list(dict.fromkeys([*old.get('sources',[]),desc]))}

def branch_card(b):
    schools=[v for values in b['schools'].values() for v in values]
    search=' '.join([b['name'],b['displayName'],b['region'],b['district'],b['address'],*[a['name'] for a in b['areas']],*schools])
    return f'<article class="bd-card" data-branch-card data-region="{e(b["region"])}" data-search="{e(search)}"><p class="bd-card-meta">{e(b["region"])} · {e(b["district"])}</p><h3>{link(b["route"],b["name"])}</h3><p>{e(b["address"])}</p><p class="bd-card-area">연결 동네 · {e(" · ".join(a["name"] for a in b["areas"]))}</p>{link(b["route"],'과목·교육비·사진 확인 →')}</article>'

def directory(region=None):
    branches=[b for b in BRANCHES if not region or b['region']==region]
    route=f'/지점안내/{region}/' if region else '/지점안내/'
    title=region+' 지점안내' if region else '우리 동네에서 찾는 지점안내'
    desc=f'{region} {len(branches)}개 지점의 주소와 과목별 학년, 교육비 자료를 비교하고 가까운 학습 상담 지점을 찾습니다.' if region else '지역·지점명·학교명으로 188개 지점을 찾고, 과목별 학년과 교육비 자료 및 지점 사진을 확인합니다.'
    hero=f'<section class="bd-hero"><p class="bd-kicker">FIND YOUR CENTER</p><h1>{e(title)}</h1><p>'+('통학할 지역과 희망 과목을 함께 살펴보세요. 지점마다 안내 학년과 수업 구성이 다릅니다.' if region else '아이의 일상에 맞는 곳부터 찾아보세요.<br>주소, 수업 범위, 교육비를 한곳에서 살펴볼 수 있습니다.')+'</p><div class="bd-summary">'+f'<div><strong>{len(branches)}</strong><span>안내 지점</span></div><div><strong>{sum(len(b["areas"]) for b in branches)}</strong><span>연결 동네</span></div><div><strong>초·중·고</strong><span>과목별 학년 확인</span></div></div></section>'
    form=f'<form class="bd-search" data-branch-search role="search"><label>지점·동네·학교 검색<input type="search" name="q" placeholder="예: 명일점, 위례, 가재울중" autocomplete="off"></label><label>지역<select name="region"><option value="">'+('현재 지역 전체' if region else '전국 전체')+'</option>'+''.join(f'<option value="{e(r)}">{e(r)}</option>' for r in ([region] if region else REGIONS))+'</select></label><button class="bd-btn" type="reset">검색 초기화</button></form><p class="bd-result" data-search-status role="status" aria-live="polite">'+str(len(branches))+'개 지점이 있습니다.</p><noscript><p>검색 필터는 자바스크립트를 켜면 사용할 수 있습니다. 아래 지역 링크와 전체 지점 목록은 그대로 이용할 수 있습니다.</p></noscript>'
    regions='<nav class="bd-region-links" aria-label="지역별 지점">'+(link('/지점안내/','전국 전체') if region else '')+''.join(link(f'/지점안내/{r}/',r+' '+str(sum(b['region']==r for b in BRANCHES))) for r in REGIONS if r!=region)+'</nav>'
    body=hero+regions+form+'<div class="bd-empty" data-search-empty hidden><h2>검색 결과가 없습니다.</h2><p>학교 이름을 짧게 입력하거나 지역 조건을 바꿔 보세요.</p></div><div class="bd-grid">'+''.join(branch_card(b) for b in branches)+'</div>'
    body+=section('how-to-choose','지점을 고를 때 먼저 볼 세 가지','<div class="bd-grid">'+''.join(f'<div class="bd-card"><span class="bd-number">0{i}</span><h3>{e(h)}</h3><p>{e(p)}</p></div>' for i,(h,p) in enumerate([('실제 등원 주소','동네 이름과 지점이 위치한 주소는 다를 수 있습니다. 방문할 건물과 층을 확인하세요.'),('우리 아이의 과목과 학년','같은 지점에서도 국어·영어·수학 등의 대상 학년이 다를 수 있습니다. 별도 확인 항목도 함께 읽어 보세요.'),('수업 구성에 맞는 비용','횟수, 시간, AI 학습 등 추가 구성에 따라 금액이 달라집니다. 지점별 교습비 자료와 상담 내용을 비교하세요.')],1))+'</div>')
    body+=section('learning-links','학습 방식도 함께 살펴보세요',guide_cards())
    crumbs=[('지점안내','/지점안내/')]+([(region,route)] if region else [])
    nodes=[{'@type':'ItemList','@id':url(route)+'#centers','name':title,'numberOfItems':len(branches),'itemListElement':[{'@type':'ListItem','position':i,'name':b['displayName'],'url':url(b['route'])} for i,b in enumerate(branches,1)]}]
    shell(route,title,desc,body,crumbs,nodes=nodes,kind='CollectionPage')

def tables(b):
    body='<p>먼저 '+link(b['feeUrl'],b['name']+' 교습비 자료',True)+'를 확인해 주세요. 학생의 학년·과목·주당 횟수와 추가 프로그램을 정한 뒤 최종 금액을 안내받아야 합니다.</p>'
    specific=[f for f in b['fees'] if f['kind']=='branch']
    entries=specific or b['fees']
    table_html=''
    for f in entries:
        for idx,rows in enumerate(f['tables']):
            if not rows:continue
            table_html+='<div class="bd-table-wrap" tabindex="0" role="region" aria-label="가로로 이동할 수 있는 교육비 표"><table class="bd-table"><caption>'+e(f['heading'])+('</caption><thead><tr>'+''.join('<th scope="col">'+e(cell)+'</th>' for cell in rows[0])+'</tr></thead><tbody>')+''.join('<tr>'+''.join('<td>'+e(cell)+'</td>' for cell in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>'
        table_html+=''.join('<p class="bd-course-note">'+e(n)+'</p>' for n in f['notes'])
    if specific:
        body+='<p class="bd-notice">아래는 제공된 '+e(b['name'])+' 교육비 안내입니다. 현재 적용 금액이나 잔여 수업 자리를 보장하지 않으며, 교재비·추가 학습비의 포함 여부는 상담에서 확인해 주세요.</p>'+table_html
    else:
        body+='<p class="bd-notice">'+e(b['name'])+'의 확정 수강료를 이 페이지의 공통 금액으로 판단하지 마세요. 제공 자료에는 공통 참고표가 포함되어 있어 별도로 구분했습니다.</p><details class="bd-details" data-reference-fees><summary>공통 참고 금액 보기 · 지점 확정 금액 아님</summary><div>'+table_html+'</div></details>'
    return body

def branch_page(b):
    route=b['route']; name=b['name']; area_names=' · '.join(a['name'] for a in b['areas'])
    desc=f'{b["region"]} {b["district"]} {name}의 주소, 과목별 안내 학년과 수강 조건, 교육비 자료 및 방문 정보를 확인합니다.'
    desc=re.sub(r' +',' ',desc)
    known=[c['subject'] for c in b['courses'] if c['grades']]
    intro=f'{area_names}에서 학습 상담을 알아볼 때 연결되는 지점입니다. '+('교육비는 지점별 제공 표와 교습비 자료를 함께 확인할 수 있습니다.' if any(f['kind']=='branch' for f in b['fees']) else '교육비는 연결된 교습비 자료를 기준으로 수업 구성과 함께 확인해 주세요.')
    hero=f'<section class="bd-hero"><p class="bd-kicker">{e(b["region"])} · {e(b["district"])} / 지점안내</p><h1>{e(name)}<br>수업과 방문 안내</h1><p>{e(b["displayName"])}</p><p class="bd-address">{e(b["address"])}</p><p>{e(intro)}</p><div class="bd-tags"><span>과목별 학년 확인</span><span>교육비 자료 연결</span>'+('<span>제공 지점 사진</span>' if b['photos'] else '')+'</div>'+actions([(FORM,'우리 아이 학습 상담',True,True),('#location','위치 먼저 보기')])+'</section>'
    if b['addressPending']:hero+='<p class="bd-notice">주소 자료가 서로 달라 기존 홈페이지 주소를 유지하고 있습니다. 방문 전 현재 지점 위치를 꼭 확인해 주세요.</p>'
    nav='<nav class="bd-jump" aria-label="지점 페이지 바로가기">'+''.join(link('#'+k,n) for k,n in [('lesson-image','상세 안내'),('courses','과목·학년'),('fees','교육비'),('location','위치'),('photos','사진'),('faq','질문')])+'</nav>'
    img=b['bodyImage']
    picture=('<picture><source media="(max-width:800px)" srcset="'+href(img['mobile'])+'">' if img.get('mobile') else '<picture>')+f'<img src="{href(img["src"])}" width="{img["width"]}" height="{img["height"]}" alt="와와 학습코칭 수업과 학습 관리 상세 안내" loading="eager" decoding="async"></picture>'
    body=hero+nav+section('lesson-image','수업을 자세히 살펴보세요','<div class="bd-image-panel">'+picture+'</div>','긴 안내 이미지를 그대로 확인할 수 있습니다. 실제 개설 과정과 교육비는 아래 지점별 정보를 함께 참고해 주세요.')
    course_html=''
    for c in b['courses']:
        grade=grade_label(c['grades']) or '대상 학년 별도 확인'
        course_html+=f'<article class="bd-card" data-course="{e(c["subject"])}" data-grades="{e(",".join(c["grades"]))}" data-pending="{e(",".join(c["pending"]))}"><h3>{e(c["subject"])}</h3><div class="bd-grade">{e(grade)}</div>'
        if c['pending']:course_html+='<p class="bd-pending">별도 확인: '+e(grade_label(c['pending']))+'. 학년 표기와 운영 조건이 달라 개설 여부를 먼저 문의해야 합니다.</p>'
        if not c['grades'] and not c['pending']:course_html+='<p>제공 자료만으로 현재 수업 학년을 확정할 수 없습니다.</p>'
        course_html+=''.join('<p class="bd-course-note">'+e(n)+'</p>' for n in c['notes'])+'</article>'
    body+=section('courses',name+' 과목별 안내 학년','<div class="bd-grid">'+course_html+'</div>'+''.join('<p class="bd-notice">'+e(n)+'</p>' for n in b['courseNotes']),'제공 자료의 학년 정보와 별도 운영 조건을 함께 정리했습니다. 시간표와 신규 등록 가능 여부는 상담에서 확인해야 합니다.')
    body+=section('fees',name+' 교육비 확인',tables(b),'표가 넓으면 좌우로 밀어 볼 수 있습니다. 금액과 함께 수업 시간·횟수·포함 항목을 읽어 주세요.')
    facts=[('안내 지점',b['displayName']),('등원 주소',b['address']),('등록 학원명',b['registeredName']),('등록번호',b['registration'])]
    if b['registrationDate']:facts.append(('운영등록일',b['registrationDate']))
    loc='<div class="bd-card"><dl class="bd-facts">'+''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in facts)+'</dl>'+actions([('https://map.naver.com/p/search/'+quote(b['address'],safe=''),'네이버 지도에서 주소 확인',True,True),(FORM,'방문 일정 상담',False,True)])+'<p class="bd-course-note">상담 전화는 학습 상담 접수 번호입니다. 실제 방문 시간과 상세 이동 경로는 지점 확인 후 정해 주세요.</p></div>'
    if b['missingSource']:loc+='<p class="bd-notice">이 지점은 추가 센터 엑셀에서 일치하는 행을 찾지 못해, 제공된 지역별 안내 자료에 확인되는 정보로 정리했습니다. 현재 개설과 위치를 먼저 확인해 주세요.</p>'
    body+=section('location',name+' 위치와 등록 정보',loc)
    if b['photos']:
        gallery='<div class="bd-gallery">'
        for i,p in enumerate(b['photos'],1):
            large=p['large'];small=p['small']
            srcset=', '.join(f'{href(v["src"])} {v["width"]}w' for v in ([small,large] if small['width']!=large['width'] else [large]))
            gallery+=f'<figure class="bd-photo"><a href="{href(large["src"])}" target="_blank" rel="noopener" aria-label="{e(name)} 제공 사진 {i} 크게 보기"><img src="{href(small["src"])}" srcset="{srcset}" sizes="(max-width:560px) calc(100vw - 32px), 520px" width="{large["width"]}" height="{large["height"]}" loading="lazy" decoding="async" alt="{e(name)} 제공 공간 사진 {i}"></a><figcaption>{e(name)} 제공 사진 {i} · 사진을 누르면 크게 볼 수 있습니다.</figcaption></figure>'
        gallery+='</div><p class="bd-source">제공된 지점별 사진입니다. 촬영 시점의 공간으로 현재 배치와 다를 수 있습니다.</p>'
    else:gallery='<div class="bd-card"><p>현재 제공 폴더에서 '+e(name)+'의 개별 공간 사진을 확인하지 못했습니다. 위의 학습 안내 이미지는 공통 설명이며, 실제 지점 내부 사진은 상담 시 요청해 주세요.</p></div>'
    body+=section('photos',name+' 공간 사진',gallery)
    school_html='<div class="bd-grid">'+''.join('<div class="bd-card"><h3>'+{'초':'초등학교','중':'중학교','고':'고등학교'}[level]+'</h3><p>'+e(' · '.join(values) or '제공 자료에 학교명이 없습니다.')+'</p></div>' for level,values in b['schools'].items())+'</div>'
    area_html='<div class="bd-grid bd-two">'
    for a in b['areas']:
        area_html+='<div class="bd-card"><h3>'+e(a['name'])+'에서 수업을 찾는다면</h3><ul class="bd-link-list">'+''.join('<li>'+link(f'/과목별학원/{category}/{a["slug"]}/',a['name']+' '+label+' 안내')+'</li>' for category,label in [('영어학원','영어'),('수학학원','수학'),('영수학원','영어·수학')])+'</ul></div>'
    area_html+='</div>'
    body+=section('schools','학교와 동네별 학습 정보',school_html+area_html,'제공 자료에 연결된 학교와 동네입니다. 재학생 재원, 학교와의 제휴, 학교별 전용반이나 통학 차량 운영을 뜻하지 않습니다.')
    faq=[(name+'은 어디로 방문하면 되나요?',b['address']+'에 안내되어 있습니다. '+('주소가 다른 자료가 있어 현재 위치를 방문 전에 확인해야 합니다.' if b['addressPending'] else '학교와 학년, 희망 과목을 알려주고 상담 시간을 먼저 정해 주세요.')),(name+'의 수강료는 얼마인가요?',('이 페이지에 지점별 제공 교육비 표와 교습비 자료를 연결했습니다.' if any(f['kind']=='branch' for f in b['fees']) else '지점 교습비 자료에서 확인해야 합니다. 공통 참고표는 이 지점의 확정 수강료가 아닙니다.')+' 주당 횟수, 수업 시간, 교재와 추가 프로그램 포함 여부에 따라 최종 비용을 확인해 주세요.'),(name+'에서 모든 과목을 같은 학년까지 배울 수 있나요?','과목마다 안내 학년과 조건이 다릅니다. '+('자료에 안내 학년이 있는 과목은 '+', '.join(known)+'입니다. ' if known else '')+'위의 과목별 표에서 학년과 별도 확인 항목을 함께 읽고 현재 개설 여부를 문의해 주세요.')]
    body+=section('faq',name+' 상담 전 자주 묻는 질문',faqs_markup(faq))
    body+=section('system','지점 상담 전에 학습 방식 알아보기',guide_cards())
    body+='<p class="bd-source">자료 반영일: '+DAY+'. 지점별 센터 자료·교육비 안내와 학교 목록을 대조해 작성했습니다. 자료 반영일은 현재 모집 상태의 확인일과 다릅니다.</p>'
    # The existing regional entity ID remains stable across old and new URLs.
    old=html.parse(str(ROOT/f'전국센터/{b["representative"]}/index.html'))
    def walk(v):
        if isinstance(v,dict):
            yield v
            for x in v.values():yield from walk(x)
        elif isinstance(v,list):
            for x in v:yield from walk(x)
    oldnodes=[n for t in old.xpath('//script[@type="application/ld+json"]/text()') for n in walk(json.loads(t))]
    orgid=next(n['@id'] for n in oldnodes if 'EducationalOrganization' in str(n.get('@type')) and 'address' in n)
    entity={'@type':'EducationalOrganization','@id':orgid,'name':b['displayName'],'url':url(route),'address':{'@type':'PostalAddress','streetAddress':b['address'],'addressCountry':'KR'},'identifier':{'@type':'PropertyValue','propertyID':'교육지원청 등록번호','value':b['registration']},'contactPoint':{'@type':'ContactPoint','telephone':'+82-10-6839-8283','contactType':'학습 상담 접수','availableLanguage':'Korean'},'areaServed':[{'@type':'Place','name':a['name']} for a in b['areas']]}
    if b['addressPending']:entity.pop('address')
    if b['photos']:entity['image']=[url(p['large']['src']) for p in b['photos']]
    body=insert_map(body,b)
    shell(route,b['displayName']+' 지점안내',desc,body,[('지점안내','/지점안내/'),(b['region'],f'/지점안내/{b["region"]}/'),(name,route)],faq,[entity],branch=True)

GUIDES=[('와와학습코칭','와와 학습코칭은 어떤 수업인가요?','진단부터 계획, 실행과 점검까지 학습코칭의 흐름을 공식 영상과 함께 살펴봅니다.'),('개별맞춤관리','진도와 공부 습관을 함께 점검하는 방법','플래너와 오답 기록이 실제 수업에서 어떤 역할을 하는지, 상담 때 무엇을 물어볼지 정리합니다.'),('AI학습','AI 학습, 아이에게 어떻게 활용할까요?','영어·수학·국어·독서 프로그램의 역할과 학년 범위, 지점에서 확인할 조건을 구분합니다.')]
def guide_cards():return '<div class="bd-grid">'+''.join('<article class="bd-card"><span class="bd-number">0'+str(i)+'</span><h3>'+link('/학습시스템/'+slug+'/',title)+'</h3><p>'+e(copy)+'</p>'+link('/학습시스템/'+slug+'/','내용 살펴보기 →')+'</article>' for i,(slug,title,copy) in enumerate(GUIDES,1))+'</div>'
def video(id,title):
    return f'<div class="bd-video"><button type="button" data-video-id="{id}" data-video-title="{e(title)}" aria-label="{e(title)} 영상 재생"><img src="https://i.ytimg.com/vi/{id}/hqdefault.jpg" width="480" height="360" alt="" loading="lazy"><span class="bd-play"><b aria-hidden="true">▶</b>공식 영상 보기</span></button></div><p class="bd-video-credit">와와학습코칭센터 공식 채널 · '+link('https://www.youtube.com/watch?v='+id,'YouTube에서 보기',True)+'</p>'
def guide_hero(kicker,title,copy):return '<section class="bd-hero"><p class="bd-kicker">'+e(kicker)+'</p><h1>'+e(title)+'</h1><p>'+e(copy)+'</p>'+actions([('/지점안내/','우리 동네 지점 찾기',True),('/학습시스템/','학습시스템 전체')])+'</section>'
def steps(items):return '<div class="bd-grid">'+''.join('<article class="bd-card"><span class="bd-number">'+f'{i:02}'+'</span><h3>'+e(h)+'</h3><p>'+e(p)+'</p></article>' for i,(h,p) in enumerate(items,1))+'</div>'
def guides():
    faq=[('학습코칭과 AI 학습 중 하나만 선택하는 건가요?','학습코칭은 계획과 실행을 점검하는 지도 방식이고, AI 학습은 진단과 연습을 돕는 도구입니다. 실제로 어떻게 조합하는지는 지점과 수업 구성에 따라 확인해야 합니다.'),('공식 프로그램 안내 학년이면 모든 지점에서 등록할 수 있나요?','아닙니다. 프로그램 자체의 대상 학년과 지점에서 운영하는 과목·학년은 다릅니다. 지점안내에서 해당 과목의 학년과 조건을 살핀 뒤 등록 가능 여부를 확인해 주세요.')]
    body=guide_hero('LEARNING GUIDE','아이의 공부가 이어지도록','문제를 푸는 시간만큼, 어디서 막혔는지 돌아보고 다음 공부를 정하는 과정도 필요합니다. 와와의 공식 안내를 바탕으로 수업 방식과 확인할 질문을 정리했습니다.')+section('programs','세 가지 관점으로 살펴보세요',guide_cards())
    body+=section('connection','진단 결과가 다음 공부로 이어지는 과정',steps([('지금의 출발점','최근 시험지나 숙제에서 반복되는 어려움을 찾습니다. 점수뿐 아니라 문제를 읽고 푸는 과정을 함께 살피는 것이 출발점입니다.'),('실행할 수 있는 계획','어떤 단원을 어느 분량까지 공부할지 정합니다. 계획과 실제 수행한 내용을 비교할 수 있도록 기록합니다.'),('다시 풀어보는 확인','틀린 원인을 점검한 뒤 비슷한 문제를 다시 해결해 봅니다. 이해가 불충분한 부분은 다음 계획에 반영합니다.')]))
    body+=section('faq','먼저 알아두면 좋은 질문',faqs_markup(faq))+source_note('intro/coachingSystem','학습코칭 시스템')
    shell('/학습시스템/','학습코칭·개별 관리·AI 학습 안내','와와의 공식 안내를 바탕으로 학습코칭과 개별 관리, AI 학습의 차이를 살피고 지점별 확인 사항을 정리합니다.',body,[('학습시스템','/학습시스템/')],faq,kind='CollectionPage')

    faq=[('개별 맞춤 수업은 선생님과 학생이 항상 일대일로 수업하나요?','개별 진도와 설명·피드백을 적용한다는 의미로 이해해야 합니다. 공식 안내에는 여러 학생이 선생님을 중심으로 공부하는 방식도 포함되어 있습니다. 실제 인원과 개별 지도 시간은 지점에서 확인해 주세요.'),('영상에 나온 성적 변화가 우리 아이에게도 적용되나요?','영상은 특정 학습 사례와 인터뷰입니다. 동일한 성적 변화나 기간을 보장하지 않습니다. 아이의 현재 수준, 출석과 과제 수행, 목표에 맞는 계획을 상담하는 것이 우선입니다.'),('처음 상담할 때 무엇을 준비하면 좋나요?','학교와 학년, 최근 시험지 또는 풀던 교재, 어려운 단원, 등원할 수 있는 요일을 정리해 주세요. 시작 진도와 복습 범위, 수업 구성 및 비용을 구체적으로 확인하는 데 도움이 됩니다.')]
    body=guide_hero('ABOUT WAWA','수업 진도와 공부하는 힘을 함께','와와학습코칭센터는 학생별 학습 상황을 진단하고, 스스로 공부하는 과정을 지도하는 방향을 안내합니다. 학습 계획과 실행을 어떻게 연결하는지부터 살펴보세요.')
    body+=section('official-video','공식 소개 영상으로 먼저 보기','<div class="bd-feature-grid"><div><h3>어떤 방식으로 공부하나요?</h3><p>브랜드가 설명하는 수업 방향을 영상으로 살펴보고, 우리 아이에게 필요한 관리가 무엇인지 생각해 보세요. 영상을 누르면 재생 화면이 열립니다.</p><p>지점별 과목, 학년, 시간표와 실제 관리 방식은 아래 지점안내에서 따로 확인해야 합니다.</p></div>'+video('59Tna9pZWrk','와와학습코칭센터 공식 소개')+'</div>')
    body+=section('flow','상담에서 수업까지 이어지는 세 단계',steps([('진단: 어떤 부분이 어려운가','교과 이해와 학습 습관을 함께 살피는 방향입니다. 틀린 문제의 점수만 비교하기보다, 개념 이해·풀이·복습 중 어느 단계에서 막혔는지 확인해 보세요.'),('계획: 무엇을 먼저 공부할까','진단 결과를 바탕으로 시작 교재와 진도를 상담합니다. 같은 학년이라도 공부할 범위와 속도는 달라질 수 있습니다.'),('점검: 혼자서도 해낼 수 있나','플래너 작성과 학습 결과 확인을 통해 계획을 실행하는 경험을 쌓도록 돕습니다. 기록을 어떻게 확인하고 다음 계획에 반영하는지 질문해 보세요.')]))
    body+=section('interviews','현장의 이야기, 맥락과 함께 보기','<div class="bd-grid">'+''.join('<article class="bd-card"><h3>'+e(title)+'</h3>'+video(id,title)+'<p>'+e(copy)+'</p></article>' for id,title,copy in [('avpJfW7eIV0','학습 변화 사례 인터뷰','특정 학생의 경험을 다룬 공식 영상입니다. 점수와 성적 향상은 개인별 결과로 읽어 주세요.'),('f_skFu40U04','원장 인터뷰로 보는 학습 성장','학습을 지도하는 관점과 현장 이야기를 들어볼 수 있습니다. 모든 지점의 운영을 대신하는 설명은 아닙니다.'),('UIXUaBZdNXU','은평점의 시험 준비 이야기','은평점의 시험기간 사례를 소개한 영상입니다. 다른 지점의 시험 대비 일정과 수업 방식은 별도로 확인하세요.')])+'</div>')
    body+=section('faq','학습코칭 상담 전 질문',faqs_markup(faq))+source_note('brand/wawacenter','와와 브랜드 소개')+section('next','구체적인 관리 방식 알아보기',guide_cards())
    shell('/학습시스템/와와학습코칭/','와와 학습코칭 수업 방식과 공식 영상','와와 학습코칭의 진단·계획·점검 흐름을 공식 영상으로 살펴보고, 개별 수업과 지점 상담에서 확인할 질문을 정리합니다.',body,[('학습시스템','/학습시스템/'),('와와 학습코칭','/학습시스템/와와학습코칭/')],faq)

    faq=[('플래너는 계획을 쓰는 것만으로 끝나나요?','계획과 실제 공부한 내용을 비교하는 데 의미가 있습니다. 누가 어느 시점에 확인하는지, 미완료 과제가 있을 때 어떻게 조정하는지 지점 상담에서 물어보세요.'),('오답노트를 많이 쓰면 좋은 관리인가요?','분량보다 틀린 원인을 구분하고 다시 풀 수 있는지 확인하는 과정이 중요합니다. 개념 부족인지 풀이 실수인지 살핀 뒤 재학습과 재풀이를 어떻게 연결하는지 확인해 보세요.'),('학부모에게 매일 결과를 보내 주나요?','공식 안내는 학습 관리와 소통의 방향을 설명합니다. 보고 주기, 전달 방식과 기록 항목은 지점별로 다를 수 있으므로 실제 작성 예시를 요청해 확인해 주세요.')]
    body=guide_hero('PERSONAL LEARNING','관리의 내용을 구체적으로 확인하세요','“꼼꼼하게 관리한다”는 말보다 어떤 기록을 보고 어떻게 피드백하는지 알아보세요. 플래너, 학습 도구, 오답 정리를 연결해 수업 상담에서 확인할 기준을 마련했습니다.')
    body+=section('planner','플래너: 할 일과 실제 결과를 나란히',steps([('목표를 작은 단위로','“수학 공부”처럼 넓은 계획보다 단원과 분량, 완료 기준을 구체적으로 정하면 실행 여부를 돌아보기 쉽습니다.'),('미완료 이유까지 확인','시간이 부족했는지, 개념이 막혔는지, 시작하지 못했는지를 구분합니다. 결과만 표시하면 다음 계획을 조정하기 어렵습니다.'),('다음 계획에 반영','잘한 부분과 다시 공부할 부분을 나눠 계획을 조정합니다. 지점에서는 어떤 기준으로 계획을 바꾸는지 확인해 보세요.')]))
    body+=section('example','수학 오답을 점검하는 예시','<div class="bd-card"><p class="bd-kicker">이해를 돕기 위한 학습 예시</p><h3>계산 실수와 개념 부족을 구분한다면</h3><p>일차방정식 문제를 틀렸을 때, 식을 잘못 세웠는지 부호 계산을 놓쳤는지부터 살펴봅니다. 식을 만드는 과정이 어려웠다면 개념과 기본 예제로 돌아가고, 계산 실수였다면 해당 풀이 단계를 다시 확인하는 식입니다.</p><p>설명을 들은 뒤 답을 가리고 다시 풀어 보고, 조건이 달라진 문제에서도 같은 원리를 적용할 수 있는지 점검해 보세요. 이 예시는 학습 원리를 설명한 것으로 모든 지점의 정해진 수업 절차를 뜻하지 않습니다.</p></div>')
    body+=section('questions','지점에서 확인할 관리 질문','<div class="bd-grid bd-two">'+''.join('<div class="bd-card"><h3>'+e(h)+'</h3><p>'+e(p)+'</p></div>' for h,p in [('개별 진도','시작 교재를 어떤 기준으로 정하고, 이해도가 달라지면 진도를 어떻게 조정하나요?'),('풀이와 피드백','모르는 문제를 질문하는 방식과 다시 풀어 보는 시점은 어떻게 정하나요?'),('공부 습관','플래너 작성, 미완료 과제와 복습 결과는 누가 언제 확인하나요?'),('학부모 소통','어떤 항목을 어떤 주기로 공유하나요? 개인정보를 가린 작성 예시를 볼 수 있나요?')])+'</div>')
    body+=section('faq','개별 관리에 관해 자주 묻는 질문',faqs_markup(faq))+source_note('intro/coachingSystem','와와 학습코칭 시스템')+section('next','도구와 지점을 이어서 확인하세요',guide_cards())
    shell('/학습시스템/개별맞춤관리/','플래너·오답으로 살펴보는 개별 학습 관리','플래너 실행 기록과 오답 재풀이가 개별 학습 관리에 어떻게 연결되는지 살피고, 지점별 피드백 방식을 확인할 질문을 정리합니다.',body,[('학습시스템','/학습시스템/'),('개별 맞춤 관리','/학습시스템/개별맞춤관리/')],faq)

    faq=[('AI가 선생님의 지도를 대신하나요?','AI 학습은 진단, 문제 추천과 결과 확인을 돕는 도구로 이해할 수 있습니다. 결과를 해석하고 학생의 계획과 수업에 연결하는 과정은 담당 지도 방식과 함께 확인해야 합니다.'),('AI 학습은 모든 지점에서 같은 비용으로 제공되나요?','지점별로 도입 여부, 대상 과목, 필수 또는 선택 구성과 비용이 다를 수 있습니다. 일반 과목 수강료에 포함되는지, 별도 금액이 있는지 확인해 주세요.'),('공식 안내 학년과 지점의 수강 학년이 다른 이유는 무엇인가요?','공식 안내는 프로그램 자체의 대상 범위입니다. 실제 지점에서 지도하는 학년, 반 편성과 등록 가능한 시간표는 별도로 정해질 수 있습니다.')]
    body=guide_hero('AI LEARNING','진단 결과를 필요한 연습으로','문제를 많이 푸는 것과 필요한 문제를 고르는 것은 다릅니다. 공식 AI 학습 안내는 진단과 분석을 토대로 학습 내용을 연결하는 방향을 설명합니다.')
    programs=[('영어','초1~고3','진단과 영역별 분석을 바탕으로 어휘·읽기·듣기·문법 등 필요한 학습을 연결하는 방식입니다. 파닉스 등 시작 단계와 현재 학습 수준을 함께 확인해 보세요.'),('수학','초1~고3','진단 후 수준에 맞는 문제를 학습하고 오답과 연관된 연습으로 부족한 부분을 확인하는 방향입니다. 추천 문제를 수업 진도와 어떻게 연결하는지 물어보세요.'),('국어','중1~고3','독서·문학·문법 영역의 학습과 취약 부분 확인을 돕는 프로그램입니다. 학교 교재 및 시험 범위와의 연결 방식은 지점에서 확인해 주세요.'),('독서','초1~중2','읽기 흥미와 수준에 맞는 독서 활동 및 기록을 돕는 방향입니다. 교과 국어 수업과는 목적과 구성이 다를 수 있습니다.')]
    body+=section('programs','과목별 공식 프로그램 범위','<p class="bd-notice">아래 학년은 공식 프로그램 설명의 범위입니다. 전국 모든 지점의 개설 학년이나 등록 가능 여부를 뜻하지 않습니다.</p><div class="bd-grid bd-two">'+''.join('<article class="bd-card"><h3>'+e(s)+'</h3><div class="bd-grade">공식 대상 범위 · '+e(g)+'</div><p>'+e(p)+'</p></article>' for s,g,p in programs)+'</div>')
    body+=section('use','진단 다음에 확인할 세 가지',steps([('왜 이 학습이 추천됐나요?','점수나 정답률만 확인하기보다 어떤 개념과 유형에서 어려움이 있었는지 설명을 들어 보세요.'),('언제 다시 확인하나요?','추천 학습 후 같은 실수가 줄었는지, 다른 문제에도 적용할 수 있는지 확인하는 방식이 필요합니다.'),('기존 수업과 어떻게 연결되나요?','학교 시험과 교재 진도, 오답 복습 계획에 AI 결과를 어떻게 반영하는지 상담해 보세요.')]))
    body+=section('faq','AI 학습을 신청하기 전 질문',faqs_markup(faq))+source_note('intro/AISystem','와와 AI 학습 시스템')
    body+='<section class="bd-section bd-dark"><p class="bd-kicker">CHECK YOUR CENTER</p><h2>사용할 지점의 조건부터 확인하세요</h2><p>학교·학년·희망 과목과 함께 AI 학습 사용 여부, 시간, 추가 비용을 물어보세요.</p>'+actions([('/지점안내/','지점별 안내 보기',True)])+'</section>'
    shell('/학습시스템/AI학습/','영어·수학·국어·독서 AI 학습 안내','공식 AI 영어·수학·국어·독서 프로그램의 대상 학년과 활용 방식을 살피고, 지점별 도입 여부와 추가 비용 확인 사항을 안내합니다.',body,[('학습시스템','/학습시스템/'),('AI 학습','/학습시스템/AI학습/')],faq)

def connect_existing(manifest):
    byarea={a['slug']:b for b in BRANCHES for a in b['areas']};changed=[]
    def process(name):
        if not name.endswith('.html') or name.startswith(('지점안내/','학습시스템/')):return None
        raw=(ROOT/name).read_bytes();text=raw.decode('utf-8');old=text
        # Add one directory destination to the established top navigation.
        def nav(m):
            block=m[0]
            if 'data-directory-nav' not in block:block=block.replace('</nav>',f'<a data-directory-nav href="{href("/지점안내/")}">지점안내</a></nav>')
            return block
        text=re.sub(r'<nav\b(?=[^>]*class="nav")[^>]*>.*?</nav>',nav,text,flags=re.S)
        parts=name.split('/');slug=parts[2] if parts[0]=='과목별학원' and len(parts)==4 else parts[1] if parts[0]=='전국센터' and len(parts) in [3,4] else None
        if slug in byarea:
            b=byarea[slug]
            def localnav(m):
                block=m[0]
                block=re.sub(r'<a data-branch-link\b[^>]*>.*?</a>','',block,flags=re.S)
                block=block.replace('</nav>',f'<a data-branch-link href="{href(b["route"])}">{e(b["name"])} 종합 안내 · 조건·교육비·사진</a></nav>')
                return block
            text=re.sub(r'<nav class="area-related-links".*?</nav>',localnav,text,flags=re.S)
        if name in ['index.html','전국센터/index.html','과목별학원/index.html','학습가이드/index.html']:
            entry='<section class="bd-entry" data-branch-entry><p class="bd-kicker">지점과 학습 방식을 한눈에</p><h2>우리 아이가 다닐 곳을 구체적으로 살펴보세요</h2><p>188개 지점의 실제 주소와 과목별 학년, 교육비 자료를 확인하고 공식 영상으로 학습코칭 방식을 알아보세요.</p><div class="bd-entry-links">'+link('/지점안내/','우리 동네 지점 찾기')+link('/학습시스템/와와학습코칭/','공식 영상과 수업 방식')+link('/학습시스템/AI학습/','AI 학습 알아보기')+'</div></section>'
            if 'data-branch-entry' not in text:
                if name=='index.html':text=re.sub(r'(<section class="metric-row".*?</section>)',lambda m:m[0]+entry,text,count=1,flags=re.S)
                else:text=text.replace('</main>',entry+'</main>')
            if 'assets/branch-directory.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/assets/branch-directory.css"></head>')
        if text!=old:
            (ROOT/name).write_bytes(text.encode('utf-8'))
        if hashlib.sha256(text.encode('utf-8')).hexdigest()!=manifest['files'][name]:return name
        return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,name in enumerate(pool.map(process,manifest['files']),1):
            if name:changed.append(name)
            if i%1000==0:print(j({'checked':i,'changed':len(changed)}),flush=True)
    return changed

def approve_manifest(manifest, changed):
    public={n for n in manifest['files'] if not n.startswith(('지점안내/','학습시스템/','assets/branch-photos/'))}|set(NEW)|{'assets/branch-directory.css','assets/branch-directory.js'}
    public|={v['src'].lstrip('/') for b in BRANCHES for p in b['photos'] for v in p.values()}
    # Only actual page edits receive a new sitemap lastmod.
    tree=etree.parse(str(ROOT/'sitemap.xml'));ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};root=tree.getroot()
    existing={unquote(urlsplit(n.find('s:loc',ns).text).path):n for n in root}
    for file in set(NEW)|set(changed):
        route='/'+file.removesuffix('index.html');node=existing.get(route)
        if node is None:
            node=etree.SubElement(root,'{'+ns['s']+'}url');etree.SubElement(node,'{'+ns['s']+'}loc').text=url(route)
        lm=node.find('s:lastmod',ns)
        if lm is None:lm=etree.SubElement(node,'{'+ns['s']+'}lastmod')
        lm.text=DAY
    tree.write(str(ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True)
    hashes={};text_hashes={}
    for name in sorted(public):
        data=(ROOT/name).read_bytes();hashes[name]=hashlib.sha256(data).hexdigest()
        if re.search(r'\.(?:html|css|js|json|xml|txt|svg|webmanifest)$',name,re.I):text_hashes[name]=hashlib.sha256(data.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
    manifest.update({'files':hashes,'textSha256':text_hashes,'createdAt':datetime.now(timezone.utc).isoformat(),'sitemapPages':len(root)})
    save(ROOT/'release-public-manifest.json',manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
    guides();directory()
    for region in REGIONS:directory(region)
    for branch in BRANCHES:branch_page(branch)
    changed=connect_existing(manifest)
    save(ROOT/'seo-descriptions.json',DESCRIPTIONS)
    if args.manifest:approve_manifest(manifest,changed)
    save(ROOT/'tools/data/branch-upgrade-pages.json',{'date':DAY,'newPages':NEW,'connectedPages':changed})
    print(j({'newPages':len(NEW),'connectedPages':len(changed),'branches':len(BRANCHES),'regions':len(REGIONS),'manifestUpdated':args.manifest}))

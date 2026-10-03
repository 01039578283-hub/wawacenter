"""Publish only supplied teacher introductions and approved illustrative portraits."""
import argparse, collections, hashlib, json, re, shutil, zipfile
from html import escape
from pathlib import Path
from urllib.parse import quote
from lxml import etree
import openpyxl
from PIL import Image
import build_branch_upgrade as ui
import build_site_shell as common

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-03'
ui.DAY=DAY
HUB='/선생님찾기/'
PHOTO_NOTE='사진은 소개용 이미지이며 실제 선생님 사진이 아닙니다.'
NEEDS={
 'understanding':('개념·이해 점검',['개념 사이 연결','기초 개념 재확인','스스로 이해 점검','교재 없이 확인','익숙한 예시 활용','배운 내용 분류하기','내용 분류하기','핵심 내용 요약','핵심 문장 만들기','핵심 표현 정리','표와 그림 정리','낯선 표현 표시']),
 'questions':('질문·설명 연습',['자기 언어로 설명','질문을 구체화','설명 전후 비교','다음 질문 남기기','질문 순서 정하기','확인 질문 직접 쓰기','다른 사람에게 설명','선택 근거 말하기','설명 순서 바꾸기','짧은 설명 녹여 쓰기','중간 점검 질문']),
 'review':('오답·풀이 점검',['오답 원인 구분','재도전 전 확인','실수 점검표 만들기','마지막 풀이 검토','문제 조건 읽기','풀이 과정 기록','두 풀이 비교하기','과정에 표시하기','피드백 한 가지 적용','수정 과정 익히기']),
 'records':('복습·학습 기록',['복습 간격 조절','짧은 회상 활동','진행 과정 기록','어려움의 변화 기록','이전 기록 다시 읽기','학습 전후 비교','자기 평가 기준','다음 학습 연결']),
 'habits':('계획·공부 습관',['학습 시간 배분','작은 목표 설정','학습 순서 설계','과제 분량 조절','학습 분량 되돌아보기','학습 목표 대화','공부 시작 습관','단계별 시간 살피기','완료 기준 정하기','자료 정돈하기','작은 과제 선택','짧은 집중 구간','학습 시작 기록']),
 'application':('문제 적용·사고 확장',['과제 난도 조절','과제 선택 이유','변형 문제 살피기','비교 기준 먼저 정하기','비슷한 내용 비교','스스로 문제 만들기','예시 두 가지 비교','작은 예외 찾기','유사 과제 연결','조건 바꾸어 보기']),
}

def teacher_needs(t):
    return [key for key,(_,focus) in NEEDS.items() if set(t['focus']) & set(focus)]

def need_select(keys=None):
    return '<label>필요한 학습 도움<select name="need"><option value="">학습 도움 전체</option>'+''.join('<option value="'+key+'">'+escape(label)+'</option>' for key,(label,_) in NEEDS.items() if keys is None or key in keys)+'</select></label>'
GUIDES={
 '오답 원인 구분':'수학오답관리','재도전 전 확인':'수학오답관리','실수 점검표 만들기':'계산실수줄이기','마지막 풀이 검토':'계산실수줄이기',
 '질문을 구체화':'학습질문만들기','다음 질문 남기기':'학습질문만들기','질문 순서 정하기':'학습질문만들기','확인 질문 직접 쓰기':'학습질문만들기',
 '복습 간격 조절':'인출연습과간격복습','짧은 회상 활동':'인출연습과간격복습','교재 없이 확인':'인출연습과간격복습',
 '문제 조건 읽기':'수학문장제읽기','풀이 과정 기록':'수학서술형풀이','두 풀이 비교하기':'수학서술형풀이',
 '학습 시간 배분':'학습플래너작성법','작은 목표 설정':'학습플래너작성법','학습 순서 설계':'학습플래너작성법',
 '진행 과정 기록':'학습변화기록','어려움의 변화 기록':'학습변화기록','피드백 한 가지 적용':'피드백활용법','수정 과정 익히기':'피드백활용법',
 '핵심 내용 요약':'독서내용요약','자기 언어로 설명':'피드백활용법','설명 전후 비교':'학습변화기록',
 '과제 분량 조절':'학습부담점검','학습 분량 되돌아보기':'학습부담점검','학습 목표 대화':'학습대화방법',
}

def save(p,obj):
    content=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if p.exists() and p.read_bytes()==content:return
    tmp=p.with_name(p.name+'.teacher-tmp');tmp.write_bytes(content)
    try:tmp.replace(p)
    except PermissionError:
        # Windows file watchers can allow writes while denying replacement.
        import ctypes
        from ctypes import wintypes
        copy=ctypes.windll.kernel32.CopyFileW
        copy.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.BOOL]
        if not copy(str(tmp),str(p),False):raise ctypes.WinError()
        tmp.unlink()
def write(p,s):ui.write(p,s)
def marked(kind,s):return '<!-- teacher-links:'+kind+':start -->'+s+'<!-- teacher-links:'+kind+':end -->'
def file_for(route):return route.lstrip('/')+'index.html'
def link(route,label):return '<a href="'+quote(route,safe='/#-?=%')+'">'+escape(label)+'</a>'
def actions(items):return '<div class="pg-links">'+''.join(link(r,t) for r,t in items)+'</div>'

def load_records(source,branches):
    names={}
    for b in branches:
        for key in {b['name'],b['sourceName'],b['displayName']}:
            assert key not in names or names[key]['route']==b['route'];names[key]=b
    book=source/'교사 프로필.xlsx';w=openpyxl.load_workbook(book,read_only=True,data_only=True)
    records=[];seen=set();groups=collections.OrderedDict();duplicates=[]
    for s in w:
        for row,values in enumerate(s.iter_rows(values_only=True),1):
            v=[str(x).strip() if x is not None else '' for x in values]
            if not any(v):continue
            if v[:2] in [['지점','이름'],['지점명','선생님명']]:continue
            assert len(v)==4 and all(v),(s.title,row,'Expected four populated teacher fields')
            if tuple(v) in seen:duplicates.append({'sheet':s.title,'row':row});continue
            seen.add(tuple(v));name,person,focus,bio=v
            assert '*' in person and len(person)<12,(row,'Keep supplied masked name')
            parts=[x.strip() for x in focus.split('/') if x.strip()]
            prefix=name+' '+person+' 선생님입니다.'
            assert bio.startswith(prefix),(row,'Introduction identity differs from row')
            content=bio[len(prefix):].strip();sentences=[x.strip() for x in re.split(r'(?<=\.)\s+',content) if x.strip()]
            assert len(sentences)>=3,(row,'Incomplete introduction')
            t={'id':'teacher-'+str(len(records)+1).zfill(4),'name':person,'focus':parts,'bio':bio,'sentences':sentences,'sourceSheet':s.title,'sourceRow':row}
            records.append(t);groups.setdefault(name,[]).append(t)
    photos=sorted(source.glob('collage-profile-*.png'))
    assert len(photos)==12 and len({hashlib.sha256(p.read_bytes()).hexdigest() for p in photos})==12
    photo_data=[]
    for p in photos:
        public='assets/teachers/'+p.name;dest=ROOT/public;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or dest.read_bytes()!=p.read_bytes():shutil.copyfile(p,dest)
        with Image.open(p) as im:width,height=im.size
        photo_data.append({'src':'/'+public,'width':width,'height':height,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    result=[]
    for idx,(name,teachers) in enumerate(groups.items()):
        b=names.get(name);assert len(teachers)<=len(photo_data)
        start=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)%len(photo_data)
        for i,t in enumerate(teachers):
            photo=photo_data[(start+i)%len(photo_data)];t['image']=photo['src'];t['imageWidth']=photo['width'];t['imageHeight']=photo['height']
        result.append({'sourceName':name,'name':b['name'] if b else name,'route':HUB+name+'/','branchRoute':b['route'] if b else None,'region':b['region'] if b else '', 'district':b['district'] if b else '', 'address':b['address'] if b else '', 'areas':b['areas'] if b else [],'teachers':teachers})
    return result,photo_data,{'sha256':hashlib.sha256(book.read_bytes()).hexdigest(),'rows':len(records),'exactDuplicatesRemoved':duplicates}

def render_page(route,title,desc,body,crumbs,faqs=(),nodes=()):
    ui.shell(route,title,desc,body,crumbs,faqs=faqs,nodes=nodes,kind='CollectionPage')
    p=ROOT/file_for(route);s=p.read_text(encoding='utf-8')
    s=re.sub(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:common.header(route),s,count=1)
    s=s.replace('<body class="','<body data-site-shell="1" class="',1)
    s=s.replace('</head>','<link rel="stylesheet" href="/assets/teacher-directory.css"><link rel="stylesheet" href="/assets/site-shell.css"><script defer src="/assets/teacher-directory.js"></script></head>',1)
    write(p,s)

def hub(groups):
    count=sum(len(g['teachers']) for g in groups)
    desc=f'{len(groups)}개 지점의 선생님 소개 {count:,}건을 동네·지점·학습 도움으로 찾고, 지도 방향과 상담 준비 자료를 확인합니다.'
    hero='<section class="bd-hero"><p class="bd-kicker">TEACHERS</p><h1>우리 아이의 공부를<br>함께할 선생님 찾기</h1><p>선생님마다 중요하게 보는 공부 과정이 다릅니다.<br>지점과 지도 키워드를 살펴보고, 아이에게 필요한 도움을 찾아보세요.</p><div class="bd-summary"><div><strong>'+str(len(groups))+'</strong><span>지점별 소개</span></div><div><strong>'+f'{count:,}'+'</strong><span>선생님 소개</span></div><div><strong>지도 방향</strong><span>질문·설명·학습 기록</span></div></div></section>'
    regions=list(dict.fromkeys(b['region'] for b in ui.BRANCHES))
    form='<form class="bd-search tf-search" role="search" data-teacher-search hidden><label>동네·지점·선생님·지도 키워드<input type="search" name="q" placeholder="예: 장항동, 명일점 질문" autocomplete="off"></label><label>지역<select name="region"><option value="">전국 전체</option>'+''.join('<option value="'+escape(r)+'">'+escape(r)+'</option>' for r in regions)+'<option value="other">그 외 지점</option></select></label>'+need_select()+'<button class="bd-btn" type="reset">검색 초기화</button></form><p class="tf-filter-help">동네와 선생님의 지도 방향을 함께 살펴보세요. 이름을 누르면 해당 선생님의 소개로 바로 이동합니다.</p><p class="bd-result" data-teacher-status role="status" aria-live="polite">'+str(len(groups))+'개 지점 · 선생님 소개 '+str(count)+'건</p><noscript><p>아래 전체 목록에서 지점별 선생님 소개를 확인할 수 있습니다.</p></noscript><div class="pg-panel" data-teacher-empty hidden><h3>검색 결과가 없습니다.</h3><p>동네·지점 이름을 짧게 입력하거나 학습 도움과 지역 조건을 바꿔 보세요.</p>'+actions([('/지점안내/','동네별 지점 안내 보기')])+'</div>'
    cards=''
    for g in groups:
        focus=list(dict.fromkeys(t for p in g['teachers'] for t in p['focus']))[:3]
        search=' '.join([g['sourceName'],g['name'],g['region'],g['district'],g['address'],*[a['name'] for a in g['areas']],*[t['name']+' '+' '.join(t['focus']) for t in g['teachers']]])
        local=' '.join([g['sourceName'],g['name'],g['region'],g['district'],g['address'],*[a['name'] for a in g['areas']]])
        people='<ul class="tf-name-list" aria-label="'+escape(g['sourceName'])+' 선생님 바로가기">'+''.join('<li data-teacher-option data-needs="'+' '.join(teacher_needs(t))+'" data-search="'+escape(t['name']+' '+' '.join(t['focus']),quote=True)+'">'+link(g['route']+'#'+t['id'],t['name']+' 선생님')+'</li>' for t in g['teachers'])+'</ul>'
        nearby='<p class="tf-nearby">연결 동네 · '+escape(' · '.join(a['name'] for a in g['areas']))+'</p>' if g['areas'] else ''
        destinations=[(g['route'],'선생님 소개 보기')]+([(g['branchRoute'],'수업·교육비·위치')] if g['branchRoute'] else [])
        cards+='<article class="bd-card tf-directory-card" data-teacher-card data-region="'+(escape(g['region']) or 'other')+'" data-count="'+str(len(g['teachers']))+'" data-local-search="'+escape(local,quote=True)+'" data-search="'+escape(search,quote=True)+'"><p class="bd-card-meta">'+escape(' · '.join(x for x in [g['region'],g['district']] if x) or '지점명으로 찾기')+'</p><h3>'+link(g['route'],g['sourceName'])+'</h3>'+nearby+'<p><span class="tf-count" data-card-count>선생님 소개 '+str(len(g['teachers']))+'건</span></p><div class="tf-tags">'+''.join('<span>'+escape(x)+'</span>' for x in focus)+'</div>'+people+actions(destinations)+('</article>')
    faq=[('선생님의 담당 과목과 학년은 어디에서 확인하나요?','소개 글은 선생님의 지도 방향을 설명합니다. 현재 담당 과목·학년·수업 시간과 배정은 희망 지점 상담에서 확인해 주세요.'),('프로필 사진은 실제 선생님 사진인가요?',PHOTO_NOTE),('상담 전에 무엇을 준비하면 좋을까요?','최근 풀이와 학교 자료, 학생이 궁금한 질문을 준비해 보세요. 혼자 해결한 부분과 도움이 필요한 부분을 나누면 필요한 지도를 이야기하기 좋습니다.')]
    body=hero+ui.section('teacher-search','지점과 지도 키워드로 찾아보세요',form+'<div class="tf-directory-grid">'+cards+'</div>')
    body+=consultation_guides()
    body+=ui.section('faq','선생님 소개를 볼 때 궁금한 점',ui.faqs_markup(faq))
    node={'@type':'ItemList','@id':ui.url(HUB)+'#branches','numberOfItems':len(groups),'itemListElement':[{'@type':'ListItem','position':i,'name':g['sourceName'],'url':ui.url(g['route'])} for i,g in enumerate(groups,1)]}
    render_page(HUB,'선생님찾기 · 지점별 학습코칭 선생님 소개',desc,body,[('선생님찾기',HUB)],faq,[node])
    return {'route':HUB,'description':desc,'teacherIds':[t['id'] for g in groups for t in g['teachers']],'kind':'hub'}

def profile(t,g):
    body='<article class="tf-profile" id="'+t['id']+'" data-teacher-profile="'+t['id']+'"><figure><img src="'+ui.href(t['image'])+'" width="'+str(t['imageWidth'])+'" height="'+str(t['imageHeight'])+'" alt="선생님 소개용 이미지" loading="lazy" decoding="async"><figcaption>소개용 이미지</figcaption></figure><div><p class="tf-profile-meta">'+escape(g['sourceName'])+'</p><h3>'+escape(t['name'])+' 선생님</h3><div class="tf-tags">'+''.join('<span>'+escape(x)+'</span>' for x in t['focus'])+'</div></div><div class="tf-bio"><p>'+escape(' '.join(t['sentences'][:2]))+'</p><details><summary>'+escape(t['name'])+' 선생님의 지도 방향 더 보기</summary>'+''.join('<p>'+escape(s)+'</p>' for s in t['sentences'][2:])+'</details></div></article>'
    return body.replace(' data-teacher-profile="'+t['id']+'"',' data-teacher-profile="'+t['id']+'" data-needs="'+' '.join(teacher_needs(t))+'" data-search="'+escape(t['name']+' '+' '.join(t['focus']),quote=True)+'"',1)

def consultation_guides():
    rows=[('상담 전: 필요한 도움 정리','학생이 막힌 풀이와 최근 과제를 준비하고, 다음 수업에서 확인할 질문을 골라 보세요.','선생님상담질문','선생님 상담 질문 정리'),('상담 때: 첫 목표 함께 정하기','점수만 이야기하기보다 학생이 오늘 해 볼 행동과 다시 확인할 자료를 정해 보세요.','학생과학습목표정하기','학생과 학습 목표 정하기'),('수업 뒤: 설명과 과제 점검','진도와 함께 학생이 설명할 수 있는 내용, 남은 질문과 다음 과제를 살펴보세요.','첫수업후점검','첫 수업 뒤 확인할 것')]
    return ui.section('before-consultation','선생님과 만나는 순서에 맞춘 학습가이드','<div class="pg-grid">'+''.join('<article class="pg-card"><h3>'+h+'</h3><p>'+p+'</p>'+actions([('/학습가이드/'+slug+'/',label)])+'</article>' for h,p,slug,label in rows)+'</div>')

def branch_page(g):
    route=g['route'];title=g['sourceName']+' 선생님 소개';topics=list(dict.fromkeys(x for t in g['teachers'] for x in t['focus']))
    desc=g['sourceName']+' 선생님 '+str(len(g['teachers']))+'명의 '+topics[0]+'·'+topics[1]+' 지도 방향과 소개 글을 살펴보고, 필요한 상담을 준비합니다.'
    assert len(desc)<=80,(route,desc)
    hero='<section class="bd-hero"><p class="bd-kicker">'+escape(' · '.join(x for x in [g['region'],g['district']] if x) or 'TEACHERS')+'</p><h1>'+escape(g['sourceName'])+'<br>선생님 소개</h1><p>학생의 생각을 듣고 공부 과정을 함께 살펴보는 선생님들의 소개입니다. 지도 키워드와 글을 읽으며 아이에게 필요한 도움을 정리해 보세요.</p>'+('<p class="bd-address">'+escape(g['address'])+'</p>' if g['address'] else '')+actions([(HUB,'전체 지점 선생님 찾기'),('#teacher-profiles','선생님 '+str(len(g['teachers']))+'명 살펴보기')])+ '</section>'
    if g['branchRoute']:hero+=ui.section('center-information','수업·학년·교육비도 함께 확인하세요','<div class="pg-panel"><p>'+escape(g['name'])+'의 방문 주소와 과목별 안내 학년, 교육비 자료를 함께 살펴보세요. 담당 과목·시간표와 선생님 배정은 상담에서 확인해 주세요.</p>'+actions([(g['branchRoute'],g['name']+' 수업과 방문 안내')])+'</div>')
    else:hero+='<p class="pg-scope">담당 과목·학년·시간표와 방문 주소는 지점 상담에서 확인해 주세요.</p>'
    keys=set(key for t in g['teachers'] for key in teacher_needs(t))
    controls='<form class="bd-search tf-search tf-branch-search" role="search" data-profile-search hidden><label>선생님 이름·지도 키워드<input type="search" name="q" placeholder="예: 질문, 풀이, 학습 기록" autocomplete="off"></label>'+need_select(keys)+'<button class="bd-btn" type="reset">검색 초기화</button></form><div class="tf-profile-tools" data-profile-tools hidden><button class="bd-btn" type="button" data-profile-details="open">소개 글 모두 펼치기</button><button class="bd-btn" type="button" data-profile-details="close">소개 글 모두 접기</button></div><p class="bd-result" data-profile-status role="status" aria-live="polite">선생님 소개 '+str(len(g['teachers']))+'건</p><p class="pg-panel" data-profile-empty hidden>검색 결과가 없습니다. 이름이나 지도 키워드를 짧게 입력하거나 학습 도움 조건을 바꿔 보세요.</p>'
    body=hero+ui.section('teacher-profiles',g['sourceName']+'에서 만나는 선생님','<p class="tf-photo-note">'+PHOTO_NOTE+'</p>'+controls+'<div class="tf-grid">'+''.join(profile(t,g) for t in g['teachers'])+'</div>')
    guide_ids=list(dict.fromkeys(GUIDES[x] for x in topics if x in GUIDES))[:3]
    guides=json.loads((ROOT/'learning-guide-data.json').read_text(encoding='utf-8'))['pages'];labels={p['route']:p['title'] for p in guides}
    related=[('/학습가이드/'+s+'/',labels['/학습가이드/'+s+'/']) for s in guide_ids]
    body+=ui.section('prepare-learning','소개 글과 함께 살펴볼 학습 자료','<div class="pg-panel"><p>'+escape(g['sourceName'])+' 소개 글의 지도 키워드와 관련된 자료입니다. 최근 공부 기록에서 적용해 볼 부분을 골라 보세요.</p>'+actions(related+[('/학습가이드/학부모상담체크리스트/','상담 준비 체크리스트')])+'</div>')
    body+=consultation_guides()
    if g['areas']:
        body+=ui.section('nearby-learning','연결 동네의 수업 안내도 살펴보세요','<div class="pg-panel"><p>통학할 동네의 수업 안내에서 학년·과목 정보를 확인하고, 실제 방문 주소와 교육비는 지점 안내에서 함께 살펴보세요.</p>'+actions([('/전국센터/'+a['slug']+'/',a['name']+' 학원·수업 안내') for a in g['areas']])+'</div>')
    faq=[(g['sourceName']+' 선생님의 담당 과목은 어떻게 확인하나요?','소개 글에는 지도 방향이 담겨 있습니다. 현재 담당 과목·학년·수업 시간과 선생님 배정은 지점 상담에서 확인해 주세요.'),('사진은 실제 선생님의 모습인가요?',PHOTO_NOTE)]
    body+=ui.section('faq',g['sourceName']+' 선생님 소개 질문',ui.faqs_markup(faq))+ui.section('consultation','학생의 질문을 가지고 상담해 보세요','<div class="pg-panel"><p>최근 풀이와 학교 자료를 준비하고, 설명을 듣고 싶은 부분을 표시해 주세요. 선생님의 지도 방향과 필요한 도움을 함께 이야기할 수 있습니다.</p>'+ui.actions([(ui.FORM,'학습 상담 신청',True,True),('tel:01068398283','전화 상담')])+'</div>')
    persons=[{'@type':'Person','@id':ui.url(route)+'#'+t['id'],'name':t['name']+' 선생님','description':' '.join(t['sentences']),'jobTitle':'선생님','url':ui.url(route)+'#'+t['id'],'worksFor':{'@type':'EducationalOrganization','name':g['sourceName'],**({'url':ui.url(g['branchRoute'])} if g['branchRoute'] else {})}} for t in g['teachers']]
    node={'@type':'ItemList','@id':ui.url(route)+'#teachers','numberOfItems':len(persons),'itemListElement':[{'@type':'ListItem','position':i,'item':{'@id':p['@id']}} for i,p in enumerate(persons,1)]}
    render_page(route,title,desc,body,[('선생님찾기',HUB),(g['sourceName'],route)],faq,[node,*persons])
    return {'route':route,'description':desc,'teacherIds':[t['id'] for t in g['teachers']],'kind':'branch'}

def contextual_entry(group=None,region=None):
    if group:
        title=group['name']+' 선생님의 지도 방향도 살펴보세요';count=len(group['teachers']);route=group['route'];label=group['name']+' 선생님 '+str(count)+'명 소개';text='질문·설명·학습 기록에서 어떤 도움을 받을지, 선생님의 소개 글을 읽으며 상담할 내용을 준비해 보세요.'
    else:
        title='아이에게 필요한 도움을 선생님 소개에서 찾아보세요';route=HUB+('?region='+quote(region,safe='') if region else '');label=(region+' ' if region else '')+'선생님 찾기';text='지점별 선생님의 지도 키워드와 소개 글을 살펴보고, 현재 담당 과목과 학년은 상담에서 확인해 주세요.'
    return '<section class="pg-panel tf-context" data-teacher-entry data-teacher-route="'+escape(route,quote=True)+'"><h2>'+escape(title)+'</h2><p>'+escape(text)+'</p>'+actions([(route,label)])+'</section>'

def existing_links(name,s,by_branch,by_area):
    route='/' if name=='index.html' else '/'+name.removesuffix('index.html');parts=route.strip('/').split('/')
    g=None
    if parts[0]=='지점안내' and len(parts)>=3:g=by_branch.get('/'+'/'.join(parts[:3])+'/')
    if parts[0]=='전국센터' and len(parts)>=2:g=by_area.get(parts[1])
    if parts[0]=='과목별학원' and len(parts)>=3:g=by_area.get(parts[2])
    if name=='index.html':
        m=re.search(r'<!-- program-review:home:end -->',s);assert m
        block=marked('home','<nav class="pg-jump" aria-label="선생님 소개 바로가기">'+link(HUB,'우리 지점 선생님 찾기')+'</nav>')
        return s[:m.end()]+block+s[m.end():],{'file':name,'target':HUB,'branch':None}
    if parts[0] not in ['지점안내','전국센터','과목별학원']:return s,None
    region=parts[1] if parts[0]=='지점안내' and len(parts)==2 else None
    block=marked('entry',contextual_entry(g,region))
    # Close to the first decision point, before long conversion imagery.
    image=re.search(r'<section\b[^>]*\bid="lesson-image"[^>]*>',s)
    if image:end=image.start()
    else:end=common.hero_end(s)
    s=s[:end]+block+s[end:]
    return s,{'file':name,'target':g['route'] if g else HUB+('?region='+quote(region,safe='') if region else ''),'branch':g['branchRoute'] if g else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
    before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'));groups,photos,source=load_records(args.source,ui.BRANCHES)
    by_branch={g['branchRoute']:g for g in groups if g['branchRoute']}
    areas=json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'))['areas'];area_branches={}
    for b in ui.BRANCHES:
        for k in {b['name'],b['sourceName'],b['displayName']}:area_branches[k]=b['route']
    by_area={a['slug']:by_branch[area_branches[a['branch']]] for a in areas if a['branch'] in area_branches and area_branches[a['branch']] in by_branch}
    linked=[];all_html=[]
    with zipfile.ZipFile(args.audit/'before-source.zip') as z:
        for name in before['files']:
            if not name.endswith('.html'):continue
            s=z.read(name).decode('utf-8');route='/' if name=='index.html' else '/'+name.removesuffix('index.html')
            s=re.sub(r'<header\b[^>]*>[\s\S]*?</header>',lambda _:common.header(route),s,count=1)
            s,entry=existing_links(name,s,by_branch,by_area)
            if entry:linked.append(entry)
            write(ROOT/name,s);all_html.append(name)
    pages=[hub(groups)]+[branch_page(g) for g in groups]
    css=(args.audit/'before-source.zip')
    with zipfile.ZipFile(css) as z:s=z.read('assets/site-shell.css').decode('utf-8')
    s=s.replace('grid-template-columns:repeat(4,minmax(0,1fr))!important','grid-template-columns:repeat(3,minmax(0,1fr))!important')
    s+='\n.tf-context{margin:24px 0;padding:19px 22px}.tf-context h2{font-size:20px;line-height:1.5;margin:0 0 8px;color:#103f67}.tf-context p{margin:0;font-size:14px;line-height:1.8}.tf-context .pg-links{margin-top:13px}\n'
    s+='@media(max-width:740px){body[data-site-shell] .site-header[data-site-header] .nav{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:2px}body[data-site-shell] .site-header[data-site-header] .nav a:nth-child(n){font-size:12px;padding:5px 3px}}\n'
    write(ROOT/'assets/site-shell.css',s)
    all_html += [file_for(p['route']) for p in pages]
    shell=json.loads((ROOT/'site-shell-data.json').read_text(encoding='utf-8'));save(ROOT/'site-shell-data.json',{**shell,'nav':common.NAV,'pages':all_html})
    save(ROOT/'seo-descriptions.json',ui.DESCRIPTIONS)
    with zipfile.ZipFile(args.audit/'before-source.zip') as z:tree=etree.fromstring(z.read('sitemap.xml'))
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';existing={u.find('{'+ns+'}loc').text for u in tree}
    for p in pages:
        assert ui.url(p['route']) not in existing
        item=etree.SubElement(tree,'{'+ns+'}url');etree.SubElement(item,'{'+ns+'}loc').text=ui.url(p['route']);etree.SubElement(item,'{'+ns+'}lastmod').text=DAY
    (ROOT/'sitemap.xml').write_bytes(etree.tostring(tree,encoding='utf-8',xml_declaration=True,pretty_print=True))
    selected=set(before['files'])|set(ui.NEW)|{p['src'].lstrip('/') for p in photos}|{'assets/teacher-directory.css','assets/teacher-directory.js'}
    files={};text={}
    for name in sorted(selected):
        b=(ROOT/name).read_bytes();files[name]=hashlib.sha256(b).hexdigest()
        if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name):text[name]=hashlib.sha256(b.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
    save(ROOT/'release-public-manifest.json',{**before,'createdAt':'2026-10-02T12:00:00+09:00','files':files,'textSha256':text,'sitemapPages':len(tree)})
    data={'version':2,'reviewed':DAY,'photoNote':PHOTO_NOTE,'source':source,'photos':photos,'branches':groups,'pages':pages,'linkedPages':linked,'needs':[{'id':key,'label':label,'focus':focus} for key,(label,focus) in NEEDS.items()]}
    save(ROOT/'teacher-directory-data.json',data)
    report={'teachers':sum(len(g['teachers']) for g in groups),'teacherBranches':len(groups),'connectedExistingBranches':len(by_branch),'separateBranchNames':[g['sourceName'] for g in groups if not g['branchRoute']],'newPages':len(pages),'linkedPages':len(linked),'directBranchLinks':sum(bool(p['branch']) for p in linked),'htmlPages':len(all_html),'sitemapPages':len(tree),'publicFiles':len(files),'photos':len(photos),'deployed':False}
    save(args.audit/'generation-summary.json',report);print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()

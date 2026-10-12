"""Improve existing page roles; preserve every URL, image and factual course record.

Uses only the previously reconciled branch/area datasets. Dry-run by default.
No new classes, prices, schedules, facilities or outcomes are inferred.
"""
import argparse, collections, hashlib, html, json, re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from lxml import html as dom
import refresh_local_copy as legacy
from refresh_area_facts import scope, filtered, grade_text, walk, LD
from subject_editorial import BY_ID

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-13'
STYLE='assets/search-content.css'
e=lambda s:html.escape(str(s),quote=True)
def load(n):return json.loads((ROOT/n).read_text('utf8'))
BRANCHES={b['route']:b for b in load('branch-directory-data.json')['branches']}
AREAS={a['slug']:a for a in load('area-reference.json')['areas']}
AREA_BRANCH={a['slug']:b for b in BRANCHES.values() for a in b['areas']}
GRADES={p['route']:p for p in load('grade-directory-data.json')['pages']}
SUBJECT_DATA=load('subject-directory-data.json')
SUBJECTS={p['route']:p for p in SUBJECT_DATA['pages']}
STAGES={'초':'초등학생','중':'중학생','고':'고등학생'}
STUDY_STAGES={'초':'초등','중':'중등','고':'고등'}
ROLES={
 '지역학원':('동네에서 지점 고르기','지점 위치·과목 선택','필요 과목과 등원 일정'),
 '와와학습코칭학원':('공부 습관 상담 준비','계획·실행 기록','공부 시작과 복습 기록'),
 '영어수학학원':('영어·수학 주간 계획','두 과목 일정 조율','영어·수학 공부 시간 배분'),
 '영수학원':('영어·수학 수강 비교','과목 선택 기준','한 과목과 두 과목 수강 비교'),
 '초등영수학원':('초등 영어·수학 시작 점검','기초·학습 부담','초등 읽기·연산과 과제 부담'),
 '중등영수학원':('중등 영어·수학 내신 준비','평가 자료·복습 순서','중등 학교 자료와 복습 우선순위'),
 '고등영수학원':('고등 영어·수학 학습 계획','선택 과목·시간 배분','고등 선택 과목과 시험 준비'),
 '영어학원':('영어 영역별 수강 점검','어휘·독해 진단','영어 영역별 어려움과 수강 조건'),
 '수학학원':('수학 단계별 수강 점검','개념·풀이 진단','수학 개념·풀이와 수강 조건'),
}

def route(name):return '/'+name.removesuffix('index.html')
def link(url,label):return '<a href="'+e(quote(url,safe='/#?:=&'))+'">'+e(label)+'</a>'
def replace_section(text,ident,fn):
    m=re.search(r'<section\b[^>]*\bid="'+re.escape(ident)+r'"[^>]*>',text)
    if not m:return text
    depth=1
    for end in re.finditer(r'</?section\b[^>]*>',text[m.end():]):
        depth+= -1 if end[0].startswith('</') else 1
        if depth==0:
            stop=m.end()+end.end();return text[:m.start()]+fn(text[m.start():stop])+text[stop:]
    raise ValueError('Unclosed section '+ident)

def course_comparison(a,ss,stage=None):
    known=[s+' '+grade_text(filtered(a,s,stage)) for s in ss if filtered(a,s,stage)]
    missing=[s for s in ss if not filtered(a,s,stage)]
    text=('자료의 안내 범위는 '+', '.join(known)+'입니다. ') if known else ''
    if missing:text+=' · '.join(missing)+'의 해당 학년은 자료에서 확인되지 않아 현재 수강 가능 여부를 먼저 문의해야 합니다. '
    return text+'안내 학년이 같더라도 시간표·담당 수업·등록 가능 여부가 같다는 뜻은 아닙니다.'

def role_rows(category,a,b,ss,stage):
    if category=='지역학원':
        offered=[s for s,g in a['grades'].items() if g]
        return [
          ('첫 확인: 필요한 과목과 학년', '자료에 학년이 기재된 과목은 '+(' · '.join(offered) or '확인되지 않았습니다')+('입니다. ' if offered else '. ')+ '여러 과목을 한꺼번에 정하기 전에, 학생이 혼자 해결하기 어려운 과제 한 가지와 해당 학년을 알려 주세요.'),
          ('두 번째 확인: 동네명과 실제 방문 주소',a['area']+' 페이지에서 연결하는 곳은 '+b['name']+'입니다. 동네 이름만으로 이동 시간을 예상하지 말고 위 지도의 실제 주소를 기준으로 하교·식사·이동·귀가 시간을 확인하세요. 차량 운행이나 특정 학교 전용 수업은 별도로 확인해야 합니다.'),
          ('세 번째 확인: 적용되는 수업 구성','교육비 표의 과목·학년·주당 횟수·회당 시간을 함께 읽으세요. 공통 참고표와 지점별 안내를 구분하고, 교재비와 별도 프로그램 비용을 포함한 최종 조건을 문의하세요.')]
    if category=='와와학습코칭학원':
        return [('시작이 늦는 날과 풀이가 막히는 날 구분','며칠 동안 계획한 시작 시각, 실제 시작 시각, 끝낸 과제를 기록해 보세요. 시작 전 준비가 어려운지, 시작한 뒤 특정 단원에서 멈추는지 구분하면 필요한 도움을 더 정확하게 설명할 수 있습니다.'),('같은 과제를 혼자 다시 하는 과정','설명을 들었을 때 이해한 문제와 다음 날 도움 없이 푼 문제를 나누어 기록하세요. 정답뿐 아니라 힌트가 필요했던 줄을 남기고, 상담에서 도움을 줄이는 방법을 질문하세요.'),('상담 뒤 비교할 기록 정하기',b['name']+'에서 상담할 때는 시작 과제의 범위, 끝냈다고 판단할 기준, 다음에 확인할 자료를 정리하세요. 구체적인 관리 주기와 학부모 안내 방식은 실제 운영 조건을 확인해야 합니다.')]
    if category=='영어수학학원':
        return [('학교 일정부터 놓고 두 과목 시간 배분','일주일 달력에 학교 과제·평가일과 고정 활동부터 적으세요. 영어·수학에 쓸 수 있는 시간을 각각 남긴 뒤 미완료 과제가 몰리는 날을 확인합니다. 수업 시간표는 희망 일정과 맞는지 지점에서 확인하세요.'),('영어 복습과 수학 재풀이의 완료 기준','영어는 외운 표현을 문장에서 설명했는지, 수학은 풀이를 보지 않고 다시 풀었는지 남기세요. 같은 30분을 공부했더라도 완료한 활동이 다르므로 페이지 수만으로 비교하지 않습니다.'),('두 과목 일정이 충돌할 때 질문','영어와 수학의 안내 범위부터 각각 확인하세요. '+course_comparison(a,['영어','수학'])+' 한 과목의 과제가 밀릴 때 분량과 복습 시점을 어떻게 조정하는지도 물어보세요.')]
    if category=='영수학원':
        return [('함께 수강할 수 있는 학년인지 비교',course_comparison(a,['영어','수학'])+' 한 과목의 안내만 보고 두 과목 모두 등록할 수 있다고 판단하지 마세요.'),('한 과목부터 시작할지 판단할 자료','최근 영어 답안과 수학 풀이에서 혼자 해결하지 못한 부분을 표시해 보세요. 학교 일정과 현재 공부 부담까지 비교해 우선 필요한 과목을 정하고, 두 과목을 함께 배울 경우의 지도·과제 구성을 질문하세요.'),('교육비와 시간표를 같은 조건으로 비교','한 과목 금액과 두 과목 구성을 구분하고, 회당 시간·주당 횟수·교재비·추가 프로그램을 함께 확인하세요. 합산 금액이나 동시 수강 혜택을 임의로 가정하지 말고 적용되는 조건을 안내받으세요.')]
    if category in ['초등영수학원','중등영수학원','고등영수학원']:
        rows=list(legacy.COMBINED[stage])
        third={'초':('과제와 휴식의 균형','학생이 혼자 읽을 수 있는 지시문과 설명이 필요한 지시문을 나누세요. 영어·수학 과제를 끝내는 데 걸린 실제 시간과 쉬는 시간을 기록해, 두 과목을 함께 시작해도 부담이 과하지 않을지 상담하세요.'),'중':('학교 평가 자료로 복습 순서 정하기','영어 교과서·배부 자료와 수학 시험 범위를 같은 달력에 적으세요. 서술형 감점 이유, 조건 해석 오류, 계산 실수를 나누고 과목마다 다시 확인할 문제를 골라 질문하세요. 학교명만으로 시험 대비 방식이 같다고 판단하지 않습니다.'),'고':('선택 과목과 목표에 맞춰 시간 배분','학년, 수학 선택 과목, 학교 시험 범위, 최근 영어 지문을 함께 준비하세요. 내신과 모의고사에서 어려운 부분이 같은지 비교하고, 제한 시간 안에 못 푼 문제와 개념을 몰라 멈춘 문제를 구분해 상담하세요.')}[stage]
        return rows+[third,('과목별 안내 학년을 따로 확인',course_comparison(a,['영어','수학'],stage))]
    subject=ss[0]
    rows=[]
    bank=legacy.MATH if subject=='수학' else legacy.ENGLISH
    for lv in ['초','중','고']:
        if filtered(a,subject,lv):
            h,body=bank[lv];rows.append((h+'에서 가져올 학습 자료',body))
    if not rows:rows=[(subject+' 상담 전에 개설 여부부터 확인','제공 자료에서는 해당 과목의 안내 학년을 확인하지 못했습니다. 학생의 학년과 배우는 범위를 먼저 알려 주고 수강 가능 여부를 확인한 뒤 상담 자료를 준비하세요.')]
    rows.append(('시작할 범위와 다음 확인 기준',('개념은 설명하지만 첫 식을 못 쓰는지, 식은 맞지만 계산에서 틀리는지 구분하세요. 도움받은 풀이와 혼자 다시 푼 풀이를 나란히 두고 다음에 확인할 문제의 조건을 질문하세요.' if subject=='수학' else '단어의 뜻, 문장 구조, 글의 근거 중 어디에서 멈추는지 표시하세요. 틀린 답을 고친 뒤 새 문장에서도 같은 방법을 적용할 수 있는지 확인할 자료를 질문하세요.')))
    return rows

def legacy_page(text,name,a,b):
    cat,ss,stage=scope(name);role,purpose,topic=ROLES[cat]
    oldtitle=legacy.plain(re.search(r'<title>(.*?)</title>',text,re.S)[1])
    model=legacy.content_model(a,name,oldtitle)
    model.update(heading=a['area']+' '+role,intro=a['area']+'에서 '+b['name']+'을 알아볼 때 '+topic+'을 살펴보는 안내입니다. 위의 과목별 학년·주소·교습비 자료와 아래 학생 기록을 함께 확인해 주세요.',rows=role_rows(cat,a,b,ss,stage),focus='')
    if cat=='지역학원':model['prep']=['희망 과목과 학생의 현재 학년','학교에서 출발하는 시각과 귀가해야 하는 시각','교육비·횟수·교재비를 함께 적을 상담 메모']
    elif cat=='와와학습코칭학원':model['prep']=['계획한 시각과 실제로 시작한 시각','혼자 한 과제와 도움받은 과제의 구분','다음 날 다시 풀어 본 결과']
    elif cat=='영어수학학원':model['prep']=['학교·학원·다른 활동을 적은 주간 일정','영어와 수학의 실제 공부 시간·완료량','일정이 겹쳐 미룬 과제와 다시 할 날짜']
    elif cat=='영수학원':model['prep']=['영어·수학에서 가장 어려웠던 답안 각각','한 과목 또는 두 과목에 쓸 수 있는 시간','과목별 횟수·수업 시간·비용 비교 메모']
    else:model['prep']=[model['prep'][0],'정답을 고치기 전 풀이·답안과 도움받은 부분',model['prep'][1],model['prep'][2]]
    new=legacy.render(a,model).replace('data-copy-version="1"','data-copy-version="1" data-content-role="'+e(role)+'"')
    follow='상담에서 정한 '+topic+'의 첫 확인 항목과 학생이 가져갈 기록을 적어 두세요. 현재 시간표와 수강 조건은 '+link(b['route'],b['name']+' 지점 안내')+'에서 확인하고 상담으로 확정해 주세요.'
    new=re.sub(r'(<h2 id="review-title">.*?</h2>)<p>.*?</p>',lambda m:m[1]+'<p>'+follow+'</p>',new,flags=re.S)
    if cat=='지역학원':
        model['faqs'][2]=('동네 이름과 실제 지점 이름이 다른데 어디로 방문하나요?',e(a['area']+' 안내에 연결된 실제 지점은 '+b['name']+'이며 주소는 '+b['address']+'입니다. 방문 전 상담 일정과 위치를 확인해 주세요.'))
        new=re.sub(r'(<div class="local-copy-faq">).*?(</div>)',lambda m:m[1]+''.join('<details><summary>'+e(q)+'</summary><p>'+ans+'</p></details>' for q,ans in model['faqs'])+m[2],new,flags=re.S)
    text=re.sub(r'<!-- local-copy:start -->.*?<!-- local-copy:end -->',lambda _:new,text,flags=re.S)
    heads=[(m[1],legacy.plain(m[2])) for m in re.finditer(r'<h[23] id="([^"]+)">(.*?)</h[23]>',new,re.S)]
    canonical=dom.fromstring(text).xpath('//link[@rel="canonical"]/@href')[0]
    def schema(m):
        obj=json.loads(m[2])
        for n in walk(obj):
            kind=n.get('@type')
            if kind=='FAQPage':n['mainEntity']=[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':legacy.plain(ans)}} for q,ans in model['faqs']]
            if kind in ['WebPage','Article']:
                n['hasPart']=[{'@type':'WebPageElement','name':title,'url':canonical+'#'+ident} for ident,title in heads]
                if kind=='Article':n['articleSection']=[title for ident,title in heads]
            if kind=='ItemList' and n.get('@id','').endswith('#checklist'):
                n['itemListElement']=[{'@type':'ListItem','position':i,'name':v} for i,v in enumerate(model['prep'],1)]
        return m[1]+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+m[3]
    text=LD.sub(schema,text)
    title=f'{a["area"]} {cat if cat!="지역학원" else "학원 안내"} | {b["name"]} {purpose}'
    desc=f'{a["area"]} {cat if cat!="지역학원" else "학원"} 안내에서 {b["name"]}의 수강 조건과 {topic} 확인 방법을 살펴보세요.'
    return text,role,title,desc

def consolidate_courses(block):
    # Course names and grade data stay on their individual cards. Only identical
    # qualifications are shared once in the same course section.
    paragraphs=re.findall(r'<p(?: class="(?:bd-pending|bd-course-note)")?>[^<]+</p>',block)
    repeats={p for p,n in collections.Counter(paragraphs).items() if n>1}
    notes=[];original=dom.fromstring(block)
    for p in sorted(repeats):
        # Exclude arbitrary instructional or contact text.
        if not any(s in p for s in ['제공 자료','화상 수업','상담 시 학생','수업은','학년','예비']):continue
        note_text=legacy.plain(p);subjects=[]
        for card in original.xpath('//*[@data-course or @data-stage-course]'):
            if any(legacy.plain(dom.tostring(x,encoding='unicode'))==note_text for x in card.xpath('.//p')):
                subjects.append(card.get('data-course') or card.get('data-stage-course'))
        assert subjects,'Shared course condition must retain its subjects'
        labelled=re.sub(r'(<p\b[^>]*>)',lambda m:m[1]+'<strong>'+e(' · '.join(subjects))+':</strong> ',p,count=1)
        block=block.replace(p,'');notes.append(labelled)
    if notes:block=block.removesuffix('</section>')+'<div class="sc-course-note"><strong>과목별로 따로 확인할 조건</strong>'+''.join(notes)+'</div></section>'
    return block

def subject_page(text,p,b):
    keys=p['topics'];subject=p['subject'];stage=STAGES[p['stage']]
    groups=[[],[],[]]
    for key in keys:
        index=0 if BY_ID[key][1]==subject else 2 if key in ['study-dialogue','reward','feedback','progress-review'] else 1
        groups[index].append(key)
    # Preserve all topic content and existing fragment URLs, but make the subject
    # skills the first group. The content catalog follows that visible order.
    blocks={m[1]:m[0] for m in re.finditer(r'<section data-subject-topic="([^"]+)".*?</section>',text,re.S)}
    assert set(blocks)==set(keys),(p['route'],'topic sections')
    titles=[stage+' '+subject+'에서 막힌 단계 찾기','풀이·복습 기록으로 수업 비교하기','학부모와 함께 정할 다음 점검']
    intros=['현재 배우는 범위에 해당하는 항목을 골라 학생의 실제 답안과 비교하세요. 모든 내용을 한 번에 시작할 필요는 없습니다.','설명을 들은 결과와 혼자 다시 해 본 결과를 구분해 수업에서 필요한 도움을 질문하세요.','성과를 약속받기보다 확인할 기록과 다음 행동을 구체적으로 정하는 데 활용하세요.']
    grouped=''
    for i,group in enumerate(groups):
        if not group:continue
        grouped+='<section class="bd-section sc-topic-group" id="subject-reading-'+str(i)+'" aria-labelledby="subject-reading-'+str(i)+'-title"><h2 id="subject-reading-'+str(i)+'-title">'+e(titles[i])+'</h2><p class="bd-lead">'+e(intros[i])+'</p><div class="sc-topic-grid">'
        for key in group:
            block=blocks[key].replace('<section ','<article ',1).removesuffix('</section>')+'</article>'
            block=block.replace('<h3>학생 자료에서 해 볼 점검</h3>','<h4>학생 자료에서 해 볼 점검</h4>')
            block=re.sub(r'<h2(\b[^>]*)>(.*?)</h2>',r'<h3\1>\2</h3>',block,flags=re.S)
            grouped+=block
        grouped+='</div></section>'
    first=next(iter(blocks.values()));text=text.replace(first,grouped,1)
    for block in list(blocks.values())[1:]:text=text.replace(block,'',1)
    p['topics']=[key for group in groups for key in group]
    def local(block):
        # The full school inventory remains in schools; avoid repeating both it
        # and the exact same topic questions from the reading above.
        documents={
          '초':[('학교·가정 과제','최근 배운 단원과 숙제에서 혼자 읽고 시작한 부분을 표시하세요.'),('학생의 말과 풀이','설명을 따라 한 답과 학생이 스스로 설명한 답을 구분하세요.'),('과제에 걸린 시간','준비·풀이·휴식 시간을 나누어 실제 부담을 알려 주세요.')],
          '중':[('교과서·배부 자료','단원명, 선생님이 안내한 범위와 제출 기한을 표시하세요.'),('시험·서술형 답안','틀린 문항과 감점된 표현을 남기고 답을 고치기 전 기록을 가져오세요.'),('평가 안내','학생이 받은 평가 기준과 수행평가 일정을 확인해 복습 순서를 의논하세요.')],
          '고':[('과목명·선택 과목','학년만 적지 말고 현재 배우는 과목과 학교 시험 범위를 함께 적으세요.'),('내신·모의고사 답안','시간 부족과 개념·해석의 어려움을 구분하고 같은 약점이 반복되는지 비교하세요.'),('교재·학습 시간','학교 교재와 개인 교재가 겹치는 범위, 과목별로 쓸 수 있는 시간을 준비하세요.')]
        }[p['stage']]
        body='<p class="bd-lead">학교마다 같은 방식으로 수업한다고 가정하지 않고, 학생이 실제로 받은 자료를 기준으로 상담할 범위를 정리합니다.</p><article class="bd-card sd-area" data-subject-area="'+e(p['area'])+'"><h3>'+e(p['name'])+' '+stage+' '+subject+' 상담에 가져갈 학교 자료</h3><dl class="sc-record-list">'+''.join('<div><dt>'+e(h)+'</dt><dd>'+e(v)+'</dd></div>' for h,v in documents)+'</dl><p>'+link('#schools',b['name']+' 실제 주소와 학교 참고 정보')+'를 확인하고 하교 후 방문 가능한 시간을 함께 알려 주세요.</p></article>'
        return re.match(r'<section[^>]*>\s*<h2.*?</h2>',block,re.S)[0]+body+'</section>'
    text=replace_section(text,'local-focus',local)
    role=stage+' '+subject+' 수강·학습 점검'
    def intro(block):
        core=next((BY_ID[k][3] for k in p['topics'] if BY_ID[k][1]==subject),'현재 배우는 범위 확인')
        previous_links=re.findall(r'<a\b[^>]*>.*?</a>',block,re.S)
        body='<p class="gd-answer">'+e(p['name']+'의 '+stage+' '+subject+' 수업을 알아볼 때는 '+core+'부터 학생 답안으로 확인해 보세요. 연결 지점은 '+b['name']+'입니다.')+'</p><p>먼저 '+link('#subject-course','이 과목의 안내 학년·수강 조건')+'을 확인하세요. 아래 학습 점검은 상담 준비 자료이며, 지점에서 모든 과정을 운영한다는 뜻은 아닙니다.</p>'
        if previous_links:body+='<p>함께 점검할 내용: '+' · '.join(previous_links)+'</p>'
        return re.match(r'<section[^>]*>\s*<h2.*?</h2>',block,re.S)[0]+body+'</section>'
    text=replace_section(text,'learning',intro)
    return text,role

def directory_page(text,p,b,kind):
    if kind=='subject':return subject_page(text,p,b)
    text=replace_section(text,'courses',consolidate_courses)
    if kind=='grade':
        stage=STAGES[p['prefix']]
        def school(block):
            # The neighborhood-specific list in data-grade-area remains intact.
            return re.sub(r'<p data-stage-schools>.*?</p>','<p data-stage-schools>아래 참고 학교 목록과 학생이 받은 교과서·평가 안내를 함께 살펴보세요. 같은 학년이어도 실제 배운 범위와 필요한 도움은 다를 수 있습니다.</p>',block,flags=re.S)
        text=replace_section(text,'schools',school)
        available=[c['subject']+' '+grade_text(c['grades']) for c in p['courses'] if c['grades']]
        summary=('자료에 기재된 '+stage+' 안내 범위는 '+', '.join(available)+'입니다. ') if available else '개설 학년을 제공 자료에서 확인하지 못했습니다. 먼저 수강 가능 여부를 문의해 주세요. '
        role=stage+' 과목 선택'
        text=re.sub(r'(<section class="bd-hero gd-hero">.*?</h1>)<p>.*?</p>',lambda m:m[1]+'<p>'+e(p['name']+'에서 '+stage+' 수업을 알아볼 때 연결 지점은 '+b['name']+'입니다. '+summary)+'과목별 조건과 교육비를 비교한 뒤 영어·수학 상세 안내에서 필요한 학습 질문을 골라 보세요.</p>',text,count=1,flags=re.S)
    else:
        role='실제 지점 수강 안내'
        summary=' · '.join(c['subject']+' '+grade_text(c['grades']) for c in b['courses'] if c['grades'])
        def course(block):
            prep='<div class="sc-branch-prep"><h3>'+e(b['name'])+' 상담에서 결정할 항목</h3><p>'+e('자료상 안내 범위: '+summary+'.' if summary else '자료에 안내 학년이 없어 현재 수강 가능 여부를 먼저 문의해야 합니다.')+'</p><ul><li>학생 학년과 희망 과목에 적용되는 수업 시간·횟수</li><li>현재 교재·최근 답안에 맞는 시작 범위와 과제 부담</li><li>교습비 자료의 해당 항목과 교재·추가 프로그램 포함 여부</li></ul><p>'+link('#fees','교육비 조건 확인')+' · '+link('#location','실제 주소·등록 정보 확인')+' · '+link('#grade-guide','동네별 학년·과목 안내')+'</p></div>'
            return block.removesuffix('</section>')+prep+'</section>'
        text=replace_section(text,'courses',course)
    return text,role

def update_metadata(text,title=None,desc=None):
    if title:
        text=re.sub(r'<title>.*?</title>',lambda _:'<title>'+e(title)+'</title>',text,count=1,flags=re.S)
        for attr in ['property="og:title"','name="twitter:title"']:
            text=re.sub('(<meta '+attr+' content=")[^"]*("[^>]*>)',lambda m:m[1]+e(title)+m[2],text)
    if desc:
        assert len(desc)<=80 and desc.endswith('.'),desc
        for attr in ['name="description"','property="og:description"','name="twitter:description"']:
            text=re.sub('(<meta '+attr+' content=")[^"]*("[^>]*>)',lambda m:m[1]+e(desc)+m[2],text)
    def schema(m):
        obj=json.loads(m[2])
        for node in walk(obj):
            types=node.get('@type',[]);types=[types] if isinstance(types,str) else types
            if set(types)&{'WebPage','CollectionPage','Article','BlogPosting'}:
                node['dateModified']=DAY
                if desc:node['description']=desc
                if title:
                    for key in ['name','headline']:
                        if key in node:node[key]=title
                    if 'abstract' in node:node['abstract']=desc
        return m[1]+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+m[3]
    return LD.sub(schema,text)

def process(name):
    raw=(ROOT/name).read_bytes();text=raw.decode('utf8');path=route(name)
    if 'data-content-role=' in text:return None
    canonical=dom.fromstring(text).xpath('//link[@rel="canonical"]/@href')[0]
    if unquote(urlsplit(canonical).path)!=path:return None
    old=text;title=desc=None;p=None
    if path in SUBJECTS:
        p=dict(SUBJECTS[path]);text,role=directory_page(text,p,BRANCHES[p['branch']],'subject')
    elif path in GRADES:
        p=GRADES[path];text,role=directory_page(text,p,BRANCHES[p['branch']],'grade')
    elif path in BRANCHES:text,role=directory_page(text,None,BRANCHES[path],'branch')
    else:
        area=legacy.regional(name)
        if not area:return None
        cat=scope(name)[0]
        if cat not in ROLES:return None
        text,role,title,desc=legacy_page(text,name,AREAS[area],AREA_BRANCH[area])
    if 'data-content-role=' not in text:text=text.replace('<main', '<main data-content-role="'+e(role)+'"',1)
    if path in SUBJECTS or path in GRADES or path in BRANCHES:
        marker='<link rel="stylesheet" href="/assets/site-shell.css">'
        assert marker in text
        text=text.replace(marker,'<link rel="stylesheet" href="/'+STYLE+'">'+marker,1)
    text=update_metadata(text,title,desc)
    # No image tag, source choice, photo order, canonical or header is rewritten.
    for pattern in [r'<(?:img|source)\b[^>]*>',r'<link\b[^>]*rel="canonical"[^>]*>',r'<meta\b[^>]*(?:og:image|twitter:image)[^>]*>',r'<header\b.*?</header>']:
        assert re.findall(pattern,old,re.S)==re.findall(pattern,text,re.S),(name,'preserved',pattern)
    before=dom.fromstring(old);after=dom.fromstring(text)
    assert set(before.xpath('//@id'))<=set(after.xpath('//@id')),(name,'lost anchor')
    assert set(before.xpath('//a/@href'))<=set(after.xpath('//a/@href')),(name,'lost link')
    return {'file':name,'role':role,'text':text,'description':desc,'subjectTopics':p['topics'] if path in SUBJECTS else None,'beforeBytes':len(raw),'afterBytes':len(text.encode('utf8'))}

def atomic(path,data):
    pending=path.with_name(path.name+'.search-content.tmp');pending.write_bytes(data);pending.replace(path)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    manifest=load('release-public-manifest.json');metadata=load('seo-descriptions.json');names=[n for n in manifest['files'] if n.endswith('.html')]
    rows=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i,result in enumerate(ex.map(process,names),1):
            if result:
                n=result['file'];text=result.pop('text');data=text.encode('utf8')
                if args.apply:
                    atomic(ROOT/n,data)
                    manifest['files'][n]=hashlib.sha256(data).hexdigest()
                    manifest.setdefault('textSha256',{})[n]=hashlib.sha256(text.replace('\r\n','\n').encode('utf8')).hexdigest()
                if result['description']:
                    entry=metadata['pages'][route(n).rstrip('/')];entry['description']=result['description'];entry['sources']=list(dict.fromkeys(entry['sources']+[result['description']]))
                if result['subjectTopics']:SUBJECTS[route(n)]['topics']=result['subjectTopics']
                rows.append(result)
            if i%1000==0:print('processed',i,'changed',len(rows),flush=True)
    if args.apply and rows:
        modified={route(x['file']) for x in rows}
        xml=(ROOT/'sitemap.xml').read_text('utf8');dates=0
        def sm(m):
            nonlocal dates
            path=unquote(urlsplit(html.unescape(re.search(r'<loc>(.*?)</loc>',m[0])[1])).path)
            if path not in modified:return m[0]
            dates+=1;return re.sub(r'<lastmod>.*?</lastmod>','<lastmod>'+DAY+'</lastmod>',m[0])
        xml=re.sub(r'<url>.*?</url>',sm,xml,flags=re.S);assert dates==len(rows)
        atomic(ROOT/'sitemap.xml',xml.encode('utf8'))
        for name,obj in [('subject-directory-data.json',SUBJECT_DATA),('seo-descriptions.json',metadata),('search-content-data.json',{'date':DAY,'pages':[{k:v for k,v in x.items() if k in ['file','role']} for x in rows]})]:
            atomic(ROOT/name,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
        for n in ['sitemap.xml',STYLE]:
            data=(ROOT/n).read_bytes();manifest['files'][n]=hashlib.sha256(data).hexdigest();manifest.setdefault('textSha256',{})[n]=hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()
        manifest['createdAt']=datetime.now(timezone(timedelta(hours=9))).isoformat()
        atomic(ROOT/'release-public-manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    report={'mode':'apply' if args.apply else 'dry-run','auditedHtml':len(names),'changedHtml':len(rows),'roles':dict(collections.Counter(x['role'] for x in rows)),'pages':rows}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps({k:v for k,v in report.items() if k!='pages'},ensure_ascii=False))
if __name__=='__main__':main()

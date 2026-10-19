"""Reviewed, idempotent improvements to existing pages. No URL or image changes.

Uses the reconciled source datasets; it does not infer new course availability.
Run with --apply after reviewing the dry-run report. Public manifest refresh is
deliberately separate, so an unreviewed generator run cannot become a release.
"""
import argparse, copy, hashlib, html, json, re
from pathlib import Path
from urllib.parse import quote
from lxml import html as dom
from refresh_area_facts import grade_text

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-19'
HOST='https://xn--3e0bz50bxucwzc.com'
LD=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)([\s\S]*?)(</script>)')
e=lambda x:html.escape(str(x),quote=True)
def load(name):return json.loads((ROOT/name).read_text('utf-8'))
def absolute(path):return HOST+quote(path,safe='/#')
def filename(route):return route.lstrip('/')+'index.html'
def dumps(data):return json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')

BRANCHES={b['route']:b for b in load('branch-directory-data.json')['branches']}
GRADES={p['route']:p for p in load('grade-directory-data.json')['pages']}
SUBJECTS={p['route']:p for p in load('subject-directory-data.json')['pages']}
MAPS=load('branch-map-data.json')['areas']
ORG={}
for route,b in BRANCHES.items():
    text=(ROOT/filename(route)).read_text('utf-8')
    graph=json.loads(LD.search(text)[2])['@graph']
    ORG[route]=next(copy.deepcopy(n) for n in graph if n.get('@type')=='EducationalOrganization')

def stylesheet(text,path):
    if 'href="/'+path+'"' not in text:
        # Keep the shared site shell last in stylesheet order.
        at=text.index('<link rel="stylesheet" href="/assets/site-shell.css"')
        text=text[:at]+'<link rel="stylesheet" href="/'+path+'">\n'+text[at:]
    return text

def snapshot(courses,branch,target):
    known=[c for c in courses if c['grades']]
    unknown=[c['subject'] for c in courses if not c['grades']]
    rows=''.join('<div><dt>'+e(c['subject'])+'</dt><dd>'+e(grade_text(c['grades']))+'</dd></div>' for c in known)
    missing='<p class="cf-unconfirmed">'+e(' · '.join(unknown))+': 이 안내 범위의 학년 정보가 없어 개설 여부를 문의해야 합니다.</p>' if unknown else ''
    notes=list(dict.fromkeys(v for c in courses for v in c.get('notes',[])))
    conditions='<ul>'+''.join('<li>'+e(v)+'</li>' for v in notes)+'</ul>' if notes else ''
    return ('<div class="cf-snapshot" data-course-snapshot role="group" aria-label="자료에 기재된 과목별 안내 학년">'
      '<p class="cf-label">자료에 기재된 과목별 안내 학년</p><dl>'+rows+'</dl>'+missing+conditions+
      '<p class="cf-note">현재 모집·수업 시간·담당 교사는 별도 확인이 필요합니다. 학습 자료의 학년 구분은 개설 수업표가 아닙니다.</p>'
      '<a class="cf-details" href="#'+target+'">'+e(branch['name'])+' 수강 조건 자세히 확인</a></div>')

def improve_hero(text,kind,p,b):
    hero=re.search(r'<section class="bd-hero[^>]*>[\s\S]*?</section>',text)
    if not hero:raise ValueError('hero missing '+p['route'])
    block=hero[0]
    if 'data-course-snapshot' in block:return text
    courses=[p['course']] if kind=='subject' else p['courses']
    if kind=='grade':
        # Replace the dense inline grade enumeration with labelled rows.
        paras=list(re.finditer(r'<p(?: [^>]*)?>[\s\S]*?</p>',block))
        intro=next(x for x in paras if not re.search(r'\bclass=',x[0]))
        stage={'초':'초등학생','중':'중학생','고':'고등학생'}[p['prefix']]
        new='<p>'+e(p['name'])+'에서 '+stage+' 수업을 알아보는 가정을 위한 과목별 안내입니다. 연결 지점은 '+e(b['name'])+'이며, 실제 안내 학년과 별도 조건을 확인한 뒤 필요한 영어·수학 학습 질문을 골라 보세요.</p>'
        block=block[:intro.start()]+new+block[intro.end():]
    target='subject-course' if kind=='subject' else 'courses'
    pos=block.index('<div class="bd-actions">')
    block=block[:pos]+snapshot(courses,b,target)+block[pos:]
    text=text[:hero.start()]+block+text[hero.end():]
    return stylesheet(text,'assets/course-facts.css')

def normalize_refs(value,key=None):
    if isinstance(value,dict):return {k:normalize_refs(v,k) for k,v in value.items()}
    if isinstance(value,list):return [normalize_refs(x,key) for x in value]
    if key in ('@id','url','item','contentUrl','embedUrl') and isinstance(value,str) and value.startswith('/'):
        return HOST+quote(value,safe='/%#?=&:')
    return value

def identity(text,branch_route):
    nodes=[]
    for m in LD.finditer(text):
        value=json.loads(m[2]);nodes+=value.get('@graph',[value])
    existing=next((n for n in nodes if 'EducationalOrganization' in ([n.get('@type')] if isinstance(n.get('@type'),str) else n.get('@type',[]))),None)
    org=existing or ORG[branch_route]
    org_id=org['@id']
    added=False
    def update(m):
        nonlocal added
        data=normalize_refs(json.loads(m[2]));graph=data.get('@graph',[data])
        has_page=False
        for n in graph:
            types=[n.get('@type')] if isinstance(n.get('@type'),str) else n.get('@type',[])
            if 'WebPage' in types:
                has_page=True
                about=n.get('about',[])
                if not isinstance(about,list):about=[about]
                if not any(x.get('@id')==org_id for x in about if isinstance(x,dict)):about.append({'@id':org_id})
                n['about']=about;n['isPartOf']={'@id':HOST+'/#website'};n['dateModified']=DAY
                if n.get('url')==absolute(branch_route):n['mainEntity']={'@id':org_id}
            if 'EducationalOrganization' in types:n['url']=absolute(branch_route)
            if 'Article' in types:
                # The site publishes these guides; there is no evidence of a
                # specific branch having authored or reviewed each manuscript.
                n['author']={'@type':'Organization','name':'전국수업.com','url':HOST+'/'}
                n['dateModified']=DAY
        if not existing and has_page and not added:
            if '@graph' not in data:raise ValueError('expected graph')
            data['@graph'].append(copy.deepcopy(ORG[branch_route]));added=True
        return m[1]+dumps(data)+m[3]
    return LD.sub(update,text),org_id

def record(a):
    tasks=a['task'][1]
    rows=''.join('<label class="sr-field"><span>'+str(i+1)+'. '+e(v)+'</span><textarea name="record-'+str(i+1)+'" rows="3" maxlength="2000" data-record-label="'+e(v)+'" placeholder="직접 해 본 내용과 다음에 확인할 점을 적어 보세요."></textarea></label>' for i,v in enumerate(tasks))
    blank='/assets/education-records/'+a['slug']+'.txt'
    form=('<form class="sr-record" data-study-record data-record-title="'+e(a['title'])+'" data-record-file="'+e(a['slug'])+'_공부기록.txt" autocomplete="off">'
       '<p class="sr-help">아래 네 가지를 학생의 실제 과제와 일정에 맞춰 적어 보세요. 작성 내용은 전송되거나 자동 저장되지 않습니다. 페이지를 닫기 전에 TXT 파일로 저장할 수 있습니다.</p>'
       '<fieldset class="sr-fields"><legend>'+e(a['task'][0])+' 기록</legend>'+rows+'</fieldset>'
       '<a class="sr-blank" href="'+quote(blank,safe='/')+'" download="'+e(a['slug'])+'_빈기록.txt">빈 기록 양식 TXT 받기</a>'
       '<div class="sr-actions" hidden><button type="button" data-record-download>작성한 기록 TXT 저장</button><button type="reset">작성 칸 비우기</button></div>'
       '<p class="sr-status" role="status" aria-live="polite"></p></form>'
       '<p class="sr-help" data-record-source>기록한 뒤에는 계획한 일·실제로 해 본 일·다음에 확인할 점을 나누어 보세요. '
       '<a href="https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/metacognition-and-self-regulation" target="_blank" rel="noopener noreferrer">EEF의 자기조절학습 자료</a>는 실제 교과 과제에서 계획·점검·평가를 연결하는 접근을 설명합니다. 위 양식은 이를 적용해 보는 예시이며, 개별 학생의 학습 결과를 보장하지 않습니다.</p>')
    return form,blank,'\ufeff'+'\r\n'.join([a['title'],absolute(a['route']),'',a['task'][0],'']+[v+'\r\n기록: ____________________\r\n' for v in tasks])+'\r\n'

def education(text,a):
    text=stylesheet(text,'assets/study-record.css')
    if 'src="/assets/study-record.js"' not in text:text=text.replace('</body>','<script defer src="/assets/study-record.js"></script>\n</body>')
    form,blank,blanktext=record(a)
    pattern=r'(<section class="ei-section ei-task" id="practice"[^>]*><h2[^>]*>.*?</h2>)[\s\S]*?(</section>)'
    text,n=re.subn(pattern,lambda m:m[1]+form+m[2],text,count=1)
    if n!=1:raise ValueError('one task required '+a['route'])
    # Leave initial publication dates and all body images untouched.
    def meta(m):
        value=json.loads(m[2])
        for node in value.get('@graph',[value]):
            if node.get('@type') in ('WebPage','Article'):node['dateModified']=DAY
            if node.get('@type')=='Article':
                tree=dom.fromstring(text)
                node['citation']=list(dict.fromkeys(tree.xpath('//*[@id="references" or @data-record-source]//a/@href')))
        return m[1]+dumps(value)+m[3]
    text=LD.sub(meta,text)
    return text,blank,blanktext

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    changes={};records=[]
    def put(name,text):
        if not (ROOT/name).exists() or (ROOT/name).read_text('utf-8')!=text:changes[name]=text
    for name in load('crawl-readability-data.json')['pages']:
        route='/'+name.removesuffix('index.html');text=(ROOT/name).read_text('utf-8');kind='legacy';p=None
        if route in BRANCHES:kind='branch';p=BRANCHES[route];br=route
        elif route in GRADES:kind='grade';p=GRADES[route];br=p['branch']
        elif route in SUBJECTS:kind='subject';p=SUBJECTS[route];br=p['branch']
        else:
            areas=[part for part in name.split('/') if part in MAPS]
            if len(areas)!=1:raise ValueError('ambiguous source area '+name)
            br=MAPS[areas[0]]['branch']
        if kind!='legacy':text=improve_hero(text,kind,p,BRANCHES[br])
        text,org_id=identity(text,br);put(name,text)
        records.append({'file':name,'branch':br,'orgId':org_id,'snapshot':kind!='legacy'})
    for a in load('education-info-data.json')['articles']:
        name=filename(a['route']);text,blank,blanktext=education((ROOT/name).read_text('utf-8'),a)
        put(name,text);put(blank.lstrip('/'),blanktext)

    # A repeated FAQ introduction is replaced by a concrete next step. Exact
    # repeated panel paragraphs are removed, keeping their first occurrence.
    books=load('book-library-data.json')
    answers={
      '초등영어':'학년을 정해 두고 한 시리즈 전체를 고르기보다, 실제 권의 샘플에서 혼자 읽은 단어와 설명이 필요했던 문장을 표시해 보세요. 이 페이지의 교재별 학습 영역과 권·단계 조건을 그 기록과 비교하세요.',
      '초등수학':'학년은 학교 범위를 찾는 기준이고, 교재의 역할은 최근 풀이로 정합니다. 개념 설명·계산·문장제 중 혼자 하기 어려운 부분을 하나 고른 뒤 이 페이지의 교재의 학습 영역과 비교해 보세요.',
      '중등영어':'학년만으로 난도를 정하지 않습니다. 최근 교과서 문장 하나에서 모르는 단어, 구조를 설명하지 못한 부분, 정답 근거를 따로 표시해 이 페이지의 교재의 보강 영역과 비교하세요.',
      '중등수학':'학년은 현재 학교 단원을 확인하는 출발점입니다. 예제 풀이를 가린 뒤 첫 식을 세울 수 있는지 확인하고, 이 페이지의 교재의 개념·유형 역할과 권·단계 조건을 비교하세요.',
      '고등영어':'같은 학년이어도 해석과 선택지 판단의 어려움은 다를 수 있습니다. 최근 답안에서 근거를 못 찾은 문장을 남기고, 이 페이지의 교재별 학습 영역과 응시 학년도·판본 조건을 대조하세요.',
      '고등수학':'학년명만 보지 말고 학교에서 배우는 과목명과 현재 단원을 먼저 적으세요. 최근 풀이에서 첫 식을 못 쓴 문제와 계산 오류를 구분한 뒤 이 페이지의 교재의 목적·교육과정·판본을 확인합니다.'}
    book_changed=[]
    for p in books['pages']:
        name=filename(p['route']);text=(ROOT/name).read_text('utf-8');tree=dom.fromstring(text)
        counts={}
        for node in tree.xpath('//p'):
            t=' '.join(node.text_content().split())
            if len(t)>=80:counts[t]=counts.get(t,0)+1
        duplicate=next((v for v,c in counts.items() if c>1),None)
        if not duplicate:continue
        key=p['route'].strip('/').split('/')[-1]
        if key in answers:
            old=p['faqs'][0][1];new=answers[key]
            # Only change the FAQ answer, not its first explanatory occurrence.
            pos=text.index('<summary>'+e(p['faqs'][0][0])+'</summary>')
            left,right=text[:pos],text[pos:]
            right=right.replace('<p>'+e(old)+'</p>','<p>'+e(new)+'</p>',1);text=left+right
            p['faqs'][0][1]=new
            def faq(m):
                data=json.loads(m[2])
                for n in data.get('@graph',[data]):
                    if n.get('@type')=='FAQPage':n['mainEntity'][0]['acceptedAnswer']['text']=new
                return m[1]+dumps(data)+m[3]
            text=LD.sub(faq,text)
        else:
            token='<p>'+e(duplicate)+'</p>'
            pos=text.rfind(token)
            if pos<0:raise ValueError('repeated panel not found '+name)
            text=text[:pos]+text[pos+len(token):]
        p['dateModified']=DAY
        def book_dates(m):
            data=json.loads(m[2])
            for n in data.get('@graph',[data]):
                types=[n.get('@type')] if isinstance(n.get('@type'),str) else n.get('@type',[])
                if any(t in ('WebPage','Article') for t in types):n['dateModified']=DAY
            return m[1]+dumps(data)+m[3]
        text=LD.sub(book_dates,text)
        put(name,text);book_changed.append(name)
    if book_changed:put('book-library-data.json',json.dumps(books,ensure_ascii=False,indent=2)+'\n')
    if not book_changed and (ROOT/'evidence-content-data.json').exists():book_changed=load('evidence-content-data.json')['consolidatedBooks']
    out={'updated':DAY,'pages':records,'articles':[{'file':filename(a['route']),'blank':'assets/education-records/'+a['slug']+'.txt','tasks':a['task'][1]} for a in load('education-info-data.json')['articles']], 'consolidatedBooks':book_changed}
    put('evidence-content-data.json',json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    if args.apply:
        for name,text in changes.items():
            target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('w',encoding='utf-8',newline='') as f:f.write(text)
    print(json.dumps({'apply':args.apply,'localPages':len(records),'earlyCourseSummaries':sum(p['snapshot'] for p in records),'articleRecords':len(out['articles']),'consolidatedBooks':book_changed,'changedFiles':len(changes)},ensure_ascii=False))

if __name__=='__main__':main()

"""Adapt the owner's coaching material for the existing home page only."""
from pathlib import Path
from html import escape
from urllib.parse import quote
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://xn--3e0bz50bxucwzc.com/'
DESCRIPTION = '전국수업의 개별맞춤 수업과 4C 학습코칭, 플래너·오답 관리를 살펴보고 지역별 지점과 학습 자료를 확인하세요.'

COMPARISON = [
    ('수업의 출발점', '학년·학교 진도·시험 범위를 중심으로 내용을 정합니다.', '학교 진도와 함께 학생의 현재 이해도와 부족한 개념을 확인합니다.'),
    ('설명과 과제', '함께 듣는 설명과 공통 과제를 중심으로 배웁니다.', '필요한 설명을 듣고, 이해 수준에 맞춰 서로 다른 과제를 수행합니다.'),
    ('진도와 속도', '반의 계획에 맞춰 같은 순서와 속도로 이동합니다.', '막힌 단원을 보완하거나 준비된 내용은 확장하며 진도를 조정합니다.'),
    ('학년의 의미', '같은 학년의 교육과정을 묶어 수업하기 쉽습니다.', '학습 출발점은 실력으로 정하되 학교 학년과 시험 일정도 고려합니다.'),
    ('활용하기 좋은 점', '공통 내용을 체계적으로 설명하고 시험 범위를 함께 정리하기 좋습니다.', '학생마다 다른 빈틈과 질문에 맞춰 학습 순서와 분량을 조정하기 좋습니다.'),
    ('선택 전 확인할 점', '설명 속도와 과제 난도가 아이에게 맞는지 살펴보세요.', '진단 후 과제 조정과 오답 피드백이 실제로 이어지는지 살펴보세요.'),
    ('학생에게 물어볼 질문', '“설명을 듣고 혼자 풀 때도 같은 방법을 적용할 수 있니?”', '“어디서 막혔고, 다음에는 무엇을 다시 확인하면 될까?”'),
    ('선생님의 역할', '내용을 설명하고 공통 진도와 과제 수행을 확인합니다.', '이해 수준을 살피고, 설명·질문·피드백으로 다음 과제를 설계합니다.'),
    ('이해도 확인', '시험·숙제 점검 등을 통해 배운 내용을 확인합니다.', '단원별 수행과 풀이 이유, 오답 재확인으로 계획을 조정합니다.'),
    ('수업 선택의 기준', '공통 진도를 따라가며 설명을 활용할 수 있는지 확인합니다.', '기초 보완·학습 습관·개인별 속도 중 어떤 관리가 필요한지 확인합니다.'),
]
STEPS = [
    ('Check', '맞춤진단', '점수와 공부 행동을 함께 보기', '최근 시험지, 풀이 과정, 숙제 수행을 살펴봅니다. 개념이 부족한지, 조건을 놓치는지, 시작과 복습이 어려운지 구분합니다.', '남길 기록: 지금 막히는 단원과 원인'),
    ('Curriculum', '맞춤처방', '이번에 할 일을 구체적으로 정하기', '보완할 개념, 사용할 자료, 해낼 수 있는 분량을 정합니다. 학교 일정과 시험 범위를 대조해 먼저 끝낼 과제를 나눕니다.', '남길 기록: 과목·단원·분량·완료 기준'),
    ('Consulting', '맞춤상담', '학생과 목표·장애물을 함께 정리하기', '학생이 어려웠던 이유를 말하고 계획의 우선순위를 확인합니다. 학부모 상담에서는 완료한 부분과 남은 과제, 필요한 도움을 정리합니다.', '남길 기록: 학생의 질문과 상담에서 정한 방향'),
    ('Coaching', '맞춤지도', '실행과 오답을 보고 다음 계획 바꾸기', '정답 여부와 함께 풀이 이유를 확인합니다. 다시 풀어도 막히는 내용과 밀린 과제를 살펴 다음 설명·분량·복습 시점을 조정합니다.', '남길 기록: 재확인 결과와 다음 학습 계획'),
]

def link(route, label, primary=False):
    return f'<a class="hc-link{" hc-primary" if primary else ""}" href="{quote(route, safe="/#")}">{escape(label)}<span aria-hidden="true">→</span></a>'

def block(key, content):
    return f'<!-- home-coaching:{key}:start -->{content}<!-- home-coaching:{key}:end -->'

def remove(text, key):
    return re.sub(r'<!-- home-coaching:'+key+r':start -->[\s\S]*?<!-- home-coaching:'+key+r':end -->', '', text)

def intro():
    nav = '<nav class="hc-jump" aria-label="메인 학습코칭 바로가기">'+''.join(link(route,label) for route,label in [('#home-coaching','수업의 특징'),('#lesson-comparison','수업 방식 비교'),('#coaching-process','4C 관리 과정'),('#home-library','학습 자료 찾기')])+'</nav>'
    content = '''<section class="hc-section hc-intro" id="home-coaching" aria-labelledby="home-coaching-title">
<div class="hc-heading"><p class="hc-kicker">와와 학습코칭의 수업 방향</p><h2 id="home-coaching-title">같은 학년이어도,<br>필요한 공부는 다릅니다.</h2><p>개념은 알지만 문제에서 막히는 아이, 복습이 밀리는 아이, 더 깊이 배우고 싶은 아이.<br class="hc-desktop-break"> 지금 필요한 설명과 과제를 찾고, 혼자 해낼 수 있는 다음 단계를 함께 정리합니다.</p></div>
<div class="hc-intro-grid"><div class="hc-photo-panel"><figure><img src="/assets/home-coaching/wawa-classroom.png" width="626" height="417" loading="lazy" decoding="async" alt="학생의 교재를 함께 살펴보는 와와 학습코칭 선생님"><figcaption>와와 학습코칭 수업 소개 사진</figcaption></figure><div class="hc-photo-copy"><h3>질문하고 설명해 보는 수업</h3><p>둥지학습은 선생님 가까이에서 과제 수행을 살피고 질문을 주고받는 수업 환경입니다. 답을 맞혔는지와 함께 “왜 이렇게 풀었는지”를 확인하는 데 초점을 둡니다.</p><div class="hc-actions">'''+link('/학습시스템/와와학습코칭/#official-video','공식 소개 영상 보기',True)+'''</div></div></div>
<div class="hc-feature-grid">
<article class="hc-feature"><span class="hc-number">01</span><h3>학교 수업과 연결한 내신 준비</h3><p>교과서·수업 자료·시험 범위를 함께 살펴 공부 순서를 정합니다. 서술형은 정답과 함께 필요한 근거와 풀이 과정을 확인합니다.</p></article>
<article class="hc-feature"><span class="hc-number">02</span><h3>할 일을 작게 나누는 플래너</h3><p>“수학 공부” 대신 단원·분량·완료 기준을 정합니다. 못 끝낸 과제는 이유를 살피고, 다음 계획에서 분량과 방법을 조정합니다.</p></article>
<article class="hc-feature"><span class="hc-number">03</span><h3>현재 이해도에 맞추는 진도</h3><p>학년만으로 출발점을 정하지 않습니다. 이전 개념의 빈틈을 보완하고, 설명할 수 있는 내용은 연결 문제로 확장하는 방향입니다.</p></article>
<article class="hc-feature"><span class="hc-number">04</span><h3>과목마다 다른 복습과 질문</h3><p>영어는 문장 이해, 수학은 풀이의 이유, 국어는 지문의 근거를 살펴봅니다. 오답노트·백지노트 등은 필요한 공부에 맞춰 활용합니다.</p></article>
</div></div><div class="hc-bottom"><p>수업 환경·개설 과목·등록 학년·관리 방식은 지점 안내와 상담에서 확인하세요.</p>'''+link('/학습시스템/개별맞춤관리/','개별맞춤 관리 자세히 보기')+'''</div></section>'''
    return block('intro', nav+content)

def comparison():
    rows=''.join(f'<div class="hc-compare-row" data-comparison="{i}"><h3>{escape(label)}</h3><div class="hc-lecture"><span class="hc-cell-label">강의 중심 수업</span><p>{escape(lecture)}</p></div><div class="hc-individual"><span class="hc-cell-label">개별맞춤형 수업</span><p>{escape(individual)}</p></div></div>' for i,(label,lecture,individual) in enumerate(COMPARISON,1))
    return block('comparison','''<section class="hc-section hc-comparison" id="lesson-comparison" aria-labelledby="lesson-comparison-title"><div class="hc-heading"><p class="hc-kicker">우리 아이에게 맞는 수업 고르기</p><h2 id="lesson-comparison-title">강의 중심 수업과<br>개별맞춤형 무학년 수업</h2><p>함께 듣는 설명이 잘 맞는 학생도, 개념과 속도를 따로 조정해야 하는 학생도 있습니다. 수업 이름보다 아이에게 필요한 설명·과제·피드백이 어떻게 이어지는지 비교해 보세요.</p></div>
<div class="hc-compare-head" aria-hidden="true"><span>비교 기준</span><strong>강의 중심 수업</strong><strong>개별맞춤형 무학년 수업</strong></div><div class="hc-compare-body">'''+rows+'''</div>
<aside class="hc-note"><h3>‘무학년’은 학교 학년을 무시한다는 뜻일까요?</h3><p>학습의 출발점을 실제 이해 수준으로 정한다는 의미입니다. 학교 진도와 시험 범위도 함께 고려합니다. 서로 다른 문제집을 풀게 하는 것만으로 끝나지 않으며, 진단·과제 설계·질문·재확인이 연결되어야 합니다.</p><p>위 비교는 수업 선택을 위한 일반적인 운영 방향입니다. 실제 수업은 두 방식을 함께 활용할 수 있고, 효과는 학생과 운영 조건에 따라 달라집니다.</p></aside>
<div class="hc-actions">'''+link('/학습가이드/학원수업비교/','학원 수업 비교 체크리스트')+link('/지점안내/','우리 동네 수업 조건 확인',True)+'''</div></section>''')

def process():
    steps=''.join(f'<li class="hc-step" data-coaching-step="{english}"><div class="hc-step-top"><span class="hc-number">0{i}</span><span lang="en">{english}</span></div><h3>{name}</h3><strong>{heading}</strong><p>{copy}</p><small>{record}</small></li>' for i,(english,name,heading,copy,record) in enumerate(STEPS,1))
    return block('process','''<section class="hc-section hc-process" id="coaching-process" aria-labelledby="coaching-process-title"><div class="hc-heading"><p class="hc-kicker">진단에서 실행으로 이어지는 4C</p><h2 id="coaching-process-title">알아본 뒤, 계획하고,<br>실행 결과를 다시 봅니다.</h2><p>첫 진단은 출발점입니다. 실제 수업과 숙제에서 드러나는 이해도와 공부 행동을 살펴 학생의 다음 계획을 조정하는 것이 학습코칭의 관리 방향입니다.</p></div><ol class="hc-steps">'''+steps+'''</ol><div class="hc-bottom"><p>진단 도구·상담 주기·기록 공유 방식은 지점마다 확인이 필요합니다.</p>'''+link('/학습시스템/','학습 시스템 전체 살펴보기')+'''</div></section>''')

def planner():
    return block('planner','''<section class="hc-section hc-planner" id="learning-record" aria-labelledby="learning-record-title"><div class="hc-heading"><p class="hc-kicker">학생에게는 다음 할 일, 학부모에게는 확인할 과정</p><h2 id="learning-record-title">“공부했니?” 다음에<br>물어볼 수 있는 기록</h2><p>시간과 페이지 수만 적기보다 무엇을 설명할 수 있게 됐는지, 어디에서 막혔는지 남겨 보세요. 기록은 아이를 비교하는 점수가 아니라 다음 과제를 정하는 자료가 됩니다.</p></div>
<div class="hc-record-grid"><article class="hc-record"><span class="hc-example">학습 기록 예시 · 수학</span><h3>맞힌 문제도 풀이 이유까지</h3><dl><div><dt>오늘 과제</dt><dd>분수 덧셈 3문제 풀고 풀이 설명하기</dd></div><div><dt>완료 기준</dt><dd>통분이 필요한 이유를 말할 수 있기</dd></div><div><dt>막힌 부분</dt><dd>분모가 다를 때 더하는 순서를 혼동함</dd></div><div><dt>다음 과제</dt><dd>그림으로 크기를 비교한 뒤 같은 문제 다시 풀기</dd></div></dl>'''+link('/학습가이드/수학오답관리/','수학 오답 기록 방법')+'''</article>
<article class="hc-record"><span class="hc-example">학습 기록 예시 · 영어</span><h3>해석한 문장의 근거 찾기</h3><dl><div><dt>오늘 과제</dt><dd>짧은 지문에서 주어·동사와 근거 문장 표시하기</dd></div><div><dt>완료 기준</dt><dd>답을 고른 이유를 본문에서 찾을 수 있기</dd></div><div><dt>막힌 부분</dt><dd>대명사가 가리키는 대상을 놓침</dd></div><div><dt>다음 과제</dt><dd>앞 문장과 연결해 대명사의 대상을 다시 표시하기</dd></div></dl>'''+link('/학습가이드/영어문장구조읽기/','영어 문장 이해 방법')+'''</article>
<article class="hc-record"><span class="hc-example">가정에서 함께 확인할 질문</span><h3>결과와 다음 계획을 연결하기</h3><ul><li>오늘 혼자 설명할 수 있게 된 것은 무엇인가요?</li><li>못 끝낸 과제는 분량 때문인가요, 이해가 어려워서인가요?</li><li>다음 수업에서 선생님께 물어볼 질문은 무엇인가요?</li><li>지난번 오답을 다시 풀었을 때 달라진 부분은 무엇인가요?</li></ul><p class="hc-small">위 기록은 작성 방법을 보여주는 예시입니다. 실제 학생의 성적·후기나 모든 지점의 공통 양식을 뜻하지 않습니다.</p>'''+link('/학습가이드/학습플래너작성법/','플래너 작성 방법')+'''</article></div>
<div class="hc-actions">'''+link('/학습가이드/학부모상담체크리스트/','학부모 상담 준비하기')+link('/학습시스템/AI학습/','AI학습의 구성과 대상 확인')+'''</div></section>''')

def enhance(root=ROOT):
    p=root/'index.html'; text=p.read_text(encoding='utf-8')
    # Refresh owned blocks in place; keep all discovery/library and branch content intact.
    for key,fn in [('intro',intro),('comparison',comparison),('process',process),('planner',planner)]:
        pattern=r'<!-- home-coaching:'+key+r':start -->[\s\S]*?<!-- home-coaching:'+key+r':end -->'
        if re.search(pattern,text):
            text=re.sub(pattern,lambda _:fn(),text)
        elif key=='intro':
            text=re.sub(r'(<section class="hero">[\s\S]*?</section>)',lambda m:m[1]+fn(),text,count=1)
        elif key=='comparison':
            # The discovery block contains search and guides; insert directly after search.
            boundary='<section class="hd-section hd-guides"'
            if boundary not in text: raise RuntimeError('Home discovery guide boundary missing')
            text=text.replace(boundary,fn()+boundary,1)
        elif key=='process':
            pattern=r'<section class="section split">\s*<div class="section-title">\s*<p class="eyebrow">Why Coaching</p>[\s\S]*?</section>'
            text,n=re.subn(pattern,lambda _:fn(),text,count=1)
            if n!=1: raise RuntimeError('Original coaching needs section not found')
        else:
            text,n=re.subn(r'<section class="dark-band">[\s\S]*?</section>',lambda _:fn(),text,count=1)
            if n!=1: raise RuntimeError('Original coaching process section not found')
    # Keep the hero headline/image/actions; make the benefit clearer in its existing lead.
    lead='영어·수학·국어, 지금 필요한 개념과 공부 습관부터 살펴봅니다. 학생의 이해 수준에 맞춘 수업과 플래너·오답 관리 방향을 알아보고, 우리 동네 지점의 수업 조건을 확인하세요.'
    text=re.sub(r'(<section class="hero">[\s\S]*?<p class="lead">)[\s\S]*?(</p>)',lambda m:m[1]+lead+m[2],text,count=1)
    text=remove(text,'styles')
    text=text.replace('<link rel="stylesheet" href="/assets/site-shell.css">',block('styles','<link rel="stylesheet" href="/assets/home-coaching.css">')+'<link rel="stylesheet" href="/assets/site-shell.css">',1)
    question='초등·중등·고등 학생 모두 상담이 가능한가요?'
    answer='학교 단계에 따라 학습 습관·기초 개념, 학교 내신, 과목별 약점과 시험 계획을 상담할 수 있습니다. 실제 개설 과목과 등록 가능한 학년은 해당 지점 안내와 상담에서 확인하세요.'
    text=re.sub(r'(<summary>'+re.escape(question)+r'</summary>\s*<p>)[\s\S]*?(</p>)',lambda m:m[1]+answer+m[2],text,count=1)
    text=remove(text,'faq')
    faq_extra=block('faq','''<details><summary>무학년 수업이면 학교 진도를 따르지 않나요?</summary><p>무학년은 학생의 현재 이해 수준을 기준으로 학습 출발점을 정한다는 뜻입니다. 필요한 이전 개념을 보완하면서 학교 진도와 시험 범위도 함께 고려합니다. 실제 반 편성과 등록 학년은 지점마다 확인하세요.</p></details><details><summary>학부모는 어떤 학습 기록을 확인하면 좋나요?</summary><p>완료한 과제, 스스로 설명할 수 있는 내용, 남아 있는 오답, 다음 복습 계획을 함께 확인하면 좋습니다. 상담과 기록 공유의 방식·주기는 해당 지점에서 확인하세요.</p></details>''')
    match=re.search(r'(<div class="faq" id="faq">)([\s\S]*?)(</div>)',text)
    if not match: raise RuntimeError('Existing FAQ missing')
    text=text[:match.start()]+match[1]+match[2]+faq_extra+match[3]+text[match.end():]
    faq_html=re.search(r'<div class="faq" id="faq">([\s\S]*?)</div>',text)[1]
    questions=re.findall(r'<summary>(.*?)</summary>\s*<p>(.*?)</p>',faq_html,re.S)
    def schema_update(m):
        data=json.loads(m[2])
        if '@graph' not in data: return m[0]
        for n in data['@graph']:
            if n.get('@type') in ['WebPage','Article']:
                n['description']=DESCRIPTION;n['dateModified']='2026-10-02'
            if n.get('@type')=='WebPage':
                owned={'#coaching-process','#lesson-comparison','#learning-record'}
                n['hasPart']=[item for item in n.get('hasPart',[]) if '#'+item.get('@id','').split('#')[-1] not in owned]+[{'@id':BASE+'#coaching-process'},{'@id':BASE+'#lesson-comparison'},{'@id':BASE+'#learning-record'}]
            if n.get('@type')=='ItemList' and n.get('@id')==BASE+'#coaching-process':
                n['name']='4C 학습코칭 관리 과정'
                n['itemListElement']=[{'@type':'ListItem','position':i,'name':name+' · '+english} for i,(english,name,*_) in enumerate(STEPS,1)]
            if n.get('@type')=='FAQPage':
                n['mainEntity']=[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in questions]
        return m[1]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+m[3]
    text=re.sub(r'(<script type="application/ld\+json">)([\s\S]*?)(</script>)',schema_update,text)
    text=re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*(">)',lambda m:m[1]+DESCRIPTION+m[2],text)
    p.write_text(text,encoding='utf-8',newline='\n')
    config_path=root/'seo-descriptions.json';config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    entry=config['pages']['/'];entry['sources']=list(dict.fromkeys(entry['sources']+[entry['description'],DESCRIPTION]));entry['description']=DESCRIPTION
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    data={'version':1,'date':'2026-10-02','description':DESCRIPTION,'comparison':COMPARISON,'steps':STEPS,'faq':questions,'officialSources':['https://www.wawacenter.com/','https://www.wawacenter.com/brand/wawacenter','https://www.wawacenter.com/intro/coachingSystem','https://www.wawacenter.com/intro/AISystem'],'photo':{'source':'https://www.wawacenter.com/assets/img/brand_info_coach.png','file':'assets/home-coaching/wawa-classroom.png','width':626,'height':417,'role':'brand introduction; not a specific branch photo'},'preserve':['shared header','hero image and consultation','branch search','learning guides','home library','education articles','tuition','branch and neighborhood pages']}
    (root/'home-coaching-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'homeUpdated':True,'comparisonRows':len(COMPARISON),'coachingSteps':len(STEPS),'faq':len(questions),'descriptionChars':len(DESCRIPTION)},ensure_ascii=False))

if __name__=='__main__': enhance()

"""Original practical articles, with verified primary references kept separate."""
GROUPS=[('grade','학년·시험','학년이 바뀌거나 평가를 준비할 때'),('math','수학','기초·풀이·오답을 연결할 때'),('english','영어','어휘·문장·독해·듣기를 구분할 때'),('literacy','국어·사회·과학','읽은 근거를 설명과 답안으로 옮길 때'),('habits','계획·습관','계획을 실제 공부로 이어갈 때'),('parents','학부모·상담','학생과 함께 수업과 다음 목표를 정할 때')]
SOURCES={
 'study':('IES','학습 시간·간격 복습·인출 연습 가이드','2007','https://ies.ed.gov/ncee/wwc/PracticeGuide/1','간격을 둔 학습, 답을 꺼내 보는 연습과 설명 질문을 다룹니다.'),
 'meta':('EEF','메타인지와 자기조절학습','2025','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/metacognition','과제 안에서 계획·실행 점검·평가를 가르치는 방법을 다룹니다.'),
 'parents':('EEF','가정과 함께 지원하는 학생 학습','2018','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/supporting-parents','학교와 가정이 학생의 학습을 지원하는 관계를 다룹니다.'),
 'math':('IES','수학 문제 해결 지도','2012, 개정 2018','https://ies.ed.gov/ncee/wwc/PracticeGuide/16','문제 해결 점검, 시각적 표현과 수학적 설명을 다룹니다.'),
 'foundation':('IES','초등 수학 학습 지원','2021','https://ies.ed.gov/ncee/wwc/practiceguide/26','수학 언어, 수직선·그림 표현과 문장제 지도를 다룹니다.'),
 'algebra':('IES','중·고등 대수 학습 지도','2015, 개정 2019','https://ies.ed.gov/ncee/wwc/practiceguide/20','풀이 분석, 식의 구조와 전략 선택을 다룹니다.'),
 'vocabulary':('IES','영어 학습자의 어휘·읽기·쓰기 지도','2014','https://ies.ed.gov/ncee/wwc/PracticeGuide/19','여러 활동에 걸친 어휘 학습과 읽기·쓰기 연결을 다룹니다.'),
 'reading':('IES','청소년 읽기 지도','2008','https://ies.ed.gov/ncee/wwc/practiceguide/8','어휘, 읽기 전략과 글의 의미에 관한 대화를 다룹니다.'),
 'literacy':('EEF','중등 읽기·쓰기·어휘 지도','2018','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/literacy-ks3-ks4','과목별 언어와 읽기·쓰기·말하기의 연결을 다룹니다.'),
 'writing':('IES','중등 글쓰기 지도','2016, 개정 2019','https://ies.ed.gov/ncee/wwc/PracticeGuide/22','글쓰기 전략의 시범·연습·성찰과 읽기 연결을 다룹니다.'),
 'listening':('British Council','수준별 영어 듣기 연습','접속 확인 2026-10-01','https://learnenglish.britishcouncil.org/free-resources/listening','수준과 상황에 따른 음성 자료와 연습 활동을 제공합니다.'),
 'science':('EEF','중등 과학 학습 지도','2018','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/science-ks3-ks4','과학 개념과 언어, 사고 과정·실험 활동의 지도를 다룹니다.'),
 'feedback':('EEF','학생 학습을 돕는 피드백','2021','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/feedback','학생의 학습 목표와 다음 학습에 연결되는 피드백을 다룹니다.'),
 'data':('IES','학습 자료를 활용한 목표와 수업 점검','2009','https://ies.ed.gov/ncee/wwc/practiceguide/12','학생이 자신의 자료를 살펴보고 학습 목표를 정하는 방법을 다룹니다.'),
 'fees':('NEIS','학원·교습소 정보 서비스','현재 정보 조회','https://hakwon.neis.go.kr/nxui/index.html','등록 학원 정보와 교습비를 확인할 때 이용하는 공식 조회 서비스입니다.'),
 'digital':('EEF','학습 목표에 맞는 디지털 도구 활용','2019','https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/digital','디지털 도구를 설명·연습·평가·피드백의 목표와 연결하는 교육 자료입니다.'),
 'media':('UNESCO','미디어·정보 리터러시','접속 확인 2026-10-02','https://www.unesco.org/en/media-information-literacy','정보를 찾고 비판적으로 평가하며 책임 있게 활용하는 역량을 안내합니다.'),
 'earlyreading':('IES','읽기 정확도·유창성·이해의 기초 지도','2016, 개정 2019','https://ies.ed.gov/ncee/wwc/PracticeGuide/21','영어권 초기 읽기 지도 자료입니다. 읽기 정확도와 의미 확인을 연결하는 활동 원리를 참고합니다.'),
 'grammar':('British Council','수준별 영어 문법 설명과 연습','자료별 내용 확인','https://learnenglish.britishcouncil.org/free-resources/grammar','문법 설명·예문·이해 확인 연습을 연결하는 공식 학습 자료입니다.'),
 'speaking':('British Council','상황별 영어 말하기 연습','자료별 내용 확인','https://learnenglish.britishcouncil.org/free-resources/speaking','대화 상황의 표현을 듣고 직접 사용하는 공식 연습 자료입니다. 자료의 상황과 수준은 학생에게 맞게 고릅니다.'),
}
PAGES=[]
def add(slug,group,title,description,audience,answer,checks,steps,example,record,avoid,next_check,faq,sources,related,tags='',needs=None,levels=None,parent_help=None):
 assert group in {g[0] for g in GROUPS} and len(description)<=80 and description.endswith('.'),slug
 assert len(steps)>=4 and len(checks)>=2 and len(record)>=4 and len(faq)==3,slug
 assert all(s in SOURCES for s in sources) and len(sources)>=1,slug
 PAGES.append(dict(slug=slug,route='/학습가이드/'+slug+'/',group=group,title=title,description=description,audience=audience,answer=answer,checks=checks,steps=steps,example=example,record=record,avoid=avoid,nextCheck=next_check,faq=faq,sources=sources,related=related,tags=tags,needs=needs,levels=levels,parentHelp=parent_help))
for module in ['learning_grade_guides','learning_math_guides','learning_english_guides','learning_literacy_guides','learning_habit_guides','learning_parent_guides']:
 __import__(module).extend(add)
__import__('learning_additional_guides').extend(add)
__import__('learning_expansion_guides').extend(add)
assert len(PAGES)==77 and len({p['slug'] for p in PAGES})==77
assert all(k in {p['slug'] for p in PAGES} for p in PAGES for k in p['related'])

LEVELS=[('elementary','초등학생'),('middle','중학생'),('high','고등학생'),('parent','학부모')]
# Reading relevance, not a statement of branch availability or a student's ability.
for p in PAGES:
 if p.get('levels'):continue
 if p['group']=='parents':
  levels=['elementary','middle','high','parent']
 elif p['slug'] in ['초등학생공부습관']:
  levels=['elementary','parent']
 elif p['slug']=='초등중등학년전환':
  levels=['elementary','middle','parent']
 elif p['slug']=='중학생내신공부법':
  levels=['middle','parent']
 elif p['slug'] in ['고등학생과목별공부법','고등수학모의고사분석']:
  levels=['high','parent']
 elif p['slug']=='중등고등학년전환':
  levels=['middle','high','parent']
 elif p['slug'] in ['수학오답관리','수학기초점검','계산실수줄이기','수학문장제읽기','수학선행학습점검','영어단어복습법','독서내용요약'] or p['group']=='habits' or p['slug']=='방학복습계획':
  levels=['elementary','middle','high']
 else:
  levels=['middle','high']
 if '보호자' in p['audience'] and 'parent' not in levels:levels.append('parent')
 p['levels']=levels

NEEDS=[('exam','시험 준비'),('basics','기초 이해'),('review','오답·복습'),('expression','과제·표현'),('routine','계획·습관'),('consultation','수업 선택·상담')]
for p in PAGES:
 if p.get('needs'):continue
 group=p['group'];slug=p['slug']
 p['needs']={'grade':['exam','routine'],'math':['basics','review'],'english':['basics','review'],'literacy':['expression','review'],'habits':['routine','review'],'parents':['consultation','routine']}[group].copy()
 if slug in ['초등학생공부습관','방학복습계획','초등중등학년전환','중등고등학년전환']:p['needs']=['basics','routine']
 if slug in ['수행평가준비','국어서술형답안','영어서술형쓰기','영어쓰기수정기록']:p['needs']=['expression','exam']
 if slug in ['수학서술형풀이','고등수학모의고사분석','영어내신준비']:p['needs']=['exam','review']
 if slug in ['학습변화기록','교재선택복습','온라인학습점검']:p['needs']=['consultation','review']
assert all(p['needs'] and set(p['needs'])<={key for key,_ in NEEDS} for p in PAGES)

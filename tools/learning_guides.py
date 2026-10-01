"""Original practical articles, with verified primary references kept separate."""
GROUPS=[('grade','학년·시험','학년이 바뀌거나 평가를 준비할 때'),('math','수학','기초·풀이·오답을 연결할 때'),('english','영어','어휘·문장·독해·듣기를 구분할 때'),('literacy','국어·과학','읽은 근거를 설명과 답안으로 옮길 때'),('habits','계획·습관','계획을 실제 공부로 이어갈 때'),('parents','학부모·상담','학생과 함께 수업과 다음 목표를 정할 때')]
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
}
PAGES=[]
def add(slug,group,title,description,audience,answer,checks,steps,example,record,avoid,next_check,faq,sources,related,tags=''):
 assert group in {g[0] for g in GROUPS} and len(description)<=80 and description.endswith('.'),slug
 assert len(steps)>=4 and len(checks)>=2 and len(record)>=4 and len(faq)==3,slug
 assert all(s in SOURCES for s in sources) and len(sources)>=1,slug
 PAGES.append(dict(slug=slug,route='/학습가이드/'+slug+'/',group=group,title=title,description=description,audience=audience,answer=answer,checks=checks,steps=steps,example=example,record=record,avoid=avoid,nextCheck=next_check,faq=faq,sources=sources,related=related,tags=tags))
for module in ['learning_grade_guides','learning_math_guides','learning_english_guides','learning_literacy_guides','learning_habit_guides','learning_parent_guides']:
 __import__(module).extend(add)
assert len(PAGES)==40 and len({p['slug'] for p in PAGES})==40
assert all(k in {p['slug'] for p in PAGES} for p in PAGES for k in p['related'])

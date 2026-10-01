"""Add reviewed, page-specific resource links without rewriting existing content."""
import argparse, hashlib, html as escape, json, re, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
STAGES={'초':'초등','중':'중등','고':'고등'}
MAIN={'초':'초등학생공부습관','중':'중학생내신공부법','고':'고등학생과목별공부법'}
NOTICE='학생의 공부와 교재 선택을 돕는 참고 자료입니다. 지점의 개설 과목·학년과 실제 사용 교재는 별도로 확인해 주세요.'
LABELS={
 '초등학생공부습관':('초등학생 공부 습관','시작 약속과 혼자 해낼 범위 정하기'),
 '중학생내신공부법':('중학생 내신 공부 방법','학교 범위와 과목별 과제 나누기'),
 '고등학생과목별공부법':('고등학생 과목별 공부 방법','과목별 막힌 지점과 공부 순서 정하기'),
 '수학기초점검':('수학 기초 점검','개념 설명과 기본 문제 적용 나누어 보기'),
 '수학오답관리':('수학 오답 복습','틀린 원인과 다시 풀 결과 남기기'),
 '계산실수줄이기':('계산 실수 줄이기','틀린 계산 줄과 확인 방법 찾기'),
 '수학문장제읽기':('수학 문장제 읽기','조건의 관계를 그림과 식으로 옮기기'),
 '수학서술형풀이':('수학 서술형 풀이','풀이의 이유를 말과 글로 설명하기'),
 '고등수학모의고사분석':('고등 수학 모의고사 분석','시간·개념·조건 오류를 구분하기'),
 '영어단어복습법':('영어 단어 복습','뜻을 기억한 뒤 문장에서도 확인하기'),
 '영어듣기복습법':('영어 듣기 복습','안 들린 부분과 모르는 표현 나누기'),
 '영어문장구조읽기':('영어 문장 구조 읽기','단어 뜻과 문장의 연결 구분하기'),
 '영어독해근거찾기':('영어 독해 근거 찾기','답과 연결되는 문장을 표시하기'),
 '영어내신준비':('영어 내신 준비','학교 자료와 서술형 범위 점검하기'),
 '영어서술형쓰기':('영어 서술형 쓰기','문장 구성과 수정 근거 확인하기'),
 '영어학습관리':('영어 공부 영역 점검','어휘·읽기·듣기·쓰기 과제 나누기'),
 '학습플래너작성법':('학습 플래너 작성','계획과 실제 공부를 함께 기록하기'),
 '학습질문만들기':('공부 질문 만드는 방법','시도한 풀이와 멈춘 지점 남기기'),
 '피드백활용법':('피드백을 공부에 활용하기','설명을 들은 뒤 혼자 다시 해 보기'),
 '인출연습과간격복습':('기억을 꺼내 보는 복습','답을 보지 않고 설명한 결과 확인하기'),
 '학부모상담체크리스트':('학부모 상담 체크리스트','최근 자료와 확인할 질문 준비하기'),
 '학습대화방법':('아이와 공부 대화하기','결과와 실제 공부 과정을 나누어 묻기'),
 '학원수업비교':('학원 수업 비교 기준','학생에게 필요한 도움과 수업 비교하기'),
 '교육비확인':('교육비 확인 방법','횟수·시간·별도 비용 함께 확인하기'),
 '학습변화기록':('학습 변화 기록하기','도움받은 부분과 혼자 한 부분 비교하기'),
 '학습부담점검':('학생의 학습 부담 점검','학교 일정과 과제량 함께 살펴보기'),
}
MATH_TOPICS={
 'math-foundation':'수학기초점검','math-place':'수학기초점검','math-fraction':'수학기초점검',
 'math-accuracy':'계산실수줄이기','math-explain':'수학서술형풀이','math-proof':'수학서술형풀이',
 'math-transfer':'수학문장제읽기','math-start':'수학문장제읽기','math-inequality':'수학문장제읽기',
 'error-revisit':'수학오답관리','retry':'수학오답관리','math-independent':'수학오답관리',
 'reading-speed':'고등수학모의고사분석',
}
EN_TOPICS={
 'en-phonics':'영어듣기복습법','sound-reading':'영어듣기복습법','en-listening':'영어듣기복습법',
 'word-recall':'영어단어복습법','en-context':'영어단어복습법',
 'en-structure':'영어문장구조읽기','en-tense':'영어문장구조읽기','en-order':'영어문장구조읽기',
 'sentence-order':'영어문장구조읽기','grammar-transfer':'영어문장구조읽기',
 'reading-evidence':'영어독해근거찾기','en-reference':'영어독해근거찾기','en-inference':'영어독해근거찾기',
 'en-paraphrase':'영어서술형쓰기','en-summary':'영어서술형쓰기',
 'exam-cram':'영어내신준비',
}
PARENT_TOPICS={'school-load':'학습부담점검','load':'학습부담점검','study-dialogue':'학습대화방법',
 'progress-review':'학습변화기록','feedback':'학습변화기록'}

def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def unique(items):return list(dict.fromkeys(items))
def route(name):return '/'+name.removesuffix('index.html')
def stages(courses,subject=''):
 grades=[g for c in courses if not subject or c['subject']==subject for g in c.get('grades',[])]
 return [s for s in STAGES if any(g.startswith(s) for g in grades)]
def category_context(category):
 stage={'초등학생학원':'초','중학생학원':'중','고등학생학원':'고'}.get(category)
 if not stage:stage=next((s for s in STAGES if category.startswith(STAGES[s])),None)
 subject='수학' if category=='수학학원' else '영어' if category=='영어학원' else ''
 return stage,subject
def context(name,branches,grades,subjects,areas):
 path=route(name);parts=path.strip('/').split('/')
 if path in subjects:
  p=subjects[path];return {'kind':'subject','label':branches[p['branch']]['name']+' '+STAGES[p['stage']]+' '+p['subject'],
   'stage':p['stage'],'subject':p['subject'],'stages':[p['stage']],'topics':p['topics']}
 if path in grades:
  p=grades[path];return {'kind':'grade','label':branches[p['branch']]['name']+' '+STAGES[p['prefix']],
   'stage':p['prefix'],'subject':'','stages':[p['prefix']],'topics':p['topics']}
 if path in branches:
  p=branches[path];return {'kind':'branch','label':p['name'],'stage':None,'subject':'','stages':stages(p['courses']),'topics':[]}
 if parts[0] in ['과목별학원','전국센터']:
  category=parts[1] if parts[0]=='과목별학원' and len(parts)>1 else parts[2] if len(parts)>2 else ''
  stage,subject=category_context(category)
  area=areas.get(parts[-1] if parts[0]=='과목별학원' else parts[1] if len(parts)>1 else '')
  available=stages([{'subject':s,'grades':g} for s,g in area['grades'].items()],subject) if area else list(STAGES)
  label=(area['area']+' ' if area else '')+category.removesuffix('학원')
  if not label:label='학원 선택'
  return {'kind':'area' if area else 'hub','label':label.strip(),'stage':stage,'subject':subject,
   'stages':[stage] if stage else available,'topics':[]}
 if parts[0]=='학습시스템':return {'kind':'system','label':'학습코칭','stage':None,'subject':'','stages':[],'topics':[], 'system':parts[-1]}
 return {'kind':'hub','label':parts[1]+' 지역' if len(parts)>1 else '지점 선택','stage':None,'subject':'','stages':list(STAGES),'topics':[]}

def guide(slug):
 label,hint=LABELS[slug]
 return {'route':'/학습가이드/'+slug+'/','label':label,'hint':hint}
def book(field=None):
 if field:return {'route':'/교재안내/'+field+'/','label':field[:2]+' '+field[2:]+' 교재 비교','hint':'20종의 학습 영역과 권·단계 조건 살펴보기'}
 return {'route':'/교재안내/','label':'영어·수학 교재 찾기','hint':'학년과 필요한 공부 영역으로 120종 살펴보기'}
def selection():return {'route':'/교재안내/교재선택/','label':'교재 선택 체크리스트','hint':'지금 필요한 주교재와 보강의 역할 정하기'}

def resources(c):
 stage,subject,topics=c['stage'],c['subject'],c['topics']
 if subject:
  defaults=['수학기초점검','수학오답관리'] if subject=='수학' else \
   ['영어단어복습법','영어듣기복습법'] if stage=='초' else \
   ['영어문장구조읽기','영어내신준비'] if stage=='중' else \
   ['영어독해근거찾기','영어내신준비'] if stage=='고' else ['영어단어복습법','영어학습관리']
  mapping=MATH_TOPICS if subject=='수학' else EN_TOPICS
  matches=[mapping[t] for t in topics if t in mapping]
  matches=[s for s in matches if s!='고등수학모의고사분석' or stage=='고']
  matches=[s for s in matches if s!='영어내신준비' or stage in ['중','고']]
  # Primary manuscript topic takes precedence; defaults provide complementary help.
  study=unique(matches+defaults)[:2]
  if stage:study.append(MAIN[stage])
  else:study.append('수학문장제읽기' if subject=='수학' else '영어독해근거찾기')
  books=[book(STAGES[s]+subject) for s in c['stages']]
  if len(books)<3:books.append(selection())
  if not c['stages']:books.insert(0,book())
 elif stage:
  study=[MAIN[stage],'수학기초점검' if stage=='초' else '수학오답관리',
   '영어단어복습법' if stage=='초' else '영어문장구조읽기' if stage=='중' else '영어독해근거찾기']
  books=[book(STAGES[stage]+'수학'),book(STAGES[stage]+'영어')]
 elif c['kind']=='system':
  study=['학습질문만들기','피드백활용법','인출연습과간격복습'] if c['system']=='AI학습' else \
   ['학습플래너작성법','학습질문만들기','피드백활용법']
  books=[selection(),{'route':'/교재안내/자기주도학습/','label':'혼자 공부할 때 교재 활용','hint':'시도·질문·재확인으로 공부 기록 남기기'}]
 else:
  study=[MAIN[s] for s in c['stages']] or ['학습플래너작성법','학습질문만들기']
  books=[book(),selection()]
 parents=[PARENT_TOPICS[t] for t in topics if t in PARENT_TOPICS][:1]
 parents+=['학부모상담체크리스트'] if c['kind'] in ['subject','grade','system'] else ['교육비확인','학원수업비교','학부모상담체크리스트']
 if len(parents)<2:parents.append('학습변화기록')
 return [
  {'id':'study','title':'학생이 바로 적용할 공부 방법','intro':'막히는 부분을 골라 실행 방법과 기록 양식을 살펴보세요.','links':[guide(s) for s in unique(study)]},
  {'id':'books','title':'필요한 영역에 맞는 교재 찾기','intro':'학생이 실제로 해 본 결과를 보고 교재의 역할을 정해 보세요.','links':books},
  {'id':'parents','title':'학부모가 함께 확인할 자료','intro':'학생의 공부 기록을 바탕으로 수업과 다음 목표를 비교해 보세요.','links':[guide(s) for s in unique(parents)[:3]]},
 ]

def marked(kind,value):return '<!-- contextual-links:'+kind+':start -->'+value+'<!-- contextual-links:'+kind+':end -->'
def strip(s):return re.sub(r'<!-- contextual-links:([a-z]+):start -->.*?<!-- contextual-links:\1:end -->','',s,flags=re.S)
def module(c,groups):
 e=escape.escape
 title=c['label']+'에 도움이 되는 학습 자료'
 lead=(STAGES[c['stage']]+' '+c['subject']+' 공부에서 어려운 부분과 다음 준비를 함께 살펴보세요.').replace('  ',' ') if c['stage'] else \
  c['subject']+' 공부 방법과 교재, 상담 때 확인할 자료를 연결했습니다.' if c['subject'] else \
  '공부 방법부터 교재 선택과 상담 준비까지, 지금 필요한 자료를 골라 보세요.'
 body='<section class="cl-resources" id="helpful-learning" aria-labelledby="helpful-learning-title" data-context-resources data-context-kind="'+c['kind']+'" data-context-stage="'+(c['stage'] or '')+'" data-context-subject="'+c['subject']+'"><p class="cl-kicker">함께 읽으면 도움이 되는 자료</p><h2 id="helpful-learning-title">'+e(title)+'</h2><p class="cl-intro">'+e(lead)+'</p><div class="cl-grid">'
 for g in groups:
  body+='<article class="cl-card" data-context-group="'+g['id']+'"><h3>'+e(g['title'])+'</h3><p>'+e(g['intro'])+'</p><div class="cl-links">'
  for a in g['links']:
   body+='<a class="cl-link" href="'+quote(a['route'],safe='/')+'"><span><strong>'+e(a['label'])+'</strong><small>'+e(a['hint'])+'</small></span></a>'
  body+='</div></article>'
 return body+'</div><p class="cl-notice">'+NOTICE+'</p></section>'

def insert(s,c,groups):
 assert strip(s)==s,'Run from the saved baseline, not an already modified source.'
 # The top shortcut is separate from every existing navigation contract.
 jump=marked('jump','<nav class="cl-jump" aria-label="학습 자료 바로가기"><a href="#helpful-learning">공부 방법·교재 자료 보기</a></nav>')
 image=re.search(r'<section\b[^>]*\bid="lesson-image"[^>]*>',s)
 if image:
  target=image
 else:
  doc=html.fromstring(s)
  hero=doc.xpath('//main/*[contains(concat(" ",normalize-space(@class)," ")," bd-hero ") or contains(concat(" ",normalize-space(@class)," ")," page-hero ")]')
  assert hero,'No page hero'
  # lxml provides the semantic location; match original bytes through nesting.
  start=re.search(r'<section\b[^>]*class="[^"]*(?:bd-hero|page-hero)[^"]*"[^>]*>',s).start()
  depth=0;end=None
  for token in re.finditer(r'</?section\b[^>]*>',s[start:]):
   depth+=-1 if token.group().startswith('</') else 1
   if depth==0:end=start+token.end();break
  assert end
  s=s[:end]+jump+s[end:];target=None
 if target:s=s[:target.start()]+jump+s[target.start():]
 block=marked('module',module(c,groups))
 if '<!-- local-copy:end -->' in s:
  s=s.replace('<!-- local-copy:end -->','<!-- local-copy:end -->'+block,1)
 elif c['kind'] in ['subject','grade','branch','system']:
  target=re.search(r'<section\b[^>]*\bid="faq"[^>]*>',s);assert target
  s=s[:target.start()]+block+s[target.start():]
 else:
  target=re.search(r'<section\b[^>]*\bid="(?:hub-directory|subject-choice)"[^>]*>',s)
  if not target:target=re.search(r'<section\b[^>]*\bid="(?:hub-answer|how-to-choose|grade-guide|faq)"[^>]*>',s)
  assert target,'No hub insertion point'
  s=s[:target.start()]+block+s[target.start():]
 assert s.count('</head>')==1
 return s.replace('</head>',marked('style','<link rel="stylesheet" href="/assets/contextual-links.css">')+'</head>',1)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 before=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 branches={p['route']:p for p in load('branch-directory-data.json')['branches']}
 grades={p['route']:p for p in load('grade-directory-data.json')['pages']}
 subjects={p['route']:p for p in load('subject-directory-data.json')['pages']}
 areas={p['slug']:p for p in load('area-reference.json')['areas']}
 guides={p['route'] for p in load('learning-guide-data.json')['pages']}
 book_routes={p['route'] for p in load('book-library-data.json')['pages']}
 names=[n for n in before['files'] if n.endswith('/index.html') and n.split('/')[0] in ['지점안내','전국센터','과목별학원','학습시스템']]
 assert len(names)==6364
 pages=[]
 with zipfile.ZipFile(args.audit/'before-source.zip') as archive:
  for name in names:
   original=archive.read(name).decode('utf-8');c=context(name,branches,grades,subjects,areas);groups=resources(c)
   links=[a['route'] for g in groups for a in g['links']]
   assert len(links)==len(set(links)) and all(r in guides|book_routes for r in links),(name,links)
   try:output=insert(original,c,groups)
   except AssertionError as error:raise AssertionError((name,c,str(error))) from error
   assert strip(output)==original,name
   encoded=output.encode('utf-8')
   if (ROOT/name).read_bytes()!=encoded:(ROOT/name).write_bytes(encoded)
   pages.append({'file':name,'route':route(name),'context':c,'groups':groups})
 selected=set(before['files'])|{'assets/contextual-links.css'}
 files=dict(before['files']);text_hashes=dict(before.get('textSha256',{}))
 for name in names+['assets/contextual-links.css']:
  data=(ROOT/name).read_bytes();files[name]=hashlib.sha256(data).hexdigest()
  if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name):text_hashes[name]=hashlib.sha256(data.decode('utf-8').replace('\r\n','\n').encode()).hexdigest()
 files=dict(sorted(files.items()));text_hashes=dict(sorted(text_hashes.items()))
 save(ROOT/'release-public-manifest.json',{**before,'createdAt':'2026-10-01T15:00:00+00:00','files':files,'textSha256':text_hashes})
 save(ROOT/'contextual-links-data.json',{'version':1,'baseline':'7585749164753b3dbe1bb1983f07df21dcb9eb2b','notice':NOTICE,'pages':pages})
 summary={'pages':len(pages),'kinds':dict(Counter(p['context']['kind'] for p in pages)),
  'links':sum(len(g['links']) for p in pages for g in p['groups']),'publicFiles':len(selected),'sitemapPages':before['sitemapPages'],'newUrls':0,'deployed':False}
 save(args.audit/'generation-summary.json',summary);print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()

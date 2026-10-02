"""Homepage discovery uses the reviewed branch mapping and guide catalog only."""
import json,re
from collections import defaultdict
import build_branch_upgrade as ui

FEATURED=['시험2주준비','방학복습계획','중등고등학년전환','수학풀이비교','영어쓰기수정기록','교재선택복습']
REGIONS=['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주']

def marked(kind,body):
 return f'<!-- home-discovery:{kind}:start -->'+body+f'<!-- home-discovery:{kind}:end -->'

def enhance(root):
 file=root/'index.html';source=file.read_text(encoding='utf-8')
 source=re.sub(r'<!-- home-discovery:([a-z]+):start -->[\s\S]*?<!-- home-discovery:\1:end -->','',source)
 branches=json.loads((root/'branch-directory-data.json').read_text(encoding='utf-8'))['branches']
 mapping=json.loads((root/'neighborhood-directory-data.json').read_text(encoding='utf-8'))['mapping']
 guides=json.loads((root/'learning-guide-data.json').read_text(encoding='utf-8'))
 areas=defaultdict(set);branch_by={b['route']:b for b in branches}
 for item in mapping:
  assert item['branch'] in branch_by and item['region']==branch_by[item['branch']]['region'],item
  areas[item['branch']].add(item['area'])
 rows=[{**{k:b[k] for k in ['route','name','region','district','address','addressPending']},'areas':sorted(areas[b['route']])} for b in branches]
 regions=[r for r in REGIONS if any(b['region']==r for b in branches)]
 ui.save(root/'assets/home-branch-search-data.json',{'version':1,'branches':rows})
 source=re.sub(r'<body class="([^"]+)"',lambda m:'<body class="'+m[1]+('' if 'home-page' in m[1].split() else ' home-page')+'"',source,count=1)
 source=re.sub(r'(<div class="hero-copy">[\s\S]*?)<h1>[\s\S]*?</h1>',lambda m:m[1]+'<h1>우리 동네에서 찾는<br>초·중·고 학습코칭</h1>',source,count=1)
 source=re.sub(r'(<div class="hero-copy">[\s\S]*?)<p class="lead">[\s\S]*?</p>',lambda m:m[1]+'<p class="lead">영어·수학·국어 수업 정보와 공부 방법을 살펴보세요. 동네별 지점 안내에서 수업 조건을 확인하고 상담을 준비할 수 있습니다.</p>',source,count=1)
 actions='<div class="hero-actions"><a class="btn btn-primary" href="#home-branch-search">우리 동네 지점 찾기</a><a class="btn btn-soft" href="'+ui.FORM+'" target="_blank" rel="noopener noreferrer">상담 신청</a></div>'
 source=re.sub(r'<div class="hero-actions">[\s\S]*?</div>',lambda _:actions,source,count=1)
 jump=re.search(r'<!-- home-library:jump:start -->[\s\S]*?<!-- home-library:jump:end -->',source)
 assert jump;source=source[:jump.start()]+source[jump.end():].lstrip('\r\n')
 options=''.join('<option value="'+r+'">'+r+'</option>' for r in regions)
 region_links=''.join(ui.link('/지점안내/'+r+'/',r) for r in regions)
 search='<section class="hd-section hd-search" id="home-branch-search" aria-labelledby="home-branch-search-title"><div class="hd-heading"><p class="eyebrow">우리 동네 학원 찾기</p><h2 id="home-branch-search-title">동네나 지점 이름으로 찾아보세요</h2><p>동네와 연결된 실제 지점의 주소·수업 조건·교육비 안내로 이동합니다.</p></div><form class="hd-search-form" role="search" aria-label="메인 지점 검색" action="'+ui.href('/지점안내/')+'" method="get" data-home-search><div><label for="home-search-region">지역</label><select id="home-search-region" name="region"><option value="">전체 지역</option>'+options+'</select></div><div><label for="home-search-query">동네·지점 이름</label><input id="home-search-query" type="search" name="q" placeholder="예: 마두점, 장항동" autocomplete="off" maxlength="100"></div><button type="submit">지점 찾기</button><button type="button" data-home-search-reset hidden>초기화</button></form><p class="hd-search-status" role="status" aria-live="polite" data-home-search-status>동네·지점 이름을 입력하거나 지역을 선택해 주세요.</p><div class="hd-results" data-home-search-results></div><button class="hd-more" type="button" data-home-search-more hidden>검색 결과 더 보기</button><details class="hd-region-links"><summary>지역별 지점 안내 바로가기</summary><nav aria-label="지역별 지점 안내">'+region_links+'</nav></details><noscript><p>지점 검색은 자바스크립트가 필요합니다. 지역별 지점 안내를 펼치거나 '+ui.link('/지점안내/','전체 지점안내')+'에서 찾아보세요.</p></noscript></section>'
 by_slug={p['slug']:p for p in guides['pages']};groups={key:title for key,title,_ in guides['groups']}
 featured=[];cards=[]
 for slug in FEATURED:
  p=by_slug[slug];assert p['isNew'],slug
  card={'route':p['route'],'title':p['title'],'description':p['description'],'group':groups[p['group']],'audience':p['audience']}
  featured.append(card)
  cards.append('<a class="hd-guide-card" data-home-featured href="'+ui.href(p['route'])+'"><span class="hd-guide-label">새 가이드 · '+ui.e(card['group'])+'</span><h3>'+ui.e(p['title'])+'</h3><p>'+ui.e(p['description'])+'</p><span class="hd-guide-action">실천 예시·기록 양식 보기 <span aria-hidden="true">→</span></span></a>')
 levels=''.join('<a href="'+ui.href('/학습가이드/')+'?level='+key+'">'+ui.e(title+' 가이드')+'</a>' for key,title in guides['levels'])
 featured_section='<section class="hd-section hd-guides" id="home-new-guides" aria-labelledby="home-new-guides-title"><div class="hd-heading"><p class="eyebrow">학생과 학부모를 위한 교육 정보</p><h2 id="home-new-guides-title">새로 추가한 학습가이드</h2><p>지금의 고민에 맞는 글을 읽고, 실천 예시를 자신의 과제에 적용해 보세요.</p></div><nav class="hd-guide-levels" aria-label="대상별 학습가이드">'+levels+'</nav><div class="hd-guide-grid">'+''.join(cards)+'</div><p class="hd-all-guides">'+ui.link('/학습가이드/',f'전체 {len(guides["pages"])}편 학습가이드 보기 →')+'</p></section>'
 marker='<!-- home-library:content:start -->';assert source.count(marker)==1
 source=source.replace(marker,marked('content',search+featured_section)+marker)
 source=source.replace('<nav class="hl-topic-grid"',jump[0]+'<nav class="hl-topic-grid"',1)
 # The shared stylesheet remains last; homepage rules do not alter navigation.
 head='<link rel="stylesheet" href="/assets/home-discovery.css"><script type="module" src="/assets/home-branch-search.js"></script>'
 source=source.replace('<link rel="stylesheet" href="/assets/site-shell.css">',marked('head',head)+'<link rel="stylesheet" href="/assets/site-shell.css">',1)
 node={'@context':'https://schema.org','@type':'ItemList','@id':ui.url('/')+'#new-learning-guides','name':'새로 추가한 학습가이드','numberOfItems':len(featured),'itemListElement':[{'@type':'ListItem','position':i,'name':p['title'],'url':ui.url(p['route'])} for i,p in enumerate(featured,1)]}
 source=source.replace('</head>',marked('schema','<script type="application/ld+json">'+ui.j(node)+'</script>')+'</head>',1)
 ui.write(file,source)
 data=json.loads((root/'home-library-data.json').read_text(encoding='utf-8'))
 ui.save(root/'home-library-data.json',{**data,'featuredGuides':featured,'search':{'branches':len(rows),'areas':sum(len(b['areas']) for b in rows),'regions':regions}})

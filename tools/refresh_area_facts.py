"""Apply reviewed area/branch facts to existing routes; dry-run unless --apply."""
import argparse, collections, datetime, hashlib, html, json, re, zipfile, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--3e0bz50bxucwzc.com'
SUBJECTS={'국어':'korean','영어':'english','수학':'math','과학':'science','사회':'social'}
LEVELS={'초':('초등','elementary'),'중':('중등','middle'),'고':('고등','high')}
CATEGORIES=['수학학원','영어학원','영수학원','초등영수학원','중등영수학원','고등영수학원','초등학생학원','중학생학원','고등학생학원']
LD=re.compile(r'(<script\b(?=[^>]*\btype=["\']application/ld\+json["\'])[^>]*>)(.*?)(</script\s*>)',re.S|re.I)
FACTS=re.compile(r'<section\b[^>]*class="[^"]*(?:subject-summary-section|geo-summary-section|area-facts-section)[^"]*"[^>]*>.*?</section>',re.S)
DATE='2026-09-28'
esc=lambda x:html.escape(str(x),quote=True)
digest=lambda b:hashlib.sha256(b).hexdigest()

def save_json(file,value):
    temporary=file.with_name('.'+file.name+'.area-facts.tmp')
    data=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    temporary.write_bytes(data)
    try:temporary.replace(file)
    except PermissionError:
        # A Windows reader can hold a mapped file and reject truncate/replace.
        # A same-size write does not change the file mapping or file permissions.
        if not file.exists() or file.stat().st_size!=len(data):raise
        with file.open('r+b') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        assert file.read_bytes()==data,'Saved JSON verification failed'
        temporary.unlink()

def page_bytes(names,baseline=None):
    if baseline:
        with zipfile.ZipFile(baseline) as saved:
            for name in names:yield name,saved.read(name)
        return
    with ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0,len(names),64):
            batch=names[start:start+64]
            for name,raw in zip(batch,pool.map(lambda n:(ROOT/n).read_bytes(),batch)):
                yield name,raw

def url(route):return DOMAIN+quote(route,safe='/#-')
def route_for(r,category=None):
    return f'/과목별학원/{category}/{r["slug"]}/' if category else f'/전국센터/{r["slug"]}/'
def grade_text(grades):
    parts=[]
    for prefix in LEVELS:
        nums=sorted({int(g[1:]) for g in grades if g.startswith(prefix)})
        if nums:
            parts.append(f'{prefix}{nums[0]}~{prefix}{nums[-1]}' if len(nums)>1 and nums==list(range(nums[0],nums[-1]+1)) else '·'.join(f'{prefix}{n}' for n in nums))
    return ' / '.join(parts)
def scope(name):
    parts=name.split('/')
    category=parts[1] if parts[0]=='과목별학원' else (parts[2] if len(parts)==4 else '지역학원')
    subjects=['수학'] if category=='수학학원' else ['영어'] if category=='영어학원' else ['영어','수학'] if '영수' in category or category=='영어수학학원' else list(SUBJECTS)
    level=next((p for p in LEVELS if category.startswith(p)),None)
    return category,subjects,level
def filtered(r,subject,level=None):return [g for g in r['grades'][subject] if not level or g.startswith(level)]
def primary(r,subject=None,level=None,combined=False):
    if combined:return route_for(r,(LEVELS[level][0] if level else '')+'영수학원')
    if subject in ['영어','수학']:
        return route_for(r,subject+'학원')+(f'#{SUBJECTS[subject]}-{LEVELS[level][1]}' if level else '')
    if level:
        category={'초':'초등학생학원','중':'중학생학원','고':'고등학생학원'}[level]
        return route_for(r,category)+(f'#subject-{SUBJECTS[subject]}' if subject else '')
    return route_for(r)+(f'#subject-{SUBJECTS[subject]}' if subject else '')
def summary(r,subjects,level):
    values=[]
    for s in subjects:
        gs=filtered(r,s,level)
        if gs:values.append(f'{s} {grade_text(gs)}')
    return '자료에 기재된 학년은 '+', '.join(values)+'입니다.' if values else '이 페이지의 과목·학년에 해당하는 수강 정보는 상담에서 확인해 주세요.'

def facts_block(r,name):
    category,subjects,level=scope(name)
    title_id='answer-title' if name.startswith('과목별학원/') else 'geo-summary-title'
    rows=[]
    for subject in subjects:
        rowlevels=list(LEVELS) if len(subjects)==1 else [level]
        for lv in rowlevels:
            gs=filtered(r,subject,lv)
            anchor=f'{SUBJECTS[subject]}-{LEVELS[lv][1]}' if len(subjects)==1 else f'subject-{SUBJECTS[subject]}'
            label=(LEVELS[lv][0]+' ' if lv else '')+subject
            value=grade_text(gs) if gs else '학년 안내 없음 · 상담 확인'
            note='<small>추가 학년은 상담에서 확인해 주세요.</small>' if subject in r['gradeConflicts'] else ''
            rows.append(f'<div id="{anchor}" data-subject="{SUBJECTS[subject]}" data-grades="{esc(",".join(gs))}"><dt>{esc(label)}</dt><dd>{esc(value)}{note}</dd></div>')
    links=[]
    targets=[(primary(r,'수학',level),f'{r["area"]} '+(LEVELS[level][0]+' ' if level else '')+'수학 안내'),(primary(r,'영어',level),f'{r["area"]} '+(LEVELS[level][0]+' ' if level else '')+'영어 안내')]
    if level:targets.append((primary(r,level=level),LEVELS[level][0]+' 과목별 학년'))
    else:targets.extend((primary(r,level=p),LEVELS[p][0]+' 과목별 학년') for p in LEVELS)
    targets.extend([(primary(r,combined=True,level=level),'영어·수학 함께 확인'),(route_for(r),'지역·지점 안내')])
    own='/'+name.removesuffix('index.html')
    for target,label in dict(targets).items():
        if target==own:continue
        links.append(f'<a href="{quote(target,safe="/#-")}">{esc(label)}</a>')
    schools=[school for p,items in r['schools'].items() if not level or p==level for school in items]
    details=f'<p>교육지원청 등록번호: {esc(r["registration"])}</p>'
    if schools:details+=f'<p>주변 학교 참고: {esc(" · ".join(schools))}. 재학생 수강 여부나 학교별 반 편성을 뜻하지 않습니다.</p>'
    if r['feeUrl']:details+=f'<p><a href="{esc(r["feeUrl"])}" target="_blank" rel="noopener noreferrer">센터별 교습비 자료 보기</a></p>'
    maplink='https://map.naver.com/p/search/'+quote(r['address'],safe='')
    pending='<small>방문 전 현재 위치를 상담으로 확인해 주세요.</small>' if r['addressStatus']=='주소 재확인 필요' else ''
    return f'''<section class="section area-facts-section" aria-labelledby="{title_id}" data-area="{esc(r['slug'])}" data-reference="{r['fingerprint']}">
      <div class="area-facts-heading"><p class="eyebrow">지점·과목 안내</p><h2 id="{title_id}">{esc(r['area'])} 수업을 알아볼 때 확인할 지점</h2><p>{esc(r['area'])}에서 수업을 알아보는 학생에게 안내하는 지점은 <strong>{esc(r['branch'])}</strong>입니다. 지점 위치와 과목별 학년을 먼저 확인해 주세요.</p></div>
      <div class="area-facts-grid"><div><h3>과목별 안내 학년</h3><dl class="area-grade-list">{''.join(rows)}</dl><p class="area-facts-note">제공 자료에 기재된 학년입니다. 현재 개설 과정·수업 시간·반 편성은 상담에서 확인해 주세요. 안내가 없는 학년은 수업 가능 여부가 확인되지 않았습니다.</p></div><div><h3>실제 지점 위치</h3><p class="area-branch-name">{esc(r['branch'])}</p><p data-branch-address>{esc(r['address'])}{pending}</p><a class="area-map-link" href="{esc(maplink)}" target="_blank" rel="noopener noreferrer">주소로 네이버 지도 검색</a><details class="area-facts-details"><summary>등록 정보·교습비·주변 학교</summary>{details}</details></div></div>
      <nav class="area-related-links" aria-label="{esc(r['area'])} 과목·학년 안내">{''.join(links)}</nav>
    </section>'''

def modify_schema(obj,r,subjects,level,oldids):
    if isinstance(obj,list):return [modify_schema(o,r,subjects,level,oldids) for o in obj]
    if not isinstance(obj,dict):return r['orgId'] if isinstance(obj,str) and obj in oldids else obj
    obj={k:modify_schema(v,r,subjects,level,oldids) for k,v in obj.items()}
    types=obj.get('@type',[]);types=[types] if isinstance(types,str) else types
    if 'EducationalOrganization' in types and ('LocalBusiness' in types or 'address' in obj):
        keep={k:v for k,v in obj.items() if k in {'@type','telephone','contactPoint'}}
        keep.update({'@id':r['orgId'],'name':r['branch'],'url':url(f'/전국센터/{r["branchRepresentativeSlug"]}/'),'address':{'@type':'PostalAddress','streetAddress':r['address'],'addressCountry':'KR'},'areaServed':[{'@type':'Place','name':area} for area in r['branchAreas']],'identifier':{'@type':'PropertyValue','propertyID':'교육지원청 등록번호','value':r['registration']},'knowsAbout':[s for s in SUBJECTS if r['grades'][s]],'educationalLevel':list(dict.fromkeys(g for s in SUBJECTS for g in r['grades'][s]))})
        if 'contactPoint' in keep:keep['contactPoint']['contactType']='학습 상담'
        return keep
    if any(t in types for t in ['WebPage','CollectionPage','Article']):obj['dateModified']=DATE
    if 'Article' in types and 'abstract' in obj:obj['abstract']=obj.get('description',summary(r,subjects,level))
    if 'Service' in types and '@id' in obj:
        obj.pop('makesOffer',None)
        obj.update({'name':r['branch']+' '+('·'.join(subjects))+' 상담 안내','serviceType':'학습 상담 안내','description':summary(r,subjects,level),'provider':{'@id':r['orgId']},'audience':{'@type':'EducationalAudience','educationalRole':'student'}})
    if r['branch'].endswith('위례점') and isinstance(obj.get('image'),list):obj['image']=[i for i in obj['image'] if not isinstance(i,str) or '/assets/maps/' not in i]
    return obj

def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)

def repair(text,name,r):
    category,subjects,level=scope(name)
    def factual_paragraph(m):
        plain=html.unescape(re.sub(r'<[^>]+>','',m[0]))
        managed='학생에게 안내하는' in plain and '의 주소는' in plain and ('자료에 기재된 학년은' in plain or '이 페이지의 과목·학년에 해당하는' in plain)
        replacement=esc(f'{r["area"]} 학생에게 안내하는 {r["branch"]}의 주소는 {r["address"]}입니다. '+summary(r,subjects,level)+' 현재 개설 과정과 수업 시간은 상담에서 다시 확인해 주세요.')
        if managed:return re.match(r'<p\b[^>]*>',m[0])[0]+replacement+'</p>'
        if '가능 학년' not in plain:return m[0]
        listed=set(re.findall(r'초[1-6]|중[1-3]|고[1-3]',plain.split('가능 학년',1)[1]))
        if not listed:return m[0]
        ss=list(SUBJECTS) if '센터 전체' in plain else subjects
        ranges=[set(filtered(r,s,level)) for s in ss]
        expected=set.intersection(*ranges) if ss==['영어','수학'] else set.union(*ranges)
        if listed==expected:return m[0]
        return re.match(r'<p\b[^>]*>',m[0])[0]+replacement+'</p>'
    text=re.sub(r'<p\b[^>]*>.*?</p>',factual_paragraph,text,flags=re.S)
    text,n=FACTS.subn(lambda m:facts_block(r,name),text)
    assert n==1,(name,'summary',n)
    def hero(m):
        block=m[0]
        lead=f'{r["area"]}의 {"·".join(subjects)} 수업을 알아보는 학생을 위해 {r["branch"]}의 위치와 과목별 안내 학년을 정리했습니다.'
        block,n=re.subn(r'<p class="lead">.*?</p>',lambda _:f'<p class="lead">{esc(lead)}</p>',block,flags=re.S);assert n==1
        block=re.sub(r'<div class="hero-points">.*?</div>',lambda _:f'<div class="hero-points"><span>{esc(r["region"]+" "+r["district"]+" "+r["area"])}</span><span>{esc(r["branch"])}</span><span>과목별 학년 확인</span></div>',block,flags=re.S)
        return block
    text,n=re.subn(r'<section\b[^>]*class="[^"]*local-hero[^"]*"[^>]*>.*?</section>',hero,text,flags=re.S);assert n==1,(name,'hero')
    def class_panel(m):
        block=m[0]
        block=re.sub(r'<p class="lead">.*?</p>','<p class="lead">과목별로 안내 학년이 다릅니다. 상단의 과목별 학년을 확인한 뒤 현재 개설 과정과 반 편성을 상담해 주세요.</p>',block,flags=re.S)
        known=[s for s in subjects if filtered(r,s,level)]
        block=re.sub(r'(<b>수업 가능 과목</b><span>).*?(</span>)',lambda x:x[1]+esc(' · '.join(known) or '상담 확인')+x[2],block,flags=re.S)
        block=re.sub(r'(<b>수업 가능 학년</b><span>).*?(</span>)',lambda x:x[1]+'과목별 안내 학년 확인'+x[2],block,flags=re.S)
        return block
    text=re.sub(r'<section class="section local-guide-panel">.*?</section>',class_panel,text,flags=re.S)
    text=re.sub(r'(<dt>페이지 반영일</dt>\s*<dd>)\d{4}-\d{2}-\d{2}',lambda m:m[1]+DATE,text)
    if r['branch'].endswith('위례점'):
        text=text.replace('경기 성남시 수정구 위례광장로 320 315호',esc(r['address']))
        # The owner reconfirmed the supplied neighborhood maps on 2026-10-02.
    def schema(m):
        obj=json.loads(m[2])
        oldids={o['@id'] for o in walk(obj) if '@id' in o and 'address' in o and 'EducationalOrganization' in str(o.get('@type'))}
        new=modify_schema(obj,r,subjects,level,oldids)
        return m[1]+json.dumps(new,ensure_ascii=False,separators=(',',':'))+m[3]
    text=LD.sub(schema,text)
    branch=r['branch'].replace('와와학습코칭센터','').strip()
    topic=category.replace('지역학원','학원').replace('와와학습코칭학원','학습코칭')
    description=f'{r["area"]} {topic} 안내에서 {branch}의 과목별 수강 학년과 위치, 교습비 자료를 확인합니다.'
    assert len(description)<=80,(name,description)
    text=re.sub(r'(<meta\b(?=[^>]*(?:name|property)="(?:description|og:description|twitter:description)")[^>]*content=")[^"]*("[^>]*>)',lambda m:m[1]+esc(description)+m[2],text)
    def descriptions(m):
        obj=json.loads(m[2])
        for node in walk(obj):
            if node.get('@type') in ['WebPage','Article','CollectionPage']:
                node['description']=description
                if node.get('@type')=='Article':node['abstract']=description
        return m[1]+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+m[3]
    text=LD.sub(descriptions,text)
    if 'assets/area-facts.css' not in text:
        depth=len(name.split('/'))-1
        text=text.replace('</head>',f'<link rel="stylesheet" href="{"../"*depth}assets/area-facts.css">\n</head>')
    from image_first_layout import rearrange
    from refresh_local_copy import rewrite
    return rewrite(rearrange(text,name,r,subjects,level,grade_text),name,r)

def query_matrix(areas):
    result=[]
    for r in areas:
        intents=[('학원',None,None,False,route_for(r)),('와와학습코칭학원',None,None,False,route_for(r)+'와와학습코칭학원/')]
        intents.extend((s+'학원',s,None,False,primary(r,s)) for s in SUBJECTS)
        intents.extend((LEVELS[p][0]+' 학원',None,p,False,primary(r,level=p)) for p in LEVELS)
        intents.extend((LEVELS[p][0]+' '+s+'학원',s,p,False,primary(r,s,p)) for p in LEVELS for s in SUBJECTS)
        intents.append(('영수학원',None,None,True,primary(r,combined=True)))
        intents.extend((LEVELS[p][0]+' 영수학원',None,p,True,primary(r,level=p,combined=True)) for p in LEVELS)
        for label,subject,level,combined,target in intents:
            ss=[subject] if subject else ['영어','수학'] if combined else list(SUBJECTS)
            values={s:filtered(r,s,level) for s in ss}
            complete=all(values.values()) if combined else any(values.values())
            state='자료 기재' if complete else '상담 확인 필요'
            if any(s in r['gradeConflicts'] for s in ss):state+=' · 자료 간 차이'
            if r['missingSource']:state+=' · 단일 자료'
            result.append({'area':r['area'],'region':r['region'],'district':r['district'],'branch':r['branch'],'query':r['area']+' '+label,'subject':subject or ('영어·수학' if combined else '전체'),'level':LEVELS[level][0] if level else '전체','status':state,'grades':' / '.join(s+' '+(grade_text(gs) or '미기재') for s,gs in values.items()),'primaryUrl':url(target),'separateSubjectPage':subject in ['영어','수학'] if subject else True,'fragment':target.split('#')[1] if '#' in target else '', 'sources':f'센터정보 정리.csv {r["mappingRow"]}행; 최신화.csv {r["latestCodeRow"]}행; 코칭센터_데이터_.xlsx 센터정보 {r["sourceRow"] or "미일치"}행'})
    return result

def main():
    args=argparse.ArgumentParser();args.add_argument('--apply',action='store_true');args.add_argument('--report',type=Path,required=True);args.add_argument('--baseline-zip',type=Path);args.add_argument('--manifest-only',action='store_true');args=args.parse_args()
    if args.manifest_only:assert args.apply and args.baseline_zip,'Recovery requires the saved baseline and --apply'
    ref=json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'));areas=ref['areas']
    for r in areas:
        r['orgId']=DOMAIN+'/#center-'+digest((r['branch']+'|'+r['address']).encode())[:12]
        r['fingerprint']=digest(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())[:16]
    byslug={r['slug']:r for r in areas}
    if args.baseline_zip:
        with zipfile.ZipFile(args.baseline_zip) as saved:manifest=json.loads(saved.read('release-public-manifest.json'))
    else:manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8-sig'))
    description_config=json.loads((ROOT/'seo-descriptions.json').read_text(encoding='utf-8-sig'))
    description_changes=0
    changed={};counts=collections.Counter()
    for name,raw in page_bytes([n for n in manifest['files'] if n.endswith('.html')],args.baseline_zip):
        parts=name.split('/')
        if name.endswith('/index.html') and parts[0]=='과목별학원' and len(parts)==4 and parts[1] in CATEGORIES:slug=parts[2]
        elif name.endswith('/index.html') and parts[0]=='전국센터' and len(parts) in [3,4]:slug=parts[1]
        else:continue
        if slug not in byslug:raise ValueError(name)
        text=raw.decode('utf-8-sig');r=byslug[slug];new=repair(text,name,r)
        description=html.unescape(re.search(r'<meta name="description" content="([^"]*)"',new)[1])
        key='/'+name.removesuffix('/index.html')
        entry=description_config['pages'][key]
        if entry['description']!=description:
            old=entry['description']
            if old not in entry['sources']:entry['sources'].append(old)
            entry['description']=description
            description_changes+=1
        for pattern in [r'<title\b[^>]*>.*?</title>',r'<h1\b[^>]*>.*?</h1>',r'<link\b[^>]*rel="canonical"[^>]*>']:
            assert re.findall(pattern,text,re.S)==re.findall(pattern,new,re.S),(name,'protected field',pattern)
        if new!=text:changed[name]=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+new.encode('utf-8')
        counts[parts[0]]+=1
        if sum(counts.values())%500==0:print(json.dumps({'checked':sum(counts.values())}),flush=True)
    assert sum(counts.values())==4452,counts
    if args.baseline_zip:
        with zipfile.ZipFile(args.baseline_zip) as saved:sitemap=saved.read('sitemap.xml').decode('utf-8').replace('\r\n','\n')
    else:sitemap=(ROOT/'sitemap.xml').read_text(encoding='utf-8')
    def dated(m):
        location=html.unescape(re.search(r'<loc>(.*?)</loc>',m[0])[1]);filename=unquote(urlsplit(location).path).strip('/')+'/index.html'
        return re.sub(r'<lastmod>.*?</lastmod>',f'<lastmod>{DATE}</lastmod>',m[0]) if filename in changed else m[0]
    newmap=re.sub(r'<url>.*?</url>',dated,sitemap,flags=re.S)
    if newmap!=sitemap:changed['sitemap.xml']=newmap.encode('utf-8')
    for css_name in ['assets/area-facts.css','assets/image-first.css','assets/local-editorial.css']:
        css=(ROOT/css_name).read_bytes()
        if manifest['files'].get(css_name)!=digest(css):changed[css_name]=css
    if args.apply:
        if description_changes:
            save_json(ROOT/'seo-descriptions.json',description_config)
        def write_file(item):
            name,raw=item
            if args.manifest_only:
                assert (ROOT/name).read_bytes()==raw,('Recovery file differs from expected transformation',name)
            else:(ROOT/name).write_bytes(raw)
            return name,digest(raw),digest(raw.decode('utf-8').replace('\r\n','\n').encode())
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i,(name,binary_hash,text_hash) in enumerate(pool.map(write_file,changed.items()),1):
                manifest['files'][name]=binary_hash
                manifest.setdefault('textSha256',{})[name]=text_hash
                if i%500==0:print(json.dumps({'written':i}),flush=True)
        if changed:
            manifest['createdAt']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
            save_json(ROOT/'release-public-manifest.json',manifest)
    report={'mode':'apply' if args.apply else 'dry-run','summary':ref['summary'],'checkedHtml':sum(counts.values()),'changedHtml':sum(n.endswith('.html') for n in changed),'descriptionConfigChanges':description_changes,'changedFiles':list(changed),'newRoutes':0,'routeCounts':dict(counts),'queries':query_matrix(areas)}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['queries','changedFiles']},ensure_ascii=False))

if __name__=='__main__':main()

"""Add the third reviewed batch; preserve earlier articles and bounded page content."""
import argparse, hashlib, json, re, random, copy
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
from lxml import etree
from PIL import Image, ImageOps
import upgrade_education_info as render
import build_education_info as view

ROOT = view.ROOT
DAY = '2026-10-06'
ALTS = '''학습 자료에 연필로 표시하는 손|교실 책상에서 교재를 읽는 학생|펼친 자료 앞에 놓인 학생의 손|교실에서 책을 펼친 학생|각자 책상에서 필기하는 두 학생|태블릿을 함께 확인하는 어른과 아이|책상에서 필기하는 학생|교재 옆의 노트에 필기하는 손|노트북과 책을 함께 보는 학생|자료를 읽으며 노트에 쓰는 모습|칠판 앞에서 설명을 듣는 학생들|온라인 영상과 학습 자료를 함께 보는 학생|벽면에 붙인 일정표를 확인하는 손|태블릿으로 자료를 확인하는 학생|책상에서 생각하는 두 학생|교재를 함께 보는 어른과 아이|교복을 입고 함께 서 있는 네 학생|조명이 켜진 책상에서 휴대전화를 보는 학생|노트북과 책이 펼쳐진 책상|교재와 필기구가 놓인 책상|노트에 글을 쓰는 모습|침대에서 쉬고 있는 모습|복도에서 대화하는 학생들|어른과 이야기를 나누는 학생|펼친 책 옆에서 기록하는 손|컴퓨터 옆의 노트에 쓰는 손|헤드폰을 쓰고 책을 보는 학생|교재를 펼쳐 필기하는 학생|책을 들고 함께 서 있는 세 학생|자료를 들어 보이는 학생|자료를 읽으며 설명하는 학생|도서관에서 책을 살펴보는 아이들|펼친 교재에 연필로 표시하는 손|노트북 앞에서 생각하는 모습|책을 함께 읽는 두 학생|식탁에서 음식 앞에 앉은 아이|책상에서 자료를 보고 필기하는 학생|학교 복도에서 함께 서 있는 학생들|책상이 놓인 학습 공간|책과 화면을 함께 보며 공부하는 학생|여러 자료와 태블릿이 놓인 책상|교재를 함께 확인하는 학생과 어른|노트에 필기하는 두 사람의 손|도서관에서 책을 함께 읽는 아이들|벽면 일정표 앞에서 자료에 표시하는 모습|책상에서 생각하는 학생|손을 들고 질문하는 학생|노트북 앞에서 글을 쓰는 손|책상에 기대어 있는 두 학생|조명 아래 책상에 앉아 있는 학생|교실에서 함께 있는 네 학생|학교 복도에서 이야기를 나누는 두 학생|교재를 들고 있는 두 학생|조명이 켜진 책상에서 공부하는 모습|학습 자료 앞에 함께 있는 두 학생|노트와 필기구가 정리된 책상|교재를 펼치고 이야기하는 세 학생|휴대전화 옆에서 생각하는 학생|조명 아래 교재를 읽는 학생|태블릿을 함께 확인하는 학생과 어른|필기구와 작은 노트가 놓인 모습|책상에서 생각에 잠긴 학생|칠판 앞에서 자료를 들고 설명하는 학생|교복을 입고 함께 서 있는 네 학생|펼쳐진 책의 여러 페이지|천장 손잡이를 잡고 이동하는 학생들|교재 옆에서 손을 들어 보이는 학생|책과 헤드폰이 놓인 모습|교재를 들고 함께 서 있는 세 학생|교실 책상에서 필기하는 아이|태블릿과 교재를 펼쳐 공부하는 학생|펼친 책에 필기하는 학생|교재 옆에서 책상에 기대어 쉬는 학생|자료를 읽으며 기록하는 모습|교재 앞에서 질문을 표현하는 학생|책에 연필로 표시하는 손|도서관에서 자료를 보는 네 학생|교실 책상에서 필기하는 학생|의자에 기대어 쉬는 모습|책상에서 노트에 글을 쓰는 모습|환경과 이동 수단을 표현한 종이 그림|책상에서 손을 들어 보이는 학생|교실에서 학생들의 학습을 살펴보는 모습|파란 장갑을 낀 두 손|침대에서 쉬고 있는 모습|필기 자료와 간식이 놓인 책상|책과 노트 앞에서 대화하는 두 사람|학교 복도에서 이야기를 나누는 학생들|교재를 펼치고 이야기하는 세 학생|노트북 앞에서 생각하는 모습'''.split('|')
assert len(ALTS) == 90
SOURCES = {
    **render.SOURCES,
    'feedback': ('EEF 학습 피드백 근거 안내', 'https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/feedback'),
    'planning': ('EEF 학습 계획과 자기 점검 안내', 'https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/metacognition-and-self-regulation'),
    'vocabulary': ('British Council 수준별 영어 어휘 자료', 'https://learnenglish.britishcouncil.org/free-resources/vocabulary'),
    'sleep': ('CDC 수면 안내', 'https://www.cdc.gov/sleep/about/'),
    'activity': ('WHO 신체활동 안내', 'https://www.who.int/news-room/fact-sheets/detail/physical-activity'),
    'adiga': ('대입정보포털 어디가', 'https://www.adiga.kr/'),
}
# Direct references are attached to the specific section they support.
REFERENCES = {1:(4,'styles'), 2:(6,'support'), 4:(5,'learning'), 5:(5,'planning'),
              8:(6,'support'), 9:(3,'feedback'), 11:(6,'sleep'), 12:(4,'learning'),
              13:(2,'adiga'), 21:(6,'planning'), 22:(6,'vocabulary'), 25:(6,'sleep'),
              29:(5,'activity'), 30:(5,'learning')}

def read_articles(selection):
    records=[]
    blocks=(ROOT/'tools/education_expansion_20261006.txt').read_text(encoding='utf-8').split('@@ ')[1:]
    for block in blocks:
        lines=block.strip().splitlines()
        n,slug,title,description,group,stages,subjects=lines[0].split('|')
        n=int(n)
        item={'batch':'20261006','batchIndex':n,'expansionIndex':60+n,'sourceIndex':60+n-1,
              'slug':slug,'title':title,'description':description,'group':view.GROUPS[int(group)],
              'stages':list(stages),'subjects':subjects.split('·') if subjects else [],
              'lead':lines[1],'sections':[],'task':None,'faq':[],
              'sources':[REFERENCES[n][1]] if n in REFERENCES else [],
              'route':'/교육정보/'+slug+'/', 'sourceTitle':selection['pages'][n-1]['sourceTitle']}
        for line in lines[2:]:
            if line.startswith('## '):item['sections'].append([line[3:],''])
            elif line.startswith('>> '):item['task']=[line[3:],[]]
            elif line.startswith('- '):item['task'][1].append(line[2:])
            elif line.startswith('?? '):item['faq'].append(line[3:].split('|'))
            elif line.strip():item['sections'][-1][1]+=line
        assert len(item['sections'])==6 and len(item['task'][1])==4 and len(item['faq'])==2,n
        assert len(description)<=80 and description.endswith('.') and all(len(p)>=100 for _,p in item['sections']),n
        records.append(item)
    assert len(records)==30 and len({a['route'] for a in records})==30
    return records

def recommend(fresh,previous,context,name):
    stage=context.get('stage');subject=context.get('subject')
    allowed=lambda a:(not stage or stage in a['stages']) and (not subject or not a['subjects'] or subject in a['subjects'])
    current=[a for a in fresh if allowed(a)];old=[a for a in previous if allowed(a)]
    seed=int(hashlib.sha256(name.encode()).hexdigest()[:12],16)
    rng=random.Random(seed);rng.shuffle(current);rng.shuffle(old)
    direct=[a for a in current if subject and subject in a['subjects']]
    result=direct[:1]
    for a in current:
        if a not in result:result.append(a)
        if len(result)==2:break
    result+=old[:1]
    assert len(result)==3
    return result

def publish_article(article, all_articles):
    render.article(article, all_articles)
    name=article['route'].lstrip('/')+'index.html'
    file=ROOT/name;text=file.read_text(encoding='utf-8')
    route='/학습커리큘럼/'
    if len(article['stages'])==1:
        route+={'초':'초등','중':'중등','고':'고등'}[article['stages'][0]]+'/'
        if len(article['subjects'])==1:route+=article['subjects'][0]+'/'
    assert (ROOT/route.lstrip('/')/'index.html').is_file(),route
    anchor=view.ui.link('/교재안내/','영어·수학 교재 살펴보기')
    assert text.count(anchor)==1
    text=text.replace(anchor,view.ui.link(route,'학년·과목별 공부 계획')+anchor,1)
    view.ui.write(file,text)

def preserve_hub_connections(text, before):
    blocks=list(re.finditer(r'<!-- curriculum-links:(\w+):start -->[\s\S]*?<!-- curriculum-links:\1:end -->',before))
    for block in blocks:
        anchor='<link rel="stylesheet" href="/assets/site-shell.css">' if block[1]=='style' else '<nav class="ei-groups"'
        assert text.count(anchor)==1
        text=text.replace(anchor,block[0]+anchor,1)
    return text

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args();out=args.audit
    previous=view.load(out/'before-education-info-data.json')
    selection=view.load(out/'source-selection.json');photos=view.load(out/'selected-images.json')
    baseline=view.load(out/'before-release-public-manifest.json')
    assert len(previous['articles'])==60 and len(photos)==90
    fresh=read_articles(selection)
    assert not ({a['sourceTitle'] for a in fresh}&{a['sourceTitle'] for a in previous['articles']})
    assert not any((ROOT/(a['route'].lstrip('/')+'index.html')).exists() for a in fresh)
    render.DAY=DAY;view.ui.DAY=DAY;render.SOURCES.update(SOURCES)
    render.REFERENCES={60+n:v for n,v in REFERENCES.items()}
    assets=[];image_rows=[]
    # Keep the random image set; put the environmental illustration beside cross-subject learning.
    photos[39],photos[80]=photos[80],photos[39]
    for i,row in enumerate(photos):
        source=Path(row['file']);assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
        name=f'assets/education-info/20261006-{i+1:03}.webp';dest=ROOT/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with Image.open(source) as original:
            im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((1200,1200),Image.Resampling.LANCZOS);im.save(dest,'WEBP',quality=82,method=6)
            img={'src':'/'+name,'alt':ALTS[i],'width':im.width,'height':im.height,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
        image_rows.append(img);assets.append(name)
    for i,a in enumerate(fresh):
        a['images']=image_rows[i*3:i*3+3]
        assert len({im['sha256'] for im in a['images']})==3,a['title']
    all_articles=fresh+previous['articles']
    for a in fresh:publish_article(a,all_articles)
    before_hub=(ROOT/'교육정보/index.html').read_text(encoding='utf-8')
    render.hub(all_articles)
    hub_file=ROOT/'교육정보/index.html'
    view.ui.write(hub_file,preserve_hub_connections(hub_file.read_text(encoding='utf-8'),before_hub))
    modules=[];usage=Counter();changed=[]
    for record in previous['existingPages']:
        item=copy.deepcopy(record);name=item['file'];module=item['module']
        if not module:modules.append(item);continue
        old=(ROOT/name).read_text(encoding='utf-8')
        if name=='index.html':
            featured=[next(a for a in fresh if a['group']==g) for g in view.GROUPS]
            body='<section class="ei-home" id="home-education" aria-labelledby="home-education-title"><p class="ei-kicker">학생과 학부모를 위한 교육정보</p><h2 id="home-education-title">지금 필요한 공부와 학습 대화</h2><p>수행평가 준비와 과목별 복습, 학습 계획과 부모의 대화를 실천 순서와 점검표로 살펴보세요.</p><div class="ei-related-grid">'+''.join(view.ui.link(a['route'],a['title']) for a in featured)+'</div>'+view.actions([('/교육정보/','교육정보 90편 살펴보기',True)])+'</section>'
            text=render.replace_block(old,'home',body)
        else:
            featured=recommend(fresh,previous['articles'],module['context'],name)
            subject=module['context'].get('subject','')
            title=(subject+' ' if subject else '')+'공부와 수업 선택에 도움이 되는 교육정보'
            text=render.replace_block(old,'module',view.related(featured,title))
        assert view.strip(old)==view.strip(text),name
        module['links']=[a['route'] for a in featured];usage.update(module['links'])
        view.ui.write(ROOT/name,text);changed.append(name);modules.append(item)
    assert all(usage[a['route']]>0 for a in fresh)
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';sitemap=etree.parse(str(ROOT/'sitemap.xml')).getroot()
    modified={view.route(n) for n in changed}|{'/교육정보/'}
    for entry in sitemap:
        if unquote(urlsplit(entry.find('{'+ns+'}loc').text).path) in modified:
            date=entry.find('{'+ns+'}lastmod')
            if date is None:date=etree.SubElement(entry,'{'+ns+'}lastmod')
            date.text=DAY
    for a in fresh:
        entry=etree.SubElement(sitemap,'{'+ns+'}url');etree.SubElement(entry,'{'+ns+'}loc').text=view.ui.url(a['route']);etree.SubElement(entry,'{'+ns+'}lastmod').text=DAY
    (ROOT/'sitemap.xml').write_bytes(etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True))
    rss=etree.parse(str(ROOT/'rss.xml')).getroot();channel=rss.find('channel');date='Tue, 06 Oct 2026 00:00:00 +0900';channel.find('lastBuildDate').text=date
    for a in reversed(fresh):
        item=etree.Element('item')
        for key,value in [('title',a['title']),('link',view.ui.url(a['route'])),('guid',view.ui.url(a['route'])),('description',a['description']),('pubDate',date)]:
            node=etree.SubElement(item,key);node.text=value
            if key=='guid':node.set('isPermaLink','true')
        channel.insert(5,item)
    (ROOT/'rss.xml').write_bytes(etree.tostring(rss,encoding='utf-8',xml_declaration=True,pretty_print=True))
    llms=(ROOT/'llms.txt').read_text(encoding='utf-8')+'\n\n## 학생의 실천과 학부모의 학습 대화\n\n'+''.join('- '+a['title']+': '+view.ui.DOMAIN+a['route']+'\n' for a in fresh)
    view.ui.write(ROOT/'llms.txt',llms)
    view.save(ROOT/'seo-descriptions.json',view.ui.DESCRIPTIONS)
    shell=view.load(ROOT/'site-shell-data.json');shell['pages']=sorted(set(shell['pages'])|set(view.ui.NEW));view.save(ROOT/'site-shell-data.json',shell)
    expansion={'date':DAY,'selectedFolders':30,'routes':[a['route'] for a in fresh]}
    data={**previous,'version':3,'selectedFolders':90,'articles':all_articles,'newPages':sorted(set(previous['newPages'])|set(view.ui.NEW)),'existingPages':modules,'images':previous['images']+image_rows,'expansion':expansion,'expansionHistory':previous.get('expansionHistory',[previous['expansion']])+[expansion]}
    view.save(ROOT/'education-info-data.json',data)
    home=view.load(ROOT/'home-library-data.json');home['educationCount']=90;home['updated']=DAY;view.save(ROOT/'home-library-data.json',home)
    provenance={'date':DAY,'seed':selection['seed'],'eligibleUnusedFolders':selection['eligible'],
        'pages':[{'route':a['route'],'sourceTitle':a['sourceTitle'],'sourceFingerprint':s['fingerprint'],'sourceFiles':[{'name':Path(f['file']).name,'sha256':f['sha256'],'encoding':f['encoding']} for f in s['files']], 'images':[{'name':Path(p['file']).name,'sha256':p['sha256']} for p in photos[i*3:i*3+3]]} for i,(a,s) in enumerate(zip(fresh,selection['pages']))]}
    view.save(ROOT/'education-info-expansion-20261006.json',provenance)
    names=sorted(set(changed+view.ui.NEW+assets+['sitemap.xml','rss.xml','llms.txt']))
    audit={'date':DAY,'articlesAdded':30,'articleTotal':90,'imagesAdded':90,'sourceSeed':selection['seed'],'relatedModules':len(changed),'incomingLinks':dict(usage),'changedPublicFiles':names,'newRoutes':[a['route'] for a in fresh]}
    view.save(out/'upgrade-audit.json',audit);render.refresh_manifest(baseline,names)
    print(json.dumps({k:audit[k] for k in ['articlesAdded','articleTotal','imagesAdded','relatedModules']},ensure_ascii=False))

if __name__=='__main__':main()

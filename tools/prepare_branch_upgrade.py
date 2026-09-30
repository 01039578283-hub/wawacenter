"""Read owner-supplied sources; freeze facts and optimized, attributed photos.

Run locally with --source, --reference-data and --audit. Raw workbooks, internal
notes and original photos are never included in the public release manifest.
"""
import argparse, csv, hashlib, json, re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from lxml import html
from openpyxl import load_workbook
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = ['국어','영어','수학','과학','사회']
DAY = '2026-10-01'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def text(el): return ' '.join(el.text_content().split())
def cls(doc, name): return doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+name+' ")]')
def grades(v): return re.findall(r'초[1-6]|중[1-3]|고[1-3]', str(v or ''))
def location(address, fallback_region, fallback_district):
    regions={'서울특별시':'서울','서울':'서울','경기도':'경기','경기':'경기','인천광역시':'인천','인천':'인천','부산광역시':'부산','부산':'부산','대구광역시':'대구','대구':'대구','광주광역시':'광주','광주':'광주','대전광역시':'대전','대전':'대전','울산광역시':'울산','울산':'울산','세종특별자치시':'세종','세종':'세종','강원특별자치도':'강원','강원도':'강원','강원':'강원','충청북도':'충북','충북':'충북','충청남도':'충남','충남':'충남','전북특별자치도':'전북','전라북도':'전북','전북':'전북','전라남도':'전남','전남':'전남','경상북도':'경북','경북':'경북','경상남도':'경남','경남':'경남','제주특별자치도':'제주','제주도':'제주','제주':'제주','제주시':'제주'}
    parts=address.split(); region=regions.get(parts[0],fallback_region)
    if region=='세종':district='세종시'
    else:district=next((v for v in parts[1:3] if re.fullmatch(r'[가-힣]+[시군구]',v)),fallback_district)
    assert region in set(regions.values()),address
    return region,district

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--reference-data',type=Path,required=True); ap.add_argument('--audit',type=Path,required=True); args=ap.parse_args()
    source=args.source; audit=args.audit; audit.mkdir(parents=True,exist_ok=True)
    areas=json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8-sig'))['areas']
    raw=list(load_workbook(source/'코칭센터_데이터_.xlsx',read_only=True,data_only=True).active.values)
    codes=list(csv.reader((source/'센터 정보 및 교육비 371개 코드_최신화.csv').open(encoding='utf-8-sig',newline='')))
    refs={c['sourceRow']:c for c in json.loads((args.reference_data/'centers.json').read_text(encoding='utf-8-sig'))['centers']}
    rules=json.loads((args.reference_data/'course-conditions.json').read_text(encoding='utf-8-sig'))['centers']
    grouped=defaultdict(list)
    for a in areas: grouped[(a['region'],a['branch'])].append(a)
    photo_root=source/'센터별 사진'
    common_hashes={sha(p) for p in (photo_root/'1 공용사진').rglob('*') if p.is_file()}
    # Identical files reused across unrelated folders cannot prove a specific room.
    photo_owners=defaultdict(set)
    for folder in photo_root.iterdir():
        if folder.is_dir():
            for p in folder.rglob('*'):
                if p.is_file(): photo_owners[sha(p)].add(folder.name)
    selected_file=ROOT/'tools/branch-photo-selection.json'
    selected=set(json.loads(selected_file.read_text(encoding='utf-8'))['selected']) if selected_file.exists() else None
    branches=[]; checks=[]; photo_evidence=[]
    for (region,branch),group in grouped.items():
        a=next(x for x in group if x['slug']==x['branchRepresentativeSlug'])
        ref=refs[a['sourceRow']]; row=raw[a['sourceRow']-1] if a['sourceRow'] else None
        if row:
            assert row[0]==ref['sourceName'], (branch,'source name')
            for n,s in enumerate(SUBJECTS): assert grades(row[n+16])==ref['subjects'].get(s,[]),(branch,s,'workbook changed')
        rule=rules.get(ref['routeName'],{})
        assert not rule or rule['sourceRow']==a['sourceRow']
        region,district=location(a['address'],region,a['district'])
        name=ref['routeName']; route=f'/지점안내/{region}/{name}/'
        doc=html.fromstring(codes[a['latestCodeRow']-1][0])
        fee_blocks=[]
        for block in cls(doc,'wawa-fee-block'):
            heading=' '.join(block.xpath('.//h3/text()'))
            common='공통 안내' in heading
            if common and (('서울 외' in heading)!=(region!='서울')):continue
            tables=[]
            for table in block.xpath('.//table'):
                tables.append([[text(c) for c in tr.xpath('./th|./td')] for tr in table.xpath('.//tr')])
            notes=[text(p) for p in block.xpath('./p') if text(p)]
            fee_blocks.append({'heading':heading,'kind':'reference' if common else 'branch','tables':tables,'notes':notes})
        # Every neighborhood attached to a branch must agree on location and fees.
        for other in group:
            assert other['address']==a['address'] and other['feeUrl']==a['feeUrl'],(branch,'mapping conflict')
            assert other['grades']==a['grades'],(branch,'grade mapping conflict')
        register={}
        for p in cls(doc,'wawa-register-line'):
            content=text(p)
            for label,key in [('등록 학원명','name'),('등록번호','number'),('운영등록일','date')]:
                if content.startswith(label): register[key]=content[len(label):].lstrip(' :：')
        # Reconcile current V/AE notes as well as the immutable grade cells.
        grade_holds={
            '돈암점':{'*':['초1','초2']},'망포점':{'*':['초1','초2','초3']},
            '수완점':{'국어':['초1','초2'],'영어':['초1','초2'],'수학':['초1','초2']},
            '영통점':{'국어':['초1','초2','초3']},'산남점':{'국어':['고1','고2','고3']},
            '마두점':{'국어':['초1','초2','초3','초4','초5','초6']},
            '상암점':{'국어':['*'],'과학':['*'],'사회':['*']},
            '관평점':{'국어':['고1','고2','고3']},'지족점':{'과학':['*'],'사회':['*']},
        }
        courses=[]
        for s in SUBJECTS:
            entries=[rule.get('subjects',{}).get(k,{}) for k in ['*',s]]
            held={g for entry in entries for g in entry.get('hold',[])}
            held.update(grade_holds.get(name,{}).get('*',[]))
            held.update(grade_holds.get(name,{}).get(s,[]))
            rawgrades=a['grades'][s]
            pending=[g for g in rawgrades if g in held or '*' in held]
            listed=[g for g in rawgrades if g not in pending]
            notes=list(dict.fromkeys(n['text'] for entry in entries for n in entry.get('notes',[])))
            if row and s=='사회' and re.search(r'사회[^\n]*역사\s*&\s*한국사\s*불가',str(row[21] or '')):
                note='역사·한국사는 사회 수업 범위에 포함되지 않습니다.'
                if note not in notes:notes.append(note)
            courses.append({'subject':s,'grades':listed,'pending':pending,'notes':notes})
        # Source-backed additional conditions not expressed in the grade cells.
        extra={
            '가좌점':'초등 저학년은 별도 확인 대상이며, 과목별 최소 수업 횟수도 함께 상담해야 합니다.',
            '장기점':'고등 과학은 물리Ⅰ·화학Ⅰ·생명과학Ⅰ의 지도 여부를 중심으로 문의해 주세요.',
            '산내점':'제공 자료에는 운정고등학교 수업이 제외되어 있습니다. 학교명을 먼저 알려 주세요.',
            '운정점':'제공 자료에는 운정고등학교 수업이 제외되어 있습니다. 학교명을 먼저 알려 주세요.',
            '미사점':'고2·고3은 별도 확인 대상입니다. 사회는 학습코칭 관리 방식으로 안내되어 있습니다.',
            '석사점':'국어·영어·수학은 초4부터의 과정을 먼저 확인해 주세요. 일대일 개인수업으로 안내하지 않습니다.',
            '진월점':'검정고시 준비 과정은 제공 자료의 수업 범위에 포함되지 않습니다.',
            '풍동점':'고2(예비 고3)의 국어·영어·수학은 화상 수업 병행 조건이 기재되어 있습니다. 수업 구성을 먼저 상담해 주세요.',
            '단구점':'국어의 한글 입문·고등 논술과 과학의 물리는 제외되어 있습니다. 과학은 통합과학·화학Ⅰ·생명과학Ⅰ·지구과학Ⅰ 범위를 먼저 확인해 주세요.',
            '덕이점':'국어는 한글 입문 수업과 구분해 상담해 주세요. 제공 자료에는 한글 수업이 제외되어 있습니다.',
            '마두점':'국어는 중·고등 내신 중심으로 기재되어 있으며, 수리논술은 수학 지도 범위에 포함되지 않습니다.',
            '삼송점':'국어의 한글·문해력·내신 지도와 전문 논술 수업은 구분됩니다. 전문 논술은 제공된 운영 범위에서 제외되어 있습니다.',
            '원흥점':'국어는 교과 수업 중심으로 안내되어 있습니다. 독서지도와 논술은 해당 수업 범위에서 제외되어 있습니다.',
            '갈매점':'고2·고3 사회는 강의식 교습이 아닌 시험 대비 관리 방식으로 기재되어 있습니다.',
            '인창점':'국어의 독서지도와 한글 입문 수업을 구분해 주세요. 한글 입문은 제공 자료에서 제외되어 있습니다.',
            '평내점':'학생 진단과 보호자 상담의 진행 순서가 구분되어 있습니다. 첫 방문 전 전화 상담으로 학생 테스트와 보호자 방문 일정을 확인해 주세요.',
            '반달점':'고3 과학은 물리·생물 중심으로 기재되어 있으며 화학·지구과학은 제외되어 있습니다. 희망 선택 과목을 먼저 알려 주세요.',
            '상동점':'국어의 한글 입문 수업은 제공 자료의 지도 범위에 포함되지 않습니다.',
            '위례점':'고등 공부9도를 선택하는 경우 주말 수업 조건이 기재되어 있습니다. 과목 수업과 추가 프로그램의 일정을 구분해 확인해 주세요.',
            '이매점':'과학은 생명과학·화학 범위로 기재되어 있습니다. 학교에서 선택한 과목과 진도를 먼저 확인해 주세요.',
            '망포점':'초등은 4학년부터의 과정으로 기재되어 있습니다. 중3 이상은 학습 시간 조건을 함께 상담해 주세요.',
            '영통점':'국어는 한글 입문·초등 저학년 수업과 구분됩니다. 해당 과정은 제공 자료에서 제외되어 있습니다.',
            '호매실점':'학년에 따라 최소 수업 구성에 차이가 있습니다. 토요일은 국어 중심으로 기재되어 있으므로 희망 요일과 과목을 함께 확인해 주세요.',
            '장곡점':'최소 수업 구성은 초등 3타임 이상, 중·고등 4타임 이상으로 기재되어 있습니다. 타임당 시간과 주당 등원 횟수를 함께 상담해 주세요.',
            '옥정점':'고등 과학은 물리Ⅰ·화학Ⅰ·생명과학Ⅰ·지구과학Ⅰ 범위로 기재되어 있습니다. 다른 선택 과목은 별도로 확인해야 합니다.',
            '세교점':'영어·수학은 과목별 주 3회부터의 구성으로 안내되어 있습니다. 실제 시간표와 비용을 함께 확인해 주세요.',
            '하남풍산점':'고등 영어·수학은 학년과 선택 과목에 따라 필요한 수업 타임이 다릅니다. 특히 고2 수학은 동시 수강 과목과 학습량을 함께 상담해 주세요.',
            '동탄호수점':'사회는 관리형 과정으로 기재되어 있습니다. 직접 교습과 구분해 학습 진행 방식을 확인해 주세요.',
            '반송점':'초등 저학년은 오후 2~3시 사이 수업 조건이 기재되어 있습니다. 현재 가능한 등원 시간을 먼저 확인해 주세요.',
            '복현점':'초등은 오후 3~5시 수업 시간대로 기재되어 있습니다. 다른 시간에 등원해야 한다면 별도로 문의해 주세요.',
            '수성만촌점':'과목당 4타임 이상의 수업 구성이 기재되어 있습니다. 학생의 학년과 과목을 기준으로 시간과 비용을 상담해 주세요.',
            '도안점':'고등 과학은 공통 과정과 물리Ⅰ·Ⅱ 중심으로 기재되어 있습니다. 희망 선택 과목의 지도 범위를 먼저 확인해 주세요.',
            '삼각산점':'고등 과학은 Ⅰ과목 범위로 기재되어 있으며, Ⅱ과목은 제공 자료의 수업 범위에서 제외되어 있습니다.',
            '하계점':'고2 이상의 과학은 화학 중심으로 기재되어 있습니다. 선택 과목을 먼저 알려 주세요.',
            '돈암점':'초등은 3학년부터의 과정으로 기재되어 있습니다. 저학년의 현재 개설 여부는 별도로 확인해 주세요.',
            '남외점':'국어의 한글 입문과 독서 수업은 제공 자료에서 제외되어 있습니다. 교과 과정의 학년과 지도 범위를 확인해 주세요.',
            '산남점':'국어는 중등까지의 지도 범위로 기재되어 있습니다. 고등 국어는 현재 개설 여부를 별도로 확인해야 합니다.',
            '관평점':'국어는 중등까지의 센터 수업으로 기재되어 있습니다. 고등 국어는 센터 수업만으로 가능한 과정과 구분해 상담해 주세요.',
            '탕정점':'과학은 통합과학·물리의 지도 범위를 먼저 확인해 주세요. 화학Ⅰ·Ⅱ는 제공 자료에서 제외되어 있습니다.',
        }
        notes=[n['text'] for n in rule.get('notes',[])]
        if name in extra:notes.append(extra[name])
        # Join school references by neighborhood, without making enrollment claims.
        schools={s:list(dict.fromkeys(school for x in group for school in x['schools'][s])) for s in ['초','중','고']}
        schools={s:[v for v in vs if not re.search(r'후보|확인|기타|특성화고$|모든|[\[\]]',v)] for s,vs in schools.items()}
        media_doc=html.parse(str(ROOT/f'전국센터/{a["slug"]}/index.html'))
        image=media_doc.xpath('//img[contains(@src,"assets/centers/common/")]')[0]
        body_src='/'+unquote(urlsplit(urljoin('https://site.test/전국센터/'+a['slug']+'/',image.get('src'))).path).lstrip('/')
        with Image.open(ROOT/body_src.lstrip('/')) as im:body_size=list(im.size)
        picture_ancestors=image.xpath('ancestor::picture[1]')
        body_picture=picture_ancestors[0] if picture_ancestors else image
        # Resolve the existing, protected responsive source, without altering pixels.
        mobile=body_picture.xpath('.//source/@srcset') if body_picture.tag=='picture' else []
        mobile_src=None
        if mobile:
            mobile_src=unquote(urlsplit(urljoin('https://site.test/전국센터/'+a['slug']+'/',mobile[0].split()[0])).path)
        photos=[]; folder=photo_root/ref['sourceName']
        candidates=[]
        if folder.exists():
            for p in sorted(folder.rglob('*')):
                if p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:continue
                h=sha(p)
                if h in common_hashes or len(photo_owners[h])>1:continue
                try:
                    with Image.open(p) as im:
                        if min(im.size)<200:continue
                    candidates.append(p)
                except OSError:continue
        # Keep a small, stable gallery; mark absent branch photos explicitly.
        for i,p in enumerate(candidates,1):
            base=ROOT/'assets/branch-photos'/region/name/f'photo-{i:02}'
            large_path='/'+base.with_name(base.name+'-1200.webp').relative_to(ROOT).as_posix()
            if selected is not None and large_path not in selected:continue
            if selected is None and i>4:break
            base.parent.mkdir(parents=True,exist_ok=True)
            sizes={}
            with Image.open(p) as original:
                clean=ImageOps.exif_transpose(original).convert('RGB')
                for width in [640,1200]:
                    output=base.with_name(base.name+f'-{width}.webp')
                    im=clean.copy(); im.thumbnail((width,width))
                    if not output.exists():im.save(output,'WEBP',quality=80,method=4)
                    sizes[width]={'src':'/'+output.relative_to(ROOT).as_posix(),'width':im.width,'height':im.height}
            photos.append({'small':sizes[640],'large':sizes[1200]})
            photo_evidence.append({'branch':route,'source':str(p),'sha256':sha(p),'outputs':sizes})
        b={'route':route,'name':name,'displayName':branch,'sourceName':ref['sourceName'],'region':region,'district':a['district'],'address':a['address'],'addressPending':a['addressStatus']=='주소 재확인 필요','registration':a['registration'],'registeredName':register.get('name',ref.get('registeredName','')),'registrationDate':register.get('date',ref.get('registrationDate','')),'feeUrl':a['feeUrl'],'fees':fee_blocks,'courses':courses,'courseNotes':list(dict.fromkeys(notes)),'schools':schools,'areas':[{'slug':x['slug'],'name':x['area']} for x in group],'representative':a['slug'],'sourceRow':a['sourceRow'],'latestCodeRows':[x['latestCodeRow'] for x in group],'photos':photos,'bodyImage':{'src':body_src,'width':body_size[0],'height':body_size[1],'mobile':mobile_src},'missingSource':a['missingSource']}
        b['district']=district
        assert b['feeUrl'].startswith('https://drive.google.com/'),(name,'fee URL')
        branches.append(b)
        checks.append({'branch':route,'sourceRow':a['sourceRow'],'ruleCells':rule.get('cells',[]),'rawNoteHash':hashlib.sha256(json.dumps([row[n] for n in [21,27,28,29,30]],ensure_ascii=False,default=str).encode()).hexdigest() if row else None})
    assert len(branches)==188 and sum(len(b['areas']) for b in branches)==371
    assert len({b['route'] for b in branches})==188
    hashes={p.name:sha(p) for p in source.iterdir() if p.is_file()}
    selected_file=ROOT/'tools/branch-photo-selection.json'
    if selected_file.exists():
        selected=set(json.loads(selected_file.read_text(encoding='utf-8'))['selected'])
        for b in branches:b['photos']=[p for p in b['photos'] if p['large']['src'] in selected]
        assert selected=={p['large']['src'] for b in branches for p in b['photos']},'Reviewed photo mapping changed'
    for b in branches:
        if '모두' in b['registeredName']:b['displayName']='모두오름학습코칭학원 '+b['name']
    result={'reviewedAt':DAY,'sourceHashes':hashes,'branches':sorted(branches,key=lambda b:(b['region'],b['district'],b['name']))}
    save(ROOT/'branch-directory-data.json',result)
    save(audit/'source-review.json',{'hashes':hashes,'checks':checks,'photos':photo_evidence})
    print(json.dumps({'branches':len(branches),'areas':371,'regions':len({b['region'] for b in branches}),'photos':len(photo_evidence),'branchFeeTables':sum(any(f['kind']=='branch' for f in b['fees']) for b in branches),'pendingAddresses':[b['route'] for b in branches if b['addressPending']]},ensure_ascii=False))

if __name__=='__main__':main()

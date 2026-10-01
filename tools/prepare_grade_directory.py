"""Consolidate all supplied area drafts into one page per actual branch/stage."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
from grade_editorial import TOPICS
ROOT=Path(__file__).resolve().parents[1]
LABELS={'초':'초등학생학원','중':'중학생학원','고':'고등학생학원'}
def normalize(s):return re.sub(r'\s+','',s)
def applies(note,prefix):
    stages={m.group(1) for m in re.finditer(r'([초중고])(?:[1-6]|등|학생|학교)',note)}
    for combined in re.findall(r'[초중고]{2,}',note):stages.update(combined)
    return not stages or prefix in stages
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
    records=json.loads((args.audit/'manuscript-records.json').read_text(encoding='utf-8'))
    facts=json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'))
    areas=json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'))['areas']
    names={normalize(n):a['slug'] for a in areas for n in [a['slug'],a['area']]}
    branches={a['slug']:b for b in facts['branches'] for a in b['areas']}
    grouped=collections.defaultdict(list)
    for r in records:
        name=normalize(Path(r['file']).stem).removesuffix(r['category'])
        assert name in names,(r['file'],name)
        grouped[(names[name],r['category'])].append(r)
    pages=[];evidence=[];repeated=0
    for a in areas:
        b=branches[a['slug']]
        for prefix,label in LABELS.items():
            source=sorted(grouped[(a['slug'],label)],key=lambda x:x['archive'])
            assert len(source)==3
            seen=set();segments=[]
            for r in source:
                body=r['text'].split('[본문]',1)[-1]
                body=re.split(r'\[(?:FAQ|학부모후기|상담 상황 예시|JSON-LD|구조화)',body)[0]
                for p in re.split(r'\n\s*\n',body):
                    p=p.strip()
                    if not p or p.startswith('##'):continue
                    key=normalize(p)
                    if key in seen:repeated+=1
                    else:seen.add(key);segments.append(p)
            # Openings contain the supplied student concerns. Unverified facility
            # names, generated reviews, grade labels and outcome claims are not copied.
            openings=[r['text'].split('[본문]',1)[-1].split('##',1)[0] for r in source]
            profiles=' '.join(openings)
            scores=[]
            for index,(key,title,pattern,copy,record,question) in enumerate(TOPICS):
                hits=[m.start() for m in re.finditer(pattern,profiles)]
                # Specific concerns outrank generic mentions repeated in every draft.
                weight=1 if key in ['priority','progress-review','error-revisit','math-explain','math-independent'] else 3
                score=len(hits)*weight + (1/(1+min(hits)) if hits else 0)
                if hits:scores.append((score,index))
            selected=[TOPICS[index][0] for _,index in sorted(scores,reverse=True)[:5]]
            assert len(selected)>=3,(a['slug'],prefix)
            # A short collection of concrete questions uses all three drafts without
            # reproducing long template paragraphs or claiming real student cases.
            selected=selected[:4]
            route=b['route']+label+'/'
            current=[{'subject':c['subject'],'grades':[g for g in c['grades'] if g.startswith(prefix)],'pending':[g for g in c['pending'] if g.startswith(prefix)],'notes':[n for n in c['notes'] if applies(n,prefix)]} for c in b['courses']]
            pages.append({'area':a['slug'],'name':a['area'],'prefix':prefix,'category':label,'route':route,'hub':b['route'],'previousRoute':f'/지점안내/{b["region"]}/{a["slug"]}/{a["slug"]}{label}/','previousHub':f'/지점안내/{b["region"]}/{a["slug"]}/','branch':b['route'],'region':b['region'],'courses':current,'courseNotes':[n for n in b['courseNotes'] if applies(n,prefix)],'schools':a['schools'].get(prefix,[]),'topics':selected,'sources':[{'archive':r['archive'],'file':r['file'],'sha256':r['sha256']} for r in source]})
            evidence.append({'route':route,'paragraphsAfterExactDedup':len(segments),'selectedTopics':selected,'openingEvidence':openings,'sources':pages[-1]['sources']})
    area_pages=pages;pages=[]
    assert len(area_pages)==1113
    for b in facts['branches']:
        for prefix,label in LABELS.items():
            group=[p for p in area_pages if p['branch']==b['route'] and p['prefix']==prefix]
            assert len(group)==len(b['areas'])
            first=group[0]
            pages.append({**first,'area':b['representative'],'name':b['name'],
                'areas':[{'area':p['area'],'name':p['name'],'schools':p['schools'],'topics':p['topics']} for p in group],
                'schools':list(dict.fromkeys(s for p in group for s in p['schools'])),
                'topics':list(dict.fromkeys(t for p in group for t in p['topics'])),
                'sources':[s for p in group for s in p['sources']]})
    assert len(pages)==564 and len({p['route'] for p in pages})==564
    public={'reviewedAt':'2026-10-01','baseCommit':'b1376f813badd60aac5bd0b1fe64a0fdff7734d6','sourceHashes':facts['sourceHashes'],'archiveHashes':{x['archive']:x['sha256'] for x in json.loads((args.audit/'input-inspection.json').read_text(encoding='utf-8'))['archives']},'areaPages':area_pages,'pages':pages}
    (ROOT/'grade-directory-data.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.audit/'editorial-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'manuscripts':len(records),'mergedPages':len(pages),'branches':len(facts['branches']),'areas':len(areas),'exactRepeatedParagraphsRemoved':repeated,'topicCoverage':len(set(t for p in pages for t in p['topics']))},ensure_ascii=False))
if __name__=='__main__':main()

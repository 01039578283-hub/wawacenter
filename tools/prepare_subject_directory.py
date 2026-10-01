"""Merge the exact 12 supplied ZIP inventories into actual branch destinations."""
import argparse,collections,hashlib,json,re
from pathlib import Path
from subject_editorial import TOPICS
from prepare_grade_directory import applies
ROOT=Path(__file__).resolve().parents[1]
LABELS={'초':'초등학생학원','중':'중학생학원','고':'고등학생학원'}
FAMILIES={'en-phonics':'phonics','sound-reading':'phonics','en-structure':'structure','grammar-transfer':'structure','en-paraphrase':'writing','sentence-order':'writing','math-start':'first-equation','math-variable':'first-equation','math-explain':'reasoning','math-proof':'reasoning','math-error':'calculation','math-negative':'calculation','load':'workload','priority':'workload','materials':'school','school-alignment':'school'}
def merged_topics(entries,subject):
 result=[];families=set()
 for a in entries:
  for key in a['topics']:
   family=FAMILIES.get(key,key)
   if family not in families:result.append(key);families.add(family)
 # The opening should answer the specific subject query before general planning.
 specific=next(k for k in result if next(t for t in TOPICS if t[0]==k)[1]==subject)
 return [specific]+[k for k in result if k!=specific]
def norm(s):return re.sub(r'\s+','',s)
def ranked(record,stage,subject):
 text=record['body'].replace('\r\n','\n').replace('\r','\n')
 body=re.split(r'\[(?:FAQ|학부모후기|JSON-LD|구조화)',text.split('[본문]',1)[-1])[0]
 headings=re.findall(r'^##\s+(.+)$',body,re.M)
 first=body.split('##',1)[0]+' '+' '.join(headings[:2])
 scores=[]
 for index,t in enumerate(TOPICS):
  if stage not in t[2] or t[1] and t[1]!=subject:continue
  hits=list(re.finditer(t[4],first));allhits=list(re.finditer(t[4],body))
  if not allhits:continue
  # Specific learning concerns rank before broad words in every template.
  factor=(3 if index<30 else 1.1) if t[1] else .65
  score=(min(len(hits),5)*8+min(len(allhits),8))*factor
  score+=sum(bool(re.search(t[4],h)) for h in headings[:2])*20*factor
  if hits:score+=1/(1+hits[0].start())
  scores.append((score,-index,t[0]))
 return [k for _,_,k in sorted(scores,reverse=True)],body,first
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 drafts=json.loads((args.audit/'manuscript-records.json').read_text(encoding='utf-8'))
 facts=json.loads((ROOT/'branch-directory-data.json').read_text(encoding='utf-8'))
 areas=json.loads((ROOT/'area-reference.json').read_text(encoding='utf-8'))['areas']
 names={norm(n):a['slug'] for a in areas for n in [a['slug'],a['area']]}
 groups=collections.defaultdict(list);evidence=[];repeats=0;paragraphs=0
 for r in drafts:
  name=norm(r['filename'].split('/')[-1]).removesuffix('.txt').removesuffix(r['stage']+'등학생'+r['subject']+'학원')
  # 중학생 has no 등; other stages do.
  if name not in names:name=norm(r['filename'].split('/')[-1]).removesuffix('.txt').removesuffix(LABELS[r['stage']].removesuffix('학원')+r['subject']+'학원')
  assert name in names,(r['filename'],name)
  groups[(names[name],r['stage'],r['subject'])].append(r)
 assert len(groups)==2226 and all(len(v)==2 for v in groups.values())
 pages=[]
 for b in facts['branches']:
  for stage,label in LABELS.items():
   for subject in ['수학','영어']:
    route=b['route']+label+'/'+subject+'/'
    entries=[];sources=[]
    for a in b['areas']:
     rr=sorted(groups[a['slug'],stage,subject],key=lambda r:(not r['archive'].startswith('프로그램'),r['archive']))
     selected=[];seen=set();trace=[];families=set()
     for r in rr:
      ranked_ids,body,opening=ranked(r,stage,subject)
      assert len(ranked_ids)>=4,(a,stage,subject)
      accepted=0
      for k in ranked_ids:
       family=FAMILIES.get(k,k)
       if family not in families:selected.append(k);families.add(family);accepted+=1
       if accepted==6:break
      for para in re.split(r'\n\s*\n',body):
       key=norm(para)
       if not key or key.startswith('##'):continue
       paragraphs+=1
       if key in seen:repeats+=1
       seen.add(key)
      sources.append({k:r[k] for k in ['archive','filename','sha256']})
      trace.append({'source':sources[-1],'openingEvidence':opening,'rankedTopics':ranked_ids[:8]})
     ar=next(x for x in areas if x['slug']==a['slug'])
     entries.append({'slug':a['slug'],'name':a['name'],'schools':ar['schools'].get(stage,[]),'topics':selected})
     evidence.append({'route':route,'area':a['slug'],'sources':trace,'selectedTopics':selected,'paragraphsAfterDedup':len(seen)})
    course=next(c for c in b['courses'] if c['subject']==subject)
    pages.append({'route':route,'parent':b['route']+label+'/','branch':b['route'],'stage':stage,'subject':subject,'areas':entries,'schools':list(dict.fromkeys(s for a in entries for s in a['schools'])),'topics':merged_topics(entries,subject),'course':{'subject':subject,'grades':[g for g in course['grades'] if g.startswith(stage)],'pending':[g for g in course['pending'] if g.startswith(stage)],'notes':[n for n in course['notes'] if applies(n,stage)]},'courseNotes':[n for n in b['courseNotes'] if applies(n,stage)],'sources':sources})
 assert len(pages)==1128 and len({p['route'] for p in pages})==1128
 assert sum(len(p['sources']) for p in pages)==4452
 inventory=json.loads((args.audit/'input-inspection.json').read_text(encoding='utf-8'))
 obj={'reviewedAt':'2026-10-01','baseCommit':'b653e69b50f54fd33fa357f644dd993564f3a3e3','sourceHashes':facts['sourceHashes'],'archiveHashes':{i['archive']:i['sha256'] for i in inventory},'pages':pages}
 (ROOT/'subject-directory-data.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (args.audit/'editorial-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'sourceDrafts':len(drafts),'areaGroups':len(groups),'newPages':len(pages),'exactRepeatedParagraphsRemoved':repeats,'sourceParagraphs':paragraphs,'topics':len(set(t for p in pages for t in p['topics'])),'topicCountRange':[min(len(p['topics']) for p in pages),max(len(p['topics']) for p in pages)]}))
if __name__=='__main__':main()

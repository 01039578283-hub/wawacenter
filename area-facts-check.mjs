/** Reject regenerated pages that lose the reviewed branch/subject relationships. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const reference=JSON.parse(fs.readFileSync(new URL('./area-reference.json',import.meta.url),'utf8'));
const areas=new Map(reference.areas.map(r=>[r.slug,r]));
const subjects={국어:'korean',영어:'english',수학:'math',과학:'science',사회:'social'};
const levels={초:'elementary',중:'middle',고:'high'};
function* nodes(value) {
  if(Array.isArray(value))for(const item of value)yield* nodes(item);
  else if(value&&typeof value==='object'){yield value;for(const item of Object.values(value))yield* nodes(item);}
}
export function assertAreaFacts(html,name) {
  const parts=name.split('/');
  const isSubject=parts[0]==='과목별학원'&&parts.length===4;
  const isCenter=parts[0]==='전국센터'&&[3,4].includes(parts.length);
  if(!name.endsWith('index.html')||(!isSubject&&!isCenter))return;
  const area=areas.get(parts[isSubject?2:1]);
  if(!area)throw Error('Missing reviewed area: '+name);
  const fail=reason=>{throw Error(`${reason}: ${name}`);};
  const category=isSubject?parts[1]:parts.length===4?parts[2]:'지역학원';
  const wanted=category==='수학학원'?['수학']:category==='영어학원'?['영어']:/영수|영어수학/.test(category)?['영어','수학']:Object.keys(subjects);
  const level=Object.keys(levels).find(p=>category.startsWith(p));
  const section=html.match(/<section\b[^>]*class="[^"]*area-facts-section[^\"]*"[^>]*>([\s\S]*?)<\/section>/)?.[0];
  if(!section)fail('Reviewed facts section missing');
  if(!section.includes(`data-area="${area.slug}"`))fail('Wrong neighborhood');
  const actual=[...section.matchAll(/<div id="([^"]+)" data-subject="([^"]+)" data-grades="([^"]*)">/g)].map(m=>m.slice(1));
  const expected=[];
  for(const subject of wanted)for(const lv of wanted.length===1?Object.keys(levels):[level]){
    const grades=area.grades[subject].filter(g=>!lv||g.startsWith(lv));
    expected.push([wanted.length===1?`${subjects[subject]}-${levels[lv]}`:`subject-${subjects[subject]}`,subjects[subject],grades.join(',')]);
  }
  if(JSON.stringify(actual)!==JSON.stringify(expected))fail('Subject grades differ from reviewed data');
  for(const match of html.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/g)){
    const plain=match[1].replace(/<[^>]+>/g,'');
    if(!plain.includes('가능 학년'))continue;
    const listed=new Set(plain.split('가능 학년')[1].match(/초[1-6]|중[1-3]|고[1-3]/g)||[]);
    if(!listed.size)continue;
    const ss=plain.includes('센터 전체')?Object.keys(subjects):wanted;
    const ranges=ss.map(s=>area.grades[s].filter(g=>!level||g.startsWith(level)));
    const allowed=new Set(ss.length===2&&ss[0]==='영어'&&ss[1]==='수학'?ranges[0].filter(g=>ranges[1].includes(g)):ranges.flat());
    if(listed.size!==allowed.size||[...listed].some(g=>!allowed.has(g)))fail('Outdated body grade statement');
  }
  const branchNodes=[];
  for(const match of html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/g)){
    for(const node of nodes(JSON.parse(match[1]))){
      if(node.address&&JSON.stringify(node['@type']).includes('EducationalOrganization'))branchNodes.push(node);
    }
  }
  if(branchNodes.length!==1)fail('Expected one physical branch');
  const branch=branchNodes[0];
  const id='https://xn--3e0bz50bxucwzc.com/#center-'+createHash('sha256').update(area.branch+'|'+area.address).digest('hex').slice(0,12);
  if(branch['@id']!==id||branch.name!==area.branch||branch.address.streetAddress!==area.address)fail('Branch identity or address differs');
  if(branch.makesOffer)fail('Unverified blanket branch offers');
  if(!section.includes(area.branch)||!section.includes(area.address.replaceAll('&','&amp;')))fail('Branch details not visible');
  if(area.branch.endsWith('위례점')&&(/위례광장로\s*320/.test(html)||/<img\b[^>]*assets\/maps\//.test(html)))fail('Outdated Wirye address or unverified map');
}

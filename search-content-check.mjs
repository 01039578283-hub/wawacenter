/** Keep page intent, readable grouping and existing neighborhood identities. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./search-content-data.json',import.meta.url),'utf8'));
const selected=new Map(data.pages.map(p=>[p.file,p]));
export function assertSearchContent(html,name){
 const p=selected.get(name);if(!p)return;
 const fail=s=>{throw Error(`${name}: content role ${s}`)};
 if(!html.includes(`data-content-role="${p.role}"`))fail('reviewed purpose missing');
 const shared=html.match(/<div class="sc-course-note">([\s\S]*?)<\/div>/)?.[1];
 if(shared&&[...shared.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/g)].some(m=>!/^<strong>(?:국어|영어|수학|과학|사회)/.test(m[1])))fail('shared condition lost its subject');
 if(html.includes('data-subject-branch=')){
  if(!html.includes('id="subject-reading-0"'))fail('subject-specific reading group missing');
  if(/<section data-subject-topic=/.test(html))fail('ungrouped repetitive headings');
  const cards=[...html.matchAll(/<article data-subject-topic="([^"]+)"[\s\S]*?<\/article>/g)];
  if(!cards.length||cards.some(m=>!m[0].includes('<h3 ')||!m[0].includes('<h4>학생 자료에서 해 볼 점검</h4>')))fail('readable topic hierarchy missing');
  if(!html.includes('학생이 실제로 받은 자료'))fail('school-material consultation guidance missing');
 }
}

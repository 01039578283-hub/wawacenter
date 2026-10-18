/** The early summary and machine-readable identity must use the same source facts. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./evidence-content-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.file,p]));
const articles=new Map(data.articles.map(p=>[p.file,p]));
const branches=new Map(JSON.parse(fs.readFileSync(new URL('./branch-directory-data.json',import.meta.url),'utf8')).branches.map(p=>[p.route,p]));
const grades=new Map(JSON.parse(fs.readFileSync(new URL('./grade-directory-data.json',import.meta.url),'utf8')).pages.map(p=>[p.route,p]));
const subjects=new Map(JSON.parse(fs.readFileSync(new URL('./subject-directory-data.json',import.meta.url),'utf8')).pages.map(p=>[p.route,p]));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
const graphOf=html=>[...html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].flatMap(m=>{const x=JSON.parse(m[1]);return x['@graph']||[x];});
const types=n=>[n['@type']].flat();
export function assertEvidenceContent(html,name){
 const fail=why=>{throw Error(`${name}: evidence content: ${why}`);};
 const p=pages.get(name),a=articles.get(name);
 if(!p&&!a)return;
 const graph=graphOf(html);
 if(p){
  const page=graph.find(n=>types(n).includes('WebPage'));
  if(!page?.about?.some(n=>n['@id']===p.orgId))fail('actual branch is not linked to the page');
  const organization=graph.find(n=>types(n).includes('EducationalOrganization')&&n['@id']===p.orgId);
  if(!organization||organization.url!=='https://xn--3e0bz50bxucwzc.com'+encodeURI(p.branch))fail('branch definition or destination differs');
  for(const article of graph.filter(n=>types(n).includes('Article')))
   if(article.author?.name!=='전국수업.com'||article.author?.url!=='https://xn--3e0bz50bxucwzc.com/')fail('unsupported branch authorship');
  if(p.snapshot){
   const matches=[...html.matchAll(/<div class="cf-snapshot" [\s\S]*?<\/dl>[\s\S]*?<a class="cf-details" [\s\S]*?<\/a><\/div>/g)];
   if(matches.length!==1||matches[0].index>html.indexOf('id="lesson-image"'))fail('one visible early summary required');
   const block=matches[0][0],route='/'+name.slice(0,-10);
   const source=subjects.get(route)||grades.get(route)||branches.get(route);
   const courses=source.course?[source.course]:source.courses;
   const known=courses.filter(c=>c.grades.length);
   if((block.match(/<dt>/g)||[]).length!==known.length)fail('unverified subject added');
   for(const c of known)if(!block.includes('<dt>'+esc(c.subject)+'</dt>'))fail('known subject missing');
   // Validate all individual grades, including non-contiguous source ranges.
   const expand=s=>[...s.matchAll(/([초중고])(\d)(?:~[초중고]?(\d))?/g)].flatMap(m=>Array.from({length:Number(m[3]||m[2])-Number(m[2])+1},(_,i)=>m[1]+(Number(m[2])+i)));
   for(const c of known){
    const value=block.match(new RegExp('<dt>'+c.subject+'</dt><dd>([^<]*)</dd>'))?.[1];
    if(JSON.stringify(expand(value||''))!==JSON.stringify(c.grades))fail('grade range differs for '+c.subject);
   }
   for(const c of courses)for(const note of c.notes||[])if(!block.includes(esc(note)))fail('special operating condition omitted');
   if(!block.includes('현재 모집·수업 시간·담당 교사는 별도 확인'))fail('availability confused with source range');
  }
 }
 if(a){
  const form=html.match(/<form class="sr-record" [\s\S]*?<\/form>/g);
  if(form?.length!==1)fail('one topic-specific record required');
  if((form[0].match(/<textarea /g)||[]).length!==a.tasks.length)fail('record field inventory differs');
  for(const task of a.tasks)if(!form[0].includes('data-record-label="'+esc(task)+'"'))fail('article task missing from record');
  if(/\b(?:action|method)=/.test(form[0])||!form[0].includes('전송되거나 자동 저장되지 않습니다'))fail('record must stay local');
  if(!form[0].includes('href="/'+encodeURI(a.blank)+'"'))fail('no-JavaScript blank record missing');
  if(!html.includes('defer src="/assets/study-record.js"'))fail('record interaction missing');
  const article=graph.find(n=>types(n).includes('Article'));
  if(!article?.citation?.length||article.dateModified!==data.updated)fail('article references or modification date missing');
 }
}

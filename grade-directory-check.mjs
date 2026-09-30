/** Guard neighborhood/stage relationships and canonical consolidation. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./grade-directory-data.json',import.meta.url),'utf8'));
const branches=new Map(JSON.parse(fs.readFileSync(new URL('./branch-directory-data.json',import.meta.url),'utf8')).branches.map(b=>[b.route,b]));
const pages=new Map(data.pages.map(p=>[p.route.slice(1)+'index.html',p]));
const hubs=new Map(data.pages.map(p=>[p.hub.slice(1)+'index.html',p.area]));
const alias=new Map(data.pages.map(p=>[`과목별학원/${p.category}/${p.area}/index.html`,p.route]));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("'",'&#x27;');
const path=p=>encodeURI(p);
export function assertGradeDirectory(html,name){
  const fail=s=>{throw Error(`${name}: ${s}`)};
  if(alias.has(name)){
    const canonical=html.match(/<link\b[^>]*rel="canonical"[^>]*href="([^"]+)"/)?.[1];
    if(!canonical||decodeURIComponent(new URL(canonical).pathname)!==alias.get(name))fail('Legacy representative differs');
    if(!html.includes('gd-legacy-note'))fail('Legacy reader link missing');
  }
  if(hubs.has(name)){
    const group=data.pages.filter(p=>p.area===hubs.get(name));
    if(!html.includes(`data-neighborhood-hub="${hubs.get(name)}"`))fail('Neighborhood hub identity differs');
    for(const p of group)if(!html.includes(`href="${path(p.route)}"`))fail('Hub stage destination missing');
  }
  const p=pages.get(name);
  if(!p){
    const b=[...branches.values()].find(b=>b.route.slice(1)+'index.html'===name);
    if(b){
      if(!html.includes('data-grade-entry'))fail('Branch grade entry missing');
      for(const a of b.areas){const target=data.pages.find(p=>p.area===a.slug);if(!html.includes(`href="${path(target.hub)}"`))fail('Branch neighborhood link missing');}
    }
    return;
  }
  const b=branches.get(p.branch);
  if(!html.includes(`data-grade-page="${p.area}" data-stage="${p.prefix}"`))fail('Wrong area or stage');
  for(const c of p.courses){
    const tag=`data-stage-course="${c.subject}" data-grades="${c.grades.join(',')}" data-pending="${c.pending.join(',')}"`;
    if(!html.includes(tag))fail('Confirmed or pending stage grades changed');
    for(const n of c.notes)if(!html.includes(esc(n)))fail('Subject condition missing');
  }
  for(const n of p.courseNotes)if(!html.includes(esc(n)))fail('Stage condition missing');
  for(const value of [b.address,b.registeredName,b.registration])if(!html.includes(esc(value)))fail('Branch fact missing');
  for(const school of p.schools)if(!html.includes(esc(school)))fail('Stage school missing');
  if(!html.includes(`href="${esc(b.feeUrl)}"`))fail('Tuition source missing');
  if(!b.fees.some(f=>f.kind==='branch')&&!html.includes('지점 확정 금액 아님'))fail('Common amount mistaken for branch price');
  if(!html.includes(`href="${path(p.branch)}"`)||!html.includes(`href="${path(p.hub)}"`))fail('Physical branch or parent link missing');
  const topics=[...html.matchAll(/data-editorial-topic="([^"]+)"/g)].map(m=>m[1]);
  if(JSON.stringify(topics)!==JSON.stringify(p.topics))fail('Consolidated concerns differ');
  const image=html.match(/<img\b[^>]*src="[^"]*assets\/centers\/common\/(?:seoul|local)6839\.webp"[^>]*>/)?.[0];
  if(!image||!image.includes('height="16116"')||!image.includes('loading="eager"')||/\bhidden(?:[\s=>])|\bstyle\s*=/.test(image)||!html.includes(path(b.bodyImage.mobile)))fail('Full mobile consultation image lost');
  if(!p.courses.some(c=>c.grades.length)&&!html.includes('개설 학년을 제공 자료에서 확인하지 못했습니다'))fail('Unconfirmed stage must be explicit');
  if(/학부모후기|★★★★★|성적 보장|전교.?등|학원교재실/.test(html))fail('Draft marketing or fictional review leaked');
  if(b.addressPending&&!html.includes('주소 자료가 서로 달라'))fail('Unresolved address lost');
}

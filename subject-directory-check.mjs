/** Preserve exact branch/stage/subject facts and the full consultation image. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./subject-directory-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.route.slice(1)+'index.html',p]));
const branches=new Map(JSON.parse(fs.readFileSync(new URL('./branch-directory-data.json',import.meta.url),'utf8')).branches.map(b=>[b.route,b]));
const parents=new Map();
for(const p of data.pages){const key=p.parent.slice(1)+'index.html';if(!parents.has(key))parents.set(key,[]);parents.get(key).push(p.route);}
const esc=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("'",'&#x27;');
export function assertSubjectDirectory(html,name){
 const fail=s=>{throw Error(`${name}: ${s}`)};
 if(parents.has(name))for(const route of parents.get(name))if(!html.includes(`href="${encodeURI(route)}"`))fail('Subject child link missing');
 const p=pages.get(name);if(!p)return;
 const b=branches.get(p.branch),c=p.course;
 if(!html.includes(`data-subject-branch="${p.branch}" data-stage="${p.stage}" data-subject="${p.subject}"`))fail('Branch/stage/subject mismatch');
 if(!html.includes(`data-subject-course="${p.subject}" data-grades="${c.grades.join(',')}" data-pending="${c.pending.join(',')}"`))fail('Subject-specific grades changed');
 for(const n of [...c.notes,...p.courseNotes])if(!html.includes(esc(n)))fail('Operating condition missing');
 for(const value of [b.address,b.registeredName,b.registration])if(!html.includes(esc(value)))fail('Branch fact missing');
 for(const a of p.areas){if(!html.includes(`data-subject-area="${a.slug}"`))fail('Merged area missing');for(const s of a.schools)if(!html.includes(esc(s)))fail('School reference missing');}
 if(!html.includes(`href="${esc(b.feeUrl)}"`))fail('Tuition source missing');
 if(!b.fees.some(f=>f.kind==='branch')&&!html.includes('지점 확정 금액 아님'))fail('Common fee mistaken for branch price');
 if(!c.grades.length&&!html.includes('개설 학년 확인 필요'))fail('Unconfirmed class presented as available');
 for(const r of [p.branch,p.parent])if(!html.includes(`href="${encodeURI(r)}"`))fail('Parent destination missing');
 const topics=[...html.matchAll(/data-subject-topic="([^"]+)"/g)].map(m=>m[1]);
 if(JSON.stringify(topics)!==JSON.stringify(p.topics))fail('Merged educational sections differ');
 const image=html.match(/<img\b[^>]*src="[^"]*assets\/centers\/common\/(?:seoul|local)6839\.webp"[^>]*>/)?.[0];
 if(!image||!image.includes('height="16116"')||!image.includes('loading="eager"')||/\bhidden(?:[\s=>])|\bstyle\s*=/.test(image)||!html.includes(encodeURI(b.bodyImage.mobile)))fail('Complete mobile consultation image lost');
 if(/학부모후기|★★★★★|성적 보장|전교.?등|학원교재실/.test(html))fail('Fictional review or unverified outcome');
 if(b.addressPending&&!html.includes('주소 자료가 서로 달라'))fail('Unresolved address missing');
}

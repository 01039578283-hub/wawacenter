import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertGradeDirectory} from '../grade-directory-check.mjs';
const name='지점안내/서울/명일점/초등학생학원/index.html';
const source=fs.readFileSync(new URL('../'+name,import.meta.url),'utf8');
test('keeps elementary subject ranges distinct',()=>assert.doesNotThrow(()=>assertGradeDirectory(source,name)));
test('rejects draft grade one being promoted into listed math classes',()=>assert.throws(()=>assertGradeDirectory(source.replace('data-stage-course="수학" data-grades="초4','data-stage-course="수학" data-grades="초1,초4'),name),/stage grades/));
test('rejects importing constructed parent reviews',()=>assert.throws(()=>assertGradeDirectory(source.replace('</main>','<p>학부모후기: 성적 보장</p></main>'),name),/fictional review/));
test('rejects misleading use of common tuition',()=>assert.throws(()=>assertGradeDirectory(source.replaceAll('지점 확정 금액 아님','확정 수강료'),name),/Common amount/));
test('rejects cropping the consultation image',()=>assert.throws(()=>assertGradeDirectory(source.replace('height="16116"','height="1000"'),name),/consultation image/));
test('rejects reinstating the duplicate legacy canonical',()=>{
 const legacyName='과목별학원/초등학생학원/명일동/index.html';
 const legacy=fs.readFileSync(new URL('../'+legacyName,import.meta.url),'utf8');
 assert.throws(()=>assertGradeDirectory(legacy.replace(/(<link\b[^>]*rel="canonical"[^>]*href=")[^"]+/, '$1https://xn--3e0bz50bxucwzc.com/과목별학원/초등학생학원/명일동/'),legacyName),/representative/);
});
test('rejects losing a branch child page',()=>{
 const hubName='지점안내/서울/명일점/index.html';
 const hub=fs.readFileSync(new URL('../'+hubName,import.meta.url),'utf8');
 assert.throws(()=>assertGradeDirectory(hub.replaceAll(encodeURI('/지점안내/서울/명일점/고등학생학원/'),'/missing/'),hubName),/destination/);
});

test('every moved grade URL redirects once to an existing actual branch child',()=>{
 const data=JSON.parse(fs.readFileSync(new URL('../grade-directory-data.json',import.meta.url),'utf8'));
 const config=JSON.parse(fs.readFileSync(new URL('../vercel.json',import.meta.url),'utf8'));
 const mappings=new Map(config.redirects.map(r=>[decodeURI(r.source)+'/',r]));
 assert.equal(mappings.size,1113);
 for(const p of data.pages){
  assert.equal(p.route,p.branch+p.category+'/');
  assert.ok(fs.existsSync(new URL('../'+p.route.slice(1)+'index.html',import.meta.url)));
 }
 for(const p of data.areaPages){
  const redirect=mappings.get(p.previousRoute);
  assert.equal(redirect.statusCode,301);
  assert.equal(decodeURI(redirect.destination),p.route);
  assert.ok(!mappings.has(p.route));
 }
});

test('obsolete neighborhood hubs and grade documents are absent from source and publication',()=>{
 const data=JSON.parse(fs.readFileSync(new URL('../grade-directory-data.json',import.meta.url),'utf8'));
 const manifest=JSON.parse(fs.readFileSync(new URL('../release-public-manifest.json',import.meta.url),'utf8'));
 for(const route of new Set(data.areaPages.flatMap(p=>[p.previousRoute,p.previousHub]))){
  const name=route.slice(1)+'index.html';
  assert.ok(!fs.existsSync(new URL('../'+name,import.meta.url)),name);
  assert.ok(!(name in manifest.files),name);
 }
});

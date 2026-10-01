import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertSubjectDirectory} from '../subject-directory-check.mjs';
import {assertBranchDirectory} from '../branch-directory-check.mjs';
import {transform} from '../seo-descriptions.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../subject-directory-data.json',import.meta.url),'utf8'));
const read=n=>fs.readFileSync(new URL('../'+n,import.meta.url),'utf8');
const p=data.pages.find(p=>p.branch.includes('명일점')&&p.stage==='초'&&p.subject==='수학');
const name=p.route.slice(1)+'index.html',source=read(name);
test('all 2226 neighborhood subject children retain source facts and descriptions',()=>{
 assert.equal(data.pages.length,2226);assert.equal(new Set(data.pages.map(p=>p.route)).size,2226);
 for(const p of data.pages){const n=p.route.slice(1)+'index.html',html=read(n);assertSubjectDirectory(html,n);assertBranchDirectory(html,n);assert.equal(transform(html,p.route).html,html);}
});
test('math cannot inherit English lower elementary grades',()=>{
 const bad=source.replace('data-subject-course="수학" data-grades="초4','data-subject-course="수학" data-grades="초1,초4');
 assert.notEqual(bad,source);assert.throws(()=>assertSubjectDirectory(bad,name),/grades changed/);
});
test('unknown subject/stage remains a confirmation request',()=>{
 const unknown=data.pages.find(p=>!p.course.grades.length);const n=unknown.route.slice(1)+'index.html';
 assert.throws(()=>assertSubjectDirectory(read(n).replaceAll('개설 학년 확인 필요','수강 가능'),n),/Unconfirmed/);
});
test('common fees cannot become confirmed tuition',()=>assert.throws(()=>assertSubjectDirectory(source.replaceAll('지점 확정 금액 아님','확정 금액'),name),/Common fee/));
test('full image cannot be cropped',()=>assert.throws(()=>assertSubjectDirectory(source.replace('height="16116"','height="900"'),name),/image lost/));
test('fictional draft reviews cannot be published',()=>assert.throws(()=>assertSubjectDirectory(source.replace('</main>','<p>학부모후기 성적 보장</p></main>'),name),/Fictional/));
test('each parent keeps both subject children',()=>{
 const n=p.parent.slice(1)+'index.html',html=read(n);assertSubjectDirectory(html,n);
 assert.throws(()=>assertSubjectDirectory(html.replaceAll(encodeURI(p.route),'/missing/'),n),/child link/);
});
test('all 4452 supplied drafts remain mapped exactly once',()=>{
 const sources=data.pages.flatMap(p=>p.sources);assert.equal(sources.length,4452);
 assert.equal(new Set(sources.map(s=>s.archive+'|'+s.filename)).size,4452);
 assert.equal(Object.keys(data.archiveHashes).length,12);
 for(const p of data.pages)assert.equal(p.sources.length,p.areas.length*2);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertLearningGuide} from '../learning-guide-check.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../learning-guide-data.json',import.meta.url),'utf8'));
const read=n=>fs.readFileSync(new URL('../'+n,import.meta.url),'utf8');
const p=data.pages.find(p=>p.slug==='수학오답관리'),name=p.route.slice(1)+'index.html',source=read(name);
const hubName='학습가이드/index.html',hub=read(hubName);
test('all guides preserve publication dates, sections, citations and FAQ',()=>{
 assert.equal(data.pages.length,40);assert.equal(data.pages.filter(p=>p.legacy).length,8);
 for(const p of data.pages){const n=p.route.slice(1)+'index.html';assertLearningGuide(read(n),n);}
 assertLearningGuide(hub,hubName);
});
test('sources cannot be removed from visible article',()=>{
 const url=data.sources[p.sources[0]][3];assert.throws(()=>assertLearningGuide(source.replace(`href="${url}"`,'href="/"'),name),/Visible primary source/);
});
test('FAQ schema cannot disagree with visible answer',()=>{
 const bad=source.replace(`"text":"${p.faq[0][1]}"`,'"text":"다른 답변"');assert.notEqual(source,bad);assert.throws(()=>assertLearningGuide(bad,name),/FAQ content/);
});
test('existing bookmarks keep legacy section anchors',()=>assert.throws(()=>assertLearningGuide(source.replace('id="section-2"','id="lost"'),name),/legacy anchor/));
test('download links are part of the article contract',()=>assert.throws(()=>assertLearningGuide(source.replace(encodeURI(p.record),'/missing.txt'),name),/download missing/));
test('guide URLs stay canonical',()=>assert.throws(()=>assertLearningGuide(source.replace('rel="canonical"','rel="alternate"'),name),/canonical changed/));
test('JavaScript cannot become the only way to find an article',()=>assert.throws(()=>assertLearningGuide(hub.replaceAll(encodeURI(p.route),'/missing/'),hubName),/Static guide link/));
test('editorial policy and unsupported outcomes cannot enter the public copy',()=>{
 for(const text of ['편집 원칙','성적 보장'])assert.throws(()=>assertLearningGuide(source.replace('</main>',`<p>${text}</p></main>`),name),/policy or unverified/);
});

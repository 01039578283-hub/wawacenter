import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertBookLibrary} from '../book-library-check.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../book-library-data.json',import.meta.url),'utf8'));
const read=n=>fs.readFileSync(new URL('../'+n,import.meta.url),'utf8');
const hubName='교재안내/index.html',hub=read(hubName);
const fieldName='교재안내/초등영어/index.html',field=read(fieldName);
const planName='교재안내/초등영어/기초/index.html',plan=read(planName);
const esc=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("'",'&#x27;');
test('all 27 book pages and both navigation entries satisfy workbook contracts',()=>{
 assert.equal(data.books.length,120);assert.equal(data.classes.length,18);assert.equal(data.pages.length,27);
 for(const p of data.pages){const n=p.route.slice(1)+'index.html';assertBookLibrary(read(n),n);}
 for(const n of data.entryPages)assertBookLibrary(read(n),n);
});
test('catalog stays complete without client rendering',()=>assert.throws(()=>assertBookLibrary(hub.replace('data-book-card','data-removed-card'),hubName),/Static catalog/));
test('primary and additional classifications cannot silently change',()=>{
 assert.throws(()=>assertBookLibrary(hub.replace('data-level="기초반"','data-level="심화반"'),hubName),/classification/);
 const b=data.books.find(b=>b.additionalLevels.length);
 const needle='data-additional="'+b.additionalLevels.join(',')+'"';
 assert.throws(()=>assertBookLibrary(hub.replace(needle,'data-additional=""'),hubName),/classification/);
});
test('full book details cannot lose selection conditions or publisher references',()=>{
 const b=data.books.find(b=>b.field==='초등영어');
 assert.throws(()=>assertBookLibrary(field.replace(esc(b.condition),'조건 삭제'),fieldName),/fact missing/);
 assert.throws(()=>assertBookLibrary(field.replace('href="'+esc(b.publicSourceUrl)+'"','href="/"'),fieldName),/publisher source/);
});
test('compare view cannot alter workbook facts',()=>assert.throws(()=>assertBookLibrary(hub.replace('&quot;condition&quot;:','&quot;incorrectCondition&quot;:'),hubName),/Comparison facts/));
test('level plans preserve their selected book IDs',()=>assert.throws(()=>assertBookLibrary(plan.replace('data-plan-book="EE01"','data-plan-book="HE01"'),planName),/plan book/));
test('FAQ visible answers must agree with machine-readable answers',()=>{
 const p=data.pages.find(p=>p.route==='/교재안내/');
 assert.throws(()=>assertBookLibrary(hub.replace('"text":"'+p.faqs[0][1]+'"','"text":"다른 답변"'),hubName),/FAQ content/);
});
test('guidance cannot be converted into unsupported academy claims or ratings',()=>{
 for(const claim of ['모든 지점에서 사용','실제 사용 교재입니다','성적 보장','편집 원칙'])
  assert.throws(()=>assertBookLibrary(hub.replace('</main>','<p>'+claim+'</p></main>'),hubName),/Unsupported claim/);
});
test('canonical, navigation entry and blank worksheet remain usable',()=>{
 assert.throws(()=>assertBookLibrary(hub.replace('rel="canonical"','rel="alternate"'),hubName),/canonical/);
 assert.throws(()=>assertBookLibrary(read('index.html').replace('id="book-discovery"','id="lost"'),'index.html'),/entry missing/);
 const n='교재안내/교재선택/index.html';
 assert.throws(()=>assertBookLibrary(read(n).replace(encodeURI('/assets/book-records/교재선택.txt'),'/missing.txt'),n),/download missing/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertGradeDirectory} from '../grade-directory-check.mjs';
const name='지점안내/서울/명일동/명일동초등학생학원/index.html';
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
test('rejects losing a neighborhood child page',()=>{
 const hubName='지점안내/서울/명일동/index.html';
 const hub=fs.readFileSync(new URL('../'+hubName,import.meta.url),'utf8');
 assert.throws(()=>assertGradeDirectory(hub.replaceAll(encodeURI('/지점안내/서울/명일동/명일동고등학생학원/'),'/missing/'),hubName),/destination/);
});

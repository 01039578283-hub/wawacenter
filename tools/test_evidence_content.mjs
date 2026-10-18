import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertEvidenceContent} from '../evidence-content-check.mjs';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const subject='지점안내/서울/명일점/명일동초등학생학원/영어/index.html';
const special='지점안내/서울/내발산점/내발산동고등학생학원/영어/index.html';
test('partial grade availability remains partial before the lesson image',()=>assert.doesNotThrow(()=>assertEvidenceContent(read(subject),subject)));
test('reject an inflated grade range',()=>assert.throws(()=>assertEvidenceContent(read(subject).replace(/(<dt>영어<\/dt><dd>)초5~초6/, '$1초1~초6'),subject),/grade range differs/));
test('reject losing a specific school restriction from the early summary',()=>{
 const s=read(special);const note='덕원여자고등학교 영어 내신 수업은 운영 범위에서 제외되어 있습니다.';
 assert.ok(s.includes(note));assert.throws(()=>assertEvidenceContent(s.replace('<li>'+note+'</li>',''),special),/condition omitted/);
});
test('reject a page linked to a different branch',()=>assert.throws(()=>assertEvidenceContent(read(subject).replace(/"about":\[\{"@id":"[^"]+"\}\]/,'"about":[{"@id":"https://example.com/wrong"}]'),subject),/actual branch/));
const article='교육정보/지루한과목질문실험/index.html';
test('topic-specific record has its primary references and offline blank',()=>assert.doesNotThrow(()=>assertEvidenceContent(read(article),article)));
test('reject a form that could submit student records',()=>assert.throws(()=>assertEvidenceContent(read(article).replace('<form class="sr-record"','<form class="sr-record" action="/send"'),article),/stay local/));

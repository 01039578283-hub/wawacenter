import test from 'node:test';
import assert from 'node:assert/strict';
import {matchesGuide, recordText} from '../assets/learning-guide-tools.mjs';
const sample={category:'math',levels:['middle','high'],search:'수학 풀이 비교 — 등식 AI 전략'};
test('reader, subject and all search terms narrow the same guide set',()=>{
 assert.equal(matchesGuide(sample,{level:'middle',category:'math',query:'풀이 전략'}),true);
 assert.equal(matchesGuide(sample,{level:'elementary',category:'math'}),false);
 assert.equal(matchesGuide(sample,{level:'high',category:'english'}),false);
 assert.equal(matchesGuide(sample,{query:'풀이 듣기'}),false);
 assert.equal(matchesGuide(sample,{}),true);
});
test('search accepts Unicode width variants, extra whitespace and English case',()=>{
 assert.equal(matchesGuide(sample,{query:'  ａｉ  \n 수학  '}),true);
 assert.equal(matchesGuide({...sample,levels:'middle high'},{level:'high'}),true);
 assert.equal(matchesGuide(sample,{query:'   '}),true);
});
test('record output preserves user text literally and normalizes Windows newlines',()=>{
 const result=recordText({title:'영어 수정',url:'https://전국수업.com/학습가이드/영어쓰기수정기록/',date:'2026-10-02',fields:[{label:'원래 문장',value:'<script>실행하지 않음</script>\n두 번째 줄'},{label:'수정 이유',value:'시제\r\n확인'}]});
 assert.ok(result.includes('<script>실행하지 않음</script>\r\n두 번째 줄'));
 assert.ok(result.includes('시제\r\n확인'));
 assert.equal(result.replaceAll('\r\n','').includes('\n'),false);
 assert.ok(result.endsWith('/\r\n'));
});
test('blank fields and missing date remain blank in a draft rather than examples',()=>{
 const result=recordText({title:'실천',url:'/가이드/',date:'',fields:[{label:'목표',value:''}]});
 assert.ok(result.includes('작성 날짜: 미작성'));
 assert.ok(result.includes('목표:\r\n\r\n'));
});

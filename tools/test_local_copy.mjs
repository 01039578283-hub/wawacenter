import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertLocalCopy} from '../local-copy-check.mjs';
const high = '과목별학원/고등영수학원/명일동/index.html';
const missing = '과목별학원/수학학원/갈현동/index.html';
const center = '전국센터/갈현동/index.html';
const read = name => fs.readFileSync(new URL('../' + name, import.meta.url), 'utf8');
test('subject, combined and center copy match visible questions and reviewed facts', () => {
  for (const name of [high, missing, center]) assertLocalCopy(read(name), name);
});
test('legacy generator copy is rejected', () => {
  assert.throws(() => assertLocalCopy(read(high).replace('<!-- local-copy:start -->', ''), high), /Reviewed local copy missing/);
});
test('changing just a visible FAQ answer is rejected', () => {
  assert.throws(() => assertLocalCopy(read(high).replace('<p>자료에 기재된 학년은', '<p>확인되지 않은 학년은'), high), /Visible FAQ and schema differ/);
});
test('unsupported math grade is rejected even if FAQ and schema both say it', () => {
  assert.throws(() => assertLocalCopy(read(high).replaceAll('수학 고1~고2', '수학 고1~고3'), high), /FAQ grades differ/);
});
test('missing math information cannot become an assertion of no classes', () => {
  assert.throws(() => assertLocalCopy(read(missing).replaceAll('수학의 해당 학년 정보는 기재되어 있지 않아 수강 가능 여부를 상담으로 확인해야 합니다.', '수학 수업은 불가합니다.'), missing), /Missing subjects need consultation/);
});
test('operator SEO explanation cannot return in visitor content', () => {
  assert.throws(() => assertLocalCopy(read(center).replace('<!-- local-copy:end -->', '<p>검색엔진과 생성형 검색</p><!-- local-copy:end -->'), center), /Obsolete repetitive copy/);
});
test('removed headings cannot stay in article markup', () => {
  assert.throws(() => assertLocalCopy(read(high).replace('id="review-title"', 'id="changed-title"'), high), /Article heading schema differs/);
});

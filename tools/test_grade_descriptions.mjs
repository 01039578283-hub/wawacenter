import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {transform} from '../seo-descriptions.mjs';
const old='/과목별학원/초등학생학원/명일동/';
const latest='/지점안내/서울/명일점/초등학생학원/';
const read=route=>fs.readFileSync(new URL('../'+route.slice(1)+'index.html',import.meta.url),'utf8');
test('legacy summary remains supported by its own body',()=>{
  const html=read(old);assert.equal(transform(html,old).html,html);
});
test('canonical alias cannot silently change to another representative',()=>{
  const html=read(old).replace(encodeURI(latest),encodeURI('/지점안내/서울/천호동/천호동초등학생학원/'));
  assert.throws(()=>transform(html,old),/canonical alias changed/);
});
test('enriched representative retains aligned new summary',()=>{
  const html=read(latest);assert.equal(transform(html,latest).html,html);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertKakaoDirections} from '../kakao-directions-check.mjs';
import {assertBranchDirectory} from '../branch-directory-check.mjs';
const name='지점안내/인천/구월점/index.html';
const html=fs.readFileSync(new URL('../'+name,import.meta.url),'utf8');
const block=html.match(/<!-- kakao-directions:start -->[\s\S]*?<!-- kakao-directions:end -->/)[0];
test('confirmed Guwol source and inert transit coexist with the original branch facts',()=>{
  assert.doesNotThrow(()=>assertKakaoDirections(html,name));assert.doesNotThrow(()=>assertBranchDirectory(html,name));
});
test('a different branch map cannot be assigned by swapping its frame URL',()=>{
  assert.throws(()=>assertKakaoDirections(html.replace('/assets/kakao-maps/k-39tauimyve7.htm','/assets/kakao-maps/k-otherbranch.htm'),name),/missing or duplicated src/);
});
test('an eager video iframe is still rejected by the original branch guard',()=>{
  assert.throws(()=>assertBranchDirectory(html.replace(/<iframe\b[^>]*>/,'<iframe src="https://www.youtube.com/embed/example">'),name),/Video/);
});
test('map loading cannot become eager',()=>{
  const next=html.replace(block,block.replace('loading="lazy"','loading="eager"'));
  assert.throws(()=>assertKakaoDirections(next,name),/loading/);assert.throws(()=>assertBranchDirectory(next,name),/Video/);
});
test('external transit links and telephone lines cannot return',()=>{
  for(const added of ['<a href="https://map.kakao.com/">버스</a>','<p>전화 032-473-6955</p>']){
    assert.throws(()=>assertKakaoDirections(html.replace(block,block.replace('</div></div>',added+'</div></div>')),name),/forbidden/);
  }
});
test('the map section cannot be hidden or moved before the existing map image',()=>{
  assert.throws(()=>assertKakaoDirections(html.replace('data-kakao-directions data-','hidden data-kakao-directions data-'),name),/visible/);
  const stripped=html.replace(block,'');assert.throws(()=>assertKakaoDirections(stripped.replace('<main',''+block+'<main'),name),/must follow/);
});

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

test('the map cannot display an outdated visiting address',()=>{
  const address=block.match(/방문 주소<\/strong>([^<]+)/)[1];
  assert.throws(()=>assertKakaoDirections(html.replace(block,block.replace(address,'이전 주소')),name),/visiting address differs/);
});

test('the owner-confirmed Nohyeong address agrees across location and teacher data',()=>{
  const expected='제주특별자치도 제주시 과원북4길 27 2층';
  const route='/지점안내/제주/노형점/';
  const read=name=>JSON.parse(fs.readFileSync(new URL('../'+name,import.meta.url),'utf8'));
  const b=read('kakao-directions-data.json').branches[route];
  assert.equal(b.address,expected);assert.equal(b.mapAddress,expected);assert.equal(b.approved,true);
  assert.equal(read('branch-directory-data.json').branches.find(b=>b.route===route).addressPending,false);
  assert.equal(read('teacher-directory-data.json').branches.find(b=>b.branchRoute===route).address,expected);
  assert.equal(read('assets/home-branch-search-data.json').branches.find(b=>b.route===route).address,expected);
  for(const a of read('area-reference.json').areas.filter(a=>['노형동','연동'].includes(a.slug))){
    assert.equal(a.address,expected);assert.notEqual(a.addressStatus,'주소 재확인 필요');
  }
  const pageName=route.slice(1)+'index.html';
  const page=fs.readFileSync(new URL('../'+pageName,import.meta.url),'utf8');
  assert.doesNotThrow(()=>assertKakaoDirections(page,pageName));
  assert.doesNotThrow(()=>assertBranchDirectory(page,pageName));
  assert.ok(!page.includes('727-3')&&!page.includes('주소 자료가 서로 달라'));
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

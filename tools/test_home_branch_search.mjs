import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {findBranches} from '../assets/home-branch-search-tools.mjs';
const read = name => JSON.parse(fs.readFileSync(new URL('../'+name,import.meta.url),'utf8'));
const branches=read('assets/home-branch-search-data.json').branches;
const mapping=read('neighborhood-directory-data.json').mapping;

test('every reviewed neighborhood finds its assigned actual branch',()=>{
  for(const row of mapping) assert.ok(findBranches(branches,{query:row.area,region:row.region}).some(b=>b.route===row.branch),JSON.stringify(row));
});
test('Madu neighborhoods resolve to one branch without inventing centers',()=>{
  for(const query of ['마두동','장항동','백석동','마두점']) assert.deepEqual(findBranches(branches,{query,region:'경기'}).map(b=>b.name),['마두점']);
});
test('region and every normalized term are required',()=>{
  assert.deepEqual(findBranches(branches,{query:'경기 장항동'}).map(b=>b.name),['마두점']);
  assert.deepEqual(findBranches(branches,{query:'장항동',region:'서울'}),[]);
  assert.deepEqual(findBranches(branches,{query:'없는동네'}),[]);
  assert.deepEqual(findBranches(branches,{query:'　장항동　',region:'경기'}).map(b=>b.name),['마두점']);
});
test('blank inputs do not flood the page and a selected region shows all its branches',()=>{
  assert.deepEqual(findBranches(branches),[]);
  for(const region of new Set(branches.map(b=>b.region))) assert.equal(findBranches(branches,{region}).length,branches.filter(b=>b.region===region).length);
});

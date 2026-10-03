import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {assertTeacherDirectory} from '../teacher-directory-check.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../teacher-directory-data.json',import.meta.url),'utf8'));
const read=n=>fs.readFileSync(new URL('../'+n,import.meta.url),'utf8');
const page=data.pages.find(p=>p.kind==='branch'),name=page.route.slice(1)+'index.html';
const group=data.branches.find(g=>g.route===page.route);
test('every supplied teacher introduction and every contextual destination survives',()=>{
  assert.equal(data.source.rows,1002);assert.equal(data.branches.length,205);
  const ids=data.branches.flatMap(g=>g.teachers.map(t=>t.id));assert.equal(ids.length,new Set(ids).size);
  for(const p of data.pages)assertTeacherDirectory(read(p.route.slice(1)+'index.html'),p.route.slice(1)+'index.html');
  for(const p of data.linkedPages)assertTeacherDirectory(read(p.file),p.file);
});
test('all approved portrait files keep exact source bytes and branch assignments are unique',()=>{
  const hashes=new Map(data.photos.map(p=>[p.src,p.sha256]));
  for(const p of data.photos)assert.equal(createHash('sha256').update(fs.readFileSync(new URL('..'+p.src,import.meta.url))).digest('hex'),p.sha256);
  for(const g of data.branches)assert.equal(new Set(g.teachers.map(t=>hashes.get(t.image))).size,g.teachers.length);
});
test('matching a branded name uses the actual source name rather than a similar branch',()=>{
  const branches=JSON.parse(read('branch-directory-data.json')).branches;
  for(const g of data.branches.filter(g=>g.branchRoute)){
    const b=branches.find(b=>b.route===g.branchRoute);assert.ok(b);
    assert.ok([b.name,b.sourceName,b.displayName].includes(g.sourceName));
  }
  for(const g of data.branches.filter(g=>g.sourceName.includes('(W+)')||g.sourceName.includes('글로리드')))assert.equal(g.branchRoute,null);
});
test('a repeated branch photo is rejected',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replace(encodeURI(group.teachers[1].image),encodeURI(group.teachers[0].image)),name));
});
test('the portrait disclosure cannot disappear',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replaceAll(data.photoNote,''),name));
});
test('masked teacher names cannot silently change',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replace('<h3>'+group.teachers[0].name+' 선생님</h3>','<h3>다른 선생님</h3>'),name));
});
test('source teaching statements cannot disappear',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replace(group.teachers[0].sentences[2],''),name));
});
test('illustrative photos cannot become factual Person portraits',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replace('"jobTitle":"선생님"','"image":"/assets/teachers/photo.png","jobTitle":"선생님"'),name));
});
test('a branch contextual link cannot point to another teacher group',()=>{
  const e=data.linkedPages.find(p=>p.branch);assert.throws(()=>assertTeacherDirectory(read(e.file).replace('data-teacher-route="'+e.target+'"','data-teacher-route="/선생님찾기/다른점/"'),e.file));
});
test('the learning-help category covers every supplied keyword exactly once',()=>{
  const supplied=new Set(data.branches.flatMap(g=>g.teachers.flatMap(t=>t.focus)));
  const covered=data.needs.flatMap(n=>n.focus);
  assert.equal(covered.length,new Set(covered).size);
  assert.deepEqual(new Set(covered),supplied);
});
test('learning-help filters cannot mislabel a teacher',()=>{
  const key=data.needs.filter(n=>n.focus.some(f=>group.teachers[0].focus.includes(f))).map(n=>n.id).join(' ');
  assert.throws(()=>assertTeacherDirectory(read(name).replace('data-needs="'+key+'"','data-needs="unrelated"'),name));
});
test('a parent consultation guide must remain available',()=>{
  assert.throws(()=>assertTeacherDirectory(read(name).replaceAll(encodeURI('/학습가이드/선생님상담질문/'),'/학습가이드/'),name));
});
test('teacher pages link back to their mapped neighborhoods',()=>{
  const page=data.branches.find(g=>g.areas.length);
  const route='/전국센터/'+page.areas[0].slug+'/';
  assert.throws(()=>assertTeacherDirectory(read(page.route.slice(1)+'index.html').replaceAll(encodeURI(route),'/전국센터/'),page.route.slice(1)+'index.html'));
});

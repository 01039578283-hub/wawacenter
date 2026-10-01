import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {assertContextualLinks} from '../contextual-links-check.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'contextual-links-data.json'),'utf8'));
const sample=data.pages.find(p=>p.context.kind==='subject' && p.context.stage==='고' && p.context.subject==='수학');
const name=sample.file,html=fs.readFileSync(path.join(root,name),'utf8');
test('all 6364 reviewed academic pages have working contextual resource groups',()=>{
  assert.equal(data.pages.length,6364);
  for(const p of data.pages)assertContextualLinks(fs.readFileSync(path.join(root,p.file),'utf8'),p.file);
});
test('a math resource cannot be silently replaced by an English resource',()=>{
  const url=sample.groups[0].links[0].route;
  assert.throws(()=>assertContextualLinks(html.replace(encodeURI(url),encodeURI('/학습가이드/영어단어복습법/')),name));
});
test('a high-school book link cannot become an elementary book link',()=>{
  assert.throws(()=>assertContextualLinks(html.replace(encodeURI('/교재안내/고등수학/'),encodeURI('/교재안내/초등수학/')),name));
});
test('the distinction between reference books and branch usage is required',()=>{
  assert.throws(()=>assertContextualLinks(html.replace(data.notice,''),name));
});
test('the resource block cannot be repeated',()=>{
  const block=html.match(/<!-- contextual-links:module:start -->[\s\S]*?<!-- contextual-links:module:end -->/)[0];
  assert.throws(()=>assertContextualLinks(html.replace('</main>',block+'</main>'),name));
});
test('the lesson image remains before the full resource block',()=>{
  const block=html.match(/<!-- contextual-links:module:start -->[\s\S]*?<!-- contextual-links:module:end -->/)[0];
  const changed=html.replace(block,'').replace(/<section\b[^>]*id="lesson-image"/,block+'$&');
  assert.throws(()=>assertContextualLinks(changed,name));
});
test('home and editorial library pages do not receive an extra generic resource block',()=>{
  for(const name of ['index.html','학습가이드/index.html','교재안내/index.html'])assertContextualLinks(fs.readFileSync(path.join(root,name),'utf8'),name);
});

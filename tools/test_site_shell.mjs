import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertSiteShell} from '../site-shell-check.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../site-shell-data.json',import.meta.url),'utf8'));
const read=name=>fs.readFileSync(new URL('../'+name,import.meta.url),'utf8');
test('all public pages share the same navigation, brand and theme',()=>{
  assert.ok(data.pages.length>=6434);for(const name of data.pages)assertSiteShell(read(name),name);
});
test('home must expose the learning-system menu and official video shortcut',()=>{
  const h=read('index.html');assert.throws(()=>assertSiteShell(h.replace('>학습시스템</a>','>교육 안내</a>'),'index.html'));
});
test('book navigation must remain visible on every page',()=>{
  const n='지점안내/index.html';assert.throws(()=>assertSiteShell(read(n).replace('>교재안내</a>','>교재</a>'),n));
});
test('AI Korean is not silently advertised to elementary students',()=>{
  const n='학습시스템/AI학습/index.html';const h=read(n).replace(/(id="ai-korean"[\s\S]*?공식 대상 범위 · )중1~고3/,'$1초1~고3');assert.throws(()=>assertSiteShell(h,n));
});
test('AI reading retains its distinct upper range',()=>{
  const n='학습시스템/AI학습/index.html';const h=read(n).replace(/(id="ai-reading"[\s\S]*?공식 대상 범위 · )초1~중2/,'$1초1~고3');assert.throws(()=>assertSiteShell(h,n));
});
test('official video retains a direct fallback destination',()=>{
  const n='학습시스템/와와학습코칭/index.html';assert.throws(()=>assertSiteShell(read(n).replace('https://www.youtube.com/watch?v=59Tna9pZWrk','https://example.com/'),n));
});
test('a page cannot override the common header with a later stylesheet',()=>{
  const n='과목별학원/index.html';assert.throws(()=>assertSiteShell(read(n).replace('</head>','<link rel="stylesheet" href="/assets/site.css"></head>'),n));
});

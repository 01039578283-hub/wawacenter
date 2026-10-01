import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(fs.readFileSync(path.join(root,'contextual-links-data.json'),'utf8'));
const pages=new Map(data.pages.map(p=>[p.file,p]));
const branch=JSON.parse(fs.readFileSync(path.join(root,'branch-directory-data.json'),'utf8'));
const area=JSON.parse(fs.readFileSync(path.join(root,'area-reference.json'),'utf8'));
const branches=new Map(branch.branches.map(p=>[p.route,p]));
const areas=new Map(area.areas.map(p=>[p.slug,p]));
const stageNames={초:'초등',중:'중등',고:'고등'};
const stageGuides={초:'초등학생공부습관',중:'중학생내신공부법',고:'고등학생과목별공부법'};
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
const fail=(name,message)=>{throw Error('Context resources '+name+': '+message);};

export function assertContextualLinks(html,name){
  const expected=pages.get(name);
  if(!expected){if(html.includes('data-context-resources'))fail(name,'unexpected resource block');return;}
  const c=expected.context;
  const modules=html.match(/<!-- contextual-links:module:start -->([\s\S]*?)<!-- contextual-links:module:end -->/g)||[];
  if(modules.length!==1)fail(name,'exactly one reviewed module required');
  const block=modules[0];
  if((html.match(/id="helpful-learning"/g)||[]).length!==1 || !html.includes('href="#helpful-learning"'))fail(name,'section or shortcut missing');
  if(!html.includes('<link rel="stylesheet" href="/assets/contextual-links.css">'))fail(name,'resource styles missing');
  for(const [key,value] of [['kind',c.kind],['stage',c.stage||''],['subject',c.subject]])
    if(!block.includes(`data-context-${key}="${value}"`))fail(name,'page context changed');
  if(!block.includes(esc(data.notice)))fail(name,'reference and branch-usage qualification missing');
  const groups=[...block.matchAll(/<article class="cl-card" data-context-group="([^"]+)">([\s\S]*?)<\/article>/g)];
  if(groups.length!==3)fail(name,'student, books and parent groups required');
  const all=[];
  for(let i=0;i<groups.length;i++){
    const g=expected.groups[i];if(groups[i][1]!==g.id)fail(name,'wrong resource group');
    const links=[...groups[i][2].matchAll(/<a class="cl-link" href="([^"]+)"><span><strong>([\s\S]*?)<\/strong><small>([\s\S]*?)<\/small><\/span><\/a>/g)];
    if(links.length!==g.links.length)fail(name,'missing descriptive link');
    for(let j=0;j<links.length;j++){
      const a=g.links[j],actual=decodeURIComponent(links[j][1]);
      if(actual!==a.route || links[j][2]!==esc(a.label) || links[j][3]!==esc(a.hint))fail(name,'link destination or explanation differs from review');
      if(!/^\/(학습가이드|교재안내)\//.test(actual))fail(name,'not an educational internal destination');
      if(!fs.existsSync(path.join(root,actual,'index.html')))fail(name,'destination does not exist');
      all.push(actual);
      if(g.id==='study'){
        const slug=actual.split('/')[2];
        if(c.subject==='수학' && slug.startsWith('영어') || c.subject==='영어' && /^(수학|계산|고등수학)/.test(slug))fail(name,'wrong subject guide');
        for(const [s,guide] of Object.entries(stageGuides))if(slug===guide && c.stage && s!==c.stage)fail(name,'wrong stage guide');
        if(slug==='고등수학모의고사분석' && c.stage!=='고')fail(name,'high-school-only guide');
        if(slug==='영어내신준비' && c.stage==='초')fail(name,'school-exam guide on elementary page');
      }
      const field=/^\/교재안내\/(초등|중등|고등)(영어|수학)\/$/.exec(actual);
      if(field){
        const s=Object.entries(stageNames).find(([,v])=>v===field[1])[0];
        if(c.stage && s!==c.stage || c.subject && field[2]!==c.subject)fail(name,'wrong stage or subject books');
        if(!c.stages.includes(s))fail(name,'unmatched book stage');
      }
    }
  }
  if(new Set(all).size!==all.length || all.length<6 || all.length>9)fail(name,'duplicate or excessive destinations');
  // Independently derive specific page intent from the actual URL, not the link catalog.
  const parts=expected.route.split('/').filter(Boolean);
  const grade=parts.find(s=>/^(초등|중|고등)학생학원$/.test(s));
  if(grade){const s=grade[0];if(c.stage!==s)fail(name,'stage disagrees with page path');}
  if(parts[0]==='지점안내' && parts.length===5 && c.subject!==parts[4])fail(name,'subject disagrees with page path');
  const available=[];
  if(c.kind==='branch'){
    const b=branches.get(expected.route);if(!b)fail(name,'unreviewed branch');
    for(const s of Object.keys(stageNames))if(b.courses.some(course=>course.grades.some(g=>g.startsWith(s))))available.push(s);
    if(available.join()!==c.stages.join())fail(name,'branch stages differ from confirmed source');
  }
  if(c.kind==='area' && !c.stage){
    const slug=parts[0]==='과목별학원'?parts.at(-1):parts[1];const a=areas.get(slug);
    if(!a)fail(name,'unreviewed neighborhood');
    for(const s of Object.keys(stageNames))if(Object.entries(a.grades).some(([subject,grades])=>(!c.subject||subject===c.subject)&&grades.some(g=>g.startsWith(s))))available.push(s);
    if(available.join()!==c.stages.join())fail(name,'neighborhood stages differ from confirmed subject source');
  }
  if(html.includes('id="lesson-image"')){
    if(html.indexOf('contextual-links:module:start')<html.indexOf('id="lesson-image"'))fail(name,'resources precede the lesson image');
    const nav=/<nav class="image-first-nav"[^>]*>([\s\S]*?)<\/nav>/.exec(html);
    if(nav && nav[1].includes('helpful-learning'))fail(name,'original image navigation changed');
  }
  const local=/<!-- local-copy:start -->([\s\S]*?)<!-- local-copy:end -->/.exec(html);
  if(local?.[1].includes('contextual-links:module:start'))fail(name,'reviewed editorial block changed');
}

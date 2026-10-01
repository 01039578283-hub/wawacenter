import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./teacher-directory-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.route.slice(1)+'index.html',p]));
const groups=new Map(data.branches.map(g=>[g.route,g]));
const entries=new Map(data.linkedPages.map(p=>[p.file,p]));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
export function assertTeacherDirectory(html,name){
  const page=pages.get(name),entry=entries.get(name);if(!page&&!entry)return;
  const fail=reason=>{throw Error(`${name}: teacher directory ${reason}`);};
  const destinations=new Set([...html.matchAll(/href="([^"]+)"/g)].map(m=>decodeURIComponent(m[1].replaceAll('&amp;','&'))));
  if(entry){
    if(!destinations.has(decodeURIComponent(entry.target)))fail('contextual destination missing');
    if(name!=='index.html'&&!html.includes(`data-teacher-route="${esc(entry.target)}"`))fail('page-specific teacher link changed');
    if(entry.branch&&!data.branches.some(g=>g.branchRoute===entry.branch&&g.route===entry.target))fail('teacher link does not belong to the branch');
  }
  if(!page)return;
  if(!html.includes('/assets/teacher-directory.css'))fail('mobile profile style missing');
  if((html.match(/<h1\b/g)||[]).length!==1)fail('one main heading required');
  const meta=html.match(/<meta name="description" content="([^"]*)"/)?.[1];
  if(meta!==esc(page.description)||[...page.description].length>80||!page.description.endsWith('.'))fail('complete page-specific description required');
  for(const key of ['og:description','twitter:description'])if(!html.includes(`="${key}" content="${meta}"`))fail('description channels differ');
  const canonical=html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  if(!canonical||decodeURIComponent(new URL(canonical).pathname)!==page.route)fail('canonical changed');
  const graph=JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1]||'null')?.['@graph'];
  if(graph?.[0].description!==page.description||graph[0].dateModified!==data.reviewed)fail('page schema differs');
  const visible=[...html.matchAll(/<details class="bd-details" data-faq><summary>(.*?)<\/summary><div><p>(.*?)<\/p><\/div><\/details>/g)].map(m=>[m[1],m[2]]);
  const schema=graph.find(n=>n['@type']==='FAQPage');
  if(JSON.stringify(visible)!==JSON.stringify((schema?.mainEntity||[]).map(n=>[esc(n.name),esc(n.acceptedAnswer.text)])))fail('FAQ differs from visible answers');
  if(/"(?:alumniOf|hasCredential|award|knowsAbout|image)"\s*:/.test(JSON.stringify(graph.filter(n=>n['@type']==='Person'))))fail('unverified teacher credential, subject or actual portrait claim');
  if(/교사 프로필\.xlsx|C:\\Users|sourceRow|sourceSheet/.test(html))fail('private source material leaked');
  if(page.kind==='hub'){
    if((html.match(/data-teacher-card /g)||[]).length!==data.branches.length)fail('branch cards missing');
    for(const g of data.branches)if(!destinations.has(g.route)||!html.includes(esc(g.sourceName)))fail('supplied branch omitted');
    if(!html.includes('/assets/teacher-directory.js'))fail('search controls missing');
    return;
  }
  const g=groups.get(page.route);if(!html.includes(data.photoNote))fail('illustrative portrait disclosure missing');
  const ids=[...html.matchAll(/data-teacher-profile="([^"]+)"/g)].map(m=>m[1]);
  if(JSON.stringify(ids)!==JSON.stringify(page.teacherIds))fail('teacher membership or order changed');
  const persons=graph.filter(n=>n['@type']==='Person');
  if(persons.length!==g.teachers.length)fail('teacher schema count changed');
  const photos=[];
  for(const [i,t] of g.teachers.entries()){
    const card=html.slice(html.indexOf('data-teacher-profile="'+t.id+'"'),html.indexOf('</article>',html.indexOf('data-teacher-profile="'+t.id+'"')));
    if(!card.includes(`<h3>${esc(t.name)} 선생님</h3>`))fail('masked teacher name changed');
    for(const focus of t.focus)if(!card.includes('<span>'+esc(focus)+'</span>'))fail('supplied focus changed');
    for(const sentence of t.sentences)if(!card.includes(esc(sentence)))fail('source introduction was lost');
    const img=card.match(/<img\b[^>]*src="([^"]+)"[^>]*>/);if(!img||decodeURI(img[1])!==t.image||!img[0].includes('alt="선생님 소개용 이미지"'))fail('assigned illustrative photo changed');
    photos.push(img[1]);
    if(persons[i].name!==t.name+' 선생님'||persons[i].worksFor.name!==g.sourceName||persons[i].description!==t.sentences.join(' '))fail('schema identity or introduction differs from supplied facts');
  }
  if(new Set(photos).size!==photos.length)fail('portrait repeated within branch');
  if(g.branchRoute&&!destinations.has(g.branchRoute))fail('verified branch return link missing');
  if(!g.branchRoute&&graph.some(n=>n.address))fail('unknown branch address invented');
}

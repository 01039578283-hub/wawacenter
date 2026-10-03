import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./education-info-data.json',import.meta.url),'utf8'));
const related=new Map(data.existingPages.filter(p=>p.module).map(p=>[p.file,p.module]));
const articles=new Map(data.articles.map(a=>[a.route.slice(1)+'index.html',a]));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
export function assertEducationInfo(html,name){
 const fail=m=>{throw Error('Education info '+name+': '+m);};
 const rel=related.get(name);
 if(rel){
  if((html.match(/id="(?:education-reading|home-education)"/g)||[]).length!==1)fail('one visible reading destination required');
  for(const route of rel.links)if(!html.includes('href="'+encodeURI(route)+'"'))fail('contextual destination missing');
  if(!html.includes('href="'+encodeURI('/교육정보/')+'"'))fail('all-articles destination missing');
 }
 if(!name.startsWith('교육정보/'))return;
 if(!html.includes('defer src="/assets/education-info.js"'))fail('progressive navigation script missing');
 if(!html.includes('data-education-finder')||!html.includes('aria-label="지역별 수업 지점"'))fail('regional fallback missing');
 const a=articles.get(name);
 if(!a){
  if(name!=='교육정보/index.html')fail('unreviewed article');
  if((html.match(/data-education-card /g)||[]).length!==data.articles.length)fail('all reviewed articles must be server-rendered');
  for(const a of data.articles)if(!html.includes('href="'+encodeURI(a.route)+'"'))fail('article absent from complete library');
  const list=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m=>JSON.parse(m[1])['@graph']||[]).find(n=>n['@type']==='ItemList');
  if(list?.numberOfItems!==data.articles.length||list?.itemListElement?.length!==data.articles.length)fail('library metadata count differs from visible list');
  return;
 }
 if((html.match(/<h1\b/g)||[]).length!==1||!html.includes('<h1>'+esc(a.title)+'</h1>'))fail('article title missing');
 if(!html.includes('<meta name="description" content="'+esc(a.description)+'">'))fail('reviewed description missing');
 if(!html.includes('<link rel="canonical" href="https://xn--3e0bz50bxucwzc.com'+encodeURI(a.route)+'">'))fail('canonical article URL missing');
 for(let i=0;i<a.sections.length;i++){
  const heading=a.sections[i][0],id='part-'+(i+1);
  if(!html.includes('<h2 id="'+id+'-title">'+esc(heading)+'</h2>')||!html.includes('href="#'+id+'"'))fail('reviewed section or table of contents missing');
 }
 const imgs=[...html.matchAll(/<figure class="ei-photo"><img ([^>]+)>/g)];
 if(imgs.length!==3)fail('three body images required');
 for(let i=0;i<3;i++){
  const im=a.images[i],tag=imgs[i][1];
  if(!tag.includes('src="'+im.src+'"')||!tag.includes('alt="'+esc(im.alt)+'"')||!tag.includes('loading="lazy"')||!tag.includes('width="'+im.width+'"')||!tag.includes('height="'+im.height+'"'))fail('image or dimensions differ from source');
 }
 for(const [q,v] of a.faq)if(!html.includes('<summary>'+esc(q)+'</summary>')||!html.includes('<p>'+esc(v)+'</p>'))fail('visible FAQ changed');
 const graph=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m=>{const x=JSON.parse(m[1]);return x['@graph']||[x];});
 const article=graph.find(n=>n['@type']==='Article'),faq=graph.find(n=>n['@type']==='FAQPage');
 if(!article||article.headline!==a.title||article.author?.name!=='전국수업.com'||article.image?.length!==3)fail('article metadata differs from visible content');
 if(article.description!==a.description)fail('article description differs from visible metadata');
 if(JSON.stringify(faq?.mainEntity.map(n=>[n.name,n.acceptedAnswer.text]))!==JSON.stringify(a.faq))fail('FAQ metadata differs from visible answers');
}

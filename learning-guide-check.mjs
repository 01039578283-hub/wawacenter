/** Learning guides: preserve usable static content and source-backed metadata. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./learning-guide-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.route.slice(1)+'index.html',p]));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("'",'&#x27;');
export function assertLearningGuide(html,name){
 if(!name.startsWith('학습가이드/'))return;
 const fail=s=>{throw Error(`${name}: ${s}`)};
 const p=pages.get(name),hub=name==='학습가이드/index.html';if(!p&&!hub)fail('Unknown learning guide');
 const expected=p||data.hub;
 if(!html.includes(`name="description" content="${esc(expected.description)}"`))fail('Guide description changed');
 if((html.match(/<h1\b/g)||[]).length!==1)fail('Single main heading required');
 if(!html.includes(`rel="canonical" href="https://xn--3e0bz50bxucwzc.com${encodeURI(expected.route)}"`))fail('Guide canonical changed');
 const scripts=[...html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)];
 const graph=scripts.flatMap(m=>JSON.parse(m[1])['@graph']||[]);
 if(/편집\s*(원칙|기준)|daezang\.co\.kr|★★★★★|성적\s*보장/.test(html))fail('Prohibited policy or unverified outcome');
 if(hub){
  if(graph.some(n=>[n['@type']].flat().includes('Article')))fail('Collection mistaken for article');
  const list=graph.find(n=>n['@type']==='ItemList');
  if(!list||list.numberOfItems!==data.pages.length||list.itemListElement.length!==data.pages.length)fail('Incomplete static guide collection');
  for(const page of data.pages)if(!html.includes(`href="${encodeURI(page.route)}"`))fail('Static guide link missing');
  if((html.match(/data-guide-card /g)||[]).length!==data.pages.length)fail('Static guide card missing');
  for(const [key,label] of data.levels)if(!html.includes(`<option value="${key}">${label}</option>`))fail('Reader filter missing');
  return;
 }
 for(const id of ['check','steps','example','record','mistakes','next','faq','sources','related',...(p.legacy?['section-1','section-2','section-3','section-4']:[])])if(!html.includes(`id="${id}"`))fail('Learning section or legacy anchor missing');
 if(!html.includes(esc(p.answer)))fail('Direct answer missing');
 if(!html.includes(`href="${encodeURI(p.record)}" download=`))fail('Blank record download missing');
 if(!html.includes('연습 예시'))fail('Worked example label missing');
 if(!html.includes('data-guide-record')||!html.includes('data-record-download')||!html.includes('data-record-print'))fail('Local record editor missing');
 if((html.match(/data-record-field /g)||[]).length!==p.recordFields.length)fail('Record field inventory mismatch');
 const article=graph.find(n=>[n['@type']].flat().includes('Article'));
 if(!article||article.datePublished!==p.datePublished||article.dateModified!==data.updated)fail('Article dates mismatch');
 if(article.headline!==p.title||article.description!==p.description)fail('Article metadata mismatch');
 const citations=p.sources.map(key=>data.sources[key][3]);
 if(JSON.stringify(article.citation)!==JSON.stringify(citations))fail('Primary citations mismatch');
 for(const citation of citations)if(!html.includes(`href="${esc(citation)}"`))fail('Visible primary source missing');
 const faq=graph.find(n=>n['@type']==='FAQPage');
 if(!faq||faq.mainEntity.length!==p.faq.length)fail('FAQ schema mismatch');
 p.faq.forEach(([q,a],i)=>{if(!html.includes(`<summary>${esc(q)}</summary>`)||!html.includes(`<p>${esc(a)}</p>`)||faq.mainEntity[i].name!==q||faq.mainEntity[i].acceptedAnswer.text!==a)fail('FAQ content mismatch');});
}

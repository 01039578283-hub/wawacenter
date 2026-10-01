/** Keep student guidance faithful to the reviewed workbook and usable without JS. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./book-library-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.route.slice(1)+'index.html',p]));
const books=new Map(data.books.map(b=>[b.id,b]));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll("'",'&#x27;');
const url=route=>'https://xn--3e0bz50bxucwzc.com'+encodeURI(route);
const link=b=>encodeURI('/교재안내/'+b.field+'/#book-'+b.id.toLowerCase());
export function assertBookLibrary(html,name){
 const fail=reason=>{throw Error(`${name}: ${reason}`)};
 if(data.entryPages.includes(name)){
  if(!html.includes('id="book-discovery"')||!html.includes('href="'+encodeURI('/교재안내/')+'"'))fail('Book library entry missing');
 }
 if(!name.startsWith('교재안내/'))return;
 const p=pages.get(name);if(!p)fail('Unknown book page');
 if((html.match(/<h1\b/g)||[]).length!==1)fail('Single main heading required');
 if(!html.includes('rel="canonical" href="'+url(p.route)+'"'))fail('Book canonical changed');
 for(const meta of ['name="description"','property="og:description"','name="twitter:description"'])
  if(!html.includes(meta+' content="'+esc(p.description)+'"'))fail('Book description mismatch');
 if(p.description.length>80||!p.description.endsWith('.'))fail('Book description must be a short complete sentence');
 if(!html.includes('/assets/book-library.css'))fail('Book styles missing');
 if(/편집\s*(원칙|기준)|성적\s*보장|★★★★★|모든\s*지점에서\s*사용|실제\s*사용\s*교재입니다|공식\s*지정\s*교재/.test(html))fail('Unsupported claim in book guidance');
 const graph=[...html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].flatMap(m=>JSON.parse(m[1])['@graph']||[]);
 if(graph.some(n=>[n['@type']].flat().some(t=>['Product','Offer','AggregateRating','Review'].includes(t))))fail('Unverified commercial schema');
 const page=graph.find(n=>n['@id']===url(p.route)+'#webpage');
 if(!page||page.description!==p.description)fail('Page schema description mismatch');
 const article=graph.find(n=>[n['@type']].flat().includes('Article'));
 if(p.article){if(!article||article.headline!==p.title||article.description!==p.description||article.dateModified!==data.updated)fail('Article metadata mismatch');}
 else if(article)fail('Collection mistaken for article');
 const faq=graph.find(n=>n['@type']==='FAQPage');
 if(!faq||faq.mainEntity.length!==p.faqs.length)fail('FAQ inventory mismatch');
 p.faqs.forEach(([q,a],i)=>{
  if(!html.includes('<summary>'+esc(q)+'</summary>')||!html.includes('<p>'+esc(a)+'</p>')||faq.mainEntity[i].name!==q||faq.mainEntity[i].acceptedAnswer.text!==a)fail('FAQ content mismatch');
 });
 if(p.bookIds.length){
  if(!html.includes(esc(data.qualification)))fail('Level qualification missing');
  const listing=graph.find(n=>n['@type']==='ItemList');
  if(!listing||listing.numberOfItems!==p.bookIds.length||listing.itemListElement.length!==p.bookIds.length)fail('Book listing inventory mismatch');
  p.bookIds.forEach((id,i)=>{
   const b=books.get(id),item=listing.itemListElement[i];
   if(!b||item.name!==b.name||item.url!==url('/교재안내/'+b.field+'/#book-'+id.toLowerCase()))fail('Book listing target mismatch');
   if(!html.includes('href="'+link(b)+'"')&&p.route!=='/교재안내/'+b.field+'/')fail('Static book link missing');
  });
 }
 if(p.route==='/교재안내/'){
  const cards=[...html.matchAll(/<article\b([^>]*data-book-card[^>]*)>([\s\S]*?)<\/article>/g)];
  if(cards.length!==120)fail('Static catalog must contain all 120 books');
  const ids=new Set();
  for(const [,attrs,body] of cards){
   const id=attrs.match(/data-book-id="([^"]+)"/)?.[1],b=books.get(id);
   if(!b||ids.has(id))fail('Duplicate or unknown book');ids.add(id);
   for(const [key,value] of [['field',b.field],['level',b.level],['additional',b.additionalLevels.join(',')]])
    if(!attrs.includes('data-'+key+'="'+esc(value)+'"'))fail('Book classification differs');
   if(!attrs.includes('data-facts="'+esc(JSON.stringify({name:b.name,field:data.fields[b.field].label,publisher:b.publisher,area:b.area,student:b.student,condition:b.condition,level:data.levels[b.level],additional:b.additionalLevels.map(l=>data.levels[l]),route:'/교재안내/'+b.field+'/#book-'+id.toLowerCase()}))+'"'))fail('Comparison facts differ');
   if(!body.includes(esc(b.name))||!body.includes(esc(b.student)))fail('Book identity or target missing');
  }
 }else if(p.bookIds.length===20){
  const cards=[...html.matchAll(/<article\b([^>]*class="bk-book-detail"[^>]*)>([\s\S]*?)<\/article>/g)];
  if(cards.length!==20)fail('Full book details inventory mismatch');
  for(const [i,[,attrs,body]] of cards.entries()){
   const b=books.get(p.bookIds[i]);
   if(!attrs.includes('data-book-id="'+b.id+'"')||!attrs.includes('id="book-'+b.id.toLowerCase()+'"'))fail('Full book anchor mismatch');
   if(!attrs.includes('data-level="'+esc(b.level)+'"')||!attrs.includes('data-additional="'+esc(b.additionalLevels.join(','))+'"'))fail('Book classification differs');
   for(const key of ['name','publisher','area','student','condition','introduction'])if(!body.includes(esc(b[key])))fail('Reviewed book fact missing: '+key);
   if(!body.includes('href="'+esc(b.publicSourceUrl)+'"'))fail('Visible publisher source missing');
  }
 }else if(p.bookIds.length){
  const ids=[...html.matchAll(/data-plan-book="([^"]+)"/g)].map(m=>m[1]);
  if(JSON.stringify(ids)!==JSON.stringify(p.bookIds))fail('Level plan book mismatch');
  const routeParts=p.route.split('/'),plan=data.classes.find(c=>c.field===routeParts[2]&&data.levels[c.level]===routeParts[3]);
  for(const key of ['student','goal','condition'])if(!html.includes(esc(plan[key])))fail('Reviewed plan fact missing');
  if(!html.includes('id="practice"')||!html.includes('연습 예시'))fail('Worked activity missing');
 }else{
  const kind=p.route.split('/')[2];
  if(!html.includes('href="'+encodeURI('/assets/book-records/'+kind+'.txt')+'" download='))fail('Blank record download missing');
 }
}

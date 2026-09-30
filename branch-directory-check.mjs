/** Fail closed when a regenerated directory loses its factual distinctions. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./branch-directory-data.json',import.meta.url),'utf8'));
const branches=new Map(data.branches.map(b=>[b.route.slice(1)+'index.html',b]));
const plain=s=>s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim().replaceAll('&amp;','&').replaceAll('&quot;','"').replaceAll('&#x27;',"'").replaceAll('&#39;',"'");
const esc=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
export function assertBranchDirectory(html,name){
  if(!name.startsWith('지점안내/')&&!name.startsWith('학습시스템/'))return;
  const fail=message=>{throw Error(`${name}: ${message}`);};
  if(!/class="[^"]*bd-page/.test(html)||!html.includes('/assets/branch-directory.css'))fail('Directory styling missing');
  if([...html.matchAll(/<h1\b/g)].length!==1)fail('One main heading required');
  const desc=html.match(/<meta name="description" content="([^"]*)"/)?.[1];
  if(!desc||[...plain(desc)].length>80||!desc.endsWith('.'))fail('Description must be a complete sentence within 80 characters');
  for(const field of ['og:description','twitter:description'])if(!html.includes(`="${field}" content="${desc}"`))fail('Description channels differ');
  const graph=JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1]||'null')?.['@graph'];
  if(!graph)fail('Structured data missing');
  if(graph[0].description!==plain(desc))fail('Page schema description differs');
  const canonical=html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  if(!canonical||decodeURIComponent(new URL(canonical).pathname)!=='/'+name.replace(/index.html$/,''))fail('Canonical does not identify this page');
  const visible=[...html.matchAll(/<details class="bd-details" data-faq><summary>(.*?)<\/summary><div><p>(.*?)<\/p><\/div><\/details>/g)].map(m=>({q:plain(m[1]),a:plain(m[2])}));
  const schema=graph.find(n=>n['@type']==='FAQPage');
  if(JSON.stringify(visible)!==JSON.stringify((schema?.mainEntity||[]).map(n=>({q:n.name,a:n.acceptedAnswer.text}))))fail('Visible answers and FAQ schema disagree');
  if(/"@type"\s*:\s*"(?:Offer|Review|AggregateRating)"/.test(html))fail('Unverified pricing or review schema');
  if(/<iframe\b/i.test(html))fail('Video must load only after a visitor requests playback');
  const b=branches.get(name);if(!b)return;
  if(!html.includes(esc(b.address))||!html.includes(esc(b.registration)))fail('Branch address or registration missing');
  if(!html.includes(`href="${esc(b.feeUrl)}"`))fail('Branch tuition source missing');
  for(const c of b.courses){
    const tag=`data-course="${c.subject}" data-grades="${c.grades.join(',')}" data-pending="${c.pending.join(',')}"`;
    if(!html.includes(tag))fail('Confirmed and inquiry-only grades changed');
  }
  if(!b.fees.some(f=>f.kind==='branch')&&!html.includes('지점 확정 금액 아님'))fail('Generic fee table presented as branch pricing');
  const image=html.match(/<img\b[^>]*src="[^"]*assets\/centers\/common\/(?:seoul|local)6839\.webp"[^>]*>/)?.[0];
  if(!image||!image.includes('height="16116"')||!image.includes('loading="eager"')||/\bhidden(?:[\s=>])|\bstyle\s*=/.test(image))fail('Complete consultation image must stay visible');
  if(!b.bodyImage.mobile||!html.includes(encodeURI(b.bodyImage.mobile)))fail('Responsive mobile consultation image missing');
  if(html.slice(html.indexOf('<main'),html.indexOf(image)).includes('<details'))fail('Consultation image hidden behind a disclosure');
  if(!html.includes('href="tel:01068398283"')||html.includes('01039578283')||html.includes('010-3957-8283'))fail('Wrong consultation number');
  if(b.addressPending&&!html.includes('주소 자료가 서로 달라'))fail('Unresolved location must remain explicit');
  if(!b.photos.length&&!html.includes('개별 공간 사진을 확인하지 못했습니다'))fail('Common image mistaken for branch photograph');
}

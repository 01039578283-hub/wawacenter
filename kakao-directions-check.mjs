/** Protect branch matching, image order, local-only navigation and lazy maps. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./kakao-directions-data.json',import.meta.url),'utf8'));
const maps=JSON.parse(fs.readFileSync(new URL('./branch-map-data.json',import.meta.url),'utf8'));
const imageAreas=new Map(Object.values(maps.areas).map(a=>[a.image.src,a]));
const frames=new Map(Object.values(data.branches).filter(b=>b.approved).map(b=>[b.frame.slice(1),b]));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const count=(s,t)=>s.split(t).length-1;
export function assertKakaoMapFrame(html,name){
 const b=frames.get(name);if(!b)throw Error('Unreviewed Kakao frame: '+name);
 const fail=s=>{throw Error('Kakao frame '+s+': '+name);};
 for(const token of ['name="robots" content="noindex,nofollow"','/assets/kakao-map-frame.css','/assets/kakao-map-frame.js','data-timestamp="'+b.timestamp+'"','data-key="'+b.key+'"'])if(count(html,token)!==1)fail('missing or duplicated '+token);
 if(count(html,'https://t1.kakaocdn.net/kakaomapweb/roughmap/loader/prod/roughmapLoader.js')!==1)fail('one official loader required');
 if(/<a\b|<iframe\b|wawa-visit-collector|전화|tel:/i.test(html))fail('extra navigation, phone or duplicate analytics');
}
export function assertKakaoDirections(html,name){
 const fail=s=>{throw Error('Kakao directions '+s+': '+name);};
 let area;
 for(const [,src] of html.matchAll(/<img\b[^>]*src="([^"]+)"[^>]*>/g)){
  let path;try{path=decodeURIComponent(new URL(src,'https://example.invalid/'+name).pathname);}catch{continue;}
  if(imageAreas.has(path)){if(area)fail('multiple existing maps');area=imageAreas.get(path);}
 }
 if(!area){
  if(html.includes('data-kakao-directions'))fail('unexpected map on another page');
  if(name==='지점안내/index.html'||/^지점안내\/[^/]+\/index\.html$/.test(name)){
   for(const card of html.matchAll(/<article\b[^>]*\bdata-branch-card\b[^>]*>[\s\S]*?<\/article>/g)){
    const href=/<h3><a href="([^"]+)"/.exec(card[0])?.[1];if(!href)continue;
    const route=decodeURIComponent(new URL(href,'https://example.invalid').pathname),b=data.branches[route];
    if(b?.approved){const links=[...card[0].matchAll(/href="([^"]*#directions)"/g)];if(links.length!==1||decodeURIComponent(links[0][1])!==route+'#directions')fail('wrong or missing hub destination');}
   }
  }
  return;
 }
 const b=data.branches[area.branch];if(!b)fail('unknown mapped branch');
 if(!b.approved){if(html.includes('data-kakao-directions'))fail('unconfirmed map published');return;}
 if(count(html,'<!-- kakao-directions:start -->')!==1||count(html,'<!-- kakao-directions:end -->')!==1)fail('one directions section required');
 const start=html.indexOf('<!-- kakao-directions:start -->'),before=html.slice(0,start);
 if(!before.endsWith('<!-- branch-map:end -->')&&!/<section\b[^>]*\bimage-first-location\b[^>]*>[\s\S]*?<\/section>$/.test(before))fail('must follow existing map section');
 const end='<!-- kakao-directions:end -->';
 const block=html.slice(start,html.indexOf(end)+end.length);
 for(const token of ['id="directions"','id="directions-title"','data-kakao-branch="'+esc(b.name)+'"','src="'+b.frame+'"','loading="lazy"','height="400"','sandbox="allow-scripts"'])if(count(block,token)!==1)fail('missing or duplicated '+token);
 if(/<a\b|<button\b|<input\b|전화|tel:|로드뷰|길찾기|지도 크게/.test(block))fail('map section has forbidden action or phone');
 if(/\bhidden\b|display\s*:\s*none|visibility\s*:\s*hidden/.test(block))fail('directions must remain visible');
 if(count(html,'href="/assets/kakao-directions.css"')!==1||count(html,'href="#directions"')!==1)fail('one shared stylesheet and shortcut required');
 if(/kakaocdn\.net\/kakaomapweb/.test(html))fail('vendor script must stay in the lazy frame');
 for(const s of b.subways)for(const value of [s.line,s.name])if(!block.includes(esc(value)))fail('missing source subway');
 for(const s of b.busStops)if(!block.includes(esc(s.name)))fail('missing source stop');
 for(const g of b.busGroups)for(const value of [g.type,...g.routes])if(!block.includes(esc(value)))fail('missing source bus');
}

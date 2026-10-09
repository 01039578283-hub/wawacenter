/** Keep the reviewed representative photo visible in its original lower position. */
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./branch-representative-data.json',import.meta.url),'utf8'));
const pages=new Map(data.pages.map(p=>[p.file,p]));
export function assertBranchRepresentative(html,name){
 const p=pages.get(name);if(!p)return;
 const fail=message=>{throw Error(`${name}: branch representative ${message}`)};
 const head=html.slice(0,html.indexOf('</head>'));
 for(const field of ['og:image','twitter:image']){
  const tags=[...head.matchAll(new RegExp(`<meta\\b[^>]*(?:property|name)="${field}"[^>]*>`,'g'))];
  if(tags.length!==1||!tags[0][0].includes(`content="${p.imageUrl}"`))fail('image metadata missing, duplicated or inconsistent');
 }
 const images=[...html.matchAll(/<img\b[^>]*data-branch-representative="[^"]*"[^>]*>/g)];
 if(images.length!==1)fail('one visible representative required');
 const img=images[0];
 const source=new URL(img[0].match(/\bsrc="([^"]+)"/)?.[1]??'',p.url).href;
 if(source!==p.imageUrl||!img[0].includes(`width="${p.width}"`)||!img[0].includes(`height="${p.height}"`))fail('body image or dimensions differ');
 if(/\bhidden(?:[\s=>])|display\s*:\s*none/.test(img[0]))fail('hidden photograph');
 const bodyImage=html.indexOf('height="16116"');
 if(!(bodyImage<img.index&&img.index<html.indexOf('</main>')))fail('photograph must follow the full lesson image inside main');
 if(!p.existingLowerPhoto&&!html.includes('<!-- branch-representative:end --></main>'))fail('new photograph must be at the end of main');
 if(!p.actualBranchPhoto&&!html.includes('실제 공간을 촬영한 사진은 아니며'))fail('common photograph attribution missing');
 if(/<img\b[^>]*style="display:none;"/.test(html))fail('old hidden representative remains');
 if(!html.includes('/assets/branch-representative.css'))fail('photo proportions stylesheet missing');
}

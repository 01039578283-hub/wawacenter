import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./home-coaching-data.json',import.meta.url),'utf8'));
const plain=s=>s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export function assertHomeCoaching(html,name){
 if(name!=='index.html')return;
 const fail=m=>{throw Error('Home coaching: '+m);};
 for(const id of ['home-coaching','lesson-comparison','coaching-process','learning-record','home-branch-search','home-new-guides','home-library','home-education'])
  if((html.match(new RegExp('id="'+id+'"','g'))||[]).length!==1)fail('missing or repeated '+id);
 const rows=[...html.matchAll(/<div class="hc-compare-row" data-comparison="\d+"><h3>(.*?)<\/h3><div class="hc-lecture"><span class="hc-cell-label">.*?<\/span><p>(.*?)<\/p><\/div><div class="hc-individual"><span class="hc-cell-label">.*?<\/span><p>(.*?)<\/p><\/div><\/div>/gs)];
 if(rows.length!==10||JSON.stringify(rows.map(m=>m.slice(1).map(plain)))!==JSON.stringify(data.comparison))fail('both readable comparison columns required');
 const steps=[...html.matchAll(/data-coaching-step="([^"]+)"/g)].map(m=>m[1]);
 if(JSON.stringify(steps)!==JSON.stringify(['Check','Curriculum','Consulting','Coaching']))fail('4C sequence differs from brand source');
 if(!html.includes('학교 진도와 시험 범위도 함께 고려합니다.')||!html.includes('실제 학생의 성적·후기나 모든 지점의 공통 양식을 뜻하지 않습니다.'))fail('learning direction and example context missing');
 const faq=/<div class="faq" id="faq">([\s\S]*?)<\/div>/.exec(html)?.[1];
 const visible=[...(faq||'').matchAll(/<summary>(.*?)<\/summary>\s*<p>(.*?)<\/p>/gs)].map(m=>m.slice(1).map(plain));
 const graph=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m=>{const n=JSON.parse(m[1]);return n['@graph']||[n];});
 const faqNodes=graph.filter(n=>n['@type']==='FAQPage');
 if(faqNodes.length!==1||JSON.stringify(faqNodes[0].mainEntity.map(n=>[n.name,n.acceptedAnswer.text]))!==JSON.stringify(visible)||visible.length!==6)fail('visible FAQ and metadata differ');
 if(!html.includes('<meta name="description" content="'+esc(data.description)+'">'))fail('reviewed summary differs');
 const photo=new RegExp('<img src="/'+data.photo.file+'"[^>]*>').exec(html)?.[0]||'';
 if(!photo.includes('loading="lazy"')||!photo.includes('width="626"')||!photo.includes('height="417"'))fail('source photo dimensions/lazy loading missing');
 for(const route of ['/학습가이드/학원수업비교/','/학습가이드/학습플래너작성법/','/학습시스템/개별맞춤관리/','/학습시스템/와와학습코칭/#official-video','/지점안내/'])
  if(!html.includes('href="'+encodeURI(route)+'"'))fail('relevant internal destination missing');
}

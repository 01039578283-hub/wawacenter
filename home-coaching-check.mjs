import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./home-coaching-data.json',import.meta.url),'utf8'));
const plain=s=>s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export function assertHomeCoaching(html,name){
 if(name!=='index.html')return;
 const fail=m=>{throw Error('Home coaching: '+m);};
 for(const id of ['home-coaching','lesson-comparison','coaching-process','learning-record','home-branch-search','home-new-guides','home-library','home-education'])
  if((html.match(new RegExp('id="'+id+'"','g'))||[]).length!==1)fail('missing or repeated '+id);
 const rows=[...html.matchAll(/<tr class="hc-compare-row" data-comparison="\d+"><th scope="row" id="compare-row-\d+">(.*?)<\/th><td class="hc-lecture" headers="compare-lecture compare-row-\d+"><span class="hc-cell-label" aria-hidden="true">.*?<\/span><p>(.*?)<\/p><\/td><td class="hc-individual" headers="compare-individual compare-row-\d+"><span class="hc-cell-label" aria-hidden="true">.*?<\/span><p>(.*?)<\/p><\/td><\/tr>/gs)];
 if(rows.length!==10||JSON.stringify(rows.map(m=>m.slice(1).map(plain)))!==JSON.stringify(data.comparison))fail('both readable comparison columns required');
 if(!html.includes('<table class="hc-compare-table"><caption>수업을 선택할 때 살펴볼 10가지 기준</caption>') || !html.includes('id="compare-lecture"') || !html.includes('id="compare-individual"'))fail('semantic comparison table and column labels required');
 for(const id of ['question-learning','planner-support'])if((html.match(new RegExp('id="'+id+'"','g'))||[]).length!==1)fail('missing or repeated '+id);
 if((html.match(/data-planner-point="\d+"/g)||[]).length!==7)fail('seven practical planner points required');
 for(const [title,record,copy,route] of data.plannerSupport)if(!html.includes(esc(title))||!html.includes(esc(record))||!html.includes(esc(copy))||!html.includes('href="'+encodeURI(route)+'"'))fail('reviewed planner guidance or reading link missing');
 for(const [title,copy] of data.questionCycle)if(!html.includes(esc(title))||!html.includes(esc(copy)))fail('question and independent retry sequence missing');
 for(const im of data.additionalImages){const tag=new RegExp('<img class="hc-support-icon" src="/'+im.file+'"[^>]*>').exec(html)?.[0]||'';if(!tag.includes('loading="lazy"')||!tag.includes('width="'+im.width+'"')||!tag.includes('height="'+im.height+'"')||!tag.includes('alt="'+esc(im.alt)+'"'))fail('introduction illustration or dimensions missing');}
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

import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('./site-shell-data.json',import.meta.url),'utf8'));
const selected=new Set(data.pages);
const plain=s=>s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
export function assertSiteShell(html,name){
  if(!selected.has(name))return;
  const fail=message=>{throw Error('Site shell '+name+': '+message);};
  if(!/<body\b[^>]*data-site-shell="1"/.test(html))fail('shared body theme missing');
  if((html.match(/href="\/assets\/site-shell.css"/g)||[]).length!==1)fail('one shared stylesheet required');
  const styles=[...html.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"/g)];
  if(styles.at(-1)?.[1]!=='/assets/site-shell.css')fail('shared styles must be loaded last');
  const headers=[...html.matchAll(/<header class="site-header" data-site-header="1">([\s\S]*?)<\/header>/g)];
  if(headers.length!==1)fail('one consistent header required');
  const h=headers[0][1];
  if(!h.includes('aria-label="전국수업.com 홈"') || !h.includes('<strong>전국수업.com</strong><small>와와센터 학습코칭</small>'))fail('site brand changed');
  const nav=/<nav class="nav" aria-label="상단 메뉴">([\s\S]*?)<\/nav>/.exec(h);
  const anchors=[...(nav?.[1]||'').matchAll(/<a\b([^>]*)>(.*?)<\/a>/g)];
  const actual=anchors.map(a=>[plain(a[2]),decodeURIComponent(/href="([^"]+)"/.exec(a[1])?.[1]||'')]);
  if(JSON.stringify(actual)!==JSON.stringify(data.nav))fail('navigation labels, order or destinations differ');
  const route=name==='index.html'?'/':'/'+name.replace(/index.html$/,'');
  const current=data.nav.slice(1).find(([,p])=>route.startsWith(p))?.[1] || (route==='/'?'/':null);
  for(let i=0;i<anchors.length;i++)if(anchors[i][1].includes('aria-current="page"')!==(data.nav[i][1]===current))fail('incorrect current section');
  if(!h.includes('https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform'))fail('consultation destination changed');
  if(name==='index.html')for(const route of ['/학습시스템/와와학습코칭/#official-video','/학습시스템/개별맞춤관리/','/학습시스템/AI학습/'])
    if(!html.includes('href="'+encodeURI(route)+'"'))fail('home program shortcut missing');
  if(name.startsWith('학습시스템/')){
    const d=data.descriptions[route];
    if(!d||d.length>80||!d.endsWith('.'))fail('reviewed program description missing');
    if(!html.includes('<meta name="description" content="'+d+'">'))fail('program description changed');
    if(name==='학습시스템/index.html'&&!html.includes('data-video-id="59Tna9pZWrk"'))fail('official introduction missing on program hub');
    if(name==='학습시스템/와와학습코칭/index.html'){
      for(const id of data.videoIds)if(!html.includes('data-video-id="'+id+'"')||!html.includes('https://www.youtube.com/watch?v='+id))fail('official video or direct fallback missing');
      if(!html.includes('id="individual-study"'))fail('individual study explanation missing');
    }
    if(name==='학습시스템/개별맞춤관리/index.html')for(const text of ['플랜 관리','학습 관리','생활 관리','백지노트','마인드맵','둥지 시스템'])if(!html.includes(text))fail('official management topic missing');
    if(name==='학습시스템/AI학습/index.html'){
      if(!html.includes('실제 도입 여부·개설 과목·등록 학년·교재와 추가 비용은 지점별로 확인'))fail('program/branch distinction missing');
      const ids={영어:'ai-english',수학:'ai-math',국어:'ai-korean',독서:'ai-reading'};
      for(const [subject,range] of Object.entries(data.aiRanges)){
        const section=new RegExp('<section class="pg-section" id="'+ids[subject]+'"([\\s\\S]*?)<\\/section>').exec(html)?.[1];
        if(!section?.includes('공식 대상 범위 · '+range))fail('incorrect official '+subject+' target range');
      }
    }
  }
}

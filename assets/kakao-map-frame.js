/* Each lazy frame contains one supplied Kakao roughmap; the parent stays light. */
(() => {
  'use strict';
  const root=document.querySelector('[data-kakao-map]');
  if(!root)return;
  const status=document.querySelector('[data-map-status]');
  let lander,lastWidth=0,configured=false;
  // These maps are read in place. Marker actions must not open another site.
  window.open=()=>null;
  function tidy(){
    root.querySelectorAll('.cont,.wrap_btn_roadview,.btn_big_map').forEach(el=>el.remove());
    root.querySelectorAll('a[href]').forEach(a=>{
      if(/^(?:https?:)?\/\//i.test(a.getAttribute('href')||'')){
        a.removeAttribute('href');a.removeAttribute('target');a.removeAttribute('rel');a.removeAttribute('tabindex');
        a.querySelectorAll('img').forEach(img=>{if(/새창|이동/.test(img.alt))img.alt='카카오맵';});
      }
    });
    if(lander?.jsMap && root.querySelector('.roughmap_maker_label')){
      if(!configured){lander.jsMap.setZoomable(false);lander.jsMap.setDraggable(innerWidth>600);configured=true;}
      if([...root.querySelectorAll('.map img')].some(i=>/\/tile\//.test(i.src)&&i.complete&&i.naturalWidth>0))document.body.dataset.mapState='ready';
    }
  }
  new MutationObserver(tidy).observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['href']});
  root.addEventListener('load',tidy,true);
  document.addEventListener('click',event=>{
    const a=event.target.closest?.('a');
    if(a && /^(?:https?:)?\/\//i.test(a.getAttribute('href')||'')){event.preventDefault();event.stopImmediatePropagation();}
  },true);
  function resize(){
    const width=Math.max(200,Math.floor(document.documentElement.clientWidth));
    if(width===lastWidth)return;lastWidth=width;
    if(lander?.jsMap){lander.jsMap.relayout();lander.jsMap.setCenter(lander.getMapCenter());lander.jsMap.setDraggable(width>600);}
  }
  function start(){
    if(!window.daum?.roughmap?.Lander){if(status)status.textContent='지도를 불러오지 못했습니다. 아래 주소와 교통정보를 확인해 주세요.';return;}
    lastWidth=Math.max(200,Math.floor(document.documentElement.clientWidth));
    lander=new daum.roughmap.Lander({timestamp:root.dataset.timestamp,key:root.dataset.key,mapWidth:String(lastWidth),mapHeight:'360'});
    try{lander.render();}catch{if(status)status.textContent='지도를 불러오지 못했습니다. 아래 주소와 교통정보를 확인해 주세요.';}
    if('ResizeObserver' in window)new ResizeObserver(resize).observe(document.documentElement);
    window.addEventListener('resize',resize,{passive:true});
    setTimeout(()=>{if(document.body.dataset.mapState!=='ready' && status)status.textContent='지도 연결이 지연되고 있습니다. 아래 주소와 교통정보를 먼저 확인해 주세요.';},20000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

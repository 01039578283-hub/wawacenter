/* Progressive filters: complete article and regional links exist without JS. */
(()=>{
 const form=document.querySelector('[data-education-filter]');
 if(form){
  const cards=[...document.querySelectorAll('[data-education-card]')],status=document.querySelector('[data-education-status]'),empty=document.querySelector('[data-education-empty]');
  function filter(){const q=form.elements.q.value.trim().toLocaleLowerCase(),group=form.elements.group.value,stage=form.elements.stage.value;let count=0;
   for(const card of cards){const match=(!q||card.dataset.search.toLocaleLowerCase().includes(q))&&(!group||card.dataset.group===group)&&(!stage||card.dataset.stages.includes(stage));card.hidden=!match;if(match)count++;}
   status.textContent=count+'개 교육정보 글이 있습니다.';empty.hidden=count!==0;
  }
  form.addEventListener('input',filter);form.addEventListener('change',filter);form.addEventListener('submit',e=>e.preventDefault());form.addEventListener('reset',()=>setTimeout(filter,0));
  document.querySelectorAll('[data-education-group]').forEach(a=>a.addEventListener('click',()=>{form.elements.group.value=a.dataset.educationGroup;filter();}));
 }
 const finder=document.querySelector('[data-education-finder]');
 if(!finder)return;
 const message=finder.querySelector('[data-finder-status]');
 fetch('/assets/education-centers.json').then(r=>{if(!r.ok)throw Error('index unavailable');return r.json();}).then(data=>{
  const region=finder.querySelector('[name=region]'),branch=finder.querySelector('[name=branch]'),area=finder.querySelector('[name=area]'),branchLink=finder.querySelector('[data-finder-branch]'),areaLink=finder.querySelector('[data-finder-area]');
  function option(value,label){const o=document.createElement('option');o.value=value;o.textContent=label;return o;}
  function setLink(el,route,label){el.href=encodeURI(route);el.textContent=label;}
  function updateArea(){const b=data.branches.find(b=>b.route===branch.value);if(!b)return;const a=b.areas.find(a=>a.slug===area.value);setLink(areaLink,a?.route||b.route,a?a.name+' 동네 수업 안내':b.name+' 안내');}
  function updateBranch(){const b=data.branches.find(b=>b.route===branch.value);area.replaceChildren(option('','동네 선택'));if(b){for(const a of b.areas)area.append(option(a.slug,a.name));area.value=b.areas[0]?.slug||'';setLink(branchLink,b.route,b.name+' 지점 정보');message.textContent=b.name+'의 연결 동네와 실제 등원 주소는 지점 안내에서 확인하세요.';updateArea();}else{setLink(branchLink,region.value?'/지점안내/'+region.value+'/':'/지점안내/','지역 지점 목록 보기');setLink(areaLink,'/전국센터/','동네별 수업 안내');message.textContent='지점을 선택하면 해당 지점과 연결 동네로 이동할 수 있습니다.';}area.disabled=!b;}
  function updateRegion(){branch.replaceChildren(option('','지점 선택'));for(const b of data.branches.filter(b=>b.region===region.value))branch.append(option(b.route,b.name));branch.disabled=!region.value;updateBranch();}
  for(const r of data.regions)region.append(option(r,r));region.addEventListener('change',updateRegion);branch.addEventListener('change',updateBranch);area.addEventListener('change',updateArea);finder.querySelector('[data-finder-fields]').hidden=false;updateRegion();
 }).catch(()=>{message.textContent='아래 지역별 지점 목록에서 희망 지점을 찾아보세요.';});
})();

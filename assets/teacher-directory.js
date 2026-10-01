/* Every branch and profile remains available without JavaScript. */
(() => {
  const form=document.querySelector('[data-teacher-search]');if(!form)return;
  const query=form.querySelector('input'),region=form.querySelector('select');
  const cards=[...document.querySelectorAll('[data-teacher-card]')];
  const status=document.querySelector('[data-teacher-status]'),empty=document.querySelector('[data-teacher-empty]');
  const normalize=value=>value.normalize('NFKC').toLocaleLowerCase('ko').replace(/[\s*]+/g,'');
  const params=new URLSearchParams(location.search);query.value=params.get('q')||'';
  if([...region.options].some(o=>o.value===params.get('region')))region.value=params.get('region');
  const apply=()=>{let count=0,total=0;const words=query.value.trim().split(/\s+/).filter(Boolean).map(normalize);
    for(const card of cards){const match=(!region.value||card.dataset.region===region.value)&&words.every(w=>normalize(card.dataset.search).includes(w));card.hidden=!match;if(match){count++;total+=Number(card.dataset.count);}}
    status.textContent=`검색 결과: ${count}개 지점 · 선생님 소개 ${total}건`;empty.hidden=count!==0;
  };
  query.addEventListener('input',apply);region.addEventListener('change',apply);form.addEventListener('submit',e=>{e.preventDefault();apply();});form.addEventListener('reset',()=>setTimeout(apply,0));apply();
})();

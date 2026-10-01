/* Progressive enhancement: all forty guide links exist in the static HTML. */
(()=>{
 const form=document.querySelector('[data-guide-search]');if(!form)return;
 const input=form.querySelector('input[type="search"]');
 const buttons=[...form.querySelectorAll('[data-guide-filter]')];
 const cards=[...document.querySelectorAll('[data-guide-card]')];
 const groups=[...document.querySelectorAll('[data-guide-group]')];
 const status=document.querySelector('[data-guide-status]');
 const empty=document.querySelector('[data-guide-empty]');
 let category='';
 const normalize=value=>value.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g,' ').trim();
 function render(){
  const terms=normalize(input.value).split(' ').filter(Boolean);let count=0;
  for(const card of cards){const haystack=normalize(card.dataset.search);const match=(!category||card.dataset.category===category)&&terms.every(t=>haystack.includes(t));card.hidden=!match;if(match)count++;}
  for(const group of groups){const count=[...group.querySelectorAll('[data-guide-card]')].filter(card=>!card.hidden).length;group.hidden=!count;group.querySelector('[data-group-count]').textContent=count+'개';}
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.guideFilter===category)));
  status.textContent=count+'개 가이드를 볼 수 있습니다.';empty.hidden=count!==0;
 }
 form.addEventListener('submit',event=>{event.preventDefault();render();});
 input.addEventListener('input',render);
 buttons.forEach(button=>button.addEventListener('click',()=>{category=button.dataset.guideFilter;render();}));
 form.addEventListener('reset',()=>{category='';input.value='';render();});
 render();
})();

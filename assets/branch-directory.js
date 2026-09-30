/* Progressive enhancement: links, facts and source videos work without JS. */
(() => {
  const form=document.querySelector('[data-branch-search]');
  if(form){
    const query=form.querySelector('input'),region=form.querySelector('select');
    const cards=[...document.querySelectorAll('[data-branch-card]')];
    const status=document.querySelector('[data-search-status]'),empty=document.querySelector('[data-search-empty]');
    const normalize=value=>value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g,'');
    const apply=()=>{
      const words=query.value.trim().split(/\s+/).filter(Boolean).map(normalize);
      let count=0;
      for(const card of cards){
        const match=(!region.value||card.dataset.region===region.value)&&words.every(w=>normalize(card.dataset.search).includes(w));
        card.hidden=!match;if(match)count++;
      }
      status.textContent=`${count}개 지점이 있습니다.`;empty.hidden=count!==0;
    };
    form.addEventListener('submit',event=>{event.preventDefault();apply();});
    query.addEventListener('input',apply);region.addEventListener('change',apply);
    form.addEventListener('reset',()=>{setTimeout(apply,0);});
    apply();
  }
  const ids=new Set(['59Tna9pZWrk','avpJfW7eIV0','f_skFu40U04','UIXUaBZdNXU']);
  for(const button of document.querySelectorAll('[data-video-id]')){
    button.addEventListener('click',()=>{
      const id=button.dataset.videoId;if(!ids.has(id))return;
      const frame=document.createElement('iframe');
      frame.src=`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`;
      frame.title=button.dataset.videoTitle;
      frame.allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.referrerPolicy='strict-origin-when-cross-origin';frame.allowFullscreen=true;
      button.replaceWith(frame);frame.focus();
    },{once:true});
  }
})();

// Records stay in the current page. No storage, analytics event or submission.
for(const form of document.querySelectorAll('form[data-study-record]')){
 const fields=[...form.querySelectorAll('textarea[data-record-label]')];
 const status=form.querySelector('[role="status"]');
 const title=form.dataset.recordTitle;
 form.addEventListener('submit',event=>event.preventDefault());
 form.querySelector('[data-record-download]').addEventListener('click',()=>{
  const lines=[title,location.href.split('#')[0],'',...fields.flatMap(field=>[field.dataset.recordLabel,field.value.trim()||'(아직 작성하지 않음)',''])];
  const blob=new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=form.dataset.recordFile;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  status.textContent='작성한 기록을 TXT 파일로 저장했습니다. 이 페이지를 닫기 전에 필요한 내용을 저장해 주세요.';
 });
 form.addEventListener('reset',()=>{status.textContent='작성 칸을 비웠습니다.';});
 form.querySelector('.sr-actions').hidden=false;
}

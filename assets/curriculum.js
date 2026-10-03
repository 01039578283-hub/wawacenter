/* All destinations are server-rendered; filtering only narrows the visible list. */
(() => {
  const form = document.querySelector('[data-curriculum-filter]');
  if (!form) return;
  const cards = [...document.querySelectorAll('[data-curriculum-card]')];
  const status = document.querySelector('[data-curriculum-status]');
  const empty = document.querySelector('[data-curriculum-empty]');
  const field = name => form.elements.namedItem(name);
  const value = name => field(name)?.value || '';
  const sync = () => {
    const stage = value('stage');
    for (const option of field('grade').options) {
      const unavailable = !!(stage && option.value && option.dataset.stage !== stage);
      option.hidden = unavailable;
      option.disabled = unavailable;
    }
    if (field('grade').selectedOptions[0]?.disabled) field('grade').value = '';
    const tokens = value('q').toLocaleLowerCase('ko-KR').trim().split(/\s+/).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const visible = (!stage || card.dataset.stage === stage) && (!value('grade') || card.dataset.grade === value('grade')) && (!value('subject') || card.dataset.subject === value('subject')) && tokens.every(t => card.dataset.search.toLocaleLowerCase('ko-KR').includes(t));
      card.hidden = !visible;
      if (visible) count++;
    }
    status.textContent = count + '개 학년·과목 안내가 있습니다.';
    empty.hidden = count > 0;
    const url = new URL(location.href);
    for (const name of ['q', 'stage', 'grade', 'subject']) {
      if (value(name)) url.searchParams.set(name, value(name));
      else url.searchParams.delete(name);
    }
    history.replaceState(null, '', url);
  };
  const params = new URLSearchParams(location.search);
  for (const name of ['q', 'stage', 'grade', 'subject']) {
    const input = field(name);
    if (!input || !params.has(name)) continue;
    if (input.tagName !== 'SELECT' || [...input.options].some(o => o.value === params.get(name))) input.value = params.get(name);
  }
  form.addEventListener('input', sync);
  form.addEventListener('change', sync);
  form.addEventListener('submit', event => { event.preventDefault(); sync(); });
  // The reset event runs before the browser restores default form values.
  form.addEventListener('reset', () => setTimeout(sync, 0));
  window.addEventListener('pageshow', sync);
  sync();
})();

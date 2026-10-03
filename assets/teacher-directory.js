/* All introductions and links remain readable without JavaScript. */
(() => {
  const directory = document.querySelector('[data-teacher-search]');
  const profiles = document.querySelector('[data-profile-search]');
  const form = directory || profiles;
  if (!form) return;
  const query = form.elements.q, region = form.elements.region, need = form.elements.need;
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/[\s*]+/g, '');
  const words = () => query.value.trim().split(/\s+/).filter(Boolean).map(normalize);
  const status = document.querySelector(directory ? '[data-teacher-status]' : '[data-profile-status]');
  const empty = document.querySelector(directory ? '[data-teacher-empty]' : '[data-profile-empty]');
  const cards = [...document.querySelectorAll(directory ? '[data-teacher-card]' : '[data-teacher-profile]')];
  const tools = document.querySelector('[data-profile-tools]');
  const matches = (person, local, terms) =>
    (!need.value || person.dataset.needs.split(' ').includes(need.value)) &&
    terms.every(word => normalize(local + ' ' + person.dataset.search).includes(word));

  const restore = () => {
    const params = new URLSearchParams(location.search);
    query.value = params.get('q') || '';
    for (const field of [region, need].filter(Boolean)) {
      const value = params.get(field.name) || '';
      field.value = [...field.options].some(option => option.value === value) ? value : '';
    }
  };
  const apply = (updateUrl = true) => {
    let branches = 0, total = 0;
    const terms = words();
    for (const card of cards) {
      if (directory) {
        const inRegion = !region.value || card.dataset.region === region.value;
        const people = [...card.querySelectorAll('[data-teacher-option]')];
        let count = 0;
        for (const person of people) {
          person.hidden = !(inRegion && matches(person, card.dataset.localSearch, terms));
          if (!person.hidden) count++;
        }
        card.hidden = count === 0;
        card.querySelector('[data-card-count]').textContent = '선생님 소개 ' + count + '건';
        if (count) { branches++; total += count; }
      } else {
        card.hidden = !matches(card, '', terms);
        if (!card.hidden) total++;
      }
    }
    status.textContent = directory
      ? `검색 결과: ${branches}개 지점 · 선생님 소개 ${total}건`
      : `검색 결과: 선생님 소개 ${total}건`;
    empty.hidden = total !== 0;
    if (tools) for (const button of tools.querySelectorAll('button')) button.disabled = total === 0;
    if (updateUrl) {
      const url = new URL(location.href);
      for (const field of [query, region, need].filter(Boolean)) {
        const value = field.value.trim();
        value ? url.searchParams.set(field.name, value) : url.searchParams.delete(field.name);
      }
      // A search must not keep a shortcut to a now-hidden profile.
      if (profiles && url.hash.startsWith('#teacher-')) {
        const target = document.getElementById(url.hash.slice(1));
        if (target?.hasAttribute('data-teacher-profile') && target.hidden) url.hash = '';
      }
      history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  };
  const showAnchor = () => {
    if (!profiles || !location.hash.startsWith('#teacher-')) return;
    const target = document.getElementById(location.hash.slice(1));
    if (!target?.hasAttribute('data-teacher-profile')) return;
    if (target.hidden) { query.value = ''; need.value = ''; apply(); }
    target.scrollIntoView({ block: 'start' });
  };
  form.hidden = false;
  if (tools) tools.hidden = false;
  restore(); apply(false); showAnchor();
  query.addEventListener('input', () => apply());
  for (const field of [region, need].filter(Boolean)) field.addEventListener('change', () => apply());
  form.addEventListener('submit', event => { event.preventDefault(); apply(); });
  form.addEventListener('reset', () => setTimeout(() => apply(), 0));
  window.addEventListener('popstate', () => { restore(); apply(false); showAnchor(); });
  window.addEventListener('hashchange', showAnchor);
  if (tools) tools.addEventListener('click', event => {
    const button = event.target.closest('[data-profile-details]');
    if (!button) return;
    for (const card of cards.filter(card => !card.hidden))
      card.querySelector('details').open = button.dataset.profileDetails === 'open';
  });
})();

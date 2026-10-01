(() => {
  'use strict';
  const form = document.querySelector('[data-book-search]');
  if (!form) return;
  const cards = Array.from(document.querySelectorAll('[data-book-card]'));
  const query = form.elements.namedItem('q');
  const field = form.elements.namedItem('field');
  const level = form.elements.namedItem('level');
  const additional = form.elements.namedItem('additional');
  const status = document.querySelector('[data-book-status]');
  const empty = document.querySelector('[data-book-empty]');
  const comparison = document.querySelector('[data-book-comparison]');
  const comparisonGrid = document.querySelector('[data-comparison-grid]');
  const comparisonStatus = document.querySelector('[data-comparison-status]');
  const comparisonDock = document.querySelector('[data-comparison-dock]');
  const comparisonCount = document.querySelector('[data-comparison-count]');
  const selected = new Map();
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g, ' ').trim();
  function filter() {
    const words = normalize(query.value).split(' ').filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const levels = [card.dataset.level];
      if (additional.checked) levels.push(...card.dataset.additional.split(',').map(item => item.trim()));
      const matches = (!field.value || field.value === card.dataset.field)
        && (!level.value || levels.includes(level.value))
        && words.every(word => normalize(card.dataset.search).includes(word));
      card.hidden = !matches;
      if (matches) count++;
    }
    status.textContent = `전체 120종 중 ${count}종이 표시됩니다.`;
    empty.hidden = count !== 0;
  }
  function element(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }
  function renderComparison() {
    comparisonGrid.replaceChildren();
    comparison.hidden = selected.size === 0;
    comparisonDock.hidden = selected.size === 0;
    comparisonCount.textContent = `${selected.size}종 교재 비교 보기`;
    comparisonStatus.textContent = `${selected.size}종을 비교하고 있습니다. 검색 조건을 바꿔도 비교 목록은 유지됩니다.`;
    for (const [id, facts] of selected) {
      const article = element('article', undefined, 'bk-compare-card');
      article.dataset.comparisonId = id;
      article.append(element('h3', facts.name));
      const dl = element('dl');
      const rows = [
        ['학년·과목', facts.field], ['출판사', facts.publisher], ['학습 영역', facts.area],
        ['대상 학생', facts.student], ['권·단계 선택 조건', facts.condition],
        ['선택 참고 분류', facts.level + (facts.additional.length ? ' / 추가: ' + facts.additional.join('·') : '')],
      ];
      for (const [label, value] of rows) dl.append(element('dt', label), element('dd', value));
      article.append(dl);
      const link = element('a', '교재 설명과 출처 확인');
      link.href = facts.route;
      article.append(link);
      const remove = element('button', '비교에서 제외');
      remove.type = 'button';
      remove.setAttribute('aria-label', facts.name + ' 비교에서 제외');
      remove.addEventListener('click', () => {
        selected.delete(id);
        const card = cards.find(item => item.dataset.bookId === id);
        card.querySelector('[data-book-compare]').checked = false;
        renderComparison();
        if (selected.size) comparisonGrid.querySelector('button').focus();
        else query.focus();
      });
      article.append(remove);
      comparisonGrid.append(article);
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); filter(); });
  form.addEventListener('input', filter);
  form.addEventListener('change', filter);
  form.addEventListener('reset', event => {
    event.preventDefault();
    query.value = '';
    field.value = '';
    level.value = '';
    additional.checked = true;
    filter();
  });
  for (const card of cards) {
    const facts = JSON.parse(card.dataset.facts);
    card.querySelector('[data-compare-control]').hidden = false;
    card.querySelector('[data-book-compare]').addEventListener('change', event => {
      if (event.target.checked) selected.set(card.dataset.bookId, facts);
      else selected.delete(card.dataset.bookId);
      renderComparison();
    });
  }
  document.querySelector('[data-comparison-clear]').addEventListener('click', () => {
    selected.clear();
    for (const card of cards) card.querySelector('[data-book-compare]').checked = false;
    renderComparison();
    query.focus();
  });
  filter();
})();

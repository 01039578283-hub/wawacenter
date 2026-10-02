import {findBranches} from './home-branch-search-tools.mjs';

const form = document.querySelector('[data-home-search]');
if (form) {
  const query = form.querySelector('input');
  const region = form.querySelector('select');
  const status = document.querySelector('[data-home-search-status]');
  const results = document.querySelector('[data-home-search-results]');
  const more = document.querySelector('[data-home-search-more]');
  const reset = form.querySelector('[data-home-search-reset]');
  let branches = [], matches = [], shown = 0;
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const render = () => {
    results.replaceChildren();
    for (const branch of matches.slice(0, shown)) {
      const card = element('article', '', 'hd-result');
      const heading = element('h3', '');
      const link = element('a', branch.name);
      link.href = branch.route;
      heading.append(link);
      card.append(element('p', `${branch.region} · ${branch.district}`, 'hd-result-region'), heading,
        element('p', branch.address || '주소 확인 필요'),
        element('p', `연결 동네 · ${branch.areas.join(' · ')}`, 'hd-result-areas'));
      if (branch.addressPending) card.append(element('p', '주소 확인 필요', 'hd-result-areas'));
      const action = element('a', '지점 안내 보기 →', 'hd-result-action');
      action.href = branch.route;
      card.append(action);
      results.append(card);
    }
    more.hidden = shown >= matches.length;
    more.textContent = `검색 결과 더 보기 (${Math.min(6, matches.length - shown)}곳)`;
    status.textContent = matches.length ? `${matches.length}개 지점을 찾았습니다. ${Math.min(shown, matches.length)}곳을 표시합니다.`
      : query.value.trim() || region.value ? '일치하는 지점이 없습니다. 동네·지점 이름이나 지역을 바꾸어 보세요.'
      : '동네·지점 이름을 입력하거나 지역을 선택해 주세요.';
  };
  const apply = () => { matches = findBranches(branches, {query: query.value, region: region.value}); shown = 6; render(); };
  try {
    const response = await fetch('/assets/home-branch-search-data.json');
    if (!response.ok) throw new Error('Branch search data unavailable');
    const data = await response.json();
    if (!Array.isArray(data.branches) || data.branches.some(branch => !/^\/지점안내\/[^/]+\/[^/]+\/$/.test(branch.route) || !Array.isArray(branch.areas))) throw new Error('Invalid branch search data');
    branches = data.branches;
    form.addEventListener('submit', event => { event.preventDefault(); apply(); });
    region.addEventListener('change', apply);
    query.addEventListener('input', apply);
    reset.addEventListener('click', () => { form.reset(); apply(); query.focus(); });
    more.addEventListener('click', () => { shown += 6; render(); });
    reset.hidden = false;
    form.dataset.searchReady = 'true';
  } catch {
    status.textContent = '검색을 불러오지 못했습니다. 아래 지역별 지점 안내에서 찾아보세요.';
  }
}

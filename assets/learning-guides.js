import {matchesGuide, recordText} from './learning-guide-tools.mjs';

// All article links and blank records also work without this enhancement.
const form = document.querySelector('[data-guide-search]');
if (form) {
  const input = form.querySelector('input[type="search"]');
  const level = form.querySelector('select[name="level"]');
  const buttons = [...form.querySelectorAll('[data-guide-filter]')];
  const cards = [...document.querySelectorAll('[data-guide-card]')];
  const groups = [...document.querySelectorAll('[data-guide-group]')];
  const status = document.querySelector('[data-guide-status]');
  const empty = document.querySelector('[data-guide-empty]');
  let category = '';
  function render(updateUrl = true) {
    let count = 0;
    const filters = {query: input.value, category, level: level.value};
    for (const card of cards) {
      const match = matchesGuide({category: card.dataset.category, levels: card.dataset.levels, search: card.dataset.search}, filters);
      card.hidden = !match;
      if (match) count++;
    }
    for (const group of groups) {
      const count = [...group.querySelectorAll('[data-guide-card]')].filter(card => !card.hidden).length;
      group.hidden = !count;
      group.querySelector('[data-group-count]').textContent = count + '개';
    }
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.guideFilter === category)));
    status.textContent = count + '개 가이드를 볼 수 있습니다.';
    empty.hidden = count !== 0;
    if (updateUrl) {
      const url = new URL(window.location.href);
      for (const [key, value] of Object.entries({q: input.value.trim(), category, level: level.value})) {
        if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
      }
      window.history.replaceState(null, '', url);
    }
  }
  function restore() {
    const params = new URLSearchParams(window.location.search);
    input.value = (params.get('q') || '').slice(0, 100);
    category = buttons.some(button => button.dataset.guideFilter === params.get('category')) ? params.get('category') : '';
    level.value = [...level.options].some(option => option.value === params.get('level')) ? params.get('level') : '';
    render(false);
  }
  form.addEventListener('submit', event => { event.preventDefault(); render(); });
  input.addEventListener('input', () => render());
  level.addEventListener('change', () => render());
  buttons.forEach(button => button.addEventListener('click', () => { category = button.dataset.guideFilter; render(); }));
  form.addEventListener('reset', event => { event.preventDefault(); category = ''; input.value = ''; level.value = ''; render(); });
  window.addEventListener('popstate', restore);
  restore();
}

const editor = document.querySelector('[data-guide-record]');
if (editor) {
  const fields = [...editor.querySelectorAll('[data-record-field]')];
  const date = editor.querySelector('[data-record-date]');
  const download = editor.querySelector('[data-record-download]');
  const print = editor.querySelector('[data-record-print]');
  const status = editor.querySelector('[data-record-status]');
  const now = new Date();
  date.value = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
  const value = () => recordText({title: editor.dataset.title, url: editor.dataset.url, date: date.value, fields: fields.map(field => ({label: field.dataset.label, value: field.value}))});
  function update() {
    const count = fields.filter(field => field.value.trim()).length;
    download.disabled = print.disabled = count === 0;
    status.textContent = count ? count + '개 항목을 작성했습니다. 파일로 저장해 다음 과제에서 확인하세요.' : '한 항목 이상 작성하면 기록을 저장하거나 인쇄할 수 있습니다.';
  }
  editor.addEventListener('input', update);
  download.addEventListener('click', () => {
    if (download.disabled) return;
    const url = URL.createObjectURL(new Blob(['\ufeff', value()], {type: 'text/plain;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url; link.download = editor.dataset.filename;
    document.body.append(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    status.textContent = 'TXT 파일 저장을 요청했습니다. 저장한 파일은 기기의 다운로드 목록에서 확인하세요.';
  });
  print.addEventListener('click', () => {
    if (print.disabled) return;
    document.querySelector('[data-record-output]').textContent = value();
    document.body.classList.add('lg-printing');
    window.print();
  });
  window.addEventListener('afterprint', () => document.body.classList.remove('lg-printing'));
  editor.hidden = false;
  update();
}

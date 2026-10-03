/** Pure helpers shared by the library filters and the local record editor. */
export function normalize(value) {
  return String(value ?? '').normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g, ' ').trim();
}

export function matchesGuide(guide, {query = '', category = '', level = '', need = ''} = {}) {
  const levels = Array.isArray(guide.levels) ? guide.levels : String(guide.levels || '').split(' ');
  const needs = Array.isArray(guide.needs) ? guide.needs : String(guide.needs || '').split(' ');
  return (!category || guide.category === category)
    && (!level || levels.includes(level))
    && (!need || needs.includes(need))
    && normalize(query).split(' ').filter(Boolean).every(term => normalize(guide.search).includes(term));
}

export function recordText({title, url, date, fields}) {
  const lines = [String(title) + ' — 실천 기록', '작성 날짜: ' + (date || '미작성'), ''];
  for (const {label, value} of fields) {
    lines.push(String(label) + ':', String(value || '').replace(/\r\n?/g, '\n').trim(), '');
  }
  lines.push('가이드: ' + String(url), '');
  return lines.join('\n').replace(/\r\n?/g, '\n').replace(/\n/g, '\r\n');
}

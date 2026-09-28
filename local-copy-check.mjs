/** Keep reviewed text, visible FAQ and search markup in agreement. */
import fs from 'node:fs';
const areas = new Map(JSON.parse(fs.readFileSync(new URL('./area-reference.json', import.meta.url), 'utf8')).areas.map(r => [r.slug, r]));
const decode = value => value.replace(/&#(x[0-9a-f]+|\d+);/gi, (_, n) => String.fromCodePoint(n[0].toLowerCase() === 'x' ? parseInt(n.slice(1), 16) : Number(n))).replaceAll('&quot;', '"').replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
const plain = value => decode(value.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
function* walk(obj) {
  if (!obj || typeof obj !== 'object') return;
  if (!Array.isArray(obj)) yield obj;
  for (const value of Object.values(obj)) yield* walk(value);
}
function gradeLabel(grades) {
  return ['초', '중', '고'].flatMap(prefix => {
    const nums = [...new Set(grades.filter(g => g.startsWith(prefix)).map(g => Number(g.slice(1))))].sort((a,b) => a-b);
    if (!nums.length) return [];
    return [nums.length > 1 && nums.at(-1) - nums[0] + 1 === nums.length ? `${prefix}${nums[0]}~${prefix}${nums.at(-1)}` : nums.map(n => prefix+n).join('·')];
  }).join(' / ');
}
export function assertLocalCopy(html, name) {
  const parts = name.split('/');
  const subjectPage = parts[0] === '과목별학원' && parts.length === 4;
  const centerPage = parts[0] === '전국센터' && [3, 4].includes(parts.length);
  if (!name.endsWith('/index.html') || (!subjectPage && !centerPage)) return;
  const fail = message => { throw Error(`${name}: ${message}`); };
  const r = areas.get(parts[subjectPage ? 2 : 1]);
  if (!r) fail('Unknown area');
  const body = html.match(/<!-- local-copy:start -->([\s\S]*?)<!-- local-copy:end -->/)?.[1];
  if (!body || !body.includes('data-copy-version="1"') || !html.includes('assets/local-editorial.css')) fail('Reviewed local copy missing');
  if (subjectPage && [...html.matchAll(/class="subject-page-toc-number"/g)].length !== 7) fail('Contents navigation incomplete');
  if (/가상|예시 후기|검색엔진과 생성형 검색|생활권을 임의로|네\. 영어는/.test(body)) fail('Obsolete repetitive copy');
  const faqs = [...body.matchAll(/<details><summary>([\s\S]*?)<\/summary><p>([\s\S]*?)<\/p><\/details>/g)].map(m => ({q: plain(m[1]), a: plain(m[2])}));
  if (faqs.length !== 3) fail('Visible FAQ missing');
  const nodes = [...html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/g)].flatMap(m => [...walk(JSON.parse(m[1]))]);
  const schemas = nodes.filter(n => n['@type'] === 'FAQPage');
  if (schemas.length !== 1) fail('FAQ schema missing or duplicated');
  const entries = (schemas[0].mainEntity || []).map(n => ({q: plain(n.name || ''), a: plain(n.acceptedAnswer?.text || '')}));
  if (JSON.stringify(entries) !== JSON.stringify(faqs)) fail('Visible FAQ and schema differ');
  const category = subjectPage ? parts[1] : parts.length === 4 ? parts[2] : '지역학원';
  const subjects = category === '수학학원' ? ['수학'] : category === '영어학원' ? ['영어'] : category.includes('영수') || category === '영어수학학원' ? ['영어', '수학'] : ['국어', '영어', '수학', '과학', '사회'];
  const level = ['초', '중', '고'].find(p => category.startsWith(p));
  const known = [], missing = [];
  for (const subject of subjects) {
    const grades = r.grades[subject].filter(g => !level || g.startsWith(level));
    if (grades.length) known.push(subject + ' ' + gradeLabel(grades)); else missing.push(subject);
  }
  const gradeClaim = faqs[0].a.match(/자료에 기재된 학년은 (.*?)입니다\./)?.[1] || '';
  if (gradeClaim !== known.join(', ')) fail('FAQ grades differ from reviewed source');
  if (missing.length && !faqs[0].a.includes(missing.join(' · ') + '의 해당 학년 정보는 기재되어 있지 않아 수강 가능 여부를 상담으로 확인해야 합니다.')) fail('Missing subjects need consultation');
  const headings = new Map([...body.matchAll(/<h[23] id="([^"]+)">([\s\S]*?)<\/h[23]>/g)].map(m => [m[1], plain(m[2])]));
  for (const node of nodes.filter(n => ['WebPage', 'Article'].includes(n['@type']))) {
    if (!Array.isArray(node.hasPart) || node.hasPart.length !== headings.size) fail('Article headings missing');
    for (const part of node.hasPart) if (headings.get(part.url?.split('#')[1]) !== part.name) fail('Article heading schema differs');
  }
  const checklist = [...body.matchAll(/<li>(.*?)<\/li>/g)].map(m => plain(m[1]));
  for (const node of nodes.filter(n => n['@type'] === 'ItemList' && n['@id']?.endsWith('#checklist'))) {
    if (JSON.stringify(node.itemListElement.map(i => i.name)) !== JSON.stringify(checklist)) fail('Checklist schema differs');
  }
}

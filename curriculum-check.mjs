import fs from 'node:fs';
const data = JSON.parse(fs.readFileSync(new URL('./curriculum-data.json', import.meta.url), 'utf8'));
const created = new Map(data.pages.map(p => [p.file, p]));
const connected = new Map(data.existingPages.map(p => [p.file, p]));
const rows = new Map(data.gradeSubjects.map(r => [r.grade + '/' + r.subject, r]));
const esc = s => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');
export function assertCurriculum(html, name) {
  const fail = message => { throw Error('Curriculum ' + name + ': ' + message); };
  const old = connected.get(name);
  if (old) {
    const blocks = [...html.matchAll(/<!-- curriculum-links:module:start -->([\s\S]*?)<!-- curriculum-links:module:end -->/g)];
    if (blocks.length !== 1 || (html.match(/id="learning-curriculum"/g) || []).length !== 1) fail('one contextual module required');
    for (const route of old.links) if (!blocks[0][1].includes('href="' + encodeURI(route) + '"')) fail('missing matching destination');
    if (!blocks[0][1].includes('실제 수업의 학년·과목·교재는 지점에서 확인하세요.')) fail('study plan and branch operations distinction missing');
    if (!html.includes('href="/assets/curriculum.css"')) fail('module style missing');
  }
  const p = created.get(name);
  if (!p) return;
  if ((html.match(/<h1\b/g) || []).length !== 1) fail('one main title required');
  if (p.description.length > 80 || !p.description.endsWith('.') || !html.includes('<meta name="description" content="' + esc(p.description) + '">')) fail('reviewed description changed');
  if (!html.includes('rel="canonical" href="https://xn--3e0bz50bxucwzc.com' + encodeURI(p.route) + '"')) fail('canonical URL changed');
  if (!html.includes('data-education-finder')) fail('branch directory fallback missing');
  if (p.type === 'grade-subject') {
    const r = rows.get(p.grade + '/' + p.subject);
    for (const text of [r.focus, r.task, r.school, r.scope, r.revision]) if (!html.includes(esc(text))) fail('workbook scope, task or school condition changed');
    for (const step of r.sequence.split('→').map(x => x.trim())) if (!html.includes('<span>' + esc(step) + '</span>')) fail('learning sequence changed');
    if (!html.includes('<h1>' + esc(p.title) + '</h1>')) fail('grade/subject title changed');
    if (['중3', '고3'].includes(p.grade) && (!html.includes('2015 개정') || !html.includes('2027년부터는 2022 개정'))) fail('curriculum transition qualification missing');
    if (['초1', '초2'].includes(p.grade) && p.subject === '영어' && !html.includes('정규 영어 교과가 아닌 선택 활동')) fail('optional elementary activity distinction missing');
    if (['초1', '초2'].includes(p.grade) && ['사회', '과학'].includes(p.subject) && !html.includes('독립된 정규 ' + p.subject + ' 과목 안내가 아닙니다')) fail('integrated subject distinction missing');
    const graph = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m => JSON.parse(m[1])['@graph'] || []);
    const faq = graph.find(n => n['@type'] === 'FAQPage');
    if (JSON.stringify(faq?.mainEntity.map(n => [n.name, n.acceptedAnswer.text])) !== JSON.stringify(p.faqs)) fail('FAQ metadata differs from visible questions');
    for (const [q, a] of p.faqs) if (!html.includes(esc(q)) || !html.includes(esc(a))) fail('visible FAQ missing');
  }
  if (p.type === 'stage-subject') {
    const stage = {초:'초등학생', 중:'중학생', 고:'고등학생'}[p.stage];
    const subject = p.subject === '역사' ? '사회' : p.subject;
    for (const plan of data.levelPlans.filter(x => x.stage === stage && x.subject === subject)) {
      for (const k of ['target', 'sequence', 'task', 'next', 'materials']) if (!html.includes(esc(plan[k]))) fail('level plan no longer matches supplied workbook');
    }
    if (!html.includes('공식 성취등급이나 지점의 실제 반 편성을 뜻하지 않으며')) fail('level meaning qualification missing');
  }
  if (p.type === 'selection') {
    if (!html.includes('2026년 고3은 2015 개정 기준')) fail('selection cohort qualification missing');
    for (const r of data.choices) for (const k of ['name', 'scope', 'prerequisite', 'connection']) if (!html.includes(esc(r[k]))) fail('choice content changed');
  }
}

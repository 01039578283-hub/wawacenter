/** Enforce the CSV-backed map and its position on every real branch page. */
import fs from 'node:fs';

const maps = JSON.parse(fs.readFileSync(new URL('./branch-map-data.json', import.meta.url), 'utf8'));
const branchData = JSON.parse(fs.readFileSync(new URL('./branch-directory-data.json', import.meta.url), 'utf8'));
const gradeData = JSON.parse(fs.readFileSync(new URL('./grade-directory-data.json', import.meta.url), 'utf8'));
const subjectData = JSON.parse(fs.readFileSync(new URL('./subject-directory-data.json', import.meta.url), 'utf8'));
const expected = new Map(branchData.branches.map(b => [b.route.slice(1)+'index.html', {area: maps.branches[b.route], branch: b.route}]));
for (const p of [...gradeData.pages, ...subjectData.pages]) expected.set(p.route.slice(1)+'index.html', p);

export function assertBranchMap(html, name) {
  const fail = reason => { throw Error(`${reason}: ${name}`); };
  let page = expected.get(name);
  if (!page) {
    const parts = name.split('/');
    const legacy = (parts[0] === '과목별학원' && parts.length === 4) || (parts[0] === '전국센터' && [3, 4].includes(parts.length));
    if (!legacy || !name.endsWith('index.html')) return;
    if (!html.includes('<!-- branch-map:start -->')) {
      if (!/<img\b[^>]*src="[^"]*assets\/maps\//.test(html)) fail('Legacy lesson page lacks its center map');
      return;
    }
    const area = parts[parts[0] === '과목별학원' ? 2 : 1];
    page = {area, branch: maps.areas[area]?.branch};
  }
  const entry = maps.areas[page.area];
  if (!entry || entry.branch !== page.branch) fail('Map neighborhood and branch disagree');
  const mapImages = [...html.matchAll(/<img\b[^>]*src="([^"]*assets\/maps\/[^\"]+)"[^>]*>/g)];
  if (mapImages.length !== 1 || mapImages[0][1] !== entry.image.src) fail('Expected the matching single center map');
  const section = html.match(/<section\b[^>]*id="lesson-image"[^>]*>[\s\S]*?<\/section>/);
  if (!section || !html.slice(section.index + section[0].length).startsWith('<!-- branch-map:start -->')) fail('Map must immediately follow the full lesson image');
  const tag = mapImages[0][0];
  if (!tag.includes(`width="${entry.image.width}" height="${entry.image.height}"`) || !tag.includes('loading="lazy"') || !tag.includes('alt="')) fail('Map dimensions, loading or text alternative missing');
  if (!html.includes('href="#center-map"') || !html.includes('id="center-map"')) fail('Map shortcut missing');
}

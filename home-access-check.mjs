import fs from 'node:fs';
const data = JSON.parse(fs.readFileSync(new URL('./home-library-data.json', import.meta.url), 'utf8'));
const plain = s => s.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
export function assertHomeAccess(html, name) {
  if (name !== 'index.html') return;
  const fail = message => { throw Error('Home access: ' + message); };
  const block = kind => {
    const blocks = [...html.matchAll(new RegExp('<!-- home-access:' + kind + ':start -->([\\s\\S]*?)<!-- home-access:' + kind + ':end -->', 'g'))];
    if (blocks.length !== 1) fail('one ' + kind + ' block required');
    return blocks[0][1];
  };
  const quick = block('quick');
  for (const p of data.quickLinks) if (!quick.includes('href="' + encodeURI(p.route) + '"') || !quick.includes(p.title)) fail('top study shortcut absent');
  if (html.indexOf(quick) > html.indexOf('<div class="hero-points"')) fail('study shortcuts too far below introduction');
  if (!block('styles').includes('href="/assets/home-access.css"')) fail('scoped discovery styles absent');
  const library = /<!-- home-library:content:start -->([\s\S]*?)<!-- home-library:content:end -->/.exec(html)?.[1] || '';
  for (const p of data.topics) {
    if (!library.includes('href="' + encodeURI(p.route) + '"') || !library.includes(p.title) || !library.includes(p.description)) fail('missing topic or body summary');
  }
  if ((library.match(/data-home-topic\b/g) || []).length !== 9 || (library.match(/data-home-reading\b/g) || []).length !== 12) fail('nine hubs and twelve specific reading links required');
  for (const p of data.listedPages) if (!library.includes('href="' + encodeURI(p.route) + '"')) fail('listed page absent from visible navigation');
  for (const [question, answer] of data.readingGroups) if (!library.includes(question) || !library.includes(answer)) fail('question or explanatory answer absent');
  const faq = /<div class="faq" id="faq">([\s\S]*?)<\/div>/.exec(html)?.[1] || '';
  const links = [...faq.matchAll(/<!-- home-access:answer:start --><a [^>]*href="([^"]+)">([\s\S]*?)<\/a><!-- home-access:answer:end -->/g)].map(m => [decodeURI(m[1]), plain(m[2]).replace(/ →$/, '')]);
  if (JSON.stringify(links) !== JSON.stringify(data.answerLinks.map(p => [p.route, p.title]))) fail('each answer must link to its relevant detail');
  const graph = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m => { const d = JSON.parse(m[1]); return d['@graph'] || [d]; });
  const lists = graph.filter(n => n['@id'] === 'https://xn--3e0bz50bxucwzc.com/#home-library-list');
  const actual = lists[0]?.itemListElement.map(p => [p.position, decodeURI(new URL(p.url).pathname), p.name]);
  const expected = data.listedPages.map((p, i) => [i + 1, p.route, p.title]);
  if (lists.length !== 1 || lists[0].numberOfItems !== expected.length || JSON.stringify(actual) !== JSON.stringify(expected)) fail('library schema differs from visible destinations');
  if (!graph.some(n => n['@type'] === 'WebPage' && n.mainEntity?.['@id'] === lists[0]['@id'])) fail('home page metadata does not reference its resource list');
}

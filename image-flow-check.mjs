/** Preserve the reviewed full-image reading order when old generators run. */
export function assertImageFlow(html, name) {
  const parts = name.split('/');
  const regional = (parts[0] === '과목별학원' && parts.length === 4) ||
    (parts[0] === '전국센터' && [3, 4].includes(parts.length));
  if (!regional || !name.endsWith('/index.html')) return;
  const fail = reason => { throw Error(`${reason}: ${name}`); };
  if (!/<body\b[^>]*class="[^"]*\bimage-first-page\b/.test(html) || !html.includes('assets/image-first.css')) fail('Image layout missing');
  const hero = html.match(/<section\b[^>]*class="[^"]*local-hero[^"]*"[^>]*>[\s\S]*?<\/section>/)?.[0];
  if (!hero || hero.includes('hero-points') || !hero.includes('image-first-brief')) fail('Compact introduction missing');
  const nav = hero.match(/<nav class="image-first-nav"[\s\S]*?<\/nav>/)?.[0];
  if (!nav || [...nav.matchAll(/<a\b/g)].length !== 2) fail('Quick links missing');
  const images = [...html.matchAll(/<img\b[^>]*src="[^"]*assets\/centers\/common\/(?:seoul|local)6839\.webp"[^>]*>/g)];
  if (images.length !== 1) fail('Expected one complete lesson image');
  const image = images[0];
  if (!image[0].includes('loading="eager"') || !image[0].includes('width="918" height="16116"') || /\b(?:hidden|style)=/.test(image[0])) fail('Lesson image display or loading changed');
  const facts = html.indexOf('class="section area-facts-section"');
  const location = html.indexOf('image-first-location');
  if (!(html.indexOf('image-first-nav') < image.index && image.index < facts && facts < location)) fail('Lesson image must precede details and map');
  if (!html.includes('-mobile.webp') || html.slice(html.indexOf('<main'), image.index).includes('<details')) fail('Lesson image must be openly displayed');
  const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
  for (const match of nav.matchAll(/href="#([^"]+)"/g)) if (!ids.has(match[1])) fail('Quick link target missing');
  const contents = html.indexOf('class="image-first-contents"');
  if (parts[0] === '과목별학원' && contents < location) fail('Detailed contents must follow the image and location');
  if (!html.includes('class="floating-actions"')) fail('Contact actions missing');
}

/** Protect always-visible images and progressive, original-resolution reading. */
import fs from 'node:fs';
const selected = new Set(JSON.parse(fs.readFileSync(new URL('./crawl-readability-data.json', import.meta.url), 'utf8')).pages);
export function assertCrawlReadability(html, name) {
  if (!selected.has(name)) return;
  const fail = reason => { throw Error(`${name}: crawl readability ${reason}`); };
  if (!html.includes('/assets/readable-images.css') || !html.includes('<script src="/assets/readable-images.js" defer>')) fail('reader enhancement missing');
  if (html.includes('user-scalable=no') || /maximum-scale=1(?:[",\s]|$)/.test(html)) fail('browser zoom restricted');
  const pictures = [...html.matchAll(/<a class="readable-image" data-image-kind="lesson"[^>]*>(<picture>[\s\S]*?<\/picture>)<\/a>/g)];
  if (pictures.length !== 1) fail('one always-visible lesson image link required');
  const pic = pictures[0][1];
  const body = pic.match(/<img\b[^>]*src="[^"]*assets\/centers\/common\/(?:seoul|local)6839\.webp"[^>]*>/)?.[0];
  if (!body || !body.includes('width="918" height="16116"') || !body.includes('loading="eager"') || /\bhidden|display\s*:\s*none/.test(body)) fail('original complete body image changed');
  if (!/srcset="[^"]*-mobile\.webp 800w, [^"]*6839\.webp 918w" sizes="/.test(pic)) fail('pixel density choices missing');
  const maps = [...html.matchAll(/<a class="readable-image" data-image-kind="map"[^>]*>(<img\b[^>]*>)<\/a>/g)];
  if (maps.length !== 1 || !maps[0][1].includes('assets/maps/')) fail('matching visible map reader missing');
  for (const [, img] of maps) if (!/\bwidth="\d+" height="\d+"/.test(img) || !img.includes('loading="lazy"')) fail('map size or lazy loading missing');
  const hidden = [...html.matchAll(/<img\b[^>]*style="display:none;"[^>]*>/g)];
  for (const [img] of hidden) if (!img.includes('loading="lazy"')) fail('unused representative image eagerly downloads');
  if (!html.includes('주소') || !html.includes('href="tel:01068398283"')) fail('copyable visit or consultation information missing');
}

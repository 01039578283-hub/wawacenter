/** No review dataset or branch operating-hours source has been verified for this snapshot. */
export function assertTrustedHtml(html, filename = 'HTML') {
  const errors = new Set();
  if (/class\s*=\s*["'][^"']*\bstars\b[^"']*["']|★★★★★/i.test(html)) {
    errors.add('unverified visible star rating');
  }
  function inspect(value) {
    if (Array.isArray(value)) return value.forEach(inspect);
    if (!value || typeof value !== 'object') return;
    const types = Array.isArray(value['@type']) ? value['@type'] : [value['@type']];
    if (types.some(type => type === 'Review' || type === 'AggregateRating')) {
      errors.add('review or rating without a verified source');
    }
    if (value.aggregateRating || (Array.isArray(value.review) ? value.review.length : value.review)) {
      errors.add('review or rating without a verified source');
    }
    if (value.openingHours === 'Mo-Sa 12:00-24:00') {
      errors.add('unverified default branch opening hours');
    }
    Object.values(value).forEach(inspect);
  }
  const scripts = html.matchAll(/<script\b(?=[^>]*\btype\s*=\s*["']application\/ld\+json["'])[^>]*>([\s\S]*?)<\/script\s*>/gi);
  for (const [, payload] of scripts) {
    try {
      inspect(JSON.parse(payload));
    } catch (error) {
      throw new Error(`${filename}: invalid JSON-LD: ${error.message}`);
    }
  }
  if (errors.size) throw new Error(`${filename}: ${[...errors].join('; ')}`);
}

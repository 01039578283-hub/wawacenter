export const normalizeSearch = value => String(value).normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/gu, '');

export function findBranches(branches, {query = '', region = ''} = {}) {
  const terms = String(query).normalize('NFKC').trim().split(/\s+/u).filter(Boolean).map(normalizeSearch);
  if (!terms.length && !region) return [];
  return branches.filter(branch => {
    if (region && branch.region !== region) return false;
    const text = normalizeSearch([branch.name, branch.region, branch.district, branch.address, ...branch.areas].join(' '));
    return terms.every(term => text.includes(term));
  }).sort((a, b) => {
    const exact = branch => [branch.name, ...branch.areas].some(value => normalizeSearch(value) === normalizeSearch(query));
    return Number(exact(b)) - Number(exact(a)) || a.region.localeCompare(b.region, 'ko') || a.name.localeCompare(b.name, 'ko');
  });
}

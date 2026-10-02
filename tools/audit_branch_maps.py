"""Validate the complete publication and CSV-to-map associations."""
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from lxml import html
from branch_maps import DATA, END, START, insert_map

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text(encoding='utf-8'))
    before = json.loads((args.audit / 'before-manifest.json').read_text(encoding='utf-8'))
    changes = json.loads((args.audit / 'map-changes.json').read_text(encoding='utf-8'))
    changed = {p['file']: p for p in changes['pages']}
    branches = {b['route']: b for b in json.loads((ROOT / 'branch-directory-data.json').read_text(encoding='utf-8'))['branches']}
    assert set(manifest['files']) == set(before['files'])
    assert {n for n in before['files'] if before['files'][n] != manifest['files'][n]} == set(changed)
    with zipfile.ZipFile(args.audit / 'before-source.zip') as archive:
        originals = {name: archive.read(name).decode('utf-8') for name in changed}

    def inspect(name):
        raw = (ROOT / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest['files'][name], name
        if name not in changed:
            assert manifest['files'][name] == before['files'][name], name
        if not name.endswith('.html'):
            return None
        text = raw.decode('utf-8')
        long_image = re.search(r'<img\b[^>]*src="[^"]*assets/centers/common/[^>]*>', text)
        if long_image and not re.search(r'<img\b[^>]*src="[^"]*assets/maps/', text):
            raise AssertionError(('Public lesson page still lacks a map', name))
        if name not in changed:
            return None
        p = changed[name]
        stripped = re.sub(re.escape(START) + r'[\s\S]*?' + re.escape(END), '', text)
        stripped = re.sub(r'<!-- branch-map:jump:start -->[\s\S]*?<!-- branch-map:jump:end -->', '', stripped)
        assert stripped == originals[name], ('Unrelated content changed', name)
        assert insert_map(text, branches[p['branch']], p['area']) == text, ('Not idempotent', name)
        doc = html.fromstring(raw)
        lesson = doc.xpath('//section[@id="lesson-image"]')[0]
        map_section = lesson.xpath('following-sibling::*[1]')[0]
        assert map_section.get('id') == 'center-map', name
        assert len(doc.xpath('//*[@id="center-map"]')) == 1
        images = map_section.xpath('.//img')
        assert len(images) == 1 and images[0].get('src') == p['image'], name
        entry = DATA['areas'][p['area']]
        assert entry['branch'] == p['branch']
        assert images[0].get('width') == str(entry['image']['width']) and images[0].get('height') == str(entry['image']['height'])
        assert images[0].get('loading') == 'lazy'
        old = html.fromstring(originals[name])
        assert old.xpath('//script[@type="application/ld+json"]/text()') == doc.xpath('//script[@type="application/ld+json"]/text()')
        return p['kind']

    with ThreadPoolExecutor(max_workers=8) as pool:
        kinds = list(pool.map(inspect, manifest['files']))
    report = {'status': 'PASS', 'publicFilesChecked': len(manifest['files']), 'pagesWithMapsAdded': len(changed), 'byKind': dict(Counter(k for k in kinds if k)), 'protectedPublicFiles': len(manifest['files']) - len(changed), 'neighborhoods': len(DATA['areas']), 'mapPlacement': 'immediately after lesson image', 'originalContentPreserved': True, 'idempotent': True, 'sitemapUnchanged': manifest['files']['sitemap.xml'] == before['files']['sitemap.xml'], 'missingMaps': []}
    (args.audit / 'map-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()

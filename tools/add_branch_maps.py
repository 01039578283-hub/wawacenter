"""Add missing maps without regenerating reviewed copy or branch facts."""
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from branch_maps import DATA, insert_map

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads((args.audit / 'before-manifest.json').read_text(encoding='utf-8'))
    branches = json.loads((ROOT / 'branch-directory-data.json').read_text(encoding='utf-8'))['branches']
    by_branch = {b['route']: b for b in branches}
    grades = json.loads((ROOT / 'grade-directory-data.json').read_text(encoding='utf-8'))['pages']
    subjects = json.loads((ROOT / 'subject-directory-data.json').read_text(encoding='utf-8'))['pages']
    pages = [{'route': b['route'], 'branch': b['route'], 'area': DATA['branches'][b['route']], 'kind': 'branch'} for b in branches]
    pages += [{**p, 'kind': kind} for kind, rows in [('grade', grades), ('subject', subjects)] for p in rows]
    assert len(pages) == 3527
    known = {p['route'].lstrip('/') + 'index.html' for p in pages}
    for name in baseline['files']:
        if name in known or not name.endswith('.html'):
            continue
        parts = name.split('/')
        if parts[0] not in ['전국센터', '과목별학원']:
            continue
        text = (ROOT / name).read_text(encoding='utf-8')
        if not re.search(r'<img\b[^>]*src="[^"]*assets/centers/common/', text) or ('branch-map:start' not in text and re.search(r'<img\b[^>]*src="[^"]*assets/maps/', text)):
            continue
        area = parts[2] if parts[0] == '과목별학원' else parts[1]
        entry = DATA['areas'][area]
        pages.append({'route': '/' + name.removesuffix('index.html'), 'area': area, 'branch': entry['branch'], 'kind': 'legacy'})
    snapshot = args.audit / 'before-source.zip'
    with zipfile.ZipFile(snapshot, 'a', zipfile.ZIP_DEFLATED) as archive:
        saved = set(archive.namelist())
        for p in pages:
            name = p['route'].lstrip('/') + 'index.html'
            if name not in saved:
                raw = (ROOT / name).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == baseline['files'][name], name
                archive.writestr(name, raw)
    changes = []
    with zipfile.ZipFile(snapshot) as archive:
        for p in pages:
            name = p['route'].lstrip('/') + 'index.html'
            original = archive.read(name).decode('utf-8')
            text = insert_map(original, by_branch[p['branch']], p['area'])
            if text == original:
                continue
            raw = text.encode('utf-8')
            if (ROOT / name).read_bytes() != raw:
                (ROOT / name).write_bytes(raw)
            baseline['files'][name] = hashlib.sha256(raw).hexdigest()
            baseline['textSha256'][name] = hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()
            changes.append({'route': p['route'], 'file': name, 'kind': p['kind'], 'area': p['area'], 'branch': p['branch'], 'image': DATA['areas'][p['area']]['image']['src']})
    baseline['createdAt'] = datetime.now(timezone.utc).isoformat()
    (ROOT / 'release-public-manifest.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report = {'changedPages': len(changes), 'byKind': dict(Counter(p['kind'] for p in changes)), 'pages': changes, 'publicFiles': len(baseline['files']), 'sitemapPages': baseline['sitemapPages'], 'deployed': False}
    (args.audit / 'map-changes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'pages'}))


if __name__ == '__main__':
    main()

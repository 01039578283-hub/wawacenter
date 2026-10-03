"""Verify every teacher page and portrait against the built HTTP response."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--label', default='http')
    args = parser.parse_args()
    data = json.loads((ROOT/'teacher-directory-data.json').read_text('utf-8'))
    targets = [p['route'] for p in data['pages']] + [p['src'] for p in data['photos']]
    targets += ['/assets/teacher-directory.css', '/assets/teacher-directory.js', '/', '/sitemap.xml']
    linked = [p for p in data['linkedPages'] if p['branch']]
    # Spot-check delivery of the already verified contextual pages in each namespace.
    for prefix in ['지점안내/', '전국센터/', '과목별학원/']:
        page = next(p for p in linked if p['file'].startswith(prefix))
        targets.append('/'+page['file'].removesuffix('index.html'))

    def check(route):
        try:
            with urlopen(args.base.rstrip('/')+quote(route, safe='/'), timeout=30) as response:
                body, status, media = response.read(), response.status, response.headers.get('Content-Type')
            name = route.lstrip('/')+('index.html' if route.endswith('/') else '')
            expected = (ROOT/'.public-release'/name).read_bytes()
            matches = (body.decode('utf-8').replace('\r\n','\n') == expected.decode('utf-8').replace('\r\n','\n')) if not name.endswith('.png') else body == expected
            return {'route': route, 'status': status, 'contentType': media,
                    'matchesBuiltFile': matches, 'sha256': hashlib.sha256(body).hexdigest(), 'pass': status == 200 and matches}
        except Exception as error:
            return {'route': route, 'pass': False, 'error': str(error)}

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(check, targets))
    report = {'base': args.base, 'checked': len(rows), 'status': 'PASS' if all(r['pass'] for r in rows) else 'FAIL', 'rows': rows}
    args.audit.mkdir(parents=True, exist_ok=True)
    (args.audit/(args.label+'-verification.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}, ensure_ascii=False))
    assert report['status'] == 'PASS', [r for r in rows if not r['pass']]


if __name__ == '__main__':
    main()

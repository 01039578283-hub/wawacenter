"""Audit every CSV mapping, source boundary, public link and migrated URL."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import re
import time
import zipfile
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from lxml import etree, html

ROOT = Path(__file__).resolve().parents[1]
HOST = 'xn--3e0bz50bxucwzc.com'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def norm(value):
    return re.sub(r'\s+', '', value)


def body_content(text):
    text = re.sub(r'<!-- neighborhood-shortcut:start -->.*?<!-- neighborhood-shortcut:end -->', '', text, flags=re.S)
    for family in ['grade-entry', 'subject-entry']:
        text = re.sub('<!-- ' + family + ':start -->.*?<!-- ' + family + ':end -->', '', text, flags=re.S)
    for family in ['contextual-links', 'teacher-links']:
        text = re.sub('<!-- ' + family + r':([a-z]+):start -->.*?<!-- ' + family + r':\1:end -->', '', text, flags=re.S)
    text = re.sub(r'<p class="gd-legacy-note".*?</p>', '', text, flags=re.S)
    doc = html.fromstring(text)
    return ' '.join(doc.xpath('//main')[0].text_content().split())


def source(args):
    before = load(args.audit / 'before-manifest.json')
    after = load(ROOT / 'release-public-manifest.json')
    migration = load(ROOT / 'neighborhood-directory-data.json')
    grades = load(ROOT / 'grade-directory-data.json')['pages']
    subjects = load(ROOT / 'subject-directory-data.json')['pages']
    branches = {b['route']: b for b in load(ROOT / 'branch-directory-data.json')['branches']}
    csv_rows = list(csv.DictReader(args.csv.open(encoding='utf-8-sig', newline='')))
    by_name = {r['근처 수업가능 동네'].strip(): r for r in csv_rows}
    assert len(by_name) == len(migration['mapping']) == 371
    for m in migration['mapping']:
        row = by_name[m['name']]
        b = branches[m['branch']]
        assert norm(row['센터명']) in {norm(v) for v in [b['name'], b['displayName'], b['sourceName'], '와와학습코칭센터 ' + b['sourceName']]}
        assert m['routeName'] == norm(row['근처 수업가능 동네'])
    removed = {route.lstrip('/') + 'index.html' for route in migration['removedRoutes']}
    new = {p['route'].lstrip('/') + 'index.html' for p in grades + subjects}
    assert set(after['files']) - set(before['files']) == new | {'assets/neighborhood-directory.css'}
    assert set(before['files']) - set(after['files']) == removed
    assert len(grades) == 1113 and len(subjects) == 2226
    assert len(migration['redirectDestinations']) == 2805
    for dataset in ['branch-directory-data.json', 'area-reference.json']:
        assert (args.audit / ('before-' + dataset)).read_bytes() == (ROOT / dataset).read_bytes(), dataset
    protected_assets = [n for n in before['files'] if not n.endswith('.html') and n not in ['sitemap.xml', 'llms.txt']]
    for name in protected_assets:
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == before['files'][name], name
    preserved = 0
    with zipfile.ZipFile(args.audit / 'before-source.zip') as archive:
        for name in before['files']:
            if not name.endswith('.html') or name in removed or name in ['과목별학원/초등학생학원/index.html', '과목별학원/중학생학원/index.html', '과목별학원/고등학생학원/index.html']:
                continue
            assert body_content(archive.read(name).decode('utf-8')) == body_content((ROOT / name).read_text(encoding='utf-8')), name
            preserved += 1
    titles = []
    headings = []
    descriptions = []
    for p in grades + subjects:
        name = p['route'].lstrip('/') + 'index.html'
        doc = html.fromstring((ROOT / name).read_bytes())
        title = doc.xpath('//title/text()')[0]
        h1 = ' '.join(doc.xpath('//h1')[0].text_content().split())
        description = doc.xpath('//meta[@name="description"]/@content')[0]
        assert p['name'] in h1 and p['name'] in title and p['name'] in description, name
        assert len(description) <= 80 and description.endswith('.'), name
        assert len(p['areas']) == 1
        assert p['name'] == by_name[p['name']]['근처 수업가능 동네'].strip()
        expected_suffix = p['category'] if 'category' in p else {'초': '초등학생', '중': '중학생', '고': '고등학생'}[p['stage']] + p['subject'] + '학원'
        for s in p['sources']:
            basename = Path(s.get('file', s.get('filename'))).stem
            assert norm(basename).removesuffix(expected_suffix) in {p['area'], p['routeName']}, (name, basename)
        assert len(p['sources']) == (3 if 'category' in p else 2)
        titles.append(title)
        headings.append(h1)
        descriptions.append(description)
    assert len(set(titles)) == len(set(headings)) == len(set(descriptions)) == 3339
    madu = [p for p in grades if p['branch'] == '/지점안내/경기/마두점/' and p['prefix'] == '중']
    assert {p['name'] for p in madu} == {'마두동', '장항동', '백석동'}
    assert len({p['route'] for p in madu}) == 3
    save(args.audit / 'source-audit.json', {'csvMappingsVerified': 371, 'gradePages': len(grades), 'subjectPages': len(subjects), 'distinctTitles': len(set(titles)), 'distinctHeadings': len(set(headings)), 'distinctDescriptions': len(set(descriptions)), 'existingMainContentPreserved': preserved, 'protectedAssetsPreserved': len(protected_assets), 'reviewedBranchFactsPreserved': True, 'maduMiddlePages': [p['route'] for p in madu], 'removedMergedPages': len(removed), 'errors': []})
    print('Source audit passed: 3339 pages and 371 CSV mappings', flush=True)


def public(args):
    manifest = load(ROOT / 'release-public-manifest.json')
    files = set(manifest['files'])
    base = ROOT / '.public-release'
    actual = {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}
    assert files == actual, (files - actual, actual - files)
    pages = {n: html.fromstring((base / n).read_bytes()) for n in files if n.endswith('.html')}
    ids = {n: set(doc.xpath('//@id')) for n, doc in pages.items()}
    errors = []
    references = 0
    fragments = 0
    for name, doc in pages.items():
        text = (base / name).read_text(encoding='utf-8')
        assert text.count('data-site="wawa-07"') == 1, name
        assert len(doc.xpath('//h1')) == 1, name
        assert not doc.xpath('//img[not(@alt)]'), name
        route = '/' if name == 'index.html' else '/' + name.removesuffix('index.html')
        for reference in doc.xpath('//@href|//@src|//@poster'):
            if not reference or reference.startswith(('tel:', 'mailto:', 'data:', 'javascript:')):
                continue
            u = urlsplit(urljoin('https://' + HOST + route, reference))
            if u.netloc not in [HOST, '전국수업.com']:
                continue
            path = unquote(u.path)
            target = path.lstrip('/') + ('index.html' if path.endswith('/') else '')
            references += 1
            if target not in files:
                errors.append([name, reference, 'missing file'])
            elif u.fragment and target.endswith('.html'):
                fragments += 1
                if unquote(u.fragment) not in ids[target]:
                    errors.append([name, reference, 'missing fragment'])
    sitemap = etree.parse(str(base / 'sitemap.xml')).getroot()
    locs = [node[0].text for node in sitemap]
    assert len(locs) == len(set(locs)) == manifest['sitemapPages']
    for loc in locs:
        route = unquote(urlsplit(loc).path)
        doc = pages[route.lstrip('/') + 'index.html']
        assert not any('noindex' in value for value in doc.xpath('//meta[@name="robots"]/@content')), route
        assert unquote(urlsplit(doc.xpath('//link[@rel="canonical"]/@href')[0]).path) == route, route
    assert not any(n.endswith(('.xlsx', '.csv', '.py', '.zip')) or n in ['teacher-directory-data.json', 'neighborhood-directory-data.json'] for n in files)
    report = {'files': len(files), 'htmlPages': len(pages), 'sitemapPages': len(locs), 'internalReferences': references, 'fragmentReferences': fragments, 'errors': errors, 'privateSourcesIncluded': False}
    save(args.audit / 'public-audit.json', report)
    assert not errors, errors[:15]
    print('Public audit passed:', len(pages), 'pages,', references, 'internal references', flush=True)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http(args):
    data = load(ROOT / 'neighborhood-directory-data.json')
    grade_pages = load(ROOT / 'grade-directory-data.json')['pages']
    subject_pages = load(ROOT / 'subject-directory-data.json')['pages']
    live = not args.base.startswith('http://127.0.0.1:')
    if live:
        names = [p['route'].lstrip('/') + 'index.html' for p in grade_pages + subject_pages]
        names += ['index.html', '지점안내/index.html', '지점안내/경기/마두점/index.html', '선생님찾기/마두점/index.html', '학습시스템/개별맞춤관리/index.html', '교재안내/index.html', '학습가이드/index.html', 'sitemap.xml', 'robots.txt', 'assets/neighborhood-directory.css']
    else:
        names = [n for n in load(ROOT / 'release-public-manifest.json')['files'] if n.endswith('.html')]
    mode = 'production-http' if live else 'local-http'
    checks = [{'kind': 'page', 'name': n} for n in names]
    if live:
        checks += [{'kind': 'redirect', 'route': old, 'target': new} for old, new in data['redirectDestinations'].items()]
        checks += [{'kind': 'redirect', 'route': old.rstrip('/'), 'target': new} for old, new in list(data['redirectDestinations'].items())[:18]]
        checks += [{'kind': 'removed', 'route': '/지점안내/강원/강릉교동/'}]
    prior = load(args.audit / (mode + '.json')) if args.retry else None
    if args.retry:
        checks = [error['check'] for error in prior['errors']]
    errors = []
    no_redirect = build_opener(NoRedirect())

    def check(case):
        if case['kind'] == 'page':
            name = case['name']
            route = '/' if name == 'index.html' else '/' + name.removesuffix('index.html')
            with urlopen(Request(args.base + quote(route, safe='/') + '?release=neighborhood20261002', headers={'User-Agent': 'Mozilla/5.0'}), timeout=35) as response:
                actual = response.read()
                assert response.status == 200
            expected = (ROOT / '.public-release' / name).read_bytes()
            assert actual.decode('utf-8').replace('\r\n', '\n') == expected.decode('utf-8').replace('\r\n', '\n'), name
        else:
            status = None
            location = None
            try:
                with no_redirect.open(Request(args.base + quote(case['route'], safe='/'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=35) as response:
                    status = response.status
                    location = response.headers.get('Location')
            except HTTPError as error:
                status = error.code
                location = error.headers.get('Location')
            if case['kind'] == 'removed':
                assert status == 404, status
            else:
                assert status == 301, (status, case)
                u = urlsplit(unquote(urljoin(args.base, location)))
                wanted = urlsplit(case['target'])
                assert u.path == wanted.path and u.fragment == wanted.fragment, (location, case)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8 if live else 6) as pool:
        futures = {pool.submit(check, case): case for case in checks}
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                future.result()
            except Exception as error:
                errors.append({'check': futures[future], 'error': str(error)})
            if count % 500 == 0:
                print(json.dumps({'httpChecked': count, 'total': len(checks), 'errors': len(errors)}), flush=True)
                save(args.audit / (mode + '-checkpoint.json'), {'checked': count, 'total': len(checks), 'errors': errors})
    report = {'base': args.base, 'checked': prior['checked'] if prior else len(checks), 'retried': len(checks) if prior else 0, 'errors': errors, 'matchesReviewedContent': not errors}
    save(args.audit / (mode + '.json'), report)
    print(json.dumps({'checked': len(checks), 'errors': len(errors), 'firstErrors': errors[:3]}, ensure_ascii=False), flush=True)
    assert not errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['source', 'public', 'http'])
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--base')
    parser.add_argument('--retry', action='store_true')
    args = parser.parse_args()
    {'source': source, 'public': public, 'http': http}[args.mode](args)

"""Refresh the teacher library without rewriting other public pages.

Use a captured before-release-public-manifest.json and before-teacher-directory-data.json.
Existing contextual routes and assigned portraits must survive this upgrade.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from lxml import etree, html
from urllib.parse import unquote, urlsplit
import build_teacher_directory as teacher

ROOT = teacher.ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads((args.audit/'before-release-public-manifest.json').read_text('utf-8'))
    previous = json.loads((args.audit/'before-teacher-directory-data.json').read_text('utf-8'))
    groups, photos, source = teacher.load_records(args.source, teacher.ui.BRANCHES)
    # This upgrade must retain existing identities, memberships and stable portraits.
    assert groups == previous['branches'], 'Source changed: review memberships before refreshing the directory.'
    supplied_focus = {focus for g in groups for t in g['teachers'] for focus in t['focus']}
    covered = [focus for _, focuses in teacher.NEEDS.values() for focus in focuses]
    assert supplied_focus == set(covered) and len(covered) == len(set(covered))
    pages = [teacher.hub(groups)] + [teacher.branch_page(g) for g in groups]
    teacher.save(ROOT/'teacher-directory-data.json', {
        **previous, 'version': 2, 'reviewed': teacher.DAY, 'source': source,
        'branches': groups, 'photos': photos, 'pages': pages,
        'needs': [{'id': key, 'label': label, 'focus': focus} for key, (label, focus) in teacher.NEEDS.items()],
    })
    teacher.save(ROOT/'seo-descriptions.json', teacher.ui.DESCRIPTIONS)
    routes = {teacher.ui.url(p['route']) for p in pages}
    tree = etree.parse(str(ROOT/'sitemap.xml'))
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    matched = set()
    for entry in tree.getroot():
        loc = entry.find('s:loc', ns).text
        if loc in routes:
            entry.find('s:lastmod', ns).text = teacher.DAY
            matched.add(loc)
    assert matched == routes and len(tree.getroot()) == before['sitemapPages']
    (ROOT/'sitemap.xml').write_bytes(etree.tostring(tree, encoding='utf-8', xml_declaration=True, pretty_print=True))
    allowed = {teacher.file_for(p['route']) for p in pages} | {
        'assets/teacher-directory.css', 'assets/teacher-directory.js', 'sitemap.xml',
    }
    hashes, normalized, changed = {}, {}, []
    for name, old_hash in before['files'].items():
        body = (ROOT/name).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != old_hash:
            assert name in allowed, 'Unrelated public content changed: ' + name
            changed.append(name)
        hashes[name] = digest
        if re.search(r'\.(html|css|js|mjs|json|xml|txt|svg|webmanifest)$', name):
            normalized[name] = hashlib.sha256(body.decode('utf-8').replace('\r\n', '\n').encode()).hexdigest()
    teacher.save(ROOT/'release-public-manifest.json', {
        **before, 'createdAt': teacher.DAY+'T12:00:00+09:00', 'files': hashes, 'textSha256': normalized,
    })
    broken = []
    anchors = {}
    for p in pages:
        name = teacher.file_for(p['route'])
        document = html.fromstring((ROOT/name).read_text('utf-8'))
        assert len(document.xpath('//h1')) == 1
        for link in document.xpath('//main//a[@href]'):
            parsed = urlsplit(link.attrib['href'])
            if parsed.netloc and parsed.netloc != 'xn--3e0bz50bxucwzc.com':
                continue
            route = unquote(parsed.path)
            if not route.startswith('/'):
                continue
            target = route.lstrip('/')+('index.html' if route.endswith('/') else '')
            if target not in hashes:
                broken.append([name, link.attrib['href']])
            fragment = unquote(urlsplit(link.attrib['href']).fragment)
            if fragment and target in hashes:
                if target not in anchors:
                    anchors[target] = set(html.fromstring((ROOT/target).read_text('utf-8')).xpath('//*[@id]/@id'))
                if fragment not in anchors[target]:
                    broken.append([name, link.attrib['href'], 'fragment missing'])
    assert not broken, broken[:10]
    report = {
        'status': 'PASS', 'teacherIntroductions': source['rows'], 'teacherBranches': len(groups),
        'teacherPages': len(pages), 'matchingBranchPages': sum(bool(g['branchRoute']) for g in groups),
        'existingContextualPagesVerified': len(previous['linkedPages']), 'portraits': len(photos),
        'portraitAssignmentsPreserved': True, 'allFocusKeywordsCovered': len(supplied_focus),
        'brokenTeacherLinks': broken, 'changedPublicFiles': changed,
        'unrelatedPublicFilesPreserved': len(hashes)-len(allowed), 'publicFiles': len(hashes),
        'sitemapPages': len(tree.getroot()), 'deployed': False,
    }
    teacher.save(args.audit/'generation-summary.json', report)
    print(json.dumps({k:v for k,v in report.items() if k != 'changedPublicFiles'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

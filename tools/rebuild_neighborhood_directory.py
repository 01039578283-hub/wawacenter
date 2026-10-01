"""Render the CSV-backed neighborhood hierarchy and migrate former branch children.

Run prepare_neighborhood_directory.py first. --audit must contain the reviewed
before-manifest.json and before-source.zip; public files outside that manifest
are never included. No deployment is performed by this builder.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from lxml import etree
import build_branch_upgrade as ui
import build_grade_directory as grade
import build_subject_directory as subject
import build_contextual_links as resources
import build_site_shell as common
import build_teacher_directory as teachers

ROOT = ui.ROOT
DAY = '2026-10-02'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def filename(route):
    return route.lstrip('/') + 'index.html'


def href(route):
    return quote(route, safe='/#-')


def finish_navigation(selected):
    """Keep the neighborhood choices reachable above the full guide image."""
    migration = load('neighborhood-directory-data.json')
    drafts = set(migration.get('discardedDraftRoutes', []))
    replacements = {}
    for p in grade.PAGES:
        old = p['branch'] + p['area'] + p['category'] + '/'
        if old in drafts:
            replacements[old] = p['route']
    for p in subject.PAGES:
        old = p['branch'] + p['area'] + grade.LABELS[p['stage']] + '/' + p['subject'] + '/'
        if old in drafts:
            replacements[old] = p['route']
    branch_files = {filename(b['route']) for b in ui.BRANCHES}
    changed = set()
    shortcut = '<!-- neighborhood-shortcut:start -->' + ui.link('#grade-guide', '동네별 학년·과목') + '<!-- neighborhood-shortcut:end -->'
    for name in sorted(n for n in selected if n.endswith('.html')):
        path = ROOT / name
        old = path.read_text(encoding='utf-8')
        text = old
        for old_route, new_route in sorted(replacements.items(), key=lambda item: -len(item[0])):
            text = text.replace(href(old_route), href(new_route))
        if name in branch_files:
            text = re.sub(r'<!-- neighborhood-shortcut:start -->.*?<!-- neighborhood-shortcut:end -->', '', text, flags=re.S)
            text, count = re.subn(r'(<nav class="bd-jump" aria-label="지점 페이지 바로가기">)', lambda m: m[1] + shortcut, text, count=1)
            assert count == 1, name
        if text != old:
            path.write_bytes(text.encode('utf-8'))
            changed.add(name)
    return changed


def redirect_rules(branches, pages):
    """371 historical rules + two merged-child rules per branch, below 2048."""
    result = []
    stages = '|'.join(quote(value, safe='') for value in grade.LABELS.values())
    subjects = '|'.join(quote(value, safe='') for value in ['수학', '영어'])
    for branch in branches.values():
        base = href(branch['route'])
        groups = [p for p in pages if p['branch'] == branch['route']]
        for area in branch['areas']:
            group = [p for p in groups if p['area'] == area['slug']]
            old = '/지점안내/' + branch['region'] + '/' + area['slug'] + '/'
            result.append({'source': href(old) + quote(area['slug'], safe='') + ':stage(' + stages + ')(/)?', 'destination': base + quote(group[0]['routeName'], safe='') + ':stage/', 'statusCode': 301})
        if len(branch['areas']) == 1:
            target = base + quote(groups[0]['routeName'], safe='') + ':stage/'
            child_target = target + ':subject/'
        else:
            target = child_target = base + '#grade-guide'
        result.append({'source': base + ':stage(' + stages + ')(/)?', 'destination': target, 'statusCode': 301})
        result.append({'source': base + ':stage(' + stages + ')/:subject(' + subjects + ')(/)?', 'destination': child_target, 'statusCode': 301})
    assert len(result) == 747
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads((args.audit / 'before-manifest.json').read_text(encoding='utf-8'))
    migration = load('neighborhood-directory-data.json')
    branches = {b['route']: b for b in ui.BRANCHES}
    grade_by_area = {(p['area'], p['prefix']): p for p in grade.PAGES}
    subject_by_area = {(p['area'], p['stage'], p['subject']): p for p in subject.PAGES}
    new_routes = {p['route'] for p in grade.PAGES + subject.PAGES}
    removed_routes = set(migration['removedRoutes'])
    assert len(new_routes) == 3339 and len(removed_routes) == 1692
    assert not new_routes & removed_routes
    removed_files = {filename(route) for route in removed_routes}
    assert removed_files <= set(before['files'])
    ui.DAY = DAY
    ui.NEW.clear()
    for index, p in enumerate(grade.PAGES, 1):
        grade.details(p)
        if index % 300 == 0:
            print(json.dumps({'gradePagesRendered': index}), flush=True)
    for index, p in enumerate(subject.PAGES, 1):
        subject.child(p)
        if index % 300 == 0:
            print(json.dumps({'subjectPagesRendered': index}), flush=True)
    for prefix, label in grade.LABELS.items():
        grade.category_hub(prefix, label)
    grade.connect_hubs()
    # Branch cards now contain all town/stage/subject destinations together.
    for branch in branches.values():
        path = ROOT / filename(branch['route'])
        text = path.read_text(encoding='utf-8')
        text = re.sub(r'<!-- subject-entry:start -->.*?<!-- subject-entry:end -->', '', text, flags=re.S)
        text = text.replace('<link rel="stylesheet" href="/assets/neighborhood-directory.css">', '')
        text = text.replace('</head>', '<link rel="stylesheet" href="/assets/neighborhood-directory.css"></head>', 1)
        path.write_bytes(text.encode('utf-8'))
    subject.enrich_parents()
    historical = {p['previousRoute']: p['route'] for p in grade.PAGES}
    aliases = {f'/과목별학원/{p["category"]}/{p["area"]}/': p['route'] for p in grade.PAGES}
    deleted_hubs = {p['previousHub']: p['branch'] for p in grade.PAGES}
    merged = {}
    for branch in branches.values():
        for stage, category in grade.LABELS.items():
            old = branch['route'] + category + '/'
            if len(branch['areas']) == 1:
                area = branch['areas'][0]['slug']
                merged[old] = grade_by_area[area, stage]['route']
                for name in ['수학', '영어']:
                    merged[old + name + '/'] = subject_by_area[area, stage, name]['route']
            else:
                merged[old] = branch['route'] + '#grade-guide'
                for name in ['수학', '영어']:
                    merged[old + name + '/'] = branch['route'] + '#grade-guide'
    assert set(merged) == removed_routes
    all_destinations = {**merged, **historical, **aliases, **deleted_hubs}
    selected = (set(before['files']) - removed_files) | {filename(route) for route in new_routes} | {'assets/neighborhood-directory.css'}
    area_to_branch = {m['area']: m['branch'] for m in migration['mapping']}
    contexts = {p['file']: p for p in load('contextual-links-data.json')['pages'] if p['file'] in selected}
    teacher_data = load('teacher-directory-data.json')
    teacher_entries = {p['file']: p for p in teacher_data['linkedPages'] if p['file'] in selected}
    by_teacher_branch = {g['branchRoute']: g for g in teacher_data['branches'] if g['branchRoute']}
    by_teacher_area = {area: by_teacher_branch[branch] for area, branch in area_to_branch.items() if branch in by_teacher_branch}
    area_data = {p['slug']: p for p in load('area-reference.json')['areas']}
    grade_by_route = {p['route']: p for p in grade.PAGES}
    subject_by_route = {p['route']: p for p in subject.PAGES}
    connected = [filename(route) for route in branches] + ['지점안내/index.html'] + [f'지점안내/{r}/index.html' for r in ui.REGIONS] + [f'전국센터/{a}/index.html' for a in area_data] + ['index.html', '전국센터/index.html', '과목별학원/index.html']
    regenerated = set(ui.NEW) | grade.MODIFIED | set(connected)
    rewritten_links = 0
    changed = set()
    for name in sorted(n for n in selected if n.endswith('.html')):
        path = ROOT / name
        old = path.read_text(encoding='utf-8')
        text = old
        route = '/' if name == 'index.html' else '/' + name.removesuffix('index.html')
        parts = route.strip('/').split('/')
        page = grade_by_route.get(route) or subject_by_route.get(route)
        area = page['area'] if page else parts[1] if parts[0] == '전국센터' and len(parts) > 1 else parts[2] if parts[0] == '과목별학원' and len(parts) > 2 else None

        def destination(old_route):
            if old_route in merged and area and area_to_branch.get(area) == '/' + '/'.join(old_route.strip('/').split('/')[:3]) + '/':
                bits = old_route.strip('/').split('/')
                stage = next(key for key, label in grade.LABELS.items() if label == bits[3])
                return subject_by_area[area, stage, bits[4]]['route'] if len(bits) == 5 else grade_by_area[area, stage]['route']
            return all_destinations.get(old_route)

        def replace_link(match):
            nonlocal rewritten_links
            reference = match[2]
            parts = urlsplit(reference.replace('&amp;', '&'))
            if parts.netloc and parts.netloc not in ['xn--3e0bz50bxucwzc.com', '전국수업.com']:
                return match[0]
            target = destination(unquote(parts.path).rstrip('/') + '/')
            if target is None:
                return match[0]
            target_parts = urlsplit(target)
            fragment = target_parts.fragment or parts.fragment
            target = href(target_parts.path) + ('?' + parts.query if parts.query else '') + ('#' + fragment if fragment else '')
            if parts.netloc:
                target = ui.DOMAIN + target
            rewritten_links += 1
            return match[1] + target.replace('&', '&amp;') + match[3]

        text = re.sub(r'(\bhref=")([^"]+)(")', replace_link, text)
        if route in aliases:
            target = aliases[route]
            text = re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")[^"]+', lambda m: m[1] + ui.url(target), text)
            text = re.sub(r'<p class="gd-legacy-note".*?</p>', '', text, flags=re.S)
            text = text.replace('</h1>', '</h1><p class="gd-legacy-note">' + ui.link(target, '이 동네의 최신 학년·교육비 안내 보기') + '</p>', 1)
        # Newly rendered pages and navigation modules retain resources and teachers.
        if name in regenerated:
            if name.startswith(('지점안내/', '과목별학원/', '전국센터/')):
                text = resources.strip(text)
                context = resources.context(name, branches, grade_by_route, subject_by_route, area_data)
                if page:
                    context['label'] = page['name'] + ' ' + resources.STAGES[page.get('prefix', page.get('stage'))] + (' ' + page['subject'] if 'subject' in page else '')
                groups = resources.resources(context)
                text = resources.insert(text, context, groups)
                contexts[name] = {'file': name, 'route': route, 'context': context, 'groups': groups}
                text = re.sub(r'<!-- teacher-links:([a-z]+):start -->.*?<!-- teacher-links:\1:end -->', '', text, flags=re.S)
                text, entry = teachers.existing_links(name, text, by_teacher_branch, by_teacher_area)
                if entry:
                    teacher_entries[name] = entry
            text = re.sub(r'<header\b[^>]*>.*?</header>', lambda _: common.header(route), text, count=1, flags=re.S)
            text = re.sub(r'<body\b([^>]*)>', lambda m: '<body' + re.sub(r'\sdata-site-shell="[^"]*"', '', m[1]) + ' data-site-shell="1">', text, count=1)
            text = re.sub(r'<link rel="stylesheet" href="/assets/site-shell.css">', '', text)
            text = text.replace('</head>', '<link rel="stylesheet" href="/assets/site-shell.css"></head>', 1)
        if text != old:
            path.write_bytes(text.encode('utf-8'))
            changed.add(name)
    for route in removed_routes | set(migration.get('discardedDraftRoutes', [])):
        ui.DESCRIPTIONS['pages'].pop(route.rstrip('/'), None)
    ui.DESCRIPTIONS['canonicalAliases'] = {a.rstrip('/'): b.rstrip('/') for a, b in aliases.items()}
    ui.save(ROOT / 'seo-descriptions.json', ui.DESCRIPTIONS)
    save(ROOT / 'contextual-links-data.json', {**load('contextual-links-data.json'), 'pages': sorted(contexts.values(), key=lambda p: p['file'])})
    save(ROOT / 'teacher-directory-data.json', {**teacher_data, 'linkedPages': sorted(teacher_entries.values(), key=lambda p: p['file'])})
    save(ROOT / 'site-shell-data.json', {**load('site-shell-data.json'), 'pages': sorted(n for n in selected if n.endswith('.html'))})
    config = load('vercel.json')
    config['redirects'] = redirect_rules(branches, grade.PAGES)
    save(ROOT / 'vercel.json', config)
    migration['redirectDestinations'] = {**merged, **historical}
    save(ROOT / 'neighborhood-directory-data.json', migration)
    tree = etree.parse(str(ROOT / 'sitemap.xml'))
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    root = tree.getroot()
    existing = {unquote(urlsplit(node.find('{' + ns + '}loc').text).path): node for node in root}
    for route in removed_routes | set(migration.get('discardedDraftRoutes', [])):
        if route in existing:
            root.remove(existing.pop(route))
    updated_routes = {'/' if name == 'index.html' else '/' + name.removesuffix('index.html') for name in changed | regenerated}
    for route in sorted(new_routes | (updated_routes & set(existing))):
        node = existing.get(route)
        if node is None:
            node = etree.SubElement(root, '{' + ns + '}url')
            etree.SubElement(node, '{' + ns + '}loc').text = ui.url(route)
        lm = node.find('{' + ns + '}lastmod')
        if lm is None:
            lm = etree.SubElement(node, '{' + ns + '}lastmod')
        lm.text = DAY
    tree.write(str(ROOT / 'sitemap.xml'), encoding='utf-8', xml_declaration=True)
    path = ROOT / 'llms.txt'
    text = path.read_text(encoding='utf-8')
    for heading in ['지점별 학년 안내', '지점별 학년·과목 안내', '동네별 학년·과목 안내']:
        text = re.sub(r'\n## ' + heading + r'\n.*?(?=\n## |\Z)', '', text, flags=re.S)
    text += '\n## 동네별 학년·과목 안내\n\n371개 동네를 188개 실제 지점에 연결했습니다. 동네별 초·중·고 안내 1,113개와 그 아래 영어·수학 안내 2,226개를 제공합니다.\n주소는 /지점안내/지역/지점/동네명초등학생학원·동네명중학생학원·동네명고등학생학원/영어·수학/ 순서입니다.\n각 동네의 원고와 학교 자료를 구분하고, 실제 연결 지점의 안내 학년·교육비·등원 주소를 확인합니다.\n학교명은 제휴·재원·전용반을 뜻하지 않으며 공통 교습비는 지점 확정 금액과 구분합니다.\n'
    path.write_bytes(text.encode('utf-8'))
    for name in removed_files | {filename(route) for route in migration.get('discardedDraftRoutes', [])}:
        for base in [ROOT, ROOT / '.public-release']:
            path = (base / name).resolve()
            assert path.is_relative_to(base.resolve()), path
            if path.is_file():
                path.unlink()
    changed.update(finish_navigation(selected))
    hashes = {}
    normalized = {}
    for name in sorted(selected):
        raw = (ROOT / name).read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$', name):
            normalized[name] = hashlib.sha256(raw.decode('utf-8').replace('\r\n', '\n').encode()).hexdigest()
    save(ROOT / 'release-public-manifest.json', {**before, 'files': hashes, 'textSha256': normalized, 'sitemapPages': len(root), 'createdAt': datetime.now(timezone.utc).isoformat()})
    report = {'neighborhoods': 371, 'branches': 188, 'gradePages': len(grade.PAGES), 'subjectPages': len(subject.PAGES), 'rebuiltPages': len(new_routes), 'removedMergedPages': len(removed_files), 'historicalRedirects': len(historical), 'migrationDestinations': len(migration['redirectDestinations']), 'redirectRules': len(config['redirects']), 'updatedLinks': rewritten_links, 'updatedExistingFiles': len(changed), 'htmlPages': sum(n.endswith('.html') for n in selected), 'sitemapPages': len(root), 'publicFiles': len(selected), 'deployed': False}
    save(args.audit / 'generation-summary.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

"""Match the user's 371 CSV titles to centers and re-read the 21 supplied ZIPs."""
import argparse
import collections
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from grade_editorial import TOPICS as GRADE_TOPICS
from prepare_grade_directory import applies
from prepare_subject_directory import FAMILIES, merged_topics, ranked

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-02'
LABELS = {'초': '초등학생학원', '중': '중학생학원', '고': '고등학생학원'}


def norm(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFC', value))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def member_name(info):
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode('cp437').decode('cp949')
    except UnicodeError:
        return info.filename


def drafts(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, path
        entries = [info for info in archive.infolist() if not info.is_dir() and info.filename.lower().endswith('.txt')]
        assert len(entries) == 371, (path, len(entries))
        for info in entries:
            assert info.file_size < 8_000_000
            raw = archive.read(info)
            for encoding in ['utf-8-sig', 'cp949', 'utf-16']:
                try:
                    body = raw.decode(encoding)
                    break
                except UnicodeError:
                    pass
            else:
                raise ValueError(str(path) + ': unknown manuscript encoding')
            yield member_name(info), body, hashlib.sha256(raw).hexdigest()


def grade_topics(records):
    openings = [r['text'].split('[본문]', 1)[-1].split('##', 1)[0] for r in records]
    profiles = ' '.join(openings)
    scores = []
    for index, (key, title, pattern, copy, record, question) in enumerate(GRADE_TOPICS):
        hits = [m.start() for m in re.finditer(pattern, profiles)]
        weight = 1 if key in ['priority', 'progress-review', 'error-revisit', 'math-explain', 'math-independent'] else 3
        if hits:
            scores.append((len(hits) * weight + 1 / (1 + min(hits)), index))
    result = [GRADE_TOPICS[index][0] for _, index in sorted(scores, reverse=True)[:4]]
    assert len(result) >= 3
    return result, openings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    args.audit.mkdir(parents=True, exist_ok=True)
    facts = json.loads((ROOT / 'branch-directory-data.json').read_text(encoding='utf-8'))
    current_grades = json.loads((ROOT / 'grade-directory-data.json').read_text(encoding='utf-8'))
    current_subjects = json.loads((ROOT / 'subject-directory-data.json').read_text(encoding='utf-8'))
    old_grades = json.loads((args.audit / 'before-grade-directory-data.json').read_text(encoding='utf-8'))
    old_subjects = json.loads((args.audit / 'before-subject-directory-data.json').read_text(encoding='utf-8'))
    area_reference = json.loads((ROOT / 'area-reference.json').read_text(encoding='utf-8'))['areas']
    areas_by_name = {norm(a['area']): a for a in area_reference}
    by_branch_name = {}
    for b in facts['branches']:
        for name in [b['name'], b['sourceName'], b['displayName'], '와와학습코칭센터 ' + b['sourceName']]:
            key = norm(name)
            assert key not in by_branch_name or by_branch_name[key]['route'] == b['route']
            by_branch_name[key] = b
    rows = list(csv.DictReader(args.csv.open(encoding='utf-8-sig', newline='')))
    assert len(rows) == 371
    mapping = []
    for row_number, row in enumerate(rows, 2):
        name = row['근처 수업가능 동네'].strip()
        assert norm(name) in areas_by_name, name
        area = areas_by_name[norm(name)]
        assert norm(row['센터명']) in by_branch_name, row['센터명']
        b = by_branch_name[norm(row['센터명'])]
        assert any(a['slug'] == area['slug'] for a in b['areas']), (name, b['name'])
        mapping.append({'area': area['slug'], 'name': name, 'routeName': norm(name), 'branch': b['route'], 'region': b['region'], 'csvRow': row_number})
    assert len({m['area'] for m in mapping}) == 371
    source_hashes = {}
    for name, expected in facts['sourceHashes'].items():
        path = args.csv.parent / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, ('Reviewed branch facts changed; reconcile before rendering', name)
        source_hashes[name] = actual
    assert source_hashes['센터정보 정리.csv'] == hashlib.sha256(args.csv.read_bytes()).hexdigest()
    names = {norm(m['name']): m['area'] for m in mapping}
    names.update({norm(m['area']): m['area'] for m in mapping})
    grade_groups = collections.defaultdict(list)
    subject_groups = collections.defaultdict(list)
    grade_hashes = {}
    subject_hashes = {}
    for stage, category in LABELS.items():
        for suffix in ['', '_001', '_002']:
            filename = category + suffix + '.zip'
            path = args.sources / '썼던 원고' / filename
            grade_hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
            for file, text, sha in drafts(path):
                name = norm(Path(file).stem).removesuffix(category)
                assert name in names, (filename, file)
                grade_groups[names[name], stage].append({'archive': filename, 'file': file, 'text': text, 'sha256': sha})
    for relative in old_subjects['archiveHashes']:
        path = args.sources / relative
        stage = path.name[0]
        subject = '영어' if '영어' in path.name else '수학'
        subject_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        suffix = LABELS[stage].removesuffix('학원') + subject + '학원'
        for filename, body, sha in drafts(path):
            name = norm(Path(filename).stem).removesuffix(suffix)
            assert name in names, (relative, filename)
            subject_groups[names[name], stage, subject].append({'archive': relative, 'filename': filename, 'body': body, 'stage': stage, 'subject': subject, 'sha256': sha})
    assert len(grade_groups) == 1113 and all(len(v) == 3 for v in grade_groups.values())
    assert len(subject_groups) == 2226 and all(len(v) == 2 for v in subject_groups.values())
    branches = {b['route']: b for b in facts['branches']}
    by_area = {a['slug']: a for a in area_reference}
    grades = []
    subjects = []
    evidence = []
    repeated = 0
    for m in mapping:
        b = branches[m['branch']]
        a = by_area[m['area']]
        for stage, category in LABELS.items():
            records = sorted(grade_groups[m['area'], stage], key=lambda r: r['archive'])
            topics, openings = grade_topics(records)
            seen = set()
            for r in records:
                body = re.split(r'\[(?:FAQ|학부모후기|상담 상황 예시|JSON-LD|구조화)', r['text'].split('[본문]', 1)[-1])[0]
                for paragraph in re.split(r'\n\s*\n', body):
                    key = norm(paragraph)
                    if not key or key.startswith('##'):
                        continue
                    if key in seen:
                        repeated += 1
                    seen.add(key)
            route = b['route'] + m['routeName'] + category + '/'
            courses = [{'subject': c['subject'], 'grades': [g for g in c['grades'] if g.startswith(stage)], 'pending': [g for g in c['pending'] if g.startswith(stage)], 'notes': [n for n in c['notes'] if applies(n, stage)]} for c in b['courses']]
            grade = {'area': m['area'], 'name': m['name'], 'prefix': stage, 'category': category, 'route': route, 'hub': b['route'], 'previousRoute': '/지점안내/' + b['region'] + '/' + m['area'] + '/' + m['area'] + category + '/', 'previousHub': '/지점안내/' + b['region'] + '/' + m['area'] + '/', 'branch': b['route'], 'region': b['region'], 'courses': courses, 'courseNotes': [n for n in b['courseNotes'] if applies(n, stage)], 'schools': a['schools'].get(stage, []), 'topics': topics, 'sources': [{k: r[k] for k in ['archive', 'file', 'sha256']} for r in records], 'areas': [{'area': m['area'], 'name': m['name'], 'schools': a['schools'].get(stage, []), 'topics': topics}]}
            grade['routeName'] = m['routeName']
            grades.append(grade)
            evidence.append({'route': route, 'area': m['area'], 'openings': openings, 'selectedTopics': topics, 'sources': grade['sources'], 'paragraphsAfterDedup': len(seen)})
            for subject in ['수학', '영어']:
                rr = sorted(subject_groups[m['area'], stage, subject], key=lambda r: (not r['archive'].startswith('프로그램'), r['archive']))
                selected = []
                families = set()
                seen = set()
                trace = []
                sources = []
                for r in rr:
                    ranked_ids, body, opening = ranked(r, stage, subject)
                    assert len(ranked_ids) >= 4
                    accepted = 0
                    for key in ranked_ids:
                        family = FAMILIES.get(key, key)
                        if family not in families:
                            selected.append(key)
                            families.add(family)
                            accepted += 1
                        if accepted == 6:
                            break
                    for paragraph in re.split(r'\n\s*\n', body):
                        key = norm(paragraph)
                        if not key or key.startswith('##'):
                            continue
                        if key in seen:
                            repeated += 1
                        seen.add(key)
                    sources.append({k: r[k] for k in ['archive', 'filename', 'sha256']})
                    trace.append({'source': sources[-1], 'opening': opening, 'rankedTopics': ranked_ids[:8]})
                entries = [{'slug': m['area'], 'name': m['name'], 'schools': a['schools'].get(stage, []), 'topics': selected}]
                course = next(c for c in courses if c['subject'] == subject)
                subject_page = {'route': route + subject + '/', 'parent': route, 'branch': b['route'], 'stage': stage, 'subject': subject, 'area': m['area'], 'name': m['name'], 'areas': entries, 'schools': a['schools'].get(stage, []), 'topics': merged_topics(entries, subject), 'course': course, 'courseNotes': grade['courseNotes'], 'sources': sources}
                subject_page['routeName'] = m['routeName']
                subjects.append(subject_page)
                evidence.append({'route': subject_page['route'], 'area': m['area'], 'selectedTopics': subject_page['topics'], 'sources': trace, 'paragraphsAfterDedup': len(seen)})
    assert len(grades) == 1113 and len(subjects) == 2226
    save(ROOT / 'grade-directory-data.json', {'reviewedAt': DAY, 'sourceHashes': source_hashes, 'archiveHashes': grade_hashes, 'areaPages': grades, 'pages': grades})
    save(ROOT / 'subject-directory-data.json', {'reviewedAt': DAY, 'sourceHashes': source_hashes, 'archiveHashes': subject_hashes, 'pages': subjects})
    final_routes = {p['route'] for p in grades + subjects}
    removed_routes = {p['route'] for p in old_grades['pages'] + old_subjects['pages']}
    discarded = {p['route'] for p in current_grades['pages'] + current_subjects['pages']} - final_routes - removed_routes
    save(ROOT / 'neighborhood-directory-data.json', {'reviewedAt': DAY, 'csvSha256': source_hashes['센터정보 정리.csv'], 'mapping': mapping, 'gradePages': len(grades), 'subjectPages': len(subjects), 'removedRoutes': sorted(removed_routes), 'discardedDraftRoutes': sorted(discarded)})
    save(args.audit / 'editorial-evidence.json', evidence)
    save(args.audit / 'input-inspection.json', {'csvRows': len(rows), 'branches': len(branches), 'mapping': mapping, 'sourceHashes': source_hashes, 'gradeArchives': grade_hashes, 'subjectArchives': subject_hashes, 'gradeDrafts': 3339, 'subjectDrafts': 4452, 'unmatched': [], 'exactRepeatedParagraphsRemoved': repeated})
    print(json.dumps({'csvRows': len(rows), 'branches': len(branches), 'gradeDrafts': 3339, 'subjectDrafts': 4452, 'gradePages': len(grades), 'subjectPages': len(subjects), 'unmatched': 0, 'exactRepeatedParagraphsRemoved': repeated}, ensure_ascii=False))


if __name__ == '__main__':
    main()

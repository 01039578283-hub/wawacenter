"""Keep the complete lesson image near the top of existing regional pages."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HERO = re.compile(r'<section\b[^>]*class="[^"]*local-hero[^"]*"[^>]*>.*?</section>', re.S)
FACTS = re.compile(r'<section\b[^>]*class="[^"]*area-facts-section[^"]*"[^>]*>.*?</section>', re.S)
MEDIA = re.compile(r'<section\b[^>]*class="[^"]*local-media-section[^"]*"[^>]*>.*?</section>', re.S)
TOC = re.compile(r'<nav\b[^>]*class="[^"]*subject-page-toc[^"]*"[^>]*>.*?</nav>', re.S)
CONTENTS = re.compile(r'<details class="image-first-contents">.*?</details>', re.S)
CARD = re.compile(r'<div class="local-media-card">.*?</div>', re.S)
LONG_IMAGE = re.compile(r'<img\b[^>]*src="([^"]*assets/centers/common/(?:seoul|local)6839\.webp)"[^>]*>')
esc = lambda value: html.escape(str(value), quote=True)
digest = lambda raw: hashlib.sha256(raw).hexdigest()


def rearrange(text, name, area, subjects, level, grade_text):
    hero = HERO.search(text)
    facts = FACTS.search(text)
    media = list(MEDIA.finditer(text))
    toc = TOC.search(text)
    contents = CONTENTS.search(text)
    assert hero and facts and media, (name, 'missing reviewed page sections')
    cards = [card for section in media for card in CARD.findall(section[0])]
    assert len(cards) == 2, (name, 'unexpected media cards')
    image = LONG_IMAGE.search(cards[0])
    assert image and not LONG_IMAGE.search(cards[1]), (name, 'unexpected lesson image')
    original_image = image[0]
    for attr in ['loading', 'decoding', 'width', 'height']:
        original_image = re.sub(r'\s+' + attr + r'="[^"]*"', '', original_image)
    original_image = original_image.removesuffix('>') + ' loading="eager" decoding="async" width="918" height="16116">'
    first_card = cards[0].replace(image[0], original_image)
    if '<picture>' not in first_card:
        mobile = image[1].replace('.webp', '-mobile.webp')
        first_card = first_card.replace(original_image, f'<picture><source media="(max-width: 680px)" srcset="{mobile}">{original_image}</picture>')

    breadcrumb = re.search(r'<nav class="mini-breadcrumb".*?</nav>', hero[0], re.S)
    heading = re.search(r'<h1\b[^>]*>.*?</h1>', hero[0], re.S)
    assert breadcrumb and heading, (name, 'missing page heading')
    opening = hero[0].split('>', 1)[0] + '>'
    values = {subject: [g for g in area['grades'][subject] if not level or g.startswith(level)] for subject in subjects}
    if len(subjects) <= 2:
        brief = ' · '.join(subject + ' ' + (grade_text(grades) or '학년 상담 확인') for subject, grades in values.items())
        brief = '자료상 안내: ' + brief
    else:
        listed = [subject for subject, grades in values.items() if grades]
        brief = '자료상 안내 과목: ' + ' · '.join(listed) if listed else '과목별 수강 정보는 상담에서 확인해 주세요.'
    facts_id = 'answer-title' if name.startswith('과목별학원/') else 'geo-summary-title'
    hero_html = f'''{opening}
      {breadcrumb[0]}
      {heading[0]}
      <p class="lead">{esc(area['area'])}에서 안내하는 지점은 <strong>{esc(area['branch'])}</strong>입니다.</p>
      <p class="image-first-brief">{esc(brief)}</p>
      <nav class="image-first-nav" aria-label="페이지 빠른 안내"><a href="#lesson-image">수업 안내 이미지</a><a href="#{facts_id}">학년·위치 확인</a></nav>
    </section>'''
    media_classes = re.search(r'class="([^"]+)"', media[0][0])[1]
    media_classes = ' '.join(c for c in media_classes.split() if not c.startswith('image-first-'))
    blocks = [hero_html,
              f'<section class="{media_classes} image-first-media" id="lesson-image" aria-label="수업 안내 이미지">\n      {first_card}\n    </section>',
              facts[0],
              f'<section class="{media_classes} image-first-location" aria-label="센터 위치 안내">\n      {cards[1]}\n    </section>']
    if toc:
        blocks.append('<details class="image-first-contents"><summary>자세한 학습 안내 목차</summary>\n' + toc[0] + '\n    </details>')
    removed = [hero, facts, *media]
    if contents:
        removed.append(contents)
    elif toc:
        removed.append(toc)
    removed.sort(key=lambda match: match.start())
    start, end = removed[0].start(), removed[-1].end()
    cursor = start
    gaps = []
    for match in removed:
        assert match.start() >= cursor, (name, 'overlapping sections')
        gaps.append(text[cursor:match.start()])
        cursor = match.end()
    assert not re.sub(r'<!--.*?-->|\s+', '', ''.join(gaps), flags=re.S), (name, 'unexpected content between sections')
    text = text[:start] + '\n\n    '.join(blocks) + text[end:]
    body = re.search(r'<body\b[^>]*>', text)[0]
    if 'image-first-page' not in body:
        if 'class="' in body:
            new_body = body.replace('class="', 'class="image-first-page ', 1)
        else:
            new_body = body[:-1] + ' class="image-first-page">'
        text = text.replace(body, new_body, 1)
    if 'assets/image-first.css' not in text:
        depth = len(name.split('/')) - 1
        text = text.replace('</head>', f'<link rel="stylesheet" href="{"../" * depth}assets/image-first.css">\n</head>')
    return text


def main():
    from refresh_area_facts import grade_text, scope, save_json
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--sample', nargs='+')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text(encoding='utf-8-sig'))
    reference = json.loads((ROOT / 'area-reference.json').read_text(encoding='utf-8'))
    areas = {area['slug']: area for area in reference['areas']}
    names = args.sample or [name for name in manifest['files'] if name.endswith('.html')]
    changes = {}
    counts = {}

    def convert(name):
        raw = (ROOT / name).read_bytes()
        text = raw.decode('utf-8-sig')
        if not FACTS.search(text):
            return None
        parts = name.split('/')
        area = areas[parts[2] if parts[0] == '과목별학원' else parts[1]]
        _, subjects, level = scope(name)
        new = rearrange(text, name, area, subjects, level, grade_text)
        assert rearrange(new, name, area, subjects, level, grade_text) == new, (name, 'not idempotent')
        for pattern in [r'<title\b[^>]*>.*?</title>', r'<h1\b[^>]*>.*?</h1>', r'<meta\b[^>]*>', r'<link\b[^>]*rel="canonical"[^>]*>', r'<script\b[^>]*>.*?</script>', r'<aside class="floating-actions".*?</aside>', FACTS.pattern]:
            assert re.findall(pattern, text, re.S) == re.findall(pattern, new, re.S), (name, 'protected content', pattern)
        data = (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + new.encode('utf-8')
        return name, parts[0], data if raw != data else None

    with ThreadPoolExecutor(max_workers=6) as pool:
        for item in pool.map(convert, names):
            if item is None:
                continue
            name, kind, raw = item
            counts[kind] = counts.get(kind, 0) + 1
            if raw is not None:
                changes[name] = raw
    if not args.sample:
        assert sum(counts.values()) == 4452, counts
    css = (ROOT / 'assets/image-first.css').read_bytes()
    if manifest['files'].get('assets/image-first.css') != digest(css):
        changes['assets/image-first.css'] = css
    if args.apply and changes:
        def write(item):
            name, raw = item
            (ROOT / name).write_bytes(raw)
            return name, digest(raw), digest(raw.decode('utf-8').replace('\r\n', '\n').encode())
        with ThreadPoolExecutor(max_workers=6) as pool:
            for name, file_hash, text_hash in pool.map(write, changes.items()):
                manifest['files'][name] = file_hash
                manifest.setdefault('textSha256', {})[name] = text_hash
        manifest['createdAt'] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
        save_json(ROOT / 'release-public-manifest.json', manifest)
    report = {'applied': args.apply, 'checkedPages': sum(counts.values()), 'changedPages': sum(name.endswith('.html') for name in changes), 'routeCounts': counts, 'changedFiles': list(changes)}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'changedFiles'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Remove the unsupported claims in the reviewed site6 snapshot; dry-run by default."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'release-public-manifest.json'
LD = re.compile(r'(<script\b(?=[^>]*\btype=["\']application/ld\+json["\'])[^>]*>)(.*?)(</script\s*>)', re.S | re.I)
SECTION = re.compile(r'^[ \t]*<section\b[^>]*>(?:(?!<section\b).)*?</section>[ \t]*(?:\r?\n)?', re.S | re.I | re.M)
DROP = object()


def read(path):
    data = path.read_bytes()
    return data, data.decode('utf-8-sig')


def encode(text, original):
    return (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clean_schema(value, counts):
    if isinstance(value, list):
        cleaned = [clean_schema(item, counts) for item in value]
        return [item for item in cleaned if item is not DROP]
    if not isinstance(value, dict):
        return value
    kind = value.get('@type')
    types = kind if isinstance(kind, list) else [kind]
    if any(item in {'Review', 'AggregateRating'} for item in types):
        counts['standalone_review_or_rating_nodes_removed'] += 1
        return DROP
    if kind == 'WebPageElement' and value.get('name') == '학부모 후기':
        counts['review_section_references_removed'] += 1
        return DROP
    result = {}
    for key, item in value.items():
        if key in {'review', 'aggregateRating'}:
            counts[key + '_removed'] += 1
            continue
        if key == 'openingHours' and item == 'Mo-Sa 12:00-24:00':
            counts['default_hours_removed'] += 1
            continue
        if key == 'articleSection' and isinstance(item, list) and '학부모 후기' in item:
            counts['review_article_section_labels_removed'] += item.count('학부모 후기')
            item = [label for label in item if label != '학부모 후기']
        cleaned = clean_schema(item, counts)
        if cleaned is not DROP:
            result[key] = cleaned
    return result


def modified_dates(value, date):
    if isinstance(value, list):
        for item in value:
            modified_dates(item, date)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        if isinstance(types, str):
            types = [types]
        if set(types) & {'WebPage', 'CollectionPage', 'Article'}:
            value['dateModified'] = date
        for item in value.values():
            modified_dates(item, date)


def invariants(text):
    """Keep identity, crawl settings, media, links and labelled examples intact."""
    return {
        'head': re.findall(r'<title\b[^>]*>.*?</title>|<meta\b[^>]*>|<link\b[^>]*>', text, re.S | re.I),
        'h1': re.findall(r'<h1\b[^>]*>.*?</h1>', text, re.S | re.I),
        'images': re.findall(r'<(?:img|source)\b[^>]*>', text, re.I),
        'links': re.findall(r'<a\b[^>]*>', text, re.I),
        'examples': re.findall(r'<section\b[^>]*class="[^"]*subject-review-section[^>]*>.*?</section>', text, re.S),
    }


def repair(text, date):
    counts = collections.Counter()
    before = invariants(text)

    def remove_stars(match):
        section = match.group(0)
        if '<p class="eyebrow">Reviews</p>' in section and 'class="stars"' in section:
            counts['star_sections_removed'] += 1
            counts['star_cards_removed'] += section.count('class="stars"')
            return ''
        return section

    result = SECTION.sub(remove_stars, text)

    def remove_schema(match):
        old = json.loads(match.group(2))
        new = clean_schema(old, counts)
        if new == old:
            return match.group(0)
        return match.group(1) + json.dumps(new, ensure_ascii=False, separators=(',', ':')) + match.group(3)

    result = LD.sub(remove_schema, result)
    old_link_label = 'FAQ와 후기까지 함께 확인합니다.'
    counts['review_link_labels_changed'] = result.count(old_link_label)
    result = result.replace(old_link_label, 'FAQ와 상담 안내를 함께 확인합니다.')
    old_hub_label = 'FAQ와 학부모 후기를 함께 확인할 수 있습니다.'
    counts['review_hub_labels_changed'] = result.count(old_hub_label)
    result = result.replace(old_hub_label, 'FAQ와 상담 안내를 함께 확인할 수 있습니다.')
    if result == text:
        return text, counts

    def update_dates(match):
        value = json.loads(match.group(2))
        modified_dates(value, date)
        return match.group(1) + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + match.group(3)

    result = LD.sub(update_dates, result)
    result = re.sub(r'(<dt>페이지 반영일</dt>\s*<dd>)\d{4}-\d{2}-\d{2}(</dd>)', lambda m: m[1] + date + m[2], result)
    if before != invariants(result):
        raise ValueError('A protected title, meta tag, H1, link, image or labelled example changed')
    return result, counts


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--apply', action='store_true')
    args.add_argument('--date', required=True, type=dt.date.fromisoformat)
    args.add_argument('--report', type=Path, required=True)
    args = args.parse_args()
    date = args.date.isoformat()
    manifest_raw, manifest_text = read(MANIFEST)
    manifest = json.loads(manifest_text)
    if manifest.get('domain') != '전국수업.com':
        raise ValueError('This migration is scoped to 전국수업.com')
    changes = {}
    totals = collections.Counter()
    pages = []
    scanned = 0
    for name in manifest['files']:
        if not name.endswith('.html'):
            continue
        file = ROOT / name
        if file.is_symlink() or not file.resolve().is_relative_to(ROOT):
            raise ValueError('Unsafe manifest path: ' + name)
        raw, original = read(file)
        updated, counts = repair(original, date)
        scanned += 1
        if updated != original:
            new_bytes = encode(updated, raw)
            changes[name] = new_bytes
            totals.update(counts)
            pages.append({'file': name, 'before_sha256': digest(raw), 'after_sha256': digest(new_bytes), 'changes': dict(counts)})
        if scanned % 1000 == 0:
            print(json.dumps({'scanned': scanned, 'changed': len(pages)}), flush=True)

    sitemap_raw, sitemap = read(ROOT / 'sitemap.xml')
    sitemap_changes = 0
    page_names = set(changes)

    def sitemap_date(match):
        nonlocal sitemap_changes
        block = match[0]
        loc = re.search(r'<loc>(.*?)</loc>', block)[1]
        filename = unquote(urlsplit(html.unescape(loc)).path).strip('/')
        filename = (filename + '/' if filename else '') + 'index.html'
        if filename not in page_names:
            return block
        result, count = re.subn(r'<lastmod>.*?</lastmod>', f'<lastmod>{date}</lastmod>', block)
        if count == 0:
            result = block.replace('</loc>', f'</loc><lastmod>{date}</lastmod>')
        elif count != 1:
            raise ValueError('Expected one lastmod for ' + filename)
        sitemap_changes += 1
        return result

    updated_sitemap = re.sub(r'<url>.*?</url>', sitemap_date, sitemap, flags=re.S)
    if sitemap_changes != len(pages):
        raise ValueError('Changed pages and sitemap updates differ')
    if updated_sitemap != sitemap:
        changes['sitemap.xml'] = encode(updated_sitemap, sitemap_raw)

    report = {'mode': 'apply' if args.apply else 'dry-run', 'root': str(ROOT), 'date': date, 'scanned': scanned,
              'changed_html': len(pages), 'totals': dict(totals), 'sitemap_entries_updated': sitemap_changes,
              'protected_fields_preserved': True, 'pages': pages}
    if args.apply and changes:
        for name, data in changes.items():
            (ROOT / name).write_bytes(data)
            manifest['files'][name] = digest(data)
            manifest.setdefault('textSha256', {})[name] = digest(data.decode('utf-8').replace('\r\n', '\n').encode('utf-8'))
        manifest['createdAt'] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat()
        MANIFEST.write_bytes(encode(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', manifest_raw))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'pages'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

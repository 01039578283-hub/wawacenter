"""One reviewed map immediately follows the full lesson image."""
import json
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'branch-map-data.json').read_text(encoding='utf-8'))
START = '<!-- branch-map:start -->'
END = '<!-- branch-map:end -->'


def map_section(branch, area=None, legacy=False):
    area = area or DATA['branches'][branch['route']]
    entry = DATA['areas'][area]
    assert entry['branch'] == branch['route'], (area, branch['name'])
    image = entry['image']
    name = escape(branch['name'], quote=True)
    alt = escape(entry['name'] + ' 연결 지점 ' + branch['name'] + ' 위치 안내 지도', quote=True)
    target = 'https://map.naver.com/p/search/' + quote(branch['address'], safe='')
    image_html = '<a href="' + target + '" target="_blank" rel="noopener noreferrer" aria-label="' + name + ' 주소를 네이버 지도에서 확인"><img src="' + image['src'] + '" width="' + str(image['width']) + '" height="' + str(image['height']) + '" loading="lazy" decoding="async" alt="' + alt + '"></a>'
    caption = name + ' 위치 안내입니다. 지도를 누르면 현재 안내 주소를 네이버 지도에서 확인할 수 있습니다.'
    attrs = ' data-center-map data-map-area="' + escape(area, quote=True) + '"'
    if legacy:
        body = '<section class="section" id="center-map" aria-labelledby="center-map-title"><h2 id="center-map-title">' + name + ' 위치 안내 지도</h2><div class="local-media-card"' + attrs + '>' + image_html + '<p>' + caption + '</p></div></section>'
    else:
        body = '<section class="bd-section" id="center-map" aria-labelledby="center-map-title"><h2 id="center-map-title">' + name + ' 위치 안내 지도</h2><div class="bd-image-panel"><figure class="bd-photo"' + attrs + '>' + image_html + '<figcaption>' + caption + '</figcaption></figure></div></section>'
    return START + body + END


def insert_map(text, branch, area=None):
    if START in text:
        return text
    import re
    maps = re.findall(r'<img\b[^>]*src="[^"]*assets/maps/[^>]*>', text)
    if maps:
        return text
    pattern = r'(<section\b[^>]*\bid="lesson-image"[^>]*>[\s\S]*?</section>)'
    section = re.search(pattern, text)
    assert section, branch['route']
    legacy = 'class="image-first-nav"' in text
    result = text[:section.end()] + map_section(branch, area, legacy) + text[section.end():]
    nav = re.search(r'<nav class="(?:bd-jump|image-first-nav)"[^>]*>[\s\S]*?</nav>', result)
    assert nav, branch['route']
    anchor = re.search(r'<a\b[^>]*href="#lesson-image"[^>]*>[\s\S]*?</a>', nav[0])
    assert anchor, branch['route']
    offset = nav.start() + anchor.end()
    shortcut = '<!-- branch-map:jump:start --><a href="#center-map">지점 지도</a><!-- branch-map:jump:end -->'
    return result[:offset] + shortcut + result[offset:]

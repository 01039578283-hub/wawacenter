"""Update homepage discovery without regenerating any regional or article page."""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

DAY = '2026-10-04'
ORIGIN = 'https://xn--3e0bz50bxucwzc.com'
TOPICS = [
    ('academy', '/지점안내/', '우리 동네 지점 찾기', '동네와 연결된 지점의 주소·사진·교육비 자료를 확인하세요.', '지점 안내 보기'),
    ('academy', '/선생님찾기/', '지점 선생님 소개', '지점별 선생님의 담당 과목과 소개를 살펴보세요.', '선생님 찾기'),
    ('academy', '/학습시스템/', '학습코칭과 수업 방식', '개별 맞춤 관리와 4C 코칭, AI 학습의 구성과 소개 영상을 확인하세요.', '학습 시스템 보기'),
    ('academy', '/과목별학원/', '학년·과목별 수업 안내', '초·중·고 영어·수학·국어 수업을 알아볼 때 확인할 내용을 살펴보세요.', '학년·과목 안내 보기'),
    ('study', '/학습가이드/', '학생·학부모 학습가이드', '시험 준비·과목별 복습·공부 습관의 실천 방법과 기록 양식을 찾으세요.', '학습가이드 읽기'),
    ('study', '/학습커리큘럼/', '학년·과목별 공부 계획', '학년별 학습 내용과 공부 순서, 기초·표준·심화 연습을 살펴보세요.', '학습커리큘럼 보기'),
    ('study', '/교재안내/', '영어·수학 교재 찾기', '교재의 학습 영역과 권·단계 조건을 비교해 필요한 연습을 정하세요.', '교재 검색·비교하기'),
    ('study', '/교육정보/', '학생과 부모를 위한 교육정보', '공부 계획·시험 준비·학습 대화를 점검하고 일상에 적용해 보세요.', '교육정보 읽기'),
    ('consult', '/상담문의/', '상담 전 준비하기', '최근 시험지와 오답, 현재 공부 계획을 챙기고 궁금한 점을 정리하세요.', '상담 준비와 신청 방법'),
]
GROUPS = [
    ('학년별 공부, 어디부터 시작할까요?', '초등은 공부 습관과 기초 개념, 중등은 시험 범위, 고등은 과목별 약점과 복습 순서를 먼저 정리하세요.', [
        ('초등학생공부습관', '초등학생 공부 습관'), ('중학생내신공부법', '중학생 내신 공부법'),
        ('고등학생과목별공부법', '고등학생 과목별 공부 계획'), ('시험4주학습계획', '시험 4주 학습 계획')]),
    ('틀린 문제와 읽기, 어떻게 복습할까요?', '틀린 첫 단계와 답의 근거를 기록하고, 같은 과제를 다시 확인할 날짜를 정해 보세요.', [
        ('수학오답관리', '수학 오답 관리'), ('영어문장구조읽기', '영어 문장 구조 읽기'),
        ('국어비문학읽기', '국어 비문학 읽기'), ('학습플래너작성법', '학습 플래너 작성법')]),
    ('학원 상담에서 무엇을 확인할까요?', '아이의 최근 학습 자료를 기준으로 수업 방식·교육비·기록 공유 방법을 묻고 비교하세요.', [
        ('학원수업비교', '학원 수업 비교'), ('교육비확인', '교육비 확인'),
        ('학부모상담체크리스트', '학부모 상담 체크리스트'), ('학습대화방법', '공부 대화 방법')]),
]
QUICK = [
    ('/학습가이드/', '학습가이드'), ('/학습커리큘럼/', '학습커리큘럼'),
    ('/교육정보/', '교육정보'), ('/교재안내/', '교재안내'),
]
FAQ_LINKS = [
    ('/학습시스템/개별맞춤관리/', '개별 맞춤 관리 자세히 보기'),
    ('/과목별학원/', '학년·과목별 수업 안내 보기'),
    ('/학습가이드/학부모상담체크리스트/', '학부모 상담 체크리스트 읽기'),
    ('/지점안내/', '우리 지점의 교육비 자료 확인하기'),
    ('/학습가이드/학원수업비교/', '수업 방식 비교 기준 읽기'),
    ('/학습가이드/학습플래너작성법/', '학습 플래너 기록 방법 읽기'),
]


def esc(value):
    return html.escape(value, quote=True)


def href(route):
    return quote(route, safe='/#?=&')


def marked(kind, body):
    return f'<!-- home-access:{kind}:start -->{body}<!-- home-access:{kind}:end -->'


def link(route, label, attrs=''):
    return f'<a {attrs}href="{href(route)}">{esc(label)}<span aria-hidden="true"> →</span></a>'


def replace_marked(source, namespace, kind, body):
    pattern = rf'<!-- {namespace}:{kind}:start -->[\s\S]*?<!-- {namespace}:{kind}:end -->'
    source, count = re.subn(pattern, lambda _: f'<!-- {namespace}:{kind}:start -->{body}<!-- {namespace}:{kind}:end -->', source)
    assert count == 1, (namespace, kind, count)
    return source


def enhance(root):
    root = Path(root)
    file = root / 'index.html'
    source = file.read_text(encoding='utf-8')
    source = re.sub(r'<!-- home-access:([a-z]+):start -->[\s\S]*?<!-- home-access:\1:end -->', '', source)
    guides = json.loads((root / 'learning-guide-data.json').read_text(encoding='utf-8'))
    education = json.loads((root / 'education-info-data.json').read_text(encoding='utf-8'))
    books = json.loads((root / 'book-library-data.json').read_text(encoding='utf-8'))
    assert len({p['slug'] for p in guides['pages']}) == len(guides['pages'])
    known = {p['slug'] for p in guides['pages']}
    assert all(slug in known for _, _, rows in GROUPS for slug, _ in rows)
    for _, route, *_ in TOPICS:
        assert (root / route.lstrip('/') / 'index.html').is_file(), route
    quick = '<nav class="ha-quick" aria-label="학생·학부모 공부 자료 바로가기"><p>공부에 필요한 자료도 찾아보세요</p><div>'
    quick += ''.join(link(route, label) for route, label in QUICK)
    quick += '</div><a class="ha-quick-all" href="#home-library">학원·학습 정보 전체 보기 <span aria-hidden="true">↓</span></a></nav>'
    anchor = '<div class="hero-points"'
    assert source.count(anchor) == 1
    source = source.replace(anchor, marked('quick', quick) + anchor, 1)

    # Keep the reviewed brand/official-video shortcuts while replacing the stale topic cards.
    program = re.search(r'<!-- program-review:home:start -->[\s\S]*?<!-- program-review:home:end -->', source)
    assert program, 'official programme shortcuts absent'
    cards = {}
    for group, route, title, desc, action in TOPICS:
        cards[route] = '<a class="hl-card ha-topic" data-home-topic href="' + href(route) + '"><h4>' + esc(title) + '</h4><p>' + esc(desc) + '</p><span class="hl-card-action">' + esc(action) + '<span aria-hidden="true"> →</span></span></a>'
    topics = '<div class="ha-topic-groups">'
    for group, title, desc in [
        ('academy', '학원 알아보기', '지점과 선생님, 수업 내용을 함께 확인하세요.'),
        ('study', '공부 자료 찾기', '학년별 계획부터 복습 방법과 교재까지 살펴보세요.'),
    ]:
        topics += '<section class="ha-topic-group" aria-labelledby="home-' + group + '-title"><h3 id="home-' + group + '-title">' + title + '</h3><p>' + desc + '</p><nav class="ha-topic-grid" aria-label="' + title + '">'
        topics += ''.join(cards[r] for g, r, *_ in TOPICS if g == group)
        topics += '</nav></section>'
    topics += '</div>'
    groups = ''
    for i, (title, desc, rows) in enumerate(GROUPS, 1):
        groups += f'<section class="hl-group" aria-labelledby="home-group-{i}"><h3 id="home-group-{i}">{esc(title)}</h3><p>{esc(desc)}</p><ul>'
        groups += ''.join('<li>' + link('/학습가이드/' + slug + '/', label, 'data-home-reading ') + '</li>' for slug, label in rows)
        groups += '</ul></section>'
    consult = TOPICS[-1]
    contents = '<section class="home-library ha-library" id="home-library" aria-labelledby="home-library-title"><div class="hl-heading"><p class="eyebrow">학원 정보와 학생·학부모 학습 자료</p><h2 id="home-library-title">지점 정보부터 공부 방법까지</h2><p>학원을 알아볼 때는 지점·선생님·수업 안내를, 공부를 계획할 때는 학습가이드·커리큘럼·교재·교육정보를 살펴보세요.</p></div>'
    contents += '<!-- home-library:jump:start --><nav class="hl-jump" aria-label="학원·학습 정보 바로가기"><a href="#home-academy-title">학원 알아보기</a><a href="#home-study-title">공부 자료 찾기</a><a href="#home-reading">고민별 학습가이드</a></nav><!-- home-library:jump:end -->'
    contents += topics + program[0]
    contents += '<section class="hl-reading" id="home-reading" aria-labelledby="home-reading-title"><div class="hl-reading-heading"><h2 id="home-reading-title">지금 고민에 맞는 학습가이드</h2>' + link('/학습가이드/', '전체 학습가이드 보기') + '</div><div class="hl-reading-grid">' + groups + '</div></section>'
    contents += '<aside class="ha-consult" aria-labelledby="home-consult-title"><div><h3 id="home-consult-title">' + esc(consult[2]) + '</h3><p>' + esc(consult[3]) + '</p></div>' + link(consult[1], consult[4], 'data-home-topic ') + '</aside></section>'
    source = replace_marked(source, 'home-library', 'content', contents)

    # Add destinations next to each answer; retain the answer text and the single FAQPage.
    faq = re.search(r'<div class="faq" id="faq">([\s\S]*?)</div>', source)
    assert faq and faq[1].count('<summary>') == len(FAQ_LINKS)
    current = iter(FAQ_LINKS)
    def faq_link(match):
        route, label = next(current)
        return match[0][:-len('</details>')] + marked('answer', link(route, label, 'class="ha-answer-link" ')) + '</details>'
    faq_body = re.sub(r'<details\b[^>]*>[\s\S]*?</details>', faq_link, faq[1])
    source = source[:faq.start(1)] + faq_body + source[faq.end(1):]
    style = marked('styles', '<link rel="stylesheet" href="/assets/home-access.css">')
    source = source.replace('<link rel="stylesheet" href="/assets/site-shell.css">', style + '<link rel="stylesheet" href="/assets/site-shell.css">', 1)

    listed = [{'route':r, 'title':t} for _, r, t, *_ in TOPICS[:-1]]
    listed += [{'route':'/학습가이드/' + slug + '/', 'title':label} for _, _, rows in GROUPS for slug, label in rows]
    listed += [{'route':consult[1], 'title':consult[2]}]
    assert len({p['route'] for p in listed}) == len(listed)
    item_list = {'@context':'https://schema.org', '@type':'ItemList', '@id':ORIGIN + '/#home-library-list', 'name':'학원 안내와 학생·학부모 학습 자료', 'numberOfItems':len(listed), 'itemListElement':[{'@type':'ListItem', 'position':i, 'name':p['title'], 'url':ORIGIN + href(p['route'])} for i, p in enumerate(listed, 1)]}
    source = replace_marked(source, 'home-library', 'schema', '<script type="application/ld+json">' + json.dumps(item_list, ensure_ascii=False, separators=(',', ':')) + '</script>')
    def webpage_metadata(match):
        obj = json.loads(match[1])
        for node in obj.get('@graph', []):
            if node.get('@type') != 'WebPage':
                continue
            node['dateModified'] = DAY
            node['mainEntity'] = {'@id':item_list['@id']}
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '</script>'
    source = re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>', webpage_metadata, source, count=1)
    file.write_text(source, encoding='utf-8', newline='\n')
    data_file = root / 'home-library-data.json'
    data = json.loads(data_file.read_text(encoding='utf-8'))
    data.update({'updated':DAY, 'guideCount':len(guides['pages']), 'educationCount':len(education['articles']), 'bookCount':len(books['books']), 'topics':[{'group':g, 'route':r, 'title':t, 'description':d, 'action':a} for g, r, t, d, a in TOPICS], 'readingGroups':GROUPS, 'listedPages':listed, 'quickLinks':[{'route':r, 'title':t} for r, t in QUICK], 'answerLinks':[{'route':r, 'title':t} for r, t in FAQ_LINKS]})
    data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    enhance(parser.parse_args().root)

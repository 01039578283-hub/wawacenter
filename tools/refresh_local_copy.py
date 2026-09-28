"""Replace repetitive regional copy using reviewed facts, retaining the full sales image.

Advice below is consultation preparation, not a promise of a branch's class format.
Run after refresh_area_facts.py when regenerating legacy pages; dry-run by default.
"""
import argparse
import datetime
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from refresh_area_facts import ROOT, LD, LEVELS, scope, filtered, grade_text, esc, digest, save_json, walk

START = '<!-- local-copy:start -->'
END = '<!-- local-copy:end -->'
CSS = 'assets/local-editorial.css'


def plain(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()


def link_destination(value):
    """Drive's usp sharing hint is not part of the document identity."""
    parsed = urlsplit(html.unescape(value))
    if parsed.netloc == 'drive.google.com' and parsed.path.startswith('/file/d/'):
        return urlunsplit(parsed._replace(query=urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k != 'usp'])))
    return html.unescape(value)


class Sections(HTMLParser):
    """Locate complete outer sections, including nested prose sections."""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.lines = [0] + [m.end() for m in re.finditer('\n', text)]
        self.depth = 0
        self.blocks = []
        self.feed(text)
        assert self.depth == 0, 'Unbalanced sections'

    def position_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag == 'section':
            if self.depth == 0:
                self.start, self.attrs = self.position_offset(), dict(attrs)
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'section':
            self.depth -= 1
            assert self.depth >= 0
            if self.depth == 0:
                self.blocks.append((self.start, self.position_offset() + len('</section>'), self.attrs))


MATH = {
    '초': ('초등 수학', '계산 답뿐 아니라 식을 세운 이유와 문제에서 구할 것을 말할 수 있는지 살펴보세요. 틀린 문제 한두 개에 계산 실수인지, 조건을 읽기 어려웠는지 표시해 오면 질문이 구체적입니다.'),
    '중': ('중등 수학', '학교 진도에서 막힌 단원과 연결되는 이전 개념을 함께 확인해 보세요. 식을 세우기 전, 계산 중, 풀이를 설명하는 단계 중 어디에서 멈추는지 풀이 흔적을 남겨 오세요.'),
    '고': ('고등 수학', '문제를 읽고 첫 식을 세운 근거, 풀이를 끝내는 데 걸린 시간, 서술 과정에서 빠진 부분을 구분해 보세요. 학교 시험 범위와 선택 과목에 맞는 수업인지도 함께 물어보세요.'),
}
ENGLISH = {
    '초': ('초등 영어', '단어를 읽는 것과 뜻을 알고 문장에서 사용하는 것을 나누어 살펴보세요. 읽기 어려운 낱말이나 이해하지 못한 짧은 문장을 표시하면 현재 수준을 설명하기 쉽습니다.'),
    '중': ('중등 영어', '학교 교과서의 어휘·문법·본문 중 무엇이 어려운지 구분해 보세요. 해석은 되지만 답의 근거를 찾지 못한 문장과 서술형에서 감점된 답안을 함께 가져오세요.'),
    '고': ('고등 영어', '어휘 부족, 긴 문장의 구조, 글의 논리와 읽는 시간 중 막히는 지점을 표시해 보세요. 내신 교재와 모의고사에서 어려움이 같은지도 비교하면 학습 우선순위를 정하기 좋습니다.'),
}
COMBINED = {
    None: [('영어에서 확인할 것', '외운 단어를 문장 속에서 이해하는지, 문법은 알아도 독해에서 적용하기 어려운지 구분해 보세요. 어려웠던 문장과 답을 고른 근거를 준비해 주세요.'), ('수학에서 확인할 것', '개념 설명, 식 세우기, 계산, 풀이 설명 중 도움이 필요한 단계를 구분해 보세요. 정답 여부만 표시된 자료보다 학생이 직접 푼 흔적이 상담에 유용합니다.')],
    '초': [('영어: 읽기와 이해', '단어 읽기와 뜻 이해를 나누고, 짧은 문장을 혼자 읽을 때 막히는 부분을 표시해 보세요. 매일 할 수 있는 복습 분량도 함께 이야기해 주세요.'), ('수학: 계산과 문제 읽기', '계산 실수와 문장제 이해의 어려움을 구분해 보세요. 문제에서 구할 것을 말해 보고 식을 적은 과정을 가져오면 시작할 범위를 의논하기 좋습니다.')],
    '중': [('영어: 교과서와 서술형', '현재 교과서, 학교 프린트, 최근 서술형 답안에서 어휘·문법·독해 중 반복되는 어려움을 찾아보세요. 시험 범위가 정해졌다면 함께 알려 주세요.'), ('수학: 단원과 풀이 과정', '학교 진도와 연결되는 이전 개념, 첫 식을 세우는 과정, 계산 실수를 나누어 살펴보세요. 영어 과제와 겹치는 날의 실제 공부 시간도 함께 적어 주세요.')],
    '고': [('영어: 내신과 모의고사', '학교 교재와 모의고사에서 어려운 유형이 같은지 살펴보세요. 긴 문장 해석, 답의 근거, 읽는 시간 중 우선 확인할 항목을 정리해 주세요.'), ('수학: 선택 과목과 시험 범위', '선택 과목과 학교 진도, 풀이를 시작하지 못한 문제를 준비해 주세요. 개념 보완과 시간 안에 풀어내는 연습 중 어느 부분이 먼저 필요한지 질문해 보세요.')],
}
GRADE_GUIDE = {
    '초': [('혼자 시작하는 과정', '숙제를 시작하기까지 필요한 도움, 한 번에 집중하는 시간, 끝낸 분량을 적어 보세요. 여러 과목을 늘리기 전에 가장 도움이 필요한 과목부터 이야기해 주세요.'), ('설명할 수 있는 내용', '국어는 글의 내용을 자기 말로 설명하는지, 영어는 낱말과 문장을 이해하는지, 수학은 식을 세운 이유를 말하는지 살펴보세요. 상담에서는 해당 지점의 과목별 개설 여부도 확인해 주세요.')],
    '중': [('학교 진도와 평가 일정', '교과서·부교재와 최근 시험지, 수행평가 일정을 준비해 주세요. 과목마다 어려운 단원과 감점 이유를 나누면 복습 순서를 정하는 데 도움이 됩니다.'), ('공부량과 완료 기준', '학원 과제와 학교 과제가 겹치는 날을 표시하고, 실제로 끝낼 수 있는 양을 적어 보세요. 오답을 다시 풀 시점과 진도를 조정할 기준을 상담에서 확인해 주세요.')],
    '고': [('선택 과목과 목표', '학년뿐 아니라 선택 과목, 학교 시험 범위, 내신과 모의고사 중 우선할 목표를 알려 주세요. 과목별 수강 학년과 현재 개설 과정을 각각 확인해야 합니다.'), ('시간을 쓰는 우선순위', '과목별 공부 시간과 최근 오답을 비교해 보세요. 오래 공부해도 해결되지 않는 유형을 먼저 정리하고, 학교 일정 안에서 가능한 수업·복습 분량을 의논해 주세요.')],
}


def topic(r, subjects, level):
    prefix = LEVELS[level][0] + ' ' if level else ''
    return prefix + ('·'.join(subjects) if len(subjects) <= 2 else '과목별 수업')


def availability(r, subjects, level):
    known = [s + ' ' + grade_text(filtered(r, s, level)) for s in subjects if filtered(r, s, level)]
    missing = [s for s in subjects if not filtered(r, s, level)]
    result = ('자료에 기재된 학년은 ' + ', '.join(known) + '입니다. ') if known else ''
    if missing:
        result += ' · '.join(missing) + '의 해당 학년 정보는 기재되어 있지 않아 수강 가능 여부를 상담으로 확인해야 합니다. '
    result += '현재 개설 과정과 수업 시간은 지점 상담에서 확인해 주세요.'
    return result


def content_model(r, name, title):
    category, subjects, level = scope(name)
    branch = r['branch'].replace('와와학습코칭센터', '').strip()
    current = {s: filtered(r, s, level) for s in subjects}
    missing = [s for s, gs in current.items() if not gs]
    if len(subjects) == 1:
        subject = subjects[0]
        intro = f'{branch}의 {subject} 안내 학년을 먼저 확인한 뒤, 현재 배우는 단원과 도움이 필요한 부분을 알려 주세요.'
        if missing:
            intro = f'{branch}의 제공 자료에는 {subject} 안내 학년이 기재되어 있지 않습니다. 수강 가능 여부를 먼저 확인한 뒤 학습 상담을 준비해 주세요.'
        guide = MATH if subject == '수학' else ENGLISH
        rows = [guide[lv] for lv in LEVELS if any(g.startswith(lv) for g in current[subject])]
        if not rows:
            rows = [(subject + ' 상담 준비', '최근에 혼자 풀어 본 문제와 사용 중인 교재를 준비해 주세요. 어려웠던 부분과 혼자 해결할 수 있었던 부분을 나누어 표시하면 상담할 내용을 정리하기 좋습니다.')]
        heading = subject + ' 상담에서 짚어 볼 학습 내용'
    elif len(subjects) == 2:
        heading = ('고등부 과목별 학습 우선순위' if level == '고' else '영어와 수학을 나누어 확인할 부분')
        intro = f'{branch}의 영어와 수학은 과목별 안내 학년을 각각 확인해야 합니다. 학생의 약점과 학교 일정에 따라 두 과목의 우선순위를 정리해 주세요.'
        if missing:
            intro = f'{branch}의 {"·".join(missing)} 학년 정보는 확인되지 않았습니다. 두 과목을 함께 수강할 수 있는지 상담으로 확인해 주세요.'
        elif current['영어'] != current['수학']:
            intro = f'{branch}은 영어와 수학의 안내 학년이 서로 다릅니다. 한 과목의 학년 안내가 다른 과목에도 적용되는 것은 아니므로 각각 확인해 주세요.'
        rows = COMBINED[level]
        if category == '영어수학학원':
            heading = '두 과목의 공부 시간을 배분할 때'
            rows = [('과목마다 실제로 쓴 시간', '일주일 동안 영어와 수학에 쓴 시간, 끝낸 양, 미룬 과제를 따로 적어 보세요. 두 과목의 분량을 같게 맞추기보다 학생이 어려워하는 부분에 시간을 어떻게 배분할지 의논해 주세요.'), ('복습과 과제가 겹치는 날', '단어 복습, 독해 과제, 수학 오답을 한꺼번에 몰아서 하는 날이 있는지 살펴보세요. 학교 과제와 함께 진행할 수 있는 수업 요일과 과제량을 확인해 주세요.')]
    elif level:
        heading = LEVELS[level][0] + ' 학습 상담에서 확인할 내용'
        intro = f'{branch}의 {LEVELS[level][0]} 과정은 과목마다 안내 학년이 다릅니다. 학생의 학년과 필요한 과목을 함께 전달해 주세요.'
        if not any(current.values()):
            intro = f'{branch}의 제공 자료에서는 {LEVELS[level][0]} 수강 학년을 확인할 수 없습니다. 현재 개설 여부를 먼저 문의해 주세요.'
        rows = GRADE_GUIDE[level]
    elif category == '와와학습코칭학원':
        heading = '공부 계획이 이어지지 않을 때 살펴볼 내용'
        intro = f'{branch} 상담을 준비할 때는 계획표에 적은 양과 실제로 끝낸 양을 비교해 보세요. 학생에게 필요한 도움을 구체적으로 설명하는 출발점이 됩니다.'
        rows = [('계획보다 적게 끝나는 이유', '시작을 미루는지, 문제에서 오래 멈추는지, 계획한 양이 너무 많은지 구분해 보세요. 며칠간의 시작 시간과 완료량을 기록하면 조정할 부분을 이야기하기 쉽습니다.'), ('오답을 다시 볼 기준', '틀린 이유를 확인한 뒤 도움 없이 다시 풀 수 있는지 살펴보세요. 상담에서는 재확인 시점, 과제량 조정 기준, 학부모에게 안내하는 방식을 질문해 보세요.')]
    else:
        heading = branch + ' 상담을 준비하는 순서'
        intro = f'{r["area"]}에서 수업을 찾는 학생에게 연결된 지점은 {r["branch"]}입니다. 필요한 과목과 학년을 확인한 다음 실제 통학 일정에 맞춰 상담을 준비해 주세요.'
        rows = [('과목과 학년부터 확인', '가장 도움이 필요한 과목, 현재 교재, 학교 진도를 알려 주세요. 과목별 안내 학년이 다르므로 여러 과목을 함께 수강하려면 각각 확인해 주세요.'), ('학교생활과 이동 일정', '하교 시간과 다른 활동을 포함한 일주일 시간표를 준비해 주세요. 위의 실제 지점 주소를 기준으로 이동 시간을 살펴보고 수업 요일과 시작 시간을 문의해 주세요.')]
    prep = ['현재 교재와 최근에 직접 푼 문제', '재학 학교·학년과 시험 또는 수행평가 일정', '희망 요일과 실제로 공부할 수 있는 시간']
    if subjects == ['수학']:
        prep[0] = '풀이 흔적이 남은 문제와 막힌 단원'
    elif subjects == ['영어']:
        prep[0] = '어려운 문장을 표시한 교재와 최근 답안'
    elif category == '와와학습코칭학원':
        prep[0] = '며칠간의 계획량·완료량과 미룬 과제'
    focus = title.partition('|')[2].strip()
    schools = [(lv, names) for lv, names in r['schools'].items() if (not level or lv == level) and names]
    fee = ('<a href="' + esc(r['feeUrl']) + '" target="_blank" rel="noopener noreferrer">센터별 교습비 자료</a>에서 안내 금액을 확인할 수 있습니다. ' if r['feeUrl'] else '')
    faqs = [(branch + '의 ' + topic(r, subjects, level) + ' 안내 학년은 어떻게 되나요?', esc(availability(r, subjects, level))),
            ('교습비와 현재 수업 시간은 어떻게 확인하나요?', fee + '희망 과목·학년을 알려 주고 현재 과정의 교습비, 교재비 등 추가 비용, 수업 요일과 시간을 확인해 주세요.')]
    if len(subjects) == 2:
        faqs.append(('영어와 수학을 꼭 같은 양으로 공부해야 하나요?', '현재 이해도와 학교 과제가 다르므로 두 과목의 분량을 동일하게 정할 필요는 없습니다. 과목별로 끝낼 수 있는 양과 복습 시간을 적어 보고, 함께 수강할 경우의 일정과 과제 조정 방식을 문의해 주세요.'))
    else:
        faqs.append(('상담에서 학습관리 방식은 무엇을 물어보면 좋나요?', '학생이 푼 문제와 실제 공부량을 어떻게 확인하는지, 오답을 언제 다시 보는지, 계획한 양을 끝내기 어려울 때 어떻게 조정하는지 물어보세요. 점검 주기와 학부모 안내 방식도 함께 확인해 주세요.'))
    return dict(heading=heading, intro=intro, rows=rows, prep=prep, focus=focus, schools=schools, faqs=faqs)


def render(r, model):
    rows = ''.join(f'<div class="local-reading-row"><h3>{esc(h)}</h3><p>{esc(p)}</p></div>' for h, p in model['rows'])
    checklist = ''.join(f'<li>{esc(item)}</li>' for item in model['prep'])
    focus = f'<p class="local-copy-focus"><strong>함께 의논할 주제</strong> {esc(model["focus"])}</p>' if model['focus'] else ''
    schools = ''.join(f'<div><dt>{LEVELS[lv][0]}</dt><dd>{esc(" · ".join(names))}</dd></div>' for lv, names in model['schools'])
    school_body = f'<dl class="local-school-list">{schools}</dl><p class="local-copy-note">지역 참고 학교이며, 재원 여부나 학교별 반 운영을 뜻하지 않습니다. 재학 중인 학교의 교재·시험 범위·하교 시간을 기준으로 상담해 주세요.</p>' if schools else '<p>현재 자료에 이 학년에 해당하는 학교 목록은 없습니다. 재학 학교와 교재, 시험 일정, 하교 시간을 알려 주세요.</p>'
    faqs = ''.join(f'<details><summary>{esc(q)}</summary><p>{answer}</p></details>' for q, answer in model['faqs'])
    return f'''{START}
    <div class="local-editorial" data-copy-version="1">
      <section class="section local-reading-section" aria-labelledby="learning-guide-title">
        <p class="eyebrow">학습 상담 준비</p><h2 id="learning-guide-title">{esc(model['heading'])}</h2>
        <p class="local-copy-scope">{esc(model['intro'])}</p>{focus}
        <div class="local-reading-layout"><div>{rows}</div><aside class="local-preparation" aria-labelledby="checklist-title"><h3 id="checklist-title">상담 전에 준비해 주세요</h3><ul>{checklist}</ul></aside></div>
      </section>
      <section class="section local-school-section" aria-labelledby="local-facts-title"><p class="eyebrow">학교와 일정</p><h2 id="local-facts-title">{esc(r['area'])} 학교생활과 함께 맞춰 볼 일정</h2>{school_body}</section>
      <section class="section local-faq-section" aria-labelledby="faq-title"><p class="eyebrow">자주 묻는 질문</p><h2 id="faq-title">수강 전 확인할 질문</h2><div class="local-copy-faq">{faqs}</div></section>
      <section class="section local-followup-section" aria-labelledby="review-title"><h2 id="review-title">상담 후 정리할 내용</h2><p>안내받은 수강 과목·학년, 수업 요일·시간, 교습비와 추가 비용을 함께 적어 두세요. 학생이 시작할 학습 범위와 과제량, 다음에 학습 상태를 확인할 시점도 정리하면 계획을 이어 가기 좋습니다.</p></section>
    </div>
    {END}'''


def rewrite(text, name, r):
    title = plain(re.search(r'<title\b[^>]*>(.*?)</title>', text, re.S)[1])
    model = content_model(r, name, title)
    new_body = render(r, model)
    if START in text:
        assert text.count(START) == text.count(END) == 1
        start, end = text.index(START), text.index(END) + len(END)
        text = text[:start] + new_body + text[end:]
    else:
        blocks = Sections(text).blocks
        related = next(b for b in blocks if 'related-links-section' in b[2].get('class', '').split())
        if name.startswith('과목별학원/'):
            first = next(b for b in blocks if 'subject-article-section' in b[2].get('class', '').split())
            text = text[:first[0]] + new_body + '\n    ' + text[related[0]:]
        else:
            first = next(b for b in blocks if 'local-content' in b[2].get('class', '').split())
            faq = next(b for b in blocks if b[0] > related[1] and '<div class="faq">' in text[b[0]:b[1]])
            text = text[:first[0]] + new_body + '\n    ' + text[related[0]:related[1]] + text[faq[1]:]
    labels = {'learning-guide-title': '학습 상담 준비', 'checklist-title': '준비할 자료', 'local-facts-title': '학교와 일정', 'faq-title': '수강 전 질문', 'review-title': '상담 후 정리'}
    for number, (anchor, label) in enumerate(labels.items(), 2):
        contents = f'<span class="subject-page-toc-number" aria-hidden="true">{number:02}</span><span class="subject-page-toc-text">{label}</span>'
        text = re.sub(r'(<a\b[^>]*href="#' + anchor + r'"[^>]*>).*?(</a>)', lambda m: m[1] + contents + m[2], text, flags=re.S)
    headings = [(m[1], plain(m[2])) for m in re.finditer(r'<h[23] id="([^"]+)">(.*?)</h[23]>', new_body, re.S)]
    schools = [school for _, names in model['schools'] for school in names]
    mentions = [{'@type': 'Place', 'name': value} for value in [r['region'], r['district'], r['area']] if value]
    mentions += [{'@type': 'School', 'name': school} for school in schools]
    def update(m):
        obj = json.loads(m[2])
        for node in walk(obj):
            kind = node.get('@type')
            if kind == 'FAQPage':
                node['mainEntity'] = [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': plain(a)}} for q, a in model['faqs']]
            if kind in ['WebPage', 'Article', 'Service']:
                node['mentions'] = mentions
            if kind in ['WebPage', 'Article']:
                base = node.get('url') or node.get('@id', '').split('#')[0]
                node['hasPart'] = [{'@type': 'WebPageElement', 'name': label, 'url': base + '#' + anchor} for anchor, label in headings]
                node['dateModified'] = '2026-09-28'
            if kind == 'Article':
                node['articleSection'] = [label for _, label in headings]
            if kind == 'ItemList' and node.get('@id', '').endswith('#checklist'):
                node['name'] = '상담 전에 준비할 자료'
                node['itemListElement'] = [{'@type': 'ListItem', 'position': i, 'name': item} for i, item in enumerate(model['prep'], 1)]
        return m[1] + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + m[3]
    text = LD.sub(update, text)
    if CSS not in text:
        text = text.replace('</head>', '<link rel="stylesheet" href="' + '../' * (len(name.split('/')) - 1) + CSS + '">\n</head>')
    return text


def regional(name):
    parts = name.split('/')
    if name.endswith('/index.html') and parts[0] == '과목별학원' and len(parts) == 4:
        return parts[2]
    if name.endswith('/index.html') and parts[0] == '전국센터' and len(parts) in [3, 4]:
        return parts[1]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text(encoding='utf-8-sig'))
    areas = {r['slug']: r for r in json.loads((ROOT / 'area-reference.json').read_text(encoding='utf-8'))['areas']}
    names = [n for n in manifest['files'] if regional(n)]
    changed = []
    def process(name):
        raw = (ROOT / name).read_bytes()
        old = raw.decode('utf-8-sig')
        new = rewrite(old, name, areas[regional(name)])
        assert rewrite(new, name, areas[regional(name)]) == new, (name, 'Non-idempotent copy')
        for pattern in [r'<title\b[^>]*>.*?</title>', r'<h1\b[^>]*>.*?</h1>', r'<link\b[^>]*rel="canonical"[^>]*>', r'<meta\b[^>]*>', r'<img\b[^>]*>', r'<source\b[^>]*>', r'<aside class="floating-actions".*?</aside>']:
            assert re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S), (name, 'Protected content', pattern)
        assert set(re.findall(r'\bid="([^"]+)"', old)) <= set(re.findall(r'\bid="([^"]+)"', new)), (name, 'Lost anchor')
        assert {link_destination(v) for v in re.findall(r'<a\b[^>]*href="([^"]+)"', old)} <= {link_destination(v) for v in re.findall(r'<a\b[^>]*href="([^"]+)"', new)}, (name, 'Lost link')
        if old != new:
            data = (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + new.encode('utf-8')
            if args.apply:
                (ROOT / name).write_bytes(data)
            return name, digest(data), digest(data.decode('utf-8').replace('\r\n', '\n').encode())
        return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, result in enumerate(pool.map(process, names), 1):
            if result:
                name, binary_hash, text_hash = result
                changed.append(name)
                manifest['files'][name] = binary_hash
                manifest.setdefault('textSha256', {})[name] = text_hash
            if i % 500 == 0:
                print(json.dumps({'checked': i, 'changed': len(changed)}), flush=True)
    css = (ROOT / CSS).read_bytes()
    if args.apply:
        manifest['files'][CSS] = digest(css)
        manifest.setdefault('textSha256', {})[CSS] = digest(css.decode('utf-8').replace('\r\n', '\n').encode())
        if changed:
            manifest['createdAt'] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
        save_json(ROOT / 'release-public-manifest.json', manifest)
    report = {'mode': 'apply' if args.apply else 'dry-run', 'checkedHtml': len(names), 'changedHtml': len(changed), 'changedFiles': changed, 'newRoutes': 0}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'changedFiles'}))


if __name__ == '__main__':
    main()

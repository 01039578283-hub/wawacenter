from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote


ROOT = Path.cwd()
SOURCE_ROOT = ROOT.parent / "홈페이지"
CENTER_ROOT = ROOT / "전국센터"
ASSETS = ROOT / "assets"
MAPS = ASSETS / "maps"
COMMON = ASSETS / "centers" / "common"
SITE_NAME = "와와센터 학습코칭"
ORG_NAME = "와와센터 학습코칭"
PHONE = "010-3957-8283"
BASE_URL = "https://xn--3e0bz50bxucwzc.com"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
SMS_URL = "https://blogsms.net/01039578283"
DATE_PUBLISHED = "2026-06-29"
DATE_MODIFIED = "2026-06-30"

REGION_LABELS = {
    "seoul": "서울",
    "gyeonggi": "경기",
    "incheon": "인천",
    "daejeon": "대전",
    "chungcheong": "충청",
    "daegu": "대구",
    "ulsan": "울산",
    "busan": "부산",
    "gyeongsang": "경상",
    "gwangju": "광주",
    "jeolla": "전라",
    "gangwon": "강원",
    "jeju": "제주",
}


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def safe_slug(value: str) -> str:
    value = re.sub(r"[\s/\\:*?\"<>|]+", "", value or "")
    value = value.strip(".")
    return value or "센터"


def parse_breadcrumb_names(source: str) -> list[str]:
    m = re.search(r"<script type=\"application/ld\+json\">(.*?)</script>", source, re.S | re.I)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    items = data.get("itemListElement", []) if isinstance(data, dict) else []
    return [str(item.get("name", "")).strip() for item in items if isinstance(item, dict)]


def title_area(source: str) -> str:
    m = re.search(r"<title>(.*?)</title>", source, re.S | re.I)
    title = clean_text(m.group(1)).split("|", 1)[0].strip() if m else ""
    return re.sub(r"\s*영어\s*수학\s*학원\s*$", "", title).strip()


def find_map_file(oldslug: str, source: str) -> str:
    m = re.search(r"assets/maps/([^\"']+\.(?:jpg|jpeg|png|webp))", source, re.I)
    candidates = []
    if m:
        candidates.append(m.group(1))
    candidates.extend([f"{oldslug}.jpg", f"{oldslug}.png", f"{oldslug}.webp", f"{oldslug}.jpeg"])
    for name in candidates:
        if (MAPS / name).exists():
            return name
    return candidates[0] if candidates else f"{oldslug}.jpg"


def collect_rows() -> list[dict]:
    rows: list[dict] = []
    for p in (SOURCE_ROOT / "center").rglob("index.html"):
        rel = p.relative_to(SOURCE_ROOT)
        if len(rel.parts) != 5:
            continue
        source = p.read_text(encoding="utf-8", errors="ignore")
        names = parse_breadcrumb_names(source)
        region_slug = rel.parts[1]
        district_slug = rel.parts[2]
        oldslug = rel.parts[3]
        area = title_area(source)
        if not area:
            area = names[-1] if names else oldslug
        neighborhood = area.split()[-1]
        region_name = names[1] if len(names) > 1 else REGION_LABELS.get(region_slug, region_slug)
        district_name = names[2] if len(names) > 2 else district_slug
        rows.append(
            {
                "region_slug": region_slug,
                "region_name": region_name,
                "district_slug": district_slug,
                "district_name": district_name,
                "oldslug": oldslug,
                "area": area,
                "neighborhood": neighborhood,
                "map": find_map_file(oldslug, source),
            }
        )
    rows.sort(key=lambda r: (list(REGION_LABELS).index(r["region_slug"]) if r["region_slug"] in REGION_LABELS else 99, r["district_name"], r["area"]))
    return rows


def enrich_slugs(rows: list[dict]) -> list[dict]:
    name_counts = Counter(r["neighborhood"] for r in rows)
    used: Counter[str] = Counter()
    for r in rows:
        base = r["neighborhood"] if name_counts[r["neighborhood"]] == 1 else r["area"]
        slug = safe_slug(base)
        used[slug] += 1
        if used[slug] > 1:
            slug = safe_slug(f"{r['area']}{r['district_name']}")
            used[slug] += 1
        r["slug"] = slug
        r["title_area"] = r["area"] if name_counts[r["neighborhood"]] > 1 else r["neighborhood"]
        r["page_title"] = f"{r['title_area']} 와와학습코칭센터"
    return rows


def rel_assets(depth: int = 2) -> str:
    return "../" * depth + "assets"


def absolute_url(path: str) -> str:
    return BASE_URL + quote(path, safe="/:#")


def nav(active: str, prefix: str = "") -> str:
    links = [
        ("홈", f"{prefix or './'}"),
        ("학습가이드", f"{prefix}학습가이드/"),
        ("상담문의", f"{prefix}상담문의/"),
        ("전국학원", f"{prefix}전국센터/"),
    ]
    rendered = []
    for label, href in links:
        current = ' aria-current="page"' if label == active else ""
        rendered.append(f'<a href="{href}"{current}>{label}</a>')
    return "\n        ".join(rendered)


def floating(prefix: str = "") -> str:
    return f"""<aside class=\"floating-actions\" aria-label=\"빠른 상담 버튼\">
    <a href=\"tel:010-3957-8283\">전화문의</a>
    <a href=\"{SMS_URL}\" target=\"_blank\" rel=\"noopener\">문자문의</a>
    <a href=\"{FORM_URL}\" target=\"_blank\" rel=\"noopener\">상담신청</a>
  </aside>"""


def header(active: str, prefix: str = "") -> str:
    home = prefix or "./"
    return f"""<header class=\"site-header\">
    <div class=\"header-inner\">
      <a class=\"brand\" href=\"{home}\" aria-label=\"{SITE_NAME} 홈\"><span class=\"brand-mark\">W</span><span>{SITE_NAME}</span></a>
      <nav class=\"nav\" aria-label=\"상단 메뉴\">
        {nav(active, prefix)}
      </nav>
      <a class=\"header-cta\" href=\"{FORM_URL}\" target=\"_blank\" rel=\"noopener\">상담 신청</a>
    </div>
  </header>"""


def footer(prefix: str = "") -> str:
    return f"""<footer class=\"footer\">
    <div class=\"footer-inner\">
      <div><strong>{SITE_NAME}</strong><br>초중고 영어·수학·국어 학습관리 안내</div>
      <div>상담 전화 <a href=\"tel:01039578283\">{PHONE}</a></div>
    </div>
  </footer>"""


def faq_items(title: str, area: str) -> list[tuple[str, str]]:
    return [
        (
            f"{title} 상담에서는 무엇을 먼저 확인하나요?",
            f"{title} 상담에서는 최근 성적만 보지 않고 학교 진도, 공부 시간, 과제 수행 습관, 반복되는 오답 유형을 함께 확인합니다.",
        ),
        (
            f"{area}에서 학습코칭센터를 알아볼 때 어떤 기준이 중요할까요?",
            f"{area}에서 학습코칭센터를 비교할 때는 진도보다 학생에게 맞는 시작점, 플래너 점검, 오답 재학습, 학부모 피드백이 실제로 이어지는지 확인하는 것이 좋습니다.",
        ),
        (
            "영어·수학·국어를 함께 상담할 수 있나요?",
            "네. 영어는 어휘·문법·독해 흐름을, 수학은 개념·유형·오답 원인을, 국어는 지문 이해와 근거 찾기를 함께 확인할 수 있습니다.",
        ),
        (
            f"{title} 상담 전에 무엇을 준비하면 좋나요?",
            "최근 시험지, 현재 교재, 학교 진도, 수행평가 일정, 평소 공부 시간과 숙제 습관을 알려주시면 상담 방향을 더 구체적으로 잡을 수 있습니다.",
        ),
    ]


def review_items(area: str) -> list[tuple[str, str]]:
    return [
        ("5", f"{area} 안내를 보고 상담했는데, 아이가 어디에서 막히는지 차분히 정리할 수 있었습니다."),
        ("5", "플래너와 오답을 같이 본다는 점이 좋았습니다. 단순히 문제를 더 푸는 방식과 달라 보여요."),
        ("5", "시험지와 공부 습관을 함께 확인해 주니 학부모 입장에서도 관리 방향이 더 분명해졌습니다."),
    ]


def child_title(row: dict) -> str:
    return f"{row['title_area']} 와와학습코칭학원"


def child_faq_items(title: str, area: str) -> list[tuple[str, str]]:
    return [
        (
            f"{title}은 어떤 학생에게 맞나요?",
            f"{title}은 단순 진도보다 학생의 현재 상태를 먼저 확인하고 싶은 초등·중등·고등 학생에게 적합합니다. 특히 공부 습관, 오답 반복, 시험 준비 흐름이 흔들리는 경우 상담에서 기준을 잡기 좋습니다.",
        ),
        (
            f"{area} 와와학습코칭학원 상담에서는 어떤 자료를 보면 좋나요?",
            "최근 시험지, 현재 교재, 학교 진도, 수행평가 일정, 평소 공부 시간과 숙제 습관을 함께 보면 학생에게 필요한 관리 방향을 더 구체적으로 정리할 수 있습니다.",
        ),
        (
            "수업은 영어·수학·국어를 모두 확인하나요?",
            "네. 영어는 어휘·문법·독해, 수학은 개념·유형·오답, 국어는 지문 이해와 근거 찾기처럼 과목별로 막히는 지점을 나누어 확인합니다.",
        ),
        (
            f"{title}에서는 플래너와 오답을 어떻게 활용하나요?",
            "플래너에는 과목·단원·분량·완료 기준을 적고, 오답은 틀린 원인을 나눠 다시 맞힐 수 있는지 확인합니다. 이 과정이 다음 학습 계획에 이어지도록 관리합니다.",
        ),
    ]


def child_review_items(area: str) -> list[tuple[str, str]]:
    return [
        ("5", f"{area}에서 학습코칭학원을 찾다가 상담 내용을 확인했는데, 단순 수업보다 관리 기준이 분명해 보여 좋았습니다."),
        ("5", "아이의 시험지와 공부 습관을 함께 본다는 점이 믿음이 갔고, 오답을 다시 연결하는 방식이 마음에 들었습니다."),
        ("5", "플래너를 형식적으로 쓰는 것이 아니라 실제 실행 결과를 확인한다는 점이 도움이 될 것 같습니다."),
    ]


def english_math_title(row: dict) -> str:
    return f"{row['title_area']} 영어수학학원"


def english_math_faq_items(title: str, area: str) -> list[tuple[str, str]]:
    return [
        (
            f"{title}에서는 영어와 수학을 어떻게 같이 관리하나요?",
            f"{title}에서는 영어는 어휘·문법·독해 흐름을, 수학은 개념·유형·오답 원인을 나누어 확인합니다. 두 과목의 공부 시간이 한쪽으로 쏠리지 않도록 플래너 기준도 함께 잡습니다.",
        ),
        (
            f"{area} 영어수학학원 상담 전에 어떤 자료를 준비하면 좋나요?",
            "최근 시험지, 현재 교재, 학교 진도, 수행평가 일정, 평소 숙제 습관을 알려주시면 영어와 수학 중 어느 과목을 먼저 보완해야 하는지 더 구체적으로 정리할 수 있습니다.",
        ),
        (
            "초등·중등·고등 학생 모두 상담 가능한가요?",
            "네. 초등은 학습 습관과 기초 개념, 중등은 내신 대비와 단원별 오답, 고등은 시험 범위 관리와 취약 유형 보완을 중심으로 확인합니다.",
        ),
        (
            f"{title}에서 오답 관리는 어떻게 진행하나요?",
            "영어는 해석 오류, 문법 적용, 어휘 부족을 나누어 보고, 수학은 개념 부족, 계산 실수, 유형 미숙을 구분합니다. 틀린 문제를 다시 맞히는 기준까지 확인하는 방식입니다.",
        ),
    ]


def english_math_review_items(area: str) -> list[tuple[str, str]]:
    return [
        ("5", f"{area}에서 영어와 수학을 같이 볼 수 있는 곳을 찾았는데, 과목별로 막히는 이유를 나눠 설명해줘서 이해하기 쉬웠습니다."),
        ("5", "영어 단어와 수학 오답을 따로 관리하는 게 아니라 주간 계획 안에서 같이 보니까 아이 공부 흐름이 더 정리되는 느낌이었습니다."),
        ("5", "시험 전에는 영어 독해와 수학 유형 복습 순서를 같이 잡아준다는 점이 마음에 들었습니다."),
    ]


def internal_links_section(row: dict, current: str) -> str:
    area = row["title_area"]
    parent = row["page_title"]
    child = child_title(row)
    english_math = english_math_title(row)
    if current == "child":
        headline = f"{area} 관련 학습 페이지"
        description = "현재 페이지와 연결된 동네 안내, 영어수학학원, 전국학원, 학습가이드, 상담문의 페이지를 한 번에 이동할 수 있도록 정리했습니다."
        cards = [
            ("동네 안내", "../", parent, "센터 위치, 본문 이미지, FAQ와 후기까지 함께 확인합니다."),
            ("영어수학", "../영어수학학원/", english_math, "영어와 수학을 함께 관리하는 과목별 안내를 확인합니다."),
            ("전국학원", "../../", "전국학원 전체보기", "다른 지역과 동네의 학습코칭 안내 페이지를 찾아봅니다."),
            ("학습가이드", "../../../학습가이드/", "학습가이드", "진단 상담, 플래너, 오답 관리 기준을 더 넓게 확인합니다."),
            ("상담문의", "../../../상담문의/", "상담문의", "아이의 현재 학습 상황에 맞춰 상담을 준비합니다."),
        ]
    elif current == "english_math":
        headline = f"{area} 관련 영어·수학 학습 페이지"
        description = "현재 영어수학학원 페이지와 연결된 동네 안내, 학습코칭학원, 전국학원, 학습가이드, 상담문의 페이지를 정리했습니다."
        cards = [
            ("동네 안내", "../", parent, "센터 위치, 본문 이미지, FAQ와 후기까지 함께 확인합니다."),
            ("학습코칭", "../와와학습코칭학원/", child, "진단 상담과 플래너·오답 관리 흐름을 자세히 봅니다."),
            ("전국학원", "../../", "전국학원 전체보기", "다른 지역과 동네의 학습코칭 안내 페이지를 찾아봅니다."),
            ("학습가이드", "../../../학습가이드/", "학습가이드", "진단 상담, 플래너, 오답 관리 기준을 더 넓게 확인합니다."),
            ("상담문의", "../../../상담문의/", "상담문의", "아이의 현재 학습 상황에 맞춰 상담을 준비합니다."),
        ]
    else:
        headline = f"{area} 관련 페이지 바로가기"
        description = "동네 안내에서 더 구체적인 학습코칭학원, 영어수학학원, 상담/가이드 페이지로 자연스럽게 이동할 수 있게 정리했습니다."
        cards = [
            ("상세 안내", "와와학습코칭학원/", child, "진단 상담, 플래너 관리, 오답 재학습 기준을 자세히 봅니다."),
            ("영어수학", "영어수학학원/", english_math, "영어와 수학을 함께 관리하는 과목별 학습 기준을 봅니다."),
            ("전국학원", "../", "전국학원 전체보기", "다른 지역과 동네의 학습코칭 안내 페이지를 찾아봅니다."),
            ("학습가이드", "../../학습가이드/", "학습가이드", "진단 상담, 플래너, 오답 관리 기준을 더 넓게 확인합니다."),
            ("상담문의", "../../상담문의/", "상담문의", "아이의 현재 학습 상황에 맞춰 상담을 준비합니다."),
        ]
    card_html = "\n".join(
        f"""        <a class=\"related-link-card\" href=\"{href}\">
          <span>{html.escape(kicker)}</span>
          <b>{html.escape(title)}</b>
          <em>{html.escape(desc)}</em>
        </a>"""
        for kicker, href, title, desc in cards
    )
    return f"""    <section class=\"section related-links-section\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Internal Links</p>
        <h2>{html.escape(headline)}</h2>
        <p class=\"lead\">{html.escape(description)}</p>
      </div>
      <div class=\"related-link-grid\">
{card_html}
      </div>
    </section>"""


def parent_depth_section(row: dict, title: str, area: str) -> str:
    region = html.escape(row["region_name"])
    district = html.escape(row["district_name"])
    title_e = html.escape(title)
    area_e = html.escape(area)
    return f"""    <section class=\"section split local-content seo-depth-section\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Local Study Detail</p>
        <h2>{title_e} 선택 전 확인할<br>{area_e} 학습관리 포인트</h2>
        <p class=\"lead\">{region} {district} 생활권 안에서도 학교 진도, 수행평가 일정, 학생별 공부 습관은 다르게 나타납니다. {area_e} 학생에게 필요한 관리는 단순 진도보다 현재 막히는 원인을 정확히 나누는 데서 시작합니다.</p>
      </div>
      <div class=\"child-focus-grid\">
        <article>
          <span>초</span>
          <h3>{area_e} 초등 학습 습관</h3>
          <p>초등반은 숙제 완성도, 교과 개념 이해, 문제를 읽는 순서를 함께 점검해 중등 학습으로 이어질 기초를 잡습니다.</p>
        </article>
        <article>
          <span>중</span>
          <h3>{area_e} 중등 내신 준비</h3>
          <p>중등반은 학교 진도와 시험 범위를 기준으로 단원별 오답, 수행평가 일정, 주간 복습량을 나누어 관리합니다.</p>
        </article>
        <article>
          <span>고</span>
          <h3>{area_e} 고등 학습관리</h3>
          <p>고등반은 과목별 우선순위와 시험 전 복습 순서를 정리해 부족한 단원과 취약 유형을 반복 확인합니다.</p>
        </article>
        <article>
          <span>상</span>
          <h3>{title_e} 상담 준비</h3>
          <p>최근 시험지, 현재 교재, 학교 진도, 평소 공부 시간과 숙제 습관을 함께 보면 상담에서 더 구체적인 관리 기준을 잡을 수 있습니다.</p>
        </article>
      </div>
    </section>

    <section class=\"section local-guide-panel seo-check-section\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Who Needs Coaching</p>
        <h2>{title_e} 추천 학생</h2>
        <p class=\"lead\">점수만 올리는 설명보다, 공부 과정이 흔들리는 이유를 찾고 매주 실행 여부를 확인해야 하는 학생에게 적합합니다.</p>
      </div>
      <div class=\"local-info-grid\">
        <div><b>계획이 자주 밀리는 학생</b><span>분량·마감·완료 기준을 구체적으로 나누어 확인합니다.</span></div>
        <div><b>오답이 반복되는 학생</b><span>틀린 이유를 개념, 실수, 유형, 시간 문제로 나눠 다시 봅니다.</span></div>
        <div><b>시험 전 불안한 학생</b><span>시험 범위와 복습 순서를 정리해 마지막 점검 흐름을 만듭니다.</span></div>
      </div>
    </section>
"""


def coaching_depth_section(row: dict, title: str, area: str) -> str:
    title_e = html.escape(title)
    area_e = html.escape(area)
    return f"""    <section class=\"section split local-content seo-depth-section\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Coaching Detail</p>
        <h2>{title_e}에서 보는<br>학년별 관리 기준</h2>
        <p class=\"lead\">학습코칭은 모든 학생에게 같은 진도를 적용하는 방식이 아니라, {area_e} 학생의 현재 습관과 과목별 약점을 확인한 뒤 필요한 순서를 잡는 과정입니다.</p>
      </div>
      <div class=\"child-focus-grid\">
        <article>
          <span>01</span>
          <h3>추천하는 학생</h3>
          <p>공부 시간은 쓰고 있지만 결과가 불안정하거나, 숙제와 오답 정리가 매주 밀리는 학생에게 도움이 됩니다.</p>
        </article>
        <article>
          <span>02</span>
          <h3>초등·중등·고등 구분</h3>
          <p>초등은 습관과 기초, 중등은 내신과 수행평가, 고등은 시험 범위와 취약 단원 보완을 중심으로 확인합니다.</p>
        </article>
        <article>
          <span>03</span>
          <h3>수업 후 확인</h3>
          <p>그날 배운 내용이 실제 과제와 오답 재학습으로 이어졌는지 확인하고 다음 계획에 반영합니다.</p>
        </article>
        <article>
          <span>04</span>
          <h3>{area_e} 상담 포인트</h3>
          <p>{area_e} 학교 진도와 학생의 현재 교재를 함께 보면 필요한 과목과 단원을 더 빠르게 정리할 수 있습니다.</p>
        </article>
      </div>
    </section>
"""


def english_math_depth_section(row: dict, title: str, area: str) -> str:
    title_e = html.escape(title)
    area_e = html.escape(area)
    return f"""    <section class=\"section split local-content seo-depth-section\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Subject Detail</p>
        <h2>{title_e} 선택 전<br>영어·수학을 따로 봐야 하는 이유</h2>
        <p class=\"lead\">영어와 수학은 같은 시간표 안에서 관리하더라도 막히는 원인이 다릅니다. {area_e} 학생의 어휘·문법·독해 흐름과 수학 개념·유형·오답 원인을 나누어 봐야 관리 방향이 선명해집니다.</p>
      </div>
      <div class=\"child-focus-grid\">
        <article>
          <span>EN</span>
          <h3>영어 관리 포인트</h3>
          <p>어휘 누적, 문법 적용, 독해 속도, 학교 시험 유형을 확인해 먼저 보완할 영역을 정리합니다.</p>
        </article>
        <article>
          <span>MA</span>
          <h3>수학 관리 포인트</h3>
          <p>개념 이해, 계산 실수, 유형 적용, 시간 배분 문제를 구분해 다시 맞힐 수 있는 기준을 만듭니다.</p>
        </article>
        <article>
          <span>PL</span>
          <h3>과목별 분량 조정</h3>
          <p>영어 암기와 독해, 수학 개념과 문제풀이 시간이 한쪽으로 쏠리지 않도록 주간 계획을 조정합니다.</p>
        </article>
        <article>
          <span>EX</span>
          <h3>{area_e} 내신 대비</h3>
          <p>시험 기간에는 영어 지문·문법 포인트와 수학 단원별 오답을 시험 범위에 맞춰 다시 확인합니다.</p>
        </article>
      </div>
    </section>
"""


def geo_summary_section(row: dict, title: str, area: str, kind: str) -> str:
    title_e = html.escape(title)
    area_e = html.escape(area)
    region_e = html.escape(row["region_name"])
    district_e = html.escape(row["district_name"])
    if kind == "english_math":
        summary = f"이 페이지는 {title_e} 정보를 찾는 {area_e} 학생과 학부모를 위해, 영어 어휘·문법·독해 흐름과 수학 개념·유형·오답 원인을 따로 진단하고 주간 플래너와 시험 전 복습 순서까지 함께 정리한 영어·수학 학습 안내입니다."
        point_1 = ("핵심 과목", "영어 · 수학")
        point_2 = ("중점 관리", "어휘·독해 · 개념·유형 · 오답")
        point_3 = ("추천 대상", "두 과목의 공부 시간이 흔들리는 학생")
    elif kind == "coaching":
        summary = f"이 페이지는 {title_e} 정보를 찾는 {area_e} 학생과 학부모를 위해, 현재 공부 습관과 과목별 약점, 오답 반복 원인을 상담에서 확인하고 플래너 실행과 재학습까지 이어지도록 정리한 학습코칭 안내입니다."
        point_1 = ("핵심 과정", "진단 · 계획 · 실행 확인")
        point_2 = ("중점 관리", "플래너 · 오답 · 학부모 피드백")
        point_3 = ("추천 대상", "공부 과정 관리가 필요한 학생")
    else:
        summary = f"이 페이지는 {title_e} 정보를 찾는 {region_e} {district_e} {area_e} 학생과 학부모를 위해, 초등·중등·고등 영어·수학·국어 학습 상태 진단과 플래너 관리, 오답 재학습 기준을 한눈에 볼 수 있게 정리한 지역 학습 안내입니다."
        point_1 = ("대상 지역", f"{region_e} {district_e} {area_e}")
        point_2 = ("수업 범위", "초등 · 중등 · 고등")
        point_3 = ("관리 과목", "국어 · 영어 · 수학")
    return f"""    <section class=\"section geo-summary-section\" aria-labelledby=\"geo-summary-title\">
      <div class=\"geo-summary-card\">
        <div>
          <p class=\"eyebrow\">Key Summary</p>
          <h2 id=\"geo-summary-title\">{title_e} 핵심 요약</h2>
          <p>{summary}</p>
        </div>
        <dl class=\"geo-summary-facts\">
          <div><dt>{html.escape(point_1[0])}</dt><dd>{html.escape(point_1[1])}</dd></div>
          <div><dt>{html.escape(point_2[0])}</dt><dd>{html.escape(point_2[1])}</dd></div>
          <div><dt>{html.escape(point_3[0])}</dt><dd>{html.escape(point_3[1])}</dd></div>
        </dl>
      </div>
    </section>
"""


def geo_answer_section(row: dict, title: str, area: str, kind: str) -> str:
    title_e = html.escape(title)
    area_e = html.escape(area)
    if kind == "english_math":
        cards = [
            ("무엇을 확인하나요?", f"{area_e} 학생의 영어 어휘·문법·독해 흐름과 수학 개념·유형·오답 원인을 나누어 확인합니다."),
            ("어떻게 관리하나요?", "영어 암기와 독해, 수학 개념 복습과 문제풀이 시간이 한쪽으로 쏠리지 않도록 주간 플래너를 조정합니다."),
            ("상담 때 필요한 자료", "최근 시험지, 현재 교재, 학교 진도, 수행평가 일정, 평소 숙제 습관을 함께 보면 우선순위를 잡기 쉽습니다."),
        ]
    elif kind == "coaching":
        cards = [
            ("무엇을 확인하나요?", f"{area_e} 학생의 공부 시간, 숙제 수행, 과목별 약점, 반복되는 오답 유형을 먼저 확인합니다."),
            ("어떻게 관리하나요?", "진단 결과를 바탕으로 과목·단원·분량이 분명한 플래너를 세우고, 실행 여부와 오답 재학습을 함께 점검합니다."),
            ("상담 때 필요한 자료", "최근 시험지, 현재 교재, 학교 진도, 평소 공부 시간, 숙제 습관을 알려주면 관리 방향을 더 정확히 잡을 수 있습니다."),
        ]
    else:
        cards = [
            ("무엇을 확인하나요?", f"{area_e} 학생의 학교 진도, 최근 시험지, 공부 습관, 과목별 약점을 함께 확인합니다."),
            ("어떻게 관리하나요?", "초등은 습관과 기초, 중등은 내신과 수행평가, 고등은 시험 범위와 취약 유형 보완을 중심으로 관리합니다."),
            ("상담 때 필요한 자료", "현재 교재와 시험지, 학교 진도, 수행평가 일정, 평소 공부 시간과 숙제 습관을 준비하면 좋습니다."),
        ]
    card_html = "\n".join(
        f"""        <article class=\"geo-proof-card\">
          <span>{html.escape(label)}</span>
          <p>{html.escape(body)}</p>
        </article>"""
        for label, body in cards
    )
    return f"""    <section class=\"section geo-answer-section\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Answer Ready</p>
        <h2>{title_e} 한눈에 이해하기</h2>
        <p class=\"lead\">검색엔진과 생성형 검색이 페이지의 목적을 더 정확히 이해할 수 있도록, 상담 기준과 관리 흐름을 짧은 답변 형태로 정리했습니다.</p>
      </div>
      <div class=\"geo-proof-grid\">
{card_html}
      </div>
    </section>
"""


def schema_about(row: dict, title: str, kind: str) -> list[dict]:
    area = row["title_area"]
    base = [
        {"@type": "Thing", "name": title},
        {"@type": "Place", "name": area},
        {"@type": "Thing", "name": "학습코칭"},
        {"@type": "Thing", "name": "플래너 관리"},
        {"@type": "Thing", "name": "오답 재학습"},
    ]
    if kind == "english_math":
        base.extend([{"@type": "Thing", "name": "영어학원"}, {"@type": "Thing", "name": "수학학원"}])
    elif kind == "coaching":
        base.extend([{"@type": "Thing", "name": "학습코칭학원"}, {"@type": "Thing", "name": "학부모 상담"}])
    else:
        base.extend([{"@type": "Thing", "name": "초등 학습관리"}, {"@type": "Thing", "name": "중등 내신 관리"}, {"@type": "Thing", "name": "고등 학습관리"}])
    return base


def schema_keywords(row: dict, title: str, kind: str) -> str:
    area = row["title_area"]
    common = [title, area, row["region_name"], row["district_name"], "학습코칭", "플래너 관리", "오답 재학습", "학부모 상담"]
    if kind == "english_math":
        common.extend(["영어수학학원", "영어학원", "수학학원", "내신 대비"])
    elif kind == "coaching":
        common.extend(["와와학습코칭학원", "진단 상담", "초등 중등 고등"])
    else:
        common.extend(["와와학습코칭센터", "초등", "중등", "고등", "국어 영어 수학"])
    return ", ".join(dict.fromkeys(common))


def organization_offers(area: str, service_prefix: str = "") -> list[dict]:
    names = [
        f"{area} 초등반 학습코칭",
        f"{area} 중등반 내신 관리",
        f"{area} 고등반 학습관리",
    ]
    if service_prefix:
        names.insert(0, f"{area} {service_prefix}")
    return [
        {"@type": "Offer", "itemOffered": {"@type": "Service", "name": name, "serviceType": "TutoringService"}}
        for name in names
    ]


def local_schema(row: dict, image_path: str, map_path: str) -> dict:
    title = row["page_title"]
    area = row["title_area"]
    faq = faq_items(title, area)
    reviews = review_items(area)
    about = schema_about(row, title, "parent")
    keywords = schema_keywords(row, title, "parent")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"/전국센터/{row['slug']}/#webpage",
                "url": f"/전국센터/{row['slug']}/",
                "name": title,
                "description": f"{title} 안내입니다. {area} 지역 학생을 위한 학습 진단, 플래너 관리, 오답 재학습, 상담 정보를 확인해보세요.",
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": f"/전국센터/{row['slug']}/#primaryimage"},
                "breadcrumb": {"@id": f"/전국센터/{row['slug']}/#breadcrumb"},
                "mainEntity": {"@id": f"/전국센터/{row['slug']}/#service"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "ImageObject",
                "@id": f"/전국센터/{row['slug']}/#primaryimage",
                "url": image_path,
                "caption": f"{title} 본문 이미지",
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"/전국센터/{row['slug']}/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국센터/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": f"/전국센터/{row['slug']}/"},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": f"/전국센터/{row['slug']}/#organization",
                "name": title,
                "alternateName": ["와와센터", "와와학습코칭센터"],
                "url": f"/전국센터/{row['slug']}/",
                "telephone": PHONE,
                "openingHours": "Mo-Sa 12:00-24:00",
                "areaServed": {"@type": "Place", "name": area},
                "address": {
                    "@type": "PostalAddress",
                    "addressRegion": row["region_name"],
                    "addressLocality": row["district_name"],
                    "addressCountry": "KR",
                },
                "knowsAbout": ["초등 학습코칭", "중등 내신 관리", "고등 학습관리", "영어 수학 국어 코칭", "오답 재학습"],
                "contactPoint": {"@type": "ContactPoint", "telephone": "+82-10-3957-8283", "contactType": "학습 상담", "availableLanguage": "Korean"},
                "makesOffer": organization_offers(area),
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5", "bestRating": "5", "ratingCount": "3", "reviewCount": "3"},
                "review": [
                    {
                        "@type": "Review",
                        "author": {"@type": "Person", "name": "학부모"},
                        "reviewBody": body,
                        "reviewRating": {"@type": "Rating", "ratingValue": rating, "bestRating": "5"},
                    }
                    for rating, body in reviews
                ],
            },
            {
                "@type": "Article",
                "@id": f"/전국센터/{row['slug']}/#article",
                "headline": title,
                "description": f"{area} 지역 학생을 위한 와와학습코칭센터 학습관리 안내입니다.",
                "image": [image_path, map_path],
                "inLanguage": "ko-KR",
                "datePublished": DATE_PUBLISHED,
                "dateModified": DATE_MODIFIED,
                "author": {"@id": f"/전국센터/{row['slug']}/#organization"},
                "publisher": {"@type": "Organization", "name": ORG_NAME, "url": "/"},
                "mainEntityOfPage": {"@id": f"/전국센터/{row['slug']}/#webpage"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "Service",
                "@id": f"/전국센터/{row['slug']}/#service",
                "name": f"{area} 초중고 학습코칭",
                "serviceType": "TutoringService",
                "description": f"{area} 학생의 영어·수학·국어 학습 상태를 진단하고 플래너, 오답, 시험 대비 흐름을 관리합니다.",
                "provider": {"@id": f"/전국센터/{row['slug']}/#organization"},
                "areaServed": {"@type": "Place", "name": area},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
            },
            {
                "@type": "ItemList",
                "@id": f"/전국센터/{row['slug']}/#checklist",
                "name": f"{title} 학습관리 체크리스트",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": f"{area} 학교 진도와 현재 실력 진단"},
                    {"@type": "ListItem", "position": 2, "name": "초등·중등·고등 학년별 관리 기준 확인"},
                    {"@type": "ListItem", "position": 3, "name": "플래너 실행 여부와 오답 재학습 점검"},
                    {"@type": "ListItem", "position": 4, "name": "시험 전 복습 순서와 학부모 피드백 정리"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": f"/전국센터/{row['slug']}/#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faq
                ],
            },
        ],
    }


def child_schema(row: dict, image_path: str, map_path: str) -> dict:
    title = child_title(row)
    area = row["title_area"]
    faq = child_faq_items(title, area)
    reviews = child_review_items(area)
    url = f"/전국센터/{row['slug']}/와와학습코칭학원/"
    about = schema_about(row, title, "coaching")
    keywords = schema_keywords(row, title, "coaching")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": title,
                "description": f"{title} 안내입니다. {area} 지역 학생을 위한 진단 상담, 학습 플래너, 오답 재학습, 학부모 피드백 기준을 확인해보세요.",
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": f"{url}#primaryimage"},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#service"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "ImageObject",
                "@id": f"{url}#primaryimage",
                "url": image_path,
                "caption": f"{title} 본문 이미지",
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국센터/"},
                    {"@type": "ListItem", "position": 3, "name": row["page_title"], "item": f"/전국센터/{row['slug']}/"},
                    {"@type": "ListItem", "position": 4, "name": title, "item": url},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": f"{url}#organization",
                "name": title,
                "alternateName": ["와와센터", "와와학습코칭학원"],
                "url": url,
                "telephone": PHONE,
                "openingHours": "Mo-Sa 12:00-24:00",
                "areaServed": {"@type": "Place", "name": area},
                "address": {
                    "@type": "PostalAddress",
                    "addressRegion": row["region_name"],
                    "addressLocality": row["district_name"],
                    "addressCountry": "KR",
                },
                "knowsAbout": ["학습코칭학원", "초등 학습관리", "중등 내신 관리", "고등 학습관리", "영어 수학 국어 코칭", "오답 재학습"],
                "contactPoint": {"@type": "ContactPoint", "telephone": "+82-10-3957-8283", "contactType": "학습 상담", "availableLanguage": "Korean"},
                "makesOffer": organization_offers(area, "진단 상담"),
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5", "bestRating": "5", "ratingCount": "3", "reviewCount": "3"},
                "review": [
                    {
                        "@type": "Review",
                        "author": {"@type": "Person", "name": "학부모"},
                        "reviewBody": body,
                        "reviewRating": {"@type": "Rating", "ratingValue": rating, "bestRating": "5"},
                    }
                    for rating, body in reviews
                ],
            },
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": title,
                "description": f"{area} 지역 학생을 위한 와와학습코칭학원 학습관리 안내입니다.",
                "image": [image_path, map_path],
                "inLanguage": "ko-KR",
                "datePublished": DATE_PUBLISHED,
                "dateModified": DATE_MODIFIED,
                "author": {"@id": f"{url}#organization"},
                "publisher": {"@type": "Organization", "name": ORG_NAME, "url": "/"},
                "mainEntityOfPage": {"@id": f"{url}#webpage"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "Service",
                "@id": f"{url}#service",
                "name": f"{area} 와와학습코칭학원 학습관리",
                "serviceType": "TutoringService",
                "description": f"{area} 학생의 영어·수학·국어 학습 상태를 진단하고, 플래너 실행과 오답 재학습이 이어지도록 관리합니다.",
                "provider": {"@id": f"{url}#organization"},
                "areaServed": {"@type": "Place", "name": area},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#checklist",
                "name": f"{title} 학습코칭 체크리스트",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": f"{area} 학생의 현재 실력과 공부 습관 진단"},
                    {"@type": "ListItem", "position": 2, "name": "과목·단원·분량이 분명한 플래너 관리"},
                    {"@type": "ListItem", "position": 3, "name": "틀린 원인을 구분하는 오답 재학습"},
                    {"@type": "ListItem", "position": 4, "name": "학부모가 확인할 수 있는 학습 피드백"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": f"{url}#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faq
                ],
            },
        ],
    }


def english_math_schema(row: dict, image_path: str, map_path: str) -> dict:
    title = english_math_title(row)
    area = row["title_area"]
    faq = english_math_faq_items(title, area)
    reviews = english_math_review_items(area)
    url = f"/전국센터/{row['slug']}/영어수학학원/"
    about = schema_about(row, title, "english_math")
    keywords = schema_keywords(row, title, "english_math")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": title,
                "description": f"{title} 안내입니다. {area} 학생을 위한 영어·수학 진단 상담, 플래너 관리, 오답 재학습, 내신 준비 기준을 확인해보세요.",
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": f"{url}#primaryimage"},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#service"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "ImageObject",
                "@id": f"{url}#primaryimage",
                "url": image_path,
                "caption": f"{title} 본문 이미지",
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국센터/"},
                    {"@type": "ListItem", "position": 3, "name": row["page_title"], "item": f"/전국센터/{row['slug']}/"},
                    {"@type": "ListItem", "position": 4, "name": title, "item": url},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": f"{url}#organization",
                "name": title,
                "alternateName": ["와와센터", "와와영어수학학원"],
                "url": url,
                "telephone": PHONE,
                "openingHours": "Mo-Sa 12:00-24:00",
                "areaServed": {"@type": "Place", "name": area},
                "address": {
                    "@type": "PostalAddress",
                    "addressRegion": row["region_name"],
                    "addressLocality": row["district_name"],
                    "addressCountry": "KR",
                },
                "knowsAbout": ["영어학원", "수학학원", "영어 수학 학습관리", "초등 영어수학", "중등 내신", "고등 영어수학", "오답 재학습"],
                "contactPoint": {"@type": "ContactPoint", "telephone": "+82-10-3957-8283", "contactType": "영어수학 학습 상담", "availableLanguage": "Korean"},
                "makesOffer": organization_offers(area, "영어수학 학습관리"),
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5", "bestRating": "5", "ratingCount": "3", "reviewCount": "3"},
                "review": [
                    {
                        "@type": "Review",
                        "author": {"@type": "Person", "name": "학부모"},
                        "reviewBody": body,
                        "reviewRating": {"@type": "Rating", "ratingValue": rating, "bestRating": "5"},
                    }
                    for rating, body in reviews
                ],
            },
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": title,
                "description": f"{area} 지역 학생을 위한 영어수학학원 학습관리 안내입니다.",
                "image": [image_path, map_path],
                "inLanguage": "ko-KR",
                "datePublished": DATE_PUBLISHED,
                "dateModified": DATE_MODIFIED,
                "author": {"@id": f"{url}#organization"},
                "publisher": {"@type": "Organization", "name": ORG_NAME, "url": "/"},
                "mainEntityOfPage": {"@id": f"{url}#webpage"},
                "about": about,
                "keywords": keywords,
            },
            {
                "@type": "Service",
                "@id": f"{url}#service",
                "name": f"{area} 영어수학학원 학습관리",
                "serviceType": "TutoringService",
                "description": f"{area} 학생의 영어·수학 학습 상태를 진단하고, 과목별 플래너와 오답 재학습이 이어지도록 관리합니다.",
                "provider": {"@id": f"{url}#organization"},
                "areaServed": {"@type": "Place", "name": area},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#checklist",
                "name": f"{title} 영어수학 관리 체크리스트",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": f"{area} 영어 어휘·문법·독해 진단"},
                    {"@type": "ListItem", "position": 2, "name": f"{area} 수학 개념·유형·오답 분석"},
                    {"@type": "ListItem", "position": 3, "name": "영어와 수학 과목별 주간 분량 조정"},
                    {"@type": "ListItem", "position": 4, "name": "내신 기간 시험 범위와 오답 복습 순서 정리"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": f"{url}#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faq
                ],
            },
        ],
    }


def local_page(row: dict) -> str:
    depth_assets = rel_assets(2)
    title = row["page_title"]
    area = row["title_area"]
    common_img = "seoul.jpg" if row["region_slug"] == "seoul" else "local.jpg"
    common_src = f"{depth_assets}/centers/common/{common_img}"
    map_src = f"{depth_assets}/maps/{row['map']}"
    schema = json.dumps(local_schema(row, common_src, map_src), ensure_ascii=False, separators=(",", ":"))
    canonical = absolute_url(f"/전국센터/{row['slug']}/")
    faq = faq_items(title, area)
    reviews = review_items(area)
    faq_html = "\n".join(
        f"""          <details{' open' if i == 0 else ''}>
            <summary>{html.escape(q)}</summary>
            <p>{html.escape(a)}</p>
          </details>"""
        for i, (q, a) in enumerate(faq)
    )
    review_html = "\n".join(
        f"""        <article class=\"review\"><div class=\"stars\">{'★' * int(rating)}</div><p>“{html.escape(body)}”</p></article>"""
        for rating, body in reviews
    )
    related_links = internal_links_section(row, "parent")
    depth_section = parent_depth_section(row, title, area)
    summary_section = geo_summary_section(row, title, area, "parent")
    answer_section = geo_answer_section(row, title, area, "parent")
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)} | {SITE_NAME}</title>
  <meta name=\"description\" content=\"{html.escape(title)} 안내입니다. {html.escape(area)} 지역 학생을 위한 학습 진단, 플래너 관리, 오답 재학습, 상담 정보를 확인해보세요.\">
  <meta name=\"robots\" content=\"index,follow\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:title\" content=\"{html.escape(title)}\">
  <meta property=\"og:description\" content=\"{html.escape(area)} 학생을 위한 초중고 영어·수학·국어 학습코칭 안내입니다.\">
  <meta property=\"og:url\" content=\"{html.escape(canonical)}\">
  <meta property=\"og:image\" content=\"{common_src}\">
  <link rel=\"canonical\" href=\"{html.escape(canonical)}\">
  <link rel=\"icon\" href=\"{depth_assets}/favicon.png\">
  <link rel=\"stylesheet\" href=\"{depth_assets}/site.css\">
  <script type=\"application/ld+json\">{schema}</script>
</head>
<body>
  {header('전국학원', '../../')}
  <main>
    <section class=\"local-hero\">
      <nav class=\"mini-breadcrumb\" aria-label=\"현재 위치\">
        <a href=\"../../\">홈</a><span>›</span><a href=\"../\">전국학원</a><span>›</span><strong>{html.escape(title)}</strong>
      </nav>
      <p class=\"eyebrow\">Local Academy</p>
      <h1>{html.escape(title)}</h1>
      <p class=\"lead\">{html.escape(area)} 지역에서 영어·수학·국어 학습 흐름을 다시 잡고 싶은 학생을 위해, 진단 상담부터 플래너 관리와 오답 재학습까지 한 번에 이해할 수 있도록 정리했습니다.</p>
      <div class=\"hero-points\">
        <span>{html.escape(row['region_name'])} {html.escape(row['district_name'])}</span>
        <span>초등·중등·고등</span>
        <span>영어·수학·국어</span>
      </div>
    </section>

{summary_section}

    <section class=\"local-media-section\">
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">수업 안내 이미지</p>
        <img src=\"{common_src}\" alt=\"{html.escape(title)} 본문 이미지\">
      </div>
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">센터 위치 안내</p>
        <img src=\"{map_src}\" alt=\"{html.escape(title)} 지도\">
      </div>
    </section>

    <section class=\"section split local-content\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Learning Plan</p>
        <h2>{html.escape(area)} 학생에게 필요한 관리는<br>진단에서 시작됩니다.</h2>
        <p class=\"lead\">같은 점수라도 막히는 이유가 다르기 때문에, 처음 상담에서는 학생의 현재 학습 행동과 과목별 약점을 함께 확인하는 것이 중요합니다.</p>
      </div>
      <div class=\"card-grid feature-mosaic\">
        <article class=\"card\"><span class=\"num\">1</span><div><h3>현재 실력과 공부 습관 진단</h3><p>{html.escape(area)} 학생의 학교 진도, 최근 시험지, 숙제 수행 습관을 확인해 어느 단원부터 관리해야 할지 정리합니다.</p></div></article>
        <article class=\"card\"><span class=\"num\">2</span><h3>학생별 플래너 관리</h3><p>과목·단원·분량·완료 기준을 분명히 적고, 실제 실행 결과를 확인해 다음 계획에 반영합니다.</p></article>
        <article class=\"card\"><span class=\"num\">3</span><h3>오답 원인 재학습</h3><p>개념 부족, 계산 실수, 독해 오류, 시간 부족처럼 틀린 이유를 나눠 다시 맞힐 수 있게 관리합니다.</p></article>
        <article class=\"card\"><span class=\"num\">4</span><h3>학부모 피드백</h3><p>수업 결과와 학습 태도를 함께 보며, 시험 전에는 필요한 복습 순서와 보완 계획을 안내합니다.</p></article>
      </div>
    </section>

    <section class=\"section local-guide-panel\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Available Class</p>
        <h2>{html.escape(title)} 수업 안내</h2>
        <p class=\"lead\">과목과 학년을 넓게 열어두고, 학생의 현재 상태에 맞춰 필요한 관리 흐름을 정리합니다.</p>
      </div>
      <div class=\"local-info-grid\">
        <div><b>수업 가능 과목</b><span>국어 · 영어 · 수학</span></div>
        <div><b>수업 가능 학년</b><span>초등반 · 중등반 · 고등반</span></div>
        <div><b>관리 방식</b><span>진단 · 플래너 · 오답 · 피드백</span></div>
      </div>
    </section>

{depth_section}

{answer_section}

{related_links}

    <section class=\"section split\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">FAQ</p>
        <h2>자주 묻는 질문</h2>
      </div>
      <div class=\"faq\">
{faq_html}
      </div>
    </section>

    <section class=\"section\">
      <p class=\"eyebrow\">Reviews</p>
      <h2>{html.escape(area)} 학부모님이 기대하는 변화</h2>
      <div class=\"reviews\">
{review_html}
      </div>
    </section>

    <section class=\"section\">
      <div class=\"cta-box\">
        <p class=\"eyebrow\">Consulting</p>
        <h2>{html.escape(title)} 상담으로<br>아이에게 필요한 첫 기준을 확인해보세요.</h2>
        <p class=\"lead\">최근 시험지와 평소 공부 습관을 함께 알려주시면 더 구체적인 학습 방향을 안내받을 수 있습니다.</p>
        <div class=\"actions\" style=\"justify-content:center\">
          <a class=\"btn btn-primary\" href=\"../../상담문의/\">상담문의 보기</a>
          <a class=\"btn btn-soft\" href=\"tel:01039578283\">전화 문의</a>
        </div>
      </div>
    </section>
  </main>
  {footer('../../')}
  {floating('../../')}
</body>
</html>
"""


def child_page(row: dict) -> str:
    depth_assets = rel_assets(3)
    title = child_title(row)
    parent_title = row["page_title"]
    area = row["title_area"]
    common_img = "seoul.jpg" if row["region_slug"] == "seoul" else "local.jpg"
    common_src = f"{depth_assets}/centers/common/{common_img}"
    map_src = f"{depth_assets}/maps/{row['map']}"
    schema = json.dumps(child_schema(row, common_src, map_src), ensure_ascii=False, separators=(",", ":"))
    canonical = absolute_url(f"/전국센터/{row['slug']}/와와학습코칭학원/")
    faq = child_faq_items(title, area)
    reviews = child_review_items(area)
    faq_html = "\n".join(
        f"""          <details{' open' if i == 0 else ''}>
            <summary>{html.escape(q)}</summary>
            <p>{html.escape(a)}</p>
          </details>"""
        for i, (q, a) in enumerate(faq)
    )
    review_html = "\n".join(
        f"""        <article class=\"review\"><div class=\"stars\">{'★' * int(rating)}</div><p>“{html.escape(body)}”</p></article>"""
        for rating, body in reviews
    )
    related_links = internal_links_section(row, "child")
    depth_section = coaching_depth_section(row, title, area)
    summary_section = geo_summary_section(row, title, area, "coaching")
    answer_section = geo_answer_section(row, title, area, "coaching")
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)} | {SITE_NAME}</title>
  <meta name=\"description\" content=\"{html.escape(title)} 안내입니다. {html.escape(area)} 학생을 위한 진단 상담, 플래너 관리, 오답 재학습, 학부모 피드백 기준을 확인해보세요.\">
  <meta name=\"robots\" content=\"index,follow\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:title\" content=\"{html.escape(title)}\">
  <meta property=\"og:description\" content=\"{html.escape(area)} 학생을 위한 영어·수학·국어 학습코칭학원 안내입니다.\">
  <meta property=\"og:url\" content=\"{html.escape(canonical)}\">
  <meta property=\"og:image\" content=\"{common_src}\">
  <link rel=\"canonical\" href=\"{html.escape(canonical)}\">
  <link rel=\"icon\" href=\"{depth_assets}/favicon.png\">
  <link rel=\"stylesheet\" href=\"{depth_assets}/site.css\">
  <script type=\"application/ld+json\">{schema}</script>
</head>
<body>
  {header('전국학원', '../../../')}
  <main>
    <section class=\"local-hero child-hero\">
      <nav class=\"mini-breadcrumb\" aria-label=\"현재 위치\">
        <a href=\"../../../\">홈</a><span>›</span><a href=\"../../\">전국학원</a><span>›</span><a href=\"../\">{html.escape(parent_title)}</a><span>›</span><strong>{html.escape(title)}</strong>
      </nav>
      <p class=\"eyebrow\">Coaching Academy</p>
      <h1>{html.escape(title)}</h1>
      <p class=\"lead\">{html.escape(area)}에서 학원 선택을 고민할 때는 수업 과목만 보는 것보다 학생의 공부 습관, 오답 반복, 시험 준비 흐름을 어떻게 관리하는지 함께 확인하는 것이 좋습니다. 이 페이지는 {html.escape(area)} 학생에게 필요한 학습코칭 기준을 한 번에 볼 수 있도록 정리했습니다.</p>
      <div class=\"hero-points\">
        <span>{html.escape(row['region_name'])} {html.escape(row['district_name'])}</span>
        <span>진단 상담 중심</span>
        <span>플래너 · 오답 · 피드백</span>
      </div>
    </section>

{summary_section}

    <section class=\"local-media-section\">
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">학습코칭 안내 이미지</p>
        <img src=\"{common_src}\" alt=\"{html.escape(title)} 본문 이미지\">
      </div>
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">센터 위치 안내</p>
        <img src=\"{map_src}\" alt=\"{html.escape(title)} 지도\">
      </div>
    </section>

    <section class=\"section split local-content child-content\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Why Coaching</p>
        <h2>{html.escape(area)} 학생에게 필요한 관리는<br>점수보다 먼저 원인을 찾는 일입니다.</h2>
        <p class=\"lead\">성적이 비슷해도 막히는 이유는 다릅니다. 개념이 약한 학생, 숙제를 미루는 학생, 시험 전 복습 순서를 놓치는 학생, 틀린 문제를 다시 연결하지 못하는 학생에게는 각각 다른 관리 방식이 필요합니다.</p>
      </div>
      <div class=\"child-focus-grid\">
        <article>
          <span>01</span>
          <h3>진단 상담</h3>
          <p>{html.escape(area)} 학생의 최근 시험지, 학교 진도, 평소 공부 시간, 과목별 약점을 함께 확인해 시작점을 정리합니다.</p>
        </article>
        <article>
          <span>02</span>
          <h3>플래너 관리</h3>
          <p>과목별 단원과 분량, 완료 기준을 구체적으로 잡고 실제 실행 결과를 다음 계획에 반영합니다.</p>
        </article>
        <article>
          <span>03</span>
          <h3>오답 재학습</h3>
          <p>틀린 문제를 단순히 다시 푸는 데서 끝내지 않고, 틀린 이유와 다시 맞힐 조건을 확인합니다.</p>
        </article>
        <article>
          <span>04</span>
          <h3>학부모 피드백</h3>
          <p>수업 결과와 공부 태도를 함께 전달해 가정에서도 아이의 변화 방향을 이해할 수 있도록 돕습니다.</p>
        </article>
      </div>
    </section>

    <section class=\"section local-guide-panel\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Class Guide</p>
        <h2>{html.escape(title)} 수업 관리 기준</h2>
        <p class=\"lead\">영어·수학·국어를 과목별로 나누어 보고, 초등반·중등반·고등반의 학습 목적에 맞춰 필요한 관리 흐름을 다르게 잡습니다.</p>
      </div>
      <div class=\"local-info-grid\">
        <div><b>수업 가능 과목</b><span>국어 · 영어 · 수학</span></div>
        <div><b>수업 가능 학년</b><span>초등반 · 중등반 · 고등반</span></div>
        <div><b>관리 핵심</b><span>진단 · 계획 · 실행확인 · 오답 재학습</span></div>
      </div>
    </section>

{depth_section}

{answer_section}

{related_links}

    <section class=\"section split\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">FAQ</p>
        <h2>{html.escape(title)} 자주 묻는 질문</h2>
      </div>
      <div class=\"faq\">
{faq_html}
      </div>
    </section>

    <section class=\"section\">
      <p class=\"eyebrow\">Reviews</p>
      <h2>{html.escape(area)} 학부모님이 본 학습코칭 변화</h2>
      <div class=\"reviews\">
{review_html}
      </div>
    </section>

    <section class=\"section\">
      <div class=\"cta-box\">
        <p class=\"eyebrow\">Next Step</p>
        <h2>{html.escape(title)} 상담 전<br>아이의 현재 학습 흐름부터 확인해보세요.</h2>
        <p class=\"lead\">최근 시험지와 평소 공부 습관을 알려주시면 진단 상담에서 더 구체적인 방향을 잡을 수 있습니다.</p>
        <div class=\"actions\" style=\"justify-content:center\">
          <a class=\"btn btn-primary\" href=\"../../../상담문의/\">상담문의 보기</a>
          <a class=\"btn btn-soft\" href=\"../\">{html.escape(parent_title)}로 돌아가기</a>
        </div>
      </div>
    </section>
  </main>
  {footer('../../../')}
  {floating('../../../')}
</body>
</html>
"""


def english_math_page(row: dict) -> str:
    depth_assets = rel_assets(3)
    title = english_math_title(row)
    parent_title = row["page_title"]
    area = row["title_area"]
    common_img = "seoul.jpg" if row["region_slug"] == "seoul" else "local.jpg"
    common_src = f"{depth_assets}/centers/common/{common_img}"
    map_src = f"{depth_assets}/maps/{row['map']}"
    schema = json.dumps(english_math_schema(row, common_src, map_src), ensure_ascii=False, separators=(",", ":"))
    canonical = absolute_url(f"/전국센터/{row['slug']}/영어수학학원/")
    faq = english_math_faq_items(title, area)
    reviews = english_math_review_items(area)
    faq_html = "\n".join(
        f"""          <details{' open' if i == 0 else ''}>
            <summary>{html.escape(q)}</summary>
            <p>{html.escape(a)}</p>
          </details>"""
        for i, (q, a) in enumerate(faq)
    )
    review_html = "\n".join(
        f"""        <article class=\"review\"><div class=\"stars\">{'★' * int(rating)}</div><p>“{html.escape(body)}”</p></article>"""
        for rating, body in reviews
    )
    related_links = internal_links_section(row, "english_math")
    depth_section = english_math_depth_section(row, title, area)
    summary_section = geo_summary_section(row, title, area, "english_math")
    answer_section = geo_answer_section(row, title, area, "english_math")
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)} | {SITE_NAME}</title>
  <meta name=\"description\" content=\"{html.escape(title)} 안내입니다. {html.escape(area)} 학생을 위한 영어·수학 진단 상담, 플래너 관리, 오답 재학습, 내신 준비 기준을 확인해보세요.\">
  <meta name=\"robots\" content=\"index,follow\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:title\" content=\"{html.escape(title)}\">
  <meta property=\"og:description\" content=\"{html.escape(area)} 학생을 위한 영어·수학 학습관리 안내입니다.\">
  <meta property=\"og:url\" content=\"{html.escape(canonical)}\">
  <meta property=\"og:image\" content=\"{common_src}\">
  <link rel=\"canonical\" href=\"{html.escape(canonical)}\">
  <link rel=\"icon\" href=\"{depth_assets}/favicon.png\">
  <link rel=\"stylesheet\" href=\"{depth_assets}/site.css\">
  <script type=\"application/ld+json\">{schema}</script>
</head>
<body>
  {header('전국학원', '../../../')}
  <main>
    <section class=\"local-hero child-hero english-math-hero\">
      <nav class=\"mini-breadcrumb\" aria-label=\"현재 위치\">
        <a href=\"../../../\">홈</a><span>›</span><a href=\"../../\">전국학원</a><span>›</span><a href=\"../\">{html.escape(parent_title)}</a><span>›</span><strong>{html.escape(title)}</strong>
      </nav>
      <p class=\"eyebrow\">English Math Academy</p>
      <h1>{html.escape(title)}</h1>
      <p class=\"lead\">{html.escape(area)}에서 영어와 수학을 함께 관리할 학원을 찾는다면, 단순히 두 과목을 모두 가르치는지보다 과목별 약점과 공부 시간을 어떻게 나누어 관리하는지가 중요합니다. 이 페이지는 {html.escape(area)} 학생의 영어·수학 학습 흐름을 진단하고, 내신과 기본기를 함께 잡는 기준을 정리했습니다.</p>
      <div class=\"hero-points\">
        <span>{html.escape(row['region_name'])} {html.escape(row['district_name'])}</span>
        <span>영어 · 수학 집중관리</span>
        <span>내신 · 오답 · 플래너</span>
      </div>
    </section>

{summary_section}

    <section class=\"local-media-section\">
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">영어수학 학습 안내 이미지</p>
        <img src=\"{common_src}\" alt=\"{html.escape(title)} 본문 이미지\">
      </div>
      <div class=\"local-media-card\">
        <p class=\"local-media-label\">센터 위치 안내</p>
        <img src=\"{map_src}\" alt=\"{html.escape(title)} 지도\">
      </div>
    </section>

    <section class=\"section split local-content child-content\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">Subject Balance</p>
        <h2>{html.escape(area)} 영어·수학 관리는<br>과목별 약점을 따로 봐야 선명해집니다.</h2>
        <p class=\"lead\">영어는 어휘와 문법, 독해의 연결이 중요하고 수학은 개념 이해와 유형 적용, 오답 반복이 중요합니다. 두 과목을 같은 방식으로 관리하면 막히는 지점이 흐려질 수 있어 과목별 기준을 나누어 봅니다.</p>
      </div>
      <div class=\"child-focus-grid\">
        <article>
          <span>EN</span>
          <h3>영어 학습 진단</h3>
          <p>어휘 누적, 문법 적용, 독해 속도, 학교 시험 유형을 확인해 영어에서 먼저 보완해야 할 지점을 정리합니다.</p>
        </article>
        <article>
          <span>MA</span>
          <h3>수학 오답 분석</h3>
          <p>개념 부족, 계산 실수, 유형 미숙, 시간 배분 문제를 나누어 보고 다시 맞힐 수 있는 기준을 세웁니다.</p>
        </article>
        <article>
          <span>PL</span>
          <h3>과목별 플래너</h3>
          <p>영어 암기와 독해, 수학 개념과 문제풀이 시간이 한쪽으로 쏠리지 않도록 주간 분량을 조정합니다.</p>
        </article>
        <article>
          <span>EX</span>
          <h3>시험 전 관리</h3>
          <p>내신 기간에는 영어 지문·문법 포인트와 수학 단원별 오답을 시험 범위에 맞춰 다시 확인합니다.</p>
        </article>
      </div>
    </section>

    <section class=\"section local-guide-panel\">
      <div class=\"section-head center\">
        <p class=\"eyebrow\">Class Guide</p>
        <h2>{html.escape(title)} 수업 안내</h2>
        <p class=\"lead\">영어와 수학을 함께 보되, 학생의 학년과 현재 실력에 따라 학습 목표와 관리 방식을 다르게 잡습니다.</p>
      </div>
      <div class=\"local-info-grid\">
        <div><b>수업 가능 과목</b><span>영어 · 수학 · 필요 시 국어 상담</span></div>
        <div><b>수업 가능 학년</b><span>초등반 · 중등반 · 고등반</span></div>
        <div><b>관리 핵심</b><span>과목별 진단 · 플래너 · 오답 · 내신 대비</span></div>
      </div>
    </section>

{depth_section}

{answer_section}

{related_links}

    <section class=\"section split\">
      <div class=\"section-title\">
        <p class=\"eyebrow\">FAQ</p>
        <h2>{html.escape(title)} 자주 묻는 질문</h2>
      </div>
      <div class=\"faq\">
{faq_html}
      </div>
    </section>

    <section class=\"section\">
      <p class=\"eyebrow\">Reviews</p>
      <h2>{html.escape(area)} 학부모님이 본 영어·수학 관리 변화</h2>
      <div class=\"reviews\">
{review_html}
      </div>
    </section>

    <section class=\"section\">
      <div class=\"cta-box\">
        <p class=\"eyebrow\">Consulting</p>
        <h2>{html.escape(title)} 상담 전<br>영어와 수학 중 어디가 먼저 막히는지 확인해보세요.</h2>
        <p class=\"lead\">최근 시험지와 현재 교재, 숙제 습관을 알려주시면 영어·수학의 우선순위를 더 구체적으로 잡을 수 있습니다.</p>
        <div class=\"actions\" style=\"justify-content:center\">
          <a class=\"btn btn-primary\" href=\"../../../상담문의/\">상담문의 보기</a>
          <a class=\"btn btn-soft\" href=\"../\">{html.escape(parent_title)}로 돌아가기</a>
        </div>
      </div>
    </section>
  </main>
  {footer('../../../')}
  {floating('../../../')}
</body>
</html>
"""


def hub_schema(rows: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": "/전국센터/#webpage",
                "url": "/전국센터/",
                "name": "전국학원",
                "description": "전국 371개 동네별 와와학습코칭센터 학습관리 안내 페이지입니다.",
                "inLanguage": "ko-KR",
                "breadcrumb": {"@id": "/전국센터/#breadcrumb"},
                "mainEntity": {"@id": "/전국센터/#itemlist"},
                "about": [
                    {"@type": "Thing", "name": "전국학원"},
                    {"@type": "Thing", "name": "와와학습코칭센터"},
                    {"@type": "Thing", "name": "초중고 학습코칭"},
                    {"@type": "Thing", "name": "동네별 학습관리"},
                ],
                "keywords": "전국학원, 와와학습코칭센터, 학습코칭, 초등, 중등, 고등, 영어, 수학, 국어, 동네별 학원",
            },
            {
                "@type": "BreadcrumbList",
                "@id": "/전국센터/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국센터/"},
                ],
            },
            {
                "@type": "ItemList",
                "@id": "/전국센터/#itemlist",
                "name": "동네별 와와학습코칭센터 바로가기",
                "numberOfItems": len(rows),
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": r["page_title"], "url": f"/전국센터/{r['slug']}/"}
                    for i, r in enumerate(rows)
                ],
            },
        ],
    }


def hub_page(rows: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["region_name"], []).append(r)
    region_sections = []
    for idx, (region_name, items) in enumerate(grouped.items()):
        districts: list[str] = []
        for item in items:
            if item["district_name"] not in districts:
                districts.append(item["district_name"])
        district_preview = " · ".join(districts[:8])
        if len(districts) > 8:
            district_preview += f" 외 {len(districts) - 8}곳"
        links = "\n".join(
            f"""          <a class=\"center-town-link\" href=\"{html.escape(r['slug'])}/\"><b>{html.escape(r['title_area'])}</b><span>{html.escape(r['district_name'])} · 학습코칭 안내</span></a>"""
            for r in items
        )
        open_attr = " open" if idx == 0 else ""
        region_sections.append(
            f"""      <details class=\"hub-region-card\"{open_attr}>
        <summary class=\"hub-region-summary\">
          <span class=\"hub-region-kicker\">지역별 바로가기</span>
          <strong>{html.escape(region_name)}</strong>
          <small>{len(items)}개 동네</small>
          <em>{html.escape(district_preview)}</em>
        </summary>
        <div class=\"center-town-grid\">
{links}
        </div>
      </details>"""
        )
    schema = json.dumps(hub_schema(rows), ensure_ascii=False, separators=(",", ":"))
    canonical = absolute_url("/전국센터/")
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>전국학원 | {SITE_NAME}</title>
  <meta name=\"description\" content=\"전국 371개 동네별 와와학습코칭센터 학습관리 안내 페이지입니다. 가까운 지역의 학습코칭 정보를 확인해보세요.\">
  <meta name=\"robots\" content=\"index,follow\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:title\" content=\"전국학원 | {SITE_NAME}\">
  <meta property=\"og:description\" content=\"전국 371개 동네별 와와학습코칭센터 학습관리 안내.\">
  <meta property=\"og:url\" content=\"{html.escape(canonical)}\">
  <link rel=\"canonical\" href=\"{html.escape(canonical)}\">
  <link rel=\"icon\" href=\"../assets/favicon.png\">
  <link rel=\"stylesheet\" href=\"../assets/site.css\">
  <script type=\"application/ld+json\">{schema}</script>
</head>
<body>
  {header('전국학원', '../')}
  <main>
    <section class=\"page-hero hub-hero\">
      <p class=\"eyebrow\">National Academy</p>
      <h1>전국학원</h1>
      <p class=\"lead\">지역별 와와학습코칭센터 안내를 한곳에 정리했습니다. 동네 페이지에서는 본문 이미지와 지도, 학습코칭 안내, FAQ와 학부모 후기를 함께 확인할 수 있습니다.</p>
      <div class=\"hub-summary\">
        <span>371개 동네 페이지</span>
        <span>초등·중등·고등</span>
        <span>영어·수학·국어 학습관리</span>
      </div>
    </section>
    <section class=\"section hub-intro-panel\">
      <div class=\"panel\">
        <h2>동네별 학습코칭 안내</h2>
        <p>{SITE_NAME}은 학생의 현재 실력과 공부 습관을 먼저 확인하고, 진단 상담·플래너 관리·오답 재학습·학부모 피드백이 이어지도록 안내합니다. 아래 지역에서 가까운 동네 페이지를 선택해 보세요.</p>
      </div>
    </section>
    <section class=\"section hub-region-list\">
{chr(10).join(region_sections)}
    </section>
  </main>
  {footer('../')}
  {floating('../')}
</body>
</html>
"""


def update_navs() -> None:
    replacements = [
        (ROOT / "index.html", '<a href="상담문의/">상담문의</a>', '<a href="상담문의/">상담문의</a>\n        <a href="전국센터/">전국학원</a>'),
        (ROOT / "학습가이드" / "index.html", '<a href="../상담문의/">상담문의</a>', '<a href="../상담문의/">상담문의</a>\n        <a href="../전국센터/">전국학원</a>'),
        (ROOT / "상담문의" / "index.html", '<a href="./" aria-current="page">상담문의</a>', '<a href="./" aria-current="page">상담문의</a>\n        <a href="../전국센터/">전국학원</a>'),
    ]
    for path, old, new in replacements:
        text = path.read_text(encoding="utf-8")
        if "전국센터/" not in text.split('<nav class="nav"', 1)[1].split("</nav>", 1)[0]:
            text = text.replace(old, new)
            path.write_text(text, encoding="utf-8", newline="\n")


def update_sitemap(rows: list[dict]) -> None:
    locs = ["/", "/학습가이드/", "/상담문의/", "/전국센터/"]
    locs.extend(f"/전국센터/{r['slug']}/" for r in rows)
    locs.extend(f"/전국센터/{r['slug']}/와와학습코칭학원/" for r in rows)
    locs.extend(f"/전국센터/{r['slug']}/영어수학학원/" for r in rows)
    def absolute_url(loc: str) -> str:
        return BASE_URL.rstrip("/") + quote(loc, safe="/")
    body = "\n".join(f"  <url><loc>{html.escape(absolute_url(loc))}</loc></url>" for loc in locs)
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8", newline="\n")


def update_robots() -> None:
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL.rstrip('/')}/sitemap.xml\n"
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8", newline="\n")


def main() -> None:
    if not (SOURCE_ROOT / "center").exists():
        raise SystemExit(f"source center not found: {SOURCE_ROOT / 'center'}")
    rows = enrich_slugs(collect_rows())
    CENTER_ROOT.mkdir(exist_ok=True)
    (CENTER_ROOT / "index.html").write_text(hub_page(rows), encoding="utf-8", newline="\n")
    for row in rows:
        out_dir = CENTER_ROOT / row["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(local_page(row), encoding="utf-8", newline="\n")
        child_dir = out_dir / "와와학습코칭학원"
        child_dir.mkdir(parents=True, exist_ok=True)
        (child_dir / "index.html").write_text(child_page(row), encoding="utf-8", newline="\n")
        english_math_dir = out_dir / "영어수학학원"
        english_math_dir.mkdir(parents=True, exist_ok=True)
        (english_math_dir / "index.html").write_text(english_math_page(row), encoding="utf-8", newline="\n")
    update_navs()
    update_sitemap(rows)
    update_robots()
    missing_maps = [r for r in rows if not (MAPS / r["map"]).exists()]
    print(json.dumps({"rows": len(rows), "coaching_child_pages": len(rows), "english_math_child_pages": len(rows), "hub": str(CENTER_ROOT / "index.html"), "missing_maps": missing_maps[:5]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

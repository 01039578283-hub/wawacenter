from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "참고자료" / "공통자료"
CENTER_INFO = COMMON / "센터정보 정리.csv"
REPRESENTATIVE_CSV = COMMON / "대표 이미지 url.csv"
LEVEL = os.environ.get("SUBJECT_LEVEL", "high").strip().lower()
CONFIGS = {
    "high": {
        "zip": "고등 영수학원.zip",
        "category": "고등영수학원",
        "display": "고등 영수학원",
        "level": "고등",
        "grade_prefix": "고",
        "audience": "고등학생",
        "eyebrow": "High School English & Math",
        "card_small": "고등학생 · 영어와 수학",
        "card_description": "371개 동네별 학습 진단·내신·오답 관리 안내",
    },
    "middle": {
        "zip": "중등 영수학원.zip",
        "category": "중등영수학원",
        "display": "중등 영수학원",
        "level": "중등",
        "grade_prefix": "중",
        "audience": "중학생",
        "eyebrow": "Middle School English & Math",
        "card_small": "중학생 · 영어와 수학",
        "card_description": "371개 동네별 학교 내신·과제·오답 관리 안내",
    },
    "elementary": {
        "zip": "초등 영수학원.zip",
        "category": "초등영수학원",
        "display": "초등 영수학원",
        "level": "초등",
        "grade_prefix": "초",
        "audience": "초등학생",
        "eyebrow": "Elementary English & Math",
        "card_small": "초등학생 · 영어와 수학",
        "card_description": "371개 동네별 기초 개념·학습 습관·오답 관리 안내",
    },
}
if LEVEL not in CONFIGS:
    raise ValueError(f"Unsupported SUBJECT_LEVEL: {LEVEL}")
CONFIG = CONFIGS[LEVEL]
ZIP_PATH = Path.home() / "Desktop" / "전국수업.com 추가 원고" / CONFIG["zip"]
CATEGORY = CONFIG["category"]
CATEGORY_DISPLAY = CONFIG["display"]
LEVEL_LABEL = CONFIG["level"]
GRADE_PREFIX = CONFIG["grade_prefix"]
AUDIENCE_LABEL = CONFIG["audience"]
EYEBROW_LABEL = CONFIG["eyebrow"]
TARGET = ROOT / "과목별학원" / CATEGORY
DOMAIN = "https://xn--3e0bz50bxucwzc.com"
SITE_NAME = "와와센터 학습코칭"
PUBLIC_SITE_NAME = "전국수업.com"
PHONE = "010-6839-8283"
PHONE_LINK = "01068398283"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
SMS_URL = "https://blogsms.net/01068398283"
DATE_PUBLISHED = "2026-07-22"
DATE_MODIFIED = "2026-07-22"


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value or "").strip()


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def escape(value: str) -> str:
    return html.escape(value or "", quote=True)


def absolute_url(*parts: str) -> str:
    path = "/" + "/".join(part.strip("/") for part in parts if part) + "/"
    return DOMAIN + quote(path, safe="/")


def parse_sections(text: str) -> dict[str, str]:
    marker = re.compile(r"^\[([^\]]+)\]\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end():end].strip()
    return sections


def parse_body(body: str) -> tuple[str, list[tuple[str, list[str]]]]:
    heading = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading.finditer(body))
    intro = body[: matches[0].start()].strip() if matches else body.strip()
    result: list[tuple[str, list[str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        paragraphs = [
            re.sub(r"\s*\n\s*", " ", block.strip())
            for block in re.split(r"\n\s*\n", body[match.end():end].strip())
            if block.strip()
        ]
        result.append((match.group(1).strip(), paragraphs))
    return re.sub(r"\s*\n\s*", " ", intro), result


def parse_faq(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^Q(\d+)\.\s*(.+?)\s*\n(?:A(?:\1)?\.\s*)?(.+?)(?=\n\s*Q\d+\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        (question.strip(), re.sub(r"\s+", " ", answer).strip())
        for _, question, answer in pattern.findall(text)
    ]


def parse_review(text: str) -> tuple[str, list[str]]:
    blocks = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return "", []
    note = blocks[0] if blocks[0].startswith("※") else ""
    reviews = blocks[1:] if note else blocks
    reviews = [review.strip().strip("“”\"'") for review in reviews if review.strip()]
    return note, reviews


def read_zip_entries() -> list[dict]:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(ZIP_PATH)
    pages: list[dict] = []
    with ZipFile(ZIP_PATH) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            text = archive.read(info).decode("utf-8-sig")
            sections = parse_sections(text)
            required = {"페이지타이틀", "메타설명", "본문", "FAQ", "학부모후기", "JSON-LD 요약"}
            missing = required - sections.keys()
            if missing:
                raise ValueError(f"{info.filename}: missing sections {sorted(missing)}")
            title = clean_text(sections["페이지타이틀"])
            locality = re.sub(rf"\s*{re.escape(CATEGORY_DISPLAY)}\s*$", "", title).strip()
            if not locality or title != f"{locality} {CATEGORY_DISPLAY}":
                raise ValueError(f"Unexpected title: {title}")
            pages.append({"filename": info.filename, "locality": locality, "sections": sections})
    if len(pages) != 371:
        raise ValueError(f"Expected 371 manuscripts, found {len(pages)}")
    return pages


def read_center_rows() -> list[dict[str, str]]:
    with CENTER_INFO.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [{key.strip(): (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]
    if len(rows) != 371:
        raise ValueError(f"Expected 371 center rows, found {len(rows)}")
    return rows


def field(row: dict[str, str], prefix: str) -> str:
    for key, value in row.items():
        if key.replace("\n", "").startswith(prefix.replace("\n", "")):
            return value.strip()
    return ""


def split_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，]", value or "") if part.strip()]


def make_slugs(rows: list[dict[str, str]]) -> dict[str, str]:
    localities = [row["근처 수업가능 동네"] for row in rows]
    neighborhood_count = Counter(value.split()[-1] for value in localities)
    result: dict[str, str] = {}
    for locality in localities:
        neighborhood = locality.split()[-1]
        slug = neighborhood if neighborhood_count[neighborhood] == 1 else normalize(locality)
        result[normalize(locality)] = slug
    return result


def representative_urls() -> list[str]:
    source = REPRESENTATIVE_CSV.read_text(encoding="utf-8-sig", errors="ignore")
    values: list[str] = []
    seen: set[str] = set()
    for url in re.findall(r"https://[^\"',<>\s]+\.(?:jpg|jpeg|png|webp|gif)", source, re.IGNORECASE):
        if url.startswith("http") and url not in seen:
            seen.add(url)
            values.append(url)
    if not values:
        raise ValueError("No representative image URLs found")
    return values


def choose_representative(urls: list[str], title: str) -> str:
    digest = hashlib.sha256(f"{CATEGORY}|{title}".encode("utf-8")).hexdigest()
    return urls[int(digest[:12], 16) % len(urls)]


def map_source(row: dict[str, str], slug: str) -> str:
    map_name = row.get("동 영어", "").strip()
    candidates = [f"{map_name}.jpg", f"{map_name}.webp", f"{map_name}.png"] if map_name else []
    parent = ROOT / "전국센터" / slug / "index.html"
    if parent.exists():
        match = re.search(r"assets/maps/([^\"']+)", parent.read_text(encoding="utf-8", errors="ignore"))
        if match:
            candidates.insert(0, match.group(1))
    for name in candidates:
        if (ROOT / "assets" / "maps" / name).exists():
            return name
    raise FileNotFoundError(f"Map not found for {row.get('근처 수업가능 동네')}: {candidates}")


def grade_intersection(row: dict[str, str]) -> list[str]:
    english_grades = split_values(field(row, "가능학년(영어)"))
    math_grades = split_values(field(row, "가능학년(수학)"))
    math_set = set(math_grades)
    return [grade for grade in english_grades if grade in math_set and grade.startswith(GRADE_PREFIX)]


def paragraph_html(value: str) -> str:
    return f"<p>{escape(re.sub(r'\\s*\\n\\s*', ' ', value.strip()))}</p>"


def center_payload(row: dict[str, str], slug: str) -> dict:
    return {
        "locality": row["근처 수업가능 동네"],
        "slug": slug,
        "region": row.get("지역", ""),
        "district": row.get("시or구", ""),
        "center": row.get("센터명", ""),
        "tuition": row.get("센터 교습비", ""),
        "office": row.get("교육지원청명칭", ""),
        "registration": row.get("교육지원청 등록번호", ""),
        "address": row.get("센터 주소", ""),
        "schools": split_values(field(row, "타깃학교(고)")),
        "grades": grade_intersection(row),
        "map": map_source(row, slug),
        "body_image": "seoul6839.webp" if row.get("지역") == "서울" else "local6839.webp",
    }


def make_graph(page: dict, center: dict, representative: str) -> dict:
    sections = page["sections"]
    title = clean_text(sections["페이지타이틀"])
    description = clean_text(sections["메타설명"])
    summary = clean_text(sections["JSON-LD 요약"])
    faq = parse_faq(sections["FAQ"])
    _, body_sections = parse_body(sections["본문"])
    canonical = absolute_url("과목별학원", CATEGORY, center["slug"])
    hub_url = absolute_url("과목별학원", CATEGORY)
    subject_url = absolute_url("과목별학원")
    home_url = DOMAIN + "/"
    webpage_id = canonical + "#webpage"
    org_id = canonical + "#organization"
    article_id = canonical + "#article"
    service_id = canonical + "#service"
    breadcrumb_id = canonical + "#breadcrumb"
    faq_id = canonical + "#faq"
    itemlist_id = canonical + "#related"
    image_id = canonical + "#primaryimage"
    region_names = [value for value in (center["region"], center["district"], center["locality"]) if value]
    about = [
        {"@type": "Thing", "name": f"{LEVEL_LABEL} 영어"},
        {"@type": "Thing", "name": f"{LEVEL_LABEL} 수학"},
        {"@type": "Thing", "name": CATEGORY_DISPLAY},
        {"@type": "Thing", "name": "내신 대비"},
        {"@type": "Thing", "name": "오답 관리"},
    ]
    mentions = [{"@type": "Place", "name": name} for name in region_names]
    mentions.extend({"@type": "Organization", "name": school} for school in center["schools"])
    has_part = [{"@type": "WebPageElement", "name": heading} for heading, _ in body_sections]
    has_part.extend(
        [
            {"@type": "WebPageElement", "name": "수업·상담 핵심정보"},
            {"@type": "WebPageElement", "name": "본문 안내 이미지"},
            {"@type": "WebPageElement", "name": "센터 지도"},
            {"@type": "WebPageElement", "name": "자주 묻는 질문"},
            {"@type": "WebPageElement", "name": "학부모 상담 관점"},
            {"@type": "WebPageElement", "name": "관련 학습 안내"},
        ]
    )
    offer = {
        "@type": "Offer",
        "name": f"{title} 상담 및 학습관리",
        "itemOffered": {"@type": "Service", "name": title, "serviceType": f"{LEVEL_LABEL} 영어·수학 학습관리"},
    }
    if center["tuition"]:
        offer["url"] = center["tuition"]
    organization = {
        "@type": ["EducationalOrganization", "LocalBusiness"],
        "@id": org_id,
        "name": center["center"] or title,
        "url": canonical,
        "image": representative,
        "telephone": PHONE,
        "openingHours": "Mo-Sa 12:00-24:00",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": center["address"],
            "addressRegion": center["region"],
            "addressLocality": center["district"],
            "addressCountry": "KR",
        },
        "areaServed": {"@type": "Place", "name": center["locality"]},
        "knowsAbout": [f"{LEVEL_LABEL} 영어", f"{LEVEL_LABEL} 수학", "내신 대비", "학습 진단", "오답 재학습"],
        "makesOffer": [offer],
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+82-10-6839-8283",
            "contactType": "학습 상담",
            "availableLanguage": "Korean",
        },
    }
    if center["registration"]:
        organization["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "교육지원청 등록번호",
            "value": center["registration"],
        }
    if center["grades"]:
        organization["educationalLevel"] = center["grades"]
    graph = [
        {
            "@type": "WebPage",
            "@id": webpage_id,
            "url": canonical,
            "name": title,
            "description": description,
            "inLanguage": "ko-KR",
            "primaryImageOfPage": {"@id": image_id},
            "breadcrumb": {"@id": breadcrumb_id},
            "mainEntity": {"@id": service_id},
            "about": about,
            "mentions": mentions,
            "hasPart": has_part,
        },
        {"@type": "ImageObject", "@id": image_id, "url": representative, "caption": f"{title} {PUBLIC_SITE_NAME} 대표"},
        organization,
        {
            "@type": "BreadcrumbList",
            "@id": breadcrumb_id,
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": home_url},
                {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": subject_url},
                {"@type": "ListItem", "position": 3, "name": CATEGORY_DISPLAY, "item": hub_url},
                {"@type": "ListItem", "position": 4, "name": center["locality"], "item": canonical},
            ],
        },
        {
            "@type": "Article",
            "@id": article_id,
            "headline": title,
            "description": description,
            "abstract": summary,
            "image": [representative, absolute_url("assets", "centers", "common", center["body_image"]).rstrip("/")],
            "inLanguage": "ko-KR",
            "datePublished": DATE_PUBLISHED,
            "dateModified": DATE_MODIFIED,
            "author": {"@id": org_id},
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": home_url},
            "mainEntityOfPage": {"@id": webpage_id},
            "articleSection": [heading for heading, _ in body_sections],
            "about": about,
            "mentions": mentions,
            "hasPart": has_part,
        },
        {
            "@type": "Service",
            "@id": service_id,
            "name": f"{title} 학습관리",
            "serviceType": f"{LEVEL_LABEL} 영어·수학 학습관리",
            "description": summary,
            "provider": {"@id": org_id},
            "areaServed": {"@type": "Place", "name": center["locality"]},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student", "audienceType": AUDIENCE_LABEL},
            "about": about,
            "mentions": mentions,
            "makesOffer": [offer],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "mainEntity": [
                {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
                for question, answer in faq
            ],
        },
        {
            "@type": "ItemList",
            "@id": itemlist_id,
            "name": f"{center['locality']} 관련 학습 안내",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": f"{CATEGORY_DISPLAY} 전체 지역", "url": hub_url},
                {"@type": "ListItem", "position": 2, "name": f"{center['locality']} 전국학원 안내", "url": absolute_url("전국센터", center["slug"])},
                {"@type": "ListItem", "position": 3, "name": "학습가이드", "url": absolute_url("학습가이드")},
                {"@type": "ListItem", "position": 4, "name": "상담문의", "url": absolute_url("상담문의")},
            ],
        },
    ]
    return {"@context": "https://schema.org", "@graph": graph}


def render_info_rows(center: dict) -> str:
    grade_html = "".join(f"<span>{escape(grade)}</span>" for grade in center["grades"])
    school_html = "".join(f"<span>{escape(school)}</span>" for school in center["schools"])
    rows = [
        f"<div><dt>지역</dt><dd>{escape(' '.join(v for v in (center['region'], center['district'], center['locality']) if v))}</dd></div>",
        f"<div><dt>센터 기준</dt><dd>{escape(center['center'] or center['locality'] + ' 학습센터')}</dd></div>",
        f"<div><dt>제공 주소</dt><dd>{escape(center['address'] or '상담 시 확인')}</dd></div>",
        f"<div><dt>영어·수학 가능 학년</dt><dd><div class=\"subject-tag-list\">{grade_html or '<span>상담 시 확인</span>'}</div></dd></div>",
    ]
    if center["registration"]:
        rows.append(f"<div><dt>교육지원청 등록번호</dt><dd>{escape(center['registration'])}</dd></div>")
    if center["schools"]:
        rows.append(f"<div><dt>제공 학교 참고</dt><dd><div class=\"subject-tag-list\">{school_html}</div></dd></div>")
    if center["tuition"]:
        rows.append(
            f'<div class="subject-tuition-row"><dt>센터 교습비</dt><dd><a class="subject-tuition-link" href="{escape(center["tuition"])}" target="_blank" rel="noopener noreferrer">센터별 교습비 안내 <span aria-hidden="true">↗</span></a><small>등록된 센터별 교습비 자료를 새 창에서 확인합니다.</small></dd></div>'
        )
    return "".join(rows)


def render_page(page: dict, center: dict, representative: str) -> str:
    sections = page["sections"]
    title = clean_text(sections["페이지타이틀"])
    description = clean_text(sections["메타설명"])
    summary = clean_text(sections["JSON-LD 요약"])
    intro, body_sections = parse_body(sections["본문"])
    faq = parse_faq(sections["FAQ"])
    review_note, reviews = parse_review(sections["학부모후기"])
    canonical = absolute_url("과목별학원", CATEGORY, center["slug"])
    graph = make_graph(page, center, representative)
    body_html = "".join(
        f'<section class="subject-prose-section"><h2>{escape(heading)}</h2>{"".join(paragraph_html(paragraph) for paragraph in paragraphs)}</section>'
        for heading, paragraphs in body_sections
    )
    faq_html = "".join(
        f'<details class="subject-faq-item"{" open" if index == 0 else ""}><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>'
        for index, (question, answer) in enumerate(faq)
    )
    review_html = "".join(f'<blockquote class="subject-review-item">{escape(review)}</blockquote>' for review in reviews)
    locality = center["locality"]
    region_line = " ".join(v for v in (center["region"], center["district"], locality) if v)
    alt_base = f"{title} {PUBLIC_SITE_NAME}"
    info_rows = render_info_rows(center)
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | {PUBLIC_SITE_NAME}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(title)} | {PUBLIC_SITE_NAME}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{escape(representative)}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="../../../assets/favicon.png">
  <link rel="stylesheet" href="../../../assets/site.css">
  <link rel="stylesheet" href="../../../assets/site-modern.css">
  <script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":"))}</script>
</head>
<body class="subject-academy-page">
  <header class="site-header"><div class="header-inner">
    <a class="brand" href="../../../" aria-label="{SITE_NAME} 홈"><span class="brand-mark">W</span><span>{SITE_NAME}</span></a>
    <nav class="nav" aria-label="상단 메뉴"><a href="../../../">홈</a><a href="../../../학습가이드/">학습가이드</a><a href="../../../상담문의/">상담문의</a><a href="../../" aria-current="page">과목별학원</a><a href="../../../전국센터/">전국학원</a></nav>
    <a class="header-cta" href="{FORM_URL}" target="_blank" rel="noopener">상담 신청</a>
  </div></header>
  <main>
    <section class="local-hero subject-local-hero">
      <nav class="mini-breadcrumb" aria-label="현재 위치"><a href="../../../">홈</a><span>›</span><a href="../../">과목별학원</a><span>›</span><a href="../">{CATEGORY_DISPLAY}</a><span>›</span><strong>{escape(locality)}</strong></nav>
      <p class="eyebrow">{escape(EYEBROW_LABEL)}</p>
      <h1>{escape(title)}</h1>
      <p class="lead">{escape(description)}</p>
      <div class="hero-points"><span>{escape(region_line)}</span><span>{LEVEL_LABEL} 영어·수학</span><span>진단·내신·오답 관리</span></div>
    </section>

    <section class="section subject-summary-section">
      <div class="subject-summary-grid">
        <article class="subject-answer-card"><p class="eyebrow">30초 핵심 안내</p><h2>{escape(title)} 선택 전 확인할 기준</h2><p>{escape(summary)}</p></article>
        <aside class="subject-info-card"><h2>수업·상담 핵심정보</h2><dl>{info_rows}</dl></aside>
      </div>
    </section>

    <section class="local-media-section subject-media-section">
      <div class="local-media-card">
        <img src="{escape(representative)}" alt="{escape(alt_base)} 대표" style="display:none;">
        <p class="local-media-label">수업 안내 이미지</p>
        <img src="../../../assets/centers/common/{center['body_image']}" alt="{escape(alt_base)} 본문">
      </div>
      <div class="local-media-card"><p class="local-media-label">센터 위치 안내</p><img src="../../../assets/maps/{escape(center['map'])}" alt="{escape(alt_base)} 지도" loading="lazy"></div>
    </section>

    <section class="section subject-article-section">
      <div class="subject-article-layout">
        <article class="subject-main-article"><div class="subject-intro-answer"><p>{escape(intro)}</p></div>{body_html}</article>
        <aside class="subject-reading-guide"><p class="eyebrow">Reading Guide</p><h2>상담 전에 확인하세요</h2><ol><li>영어와 수학의 막히는 원인을 따로 기록합니다.</li><li>학교 시험 범위와 현재 교재를 함께 준비합니다.</li><li>수업·과제·오답의 다음 확인일을 묻습니다.</li><li>주소와 교습비는 제공된 최신 자료로 확인합니다.</li></ol></aside>
      </div>
    </section>

    <section class="section subject-faq-section"><div class="section-head center"><p class="eyebrow">FAQ</p><h2>{escape(title)} 자주 묻는 질문</h2></div><div class="subject-faq-list">{faq_html}</div></section>
    <section class="section subject-review-section"><div class="subject-review-card"><p class="eyebrow">Parent Perspective</p><h2>{escape(title)} 학부모 상담 관점</h2><p class="subject-review-note">{escape(review_note)}</p><div class="subject-review-list">{review_html}</div></div></section>

    <section class="section related-links-section"><div class="section-head center"><p class="eyebrow">Related Pages</p><h2>{escape(locality)} 관련 학습 안내</h2><p class="lead">현재 페이지와 같은 지역의 센터 안내, 과목별 지역 목록, 학습·상담 안내를 연결했습니다.</p></div><div class="related-link-grid">
      <a class="related-link-card" href="../"><span>전체 지역</span><b>{CATEGORY_DISPLAY}</b><em>371개 동네의 {LEVEL_LABEL} 영어·수학 안내를 살펴봅니다.</em></a>
      <a class="related-link-card" href="../../../전국센터/{escape(center['slug'])}/"><span>지역 센터</span><b>{escape(locality)} 전국학원 안내</b><em>해당 동네의 센터 위치와 전체 학습관리 기준을 확인합니다.</em></a>
      <a class="related-link-card" href="../../../학습가이드/"><span>학습관리</span><b>학습가이드</b><em>진단, 플래너, 오답 재학습의 관리 흐름을 확인합니다.</em></a>
      <a class="related-link-card" href="../../../상담문의/"><span>상담 준비</span><b>상담문의</b><em>상담 전에 준비할 자료와 질문을 정리합니다.</em></a>
    </div></section>
  </main>
  <footer class="footer"><div class="footer-inner"><div><strong>{SITE_NAME}</strong><br>초중고 영어·수학·국어 학습관리 안내</div><div>상담 전화 <a href="tel:{PHONE_LINK}">{PHONE}</a></div></div></footer>
  <aside class="floating-actions" aria-label="빠른 상담 버튼"><a href="tel:{PHONE_LINK}">전화문의</a><a href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a><a href="{FORM_URL}" target="_blank" rel="noopener">상담신청</a></aside>
</body>
</html>
'''


def hub_graph(pages: list[tuple[dict, dict]]) -> dict:
    canonical = absolute_url("과목별학원", CATEGORY)
    items = [
        {"@type": "ListItem", "position": index + 1, "name": clean_text(page["sections"]["페이지타이틀"]), "url": absolute_url("과목별학원", CATEGORY, center["slug"])}
        for index, (page, center) in enumerate(pages)
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": canonical + "#webpage", "url": canonical, "name": f"{CATEGORY_DISPLAY} 지역 안내", "description": f"371개 동네별 {LEVEL_LABEL} 영어·수학 학원 선택 기준과 센터 정보를 확인할 수 있는 지역 허브입니다.", "inLanguage": "ko-KR", "breadcrumb": {"@id": canonical + "#breadcrumb"}, "mainEntity": {"@id": canonical + "#itemlist"}, "about": [{"@type": "Thing", "name": f"{LEVEL_LABEL} 영어"}, {"@type": "Thing", "name": f"{LEVEL_LABEL} 수학"}, {"@type": "Thing", "name": CATEGORY_DISPLAY}]},
            {"@type": "BreadcrumbList", "@id": canonical + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": absolute_url("과목별학원")}, {"@type": "ListItem", "position": 3, "name": CATEGORY_DISPLAY, "item": canonical}]},
            {"@type": "ItemList", "@id": canonical + "#itemlist", "name": f"동네별 {CATEGORY_DISPLAY} 안내", "numberOfItems": len(items), "itemListElement": items},
            {"@type": "FAQPage", "@id": canonical + "#faq", "mainEntity": [
                {"@type": "Question", "name": f"{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?", "acceptedAnswer": {"@type": "Answer", "text": "영어와 수학을 같은 기준으로 묶지 말고, 영어는 어휘·문법·독해를, 수학은 개념·유형·풀이·오답을 따로 진단하는지 확인해야 합니다."}},
                {"@type": "Question", "name": "지역별 페이지에는 어떤 정보가 있나요?", "acceptedAnswer": {"@type": "Answer", "text": "제공된 지역·센터·학교·주소 자료와 개별 원고를 바탕으로 수업 대상, 상담 질문, 내신과 오답 관리 기준을 정리했습니다."}},
            ]},
        ],
    }


def render_hub(pages: list[tuple[dict, dict]]) -> str:
    canonical = absolute_url("과목별학원", CATEGORY)
    regions: dict[str, dict[str, list[tuple[dict, dict]]]] = {}
    for page, center in pages:
        regions.setdefault(center["region"], {}).setdefault(center["district"], []).append((page, center))
    region_html = []
    for region, districts in regions.items():
        district_html = []
        for district, entries in districts.items():
            links = "".join(
                f'<a class="subject-locality-link" href="{escape(center["slug"])}/" data-search="{escape(" ".join((region, district, center["locality"], center["center"], clean_text(page["sections"]["페이지타이틀"]))))}" aria-label="{escape(clean_text(page["sections"]["페이지타이틀"]))} 페이지로 이동"><b>{escape(center["locality"])}</b><span>{CATEGORY_DISPLAY}</span><i aria-hidden="true">→</i></a>'
                for page, center in entries
            )
            district_html.append(f'<section class="subject-district-block"><div class="subject-district-heading"><h3>{escape(district or region)}</h3><span>{len(entries)}곳</span></div><div class="subject-locality-grid">{links}</div></section>')
        opened = " open" if not region_html else ""
        region_count = sum(len(v) for v in districts.values())
        region_html.append(f'<details class="subject-region-block" data-region{opened}><summary class="subject-region-heading"><span><small>광역지역</small>{escape(region)}</span><strong>{region_count}개 동네<i aria-hidden="true"></i></strong></summary><div class="subject-region-content">{"".join(district_html)}</div></details>')
    graph = hub_graph(pages)
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{CATEGORY_DISPLAY} 지역 찾기 | {PUBLIC_SITE_NAME}</title>
<meta name="description" content="371개 동네별 {LEVEL_LABEL} 영어·수학 학원 선택 기준을 지역과 시군구별로 정리했습니다. 센터 정보, 학교 내신, 과목별 진단과 오답 관리 기준을 확인하세요.">
<meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:title" content="{CATEGORY_DISPLAY} 지역 찾기 | {PUBLIC_SITE_NAME}"><meta property="og:description" content="지역별 {LEVEL_LABEL} 영어·수학 학원 선택 기준과 상담 정보를 확인하세요."><meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}"><link rel="icon" href="../../assets/favicon.png"><link rel="stylesheet" href="../../assets/site.css"><link rel="stylesheet" href="../../assets/site-modern.css"><script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":"))}</script></head>
<body class="subject-hub-page"><header class="site-header"><div class="header-inner"><a class="brand" href="../../" aria-label="{SITE_NAME} 홈"><span class="brand-mark">W</span><span>{SITE_NAME}</span></a><nav class="nav" aria-label="상단 메뉴"><a href="../../">홈</a><a href="../../학습가이드/">학습가이드</a><a href="../../상담문의/">상담문의</a><a href="../" aria-current="page">과목별학원</a><a href="../../전국센터/">전국학원</a></nav><a class="header-cta" href="{FORM_URL}" target="_blank" rel="noopener">상담 신청</a></div></header>
<main><section class="page-hero subject-hub-hero"><nav class="mini-breadcrumb" aria-label="현재 위치"><a href="../../">홈</a><span>›</span><a href="../">과목별학원</a><span>›</span><strong>{CATEGORY_DISPLAY}</strong></nav><p class="eyebrow">{escape(EYEBROW_LABEL)}</p><h1>동네별 {CATEGORY_DISPLAY}</h1><p class="lead">{LEVEL_LABEL} 영어와 수학은 학습 방식이 다르기 때문에 과목별 진단과 주간 계획을 따로 세우되, 학교 시험 일정과 전체 학습량은 함께 조정해야 합니다. 아래에서 지역을 선택해 개별 원고와 확인된 센터 정보를 살펴보세요.</p><div class="hero-points"><span>371개 동네</span><span>개별 원고</span><span>제공 자료 기반</span></div></section>
<section class="section subject-hub-intro"><div class="subject-summary-grid"><article class="subject-answer-card"><p class="eyebrow">Selection Guide</p><h2>영어와 수학을 같은 방식으로 관리하지 않습니다</h2><p>영어는 어휘·구문·독해·서술형의 누적 상태를, 수학은 개념 이해·유형 적용·풀이 과정·오답 원인을 나누어 확인합니다. 상담에서는 각 과목의 우선순위와 재점검 날짜가 구체적으로 남는지 살펴보세요.</p></article><aside class="subject-info-card"><h2>페이지 구성</h2><dl><div><dt>지역</dt><dd>13개 광역권 · 371개 동네</dd></div><div><dt>대상</dt><dd>센터별 제공 가능 학년 기준</dd></div><div><dt>내용</dt><dd>개별 원고 · 센터 · 학교 · 주소 정보</dd></div><div><dt>관리</dt><dd>진단 · 내신 · 과제 · 오답 재학습</dd></div></dl></aside></div></section>
<section class="section subject-directory-section"><div class="section-head center"><p class="eyebrow">Local Directory</p><h2>{CATEGORY_DISPLAY} 지역 선택</h2><p class="lead">광역지역을 펼쳐 시군구와 동네를 차례로 확인하거나, 검색창에서 바로 찾아보세요.</p></div><div class="subject-directory-overview" aria-label="지역 안내 요약"><div><strong>{len(regions)}</strong><span>광역지역</span></div><div><strong>{len(pages)}</strong><span>동네 안내</span></div><p>처음에는 한 지역만 열어 두어 목록을 간결하게 정리했습니다.</p></div><div class="subject-directory-tools"><label class="subject-search"><span>지역 검색</span><input id="subject-local-search" type="search" placeholder="서울 · 강동구 · 명일동" autocomplete="off"></label><div class="subject-directory-actions"><button type="button" id="subject-expand-all">모두 펼치기</button><button type="button" id="subject-collapse-all">모두 접기</button></div></div><p class="subject-search-result" id="subject-search-result" aria-live="polite">전체 {len(pages)}개 동네</p><div class="subject-region-list">{"".join(region_html)}</div></section>
<section class="section"><div class="section-head center"><p class="eyebrow">FAQ</p><h2>{CATEGORY_DISPLAY} 자주 묻는 질문</h2></div><div class="faq"><details open><summary>{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?</summary><p>영어와 수학을 같은 기준으로 묶지 말고, 영어는 어휘·문법·독해를, 수학은 개념·유형·풀이·오답을 따로 진단하는지 확인해야 합니다.</p></details><details><summary>지역별 페이지에는 어떤 정보가 있나요?</summary><p>제공된 지역·센터·학교·주소 자료와 개별 원고를 바탕으로 수업 대상, 상담 질문, 내신과 오답 관리 기준을 정리했습니다.</p></details></div></section></main>
<footer class="footer"><div class="footer-inner"><div><strong>{SITE_NAME}</strong><br>초중고 영어·수학·국어 학습관리 안내</div><div>상담 전화 <a href="tel:{PHONE_LINK}">{PHONE}</a></div></div></footer><aside class="floating-actions" aria-label="빠른 상담 버튼"><a href="tel:{PHONE_LINK}">전화문의</a><a href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a><a href="{FORM_URL}" target="_blank" rel="noopener">상담신청</a></aside>
<script>(function(){{var input=document.getElementById('subject-local-search'),result=document.getElementById('subject-search-result'),links=[].slice.call(document.querySelectorAll('.subject-locality-link')),regions=[].slice.call(document.querySelectorAll('[data-region]')),expand=document.getElementById('subject-expand-all'),collapse=document.getElementById('subject-collapse-all');function update(){{var query=(input.value||'').trim().toLowerCase(),shown=0;links.forEach(function(link){{var haystack=(link.getAttribute('data-search')||link.textContent).toLowerCase(),match=!query||haystack.indexOf(query)>-1;link.hidden=!match;if(match)shown++;}});document.querySelectorAll('.subject-district-block').forEach(function(block){{block.hidden=!block.querySelector('.subject-locality-link:not([hidden])');}});regions.forEach(function(block){{block.hidden=!block.querySelector('.subject-locality-link:not([hidden])');if(query&&!block.hidden)block.open=true;}});result.textContent=query?'검색 결과 '+shown+'개':'전체 {len(pages)}개 동네';}}input.addEventListener('input',update);expand.addEventListener('click',function(){{regions.forEach(function(block){{if(!block.hidden)block.open=true;}});}});collapse.addEventListener('click',function(){{regions.forEach(function(block){{block.open=false;}});}});}})();</script></body></html>'''


def update_subject_root() -> None:
    path = ROOT / "과목별학원" / "index.html"
    source = path.read_text(encoding="utf-8")
    cards = []
    for config in CONFIGS.values():
        category = config["category"]
        if not (ROOT / "과목별학원" / category / "index.html").exists():
            continue
        cards.append(
            f'<a class="subject-category-card" href="{category}/"><span class="subject-category-icon">E+M</span><span><small>{config["card_small"]}</small><strong>{config["display"]}</strong><em>{config["card_description"]}</em></span><b aria-hidden="true">→</b></a>'
        )
    block = f'''<!-- SUBJECT-CATEGORY-CARDS-START -->
    <section class="section subject-category-section">
      <div class="section-head center"><p class="eyebrow">Published Guide</p><h2>현재 확인할 수 있는 과목별 안내</h2><p class="lead">개별 원고와 확인된 센터 자료를 바탕으로 작성한 지역 페이지입니다.</p></div>
      <div class="subject-category-grid">{"".join(cards)}</div>
    </section>
<!-- SUBJECT-CATEGORY-CARDS-END -->'''
    pattern = re.compile(
        r"\s*<!-- (?:HIGH-COMBINED|SUBJECT-CATEGORY-CARDS)-START -->.*?<!-- (?:HIGH-COMBINED|SUBJECT-CATEGORY-CARDS)-END -->",
        re.DOTALL,
    )
    source = pattern.sub("", source)
    anchor = "    <section class=\"section split\">"
    if anchor not in source:
        raise ValueError("Subject root insertion point not found")
    source = source.replace(anchor, block + "\n\n" + anchor, 1)
    path.write_text(source, encoding="utf-8", newline="\n")


def update_sitemap(urls: list[str]) -> None:
    path = ROOT / "sitemap.xml"
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    existing = {node.text for node in root.findall("sm:url/sm:loc", ns) if node.text}
    all_urls = list(existing)
    for url in urls:
        if url not in existing:
            all_urls.append(url)
            existing.add(url)
    home = DOMAIN + "/"
    ordered = [home] if home in existing else []
    ordered.extend(sorted(url for url in all_urls if url != home))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines.extend(f"  <url><loc>{escape(url)}</loc></url>" for url in ordered)
    lines.append("</urlset>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def update_llms() -> None:
    path = ROOT / "llms.txt"
    source = path.read_text(encoding="utf-8")
    line = f"- {CATEGORY_DISPLAY}: {absolute_url('과목별학원', CATEGORY)}"
    if line not in source:
        marker = f"- 과목별학원: {absolute_url('과목별학원')}"
        if marker not in source:
            subject_line = f"- 과목별학원: {absolute_url('과목별학원')}"
            source = source.replace("- 전국학원:", subject_line + "\n- 전국학원:")
        marker = f"- 과목별학원: {absolute_url('과목별학원')}"
        source = source.replace(marker, marker + "\n" + line)
    path.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    hub_only = os.environ.get("HUB_ONLY") == "1"
    manuscripts = read_zip_entries()
    rows = read_center_rows()
    slugs = make_slugs(rows)
    row_map = {normalize(row["근처 수업가능 동네"]): row for row in rows}
    manuscript_keys = {normalize(page["locality"]) for page in manuscripts}
    if manuscript_keys != set(row_map):
        raise ValueError(f"Manuscript/center mismatch: missing centers={sorted(manuscript_keys-set(row_map))[:10]}, missing manuscripts={sorted(set(row_map)-manuscript_keys)[:10]}")
    representatives = [] if hub_only else representative_urls()
    rendered: list[tuple[dict, dict]] = []
    TARGET.mkdir(parents=True, exist_ok=True)
    urls = [absolute_url("과목별학원", CATEGORY)]
    for page in sorted(manuscripts, key=lambda item: item["locality"]):
        key = normalize(page["locality"])
        row = row_map[key]
        slug = slugs[key]
        center = center_payload(row, slug)
        if not hub_only:
            parent = ROOT / "전국센터" / slug / "index.html"
            if not parent.exists():
                raise FileNotFoundError(f"Parent page missing: {parent}")
            representative = choose_representative(representatives, clean_text(page["sections"]["페이지타이틀"]))
            output = TARGET / slug / "index.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_page(page, center, representative), encoding="utf-8", newline="\n")
        rendered.append((page, center))
        urls.append(absolute_url("과목별학원", CATEGORY, slug))
    (TARGET / "index.html").write_text(render_hub(rendered), encoding="utf-8", newline="\n")
    if not hub_only:
        update_subject_root()
        update_sitemap(urls)
        update_llms()
    print(json.dumps({"category": CATEGORY, "pages": len(rendered), "hub": str(TARGET / 'index.html'), "urls": len(urls)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

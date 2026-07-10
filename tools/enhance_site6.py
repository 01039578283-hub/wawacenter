from __future__ import annotations

import json
import re
from pathlib import Path

from content_banks_site6 import FAQ_STATIC_BANK, REVIEW_BANK, pick, pick_unique

ROOT = Path(__file__).resolve().parents[1]
CENTER_ROOT = ROOT / "전국센터"


DONG_ALIASES = {
    "상동": "부천 상동",
    "읍내동": "당진 읍내동",
    "장동": "전주 장동",
}


def load_center_info() -> dict[str, dict]:
    with open(Path(__file__).parent / "center_info.json", encoding="utf-8") as f:
        raw = json.load(f)
    index = {k.replace(" ", ""): v for k, v in raw.items()}
    for bare, aliased in DONG_ALIASES.items():
        key = aliased.replace(" ", "")
        if key in index:
            index[bare] = index[key]
    return index


def target_dirs() -> list[tuple[Path, str, str]]:
    """Return (page_dir, kind, dong) for every non-hub page."""
    result = []
    for dong_dir in sorted(d for d in CENTER_ROOT.iterdir() if d.is_dir()):
        dong = dong_dir.name
        result.append((dong_dir, "parent", dong))
        coach_dir = dong_dir / "와와학습코칭학원"
        if (coach_dir / "index.html").exists():
            result.append((coach_dir, "coaching", dong))
        em_dir = dong_dir / "영어수학학원"
        if (em_dir / "index.html").exists():
            result.append((em_dir, "english_math", dong))
    return result


def type_names(node) -> list[str]:
    t = node.get("@type")
    return t if isinstance(t, list) else [t]


def find_node(graph: list[dict], type_name: str) -> dict | None:
    for node in graph:
        if isinstance(node, dict) and type_name in type_names(node):
            return node
    return None


def extract_reviews(text: str) -> list[str]:
    reviews_m = re.search(r'<div class="reviews">(.*?)</div>\s*</section>', text, re.S)
    block = reviews_m.group(1)
    return re.findall(r'<p>[“"](.*?)[”"]</p>', block)


def extract_faqs(text: str) -> list[tuple[str, str]]:
    faq_m = re.search(r'<div class="faq">(.*?)</div>\s*</section>', text, re.S)
    block = faq_m.group(1)
    return re.findall(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", block, re.S)


def render_reviews(reviews: list[str]) -> str:
    cards = [
        f'        <article class="review"><div class="stars">★★★★★</div><p>“{r}”</p></article>'
        for r in reviews
    ]
    return "\n" + "\n".join(cards) + "\n      "


def render_faqs(faqs: list[tuple[str, str]]) -> str:
    items = []
    for i, (q, a) in enumerate(faqs):
        open_attr = " open" if i == 0 else ""
        items.append(
            f"          <details{open_attr}>\n"
            f"            <summary>{q}</summary>\n"
            f"            <p>{a}</p>\n"
            f"          </details>"
        )
    return "\n" + "\n".join(items) + "\n      "


def process_page(page_dir: Path, kind: str, dong: str, center_info: dict, seen_reviews: dict) -> bool:
    path = page_dir / "index.html"
    source = path.read_text(encoding="utf-8", errors="ignore")
    page_url = path.as_posix()
    updated = source

    # 1) JSON-LD: add address/identifier if we have real branch data; diversify FAQ+reviews
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', updated, re.S)
    data = json.loads(m.group(1))
    graph = data["@graph"]

    org = find_node(graph, "EducationalOrganization")
    branch = center_info.get(dong.replace(" ", ""))
    if branch and "identifier" not in org:
        org["address"] = {
            "@type": "PostalAddress",
            "streetAddress": branch["센터 주소"],
            "addressRegion": branch["지역"],
            "addressLocality": branch["시or구"],
            "addressCountry": "KR",
        }
        org["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "교육지원청 등록번호",
            "value": branch["교육지원청 등록번호"],
        }

    # Reviews: keep slot 0 (dong-specific opener), regenerate slots 1-2 from bank
    visible_reviews = extract_reviews(updated)
    opener = visible_reviews[0]
    picked = pick_unique(REVIEW_BANK, 2, seen_reviews.setdefault(kind, set()), page_url, kind, "review")
    new_reviews = [opener] + picked

    org["review"] = [
        {
            "@type": "Review",
            "author": {"@type": "Person", "name": "학부모"},
            "reviewBody": r,
            "reviewRating": {"@type": "Rating", "ratingValue": "5", "bestRating": "5"},
        }
        for r in new_reviews
    ]

    # FAQ: keep slots 0,1,2,4 as-is, regenerate the static slot 3 from the per-kind bank
    visible_faqs = extract_faqs(updated)
    q3, a3 = pick(FAQ_STATIC_BANK[kind], 1, page_url, kind, "faq3")[0]
    new_faqs = list(visible_faqs)
    new_faqs[3] = (q3, a3)

    faq_node = find_node(graph, "FAQPage")
    faq_node["mainEntity"] = [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in new_faqs
    ]

    rendered = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"
    updated = updated[: m.start()] + rendered + updated[m.end():]

    # 2) Visible HTML
    new_review_html = render_reviews(new_reviews)
    updated = re.sub(
        r'(<div class="reviews">)(.*?)(\s*</div>\s*</section>)',
        lambda mm: mm.group(1) + new_review_html + mm.group(3),
        updated,
        count=1,
        flags=re.S,
    )
    new_faq_html = render_faqs(new_faqs)
    updated = re.sub(
        r'(<div class="faq">)(.*?)(\s*</div>\s*</section>)',
        lambda mm: mm.group(1) + new_faq_html + mm.group(3),
        updated,
        count=1,
        flags=re.S,
    )

    if updated != source:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    center_info = load_center_info()
    targets = target_dirs()
    seen_reviews: dict[str, set] = {}
    changed = 0
    errors = 0
    no_branch = 0
    for page_dir, kind, dong in targets:
        try:
            if process_page(page_dir, kind, dong, center_info, seen_reviews):
                changed += 1
            if dong.replace(" ", "") not in center_info:
                no_branch += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"ERROR {page_dir}: {exc}")
    print(json.dumps({"targets": len(targets), "changed": changed, "errors": errors, "no_branch": no_branch}, ensure_ascii=False))


if __name__ == "__main__":
    main()

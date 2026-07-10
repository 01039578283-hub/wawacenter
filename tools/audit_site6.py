from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTER_ROOT = ROOT / "전국센터"


def target_files() -> list[Path]:
    result = []
    for index in CENTER_ROOT.rglob("index.html"):
        rel = index.parent.relative_to(CENTER_ROOT)
        if str(rel) == ".":
            continue
        result.append(index)
    return sorted(result)


def main() -> None:
    files = target_files()
    print(f"total_files={len(files)}")

    faq_counter: Counter[str] = Counter()
    review_counter: Counter[str] = Counter()
    review_sets: Counter[frozenset] = Counter()
    parse_errors = 0
    faq_mismatch = 0
    review_mismatch = 0
    h1_bad = 0

    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        try:
            data = json.loads(m.group(1))
        except Exception as exc:  # noqa: BLE001
            parse_errors += 1
            print("PARSE ERROR", f, exc)
            continue

        graph = data.get("@graph", [])

        def find(type_name):
            for node in graph:
                t = node.get("@type")
                types = t if isinstance(t, list) else [t]
                if type_name in types:
                    return node
            return None

        h1s = re.findall(r"<h1\b[^>]*>.*?</h1>", text, re.S)
        if len(h1s) != 1:
            h1_bad += 1

        faq_node = find("FAQPage")
        faq_section_m = re.search(r'<div class="faq">.*?</div>\s*</section>', text, re.S)
        if faq_node and faq_section_m:
            jsonld_q = [q["name"] for q in faq_node["mainEntity"]]
            visible_q = re.findall(r"<summary>([^<]*)</summary>", faq_section_m.group(0))
            if jsonld_q != visible_q:
                faq_mismatch += 1
            for q in jsonld_q:
                faq_counter[q] += 1

        org = find("EducationalOrganization")
        reviews_section_m = re.search(r'<div class="reviews">.*?</div>\s*</section>', text, re.S)
        if org and reviews_section_m:
            jsonld_reviews = [r["reviewBody"] for r in org.get("review", [])]
            visible_reviews = re.findall(r"<p>(.*?)</p>", reviews_section_m.group(0))
            if jsonld_reviews != visible_reviews:
                review_mismatch += 1
            for r in jsonld_reviews:
                review_counter[r] += 1
            if jsonld_reviews:
                review_sets[frozenset(jsonld_reviews)] += 1

    print(f"parse_errors={parse_errors} faq_mismatch={faq_mismatch} review_mismatch={review_mismatch} h1_bad={h1_bad}")
    print(f"distinct_faq={len(faq_counter)} total_faq={sum(faq_counter.values())}")
    for text_, cnt in faq_counter.most_common(5):
        print(f"  {cnt}x {text_[:50]}")
    print(f"distinct_reviews={len(review_counter)} total_reviews={sum(review_counter.values())}")
    for text_, cnt in review_counter.most_common(5):
        print(f"  {cnt}x {text_[:50]}")
    dup_sets = sum(1 for c in review_sets.values() if c > 1)
    print(f"distinct_review_sets={len(review_sets)} dup_sets={dup_sets}")


if __name__ == "__main__":
    main()

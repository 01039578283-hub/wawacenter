from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from itertools import combinations
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

import generate_subject_high_combined as generator


ROOT = generator.ROOT
TARGET = generator.TARGET
ERRORS: list[str] = []


def fail(message: str) -> None:
    ERRORS.append(message)


def first(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1)).strip() if match else ""


def graph_types(graph: dict) -> set[str]:
    result: set[str] = set()
    for node in graph.get("@graph", []):
        value = node.get("@type")
        if isinstance(value, list):
            result.update(value)
        elif isinstance(value, str):
            result.add(value)
    return result


def node_by_type(graph: dict, wanted: str) -> dict:
    for node in graph.get("@graph", []):
        value = node.get("@type")
        if value == wanted or isinstance(value, list) and wanted in value:
            return node
    raise KeyError(wanted)


def masked_shingles(value: str, page: dict, center: dict, size: int = 5) -> set[tuple[str, ...]]:
    text = generator.clean_text(value)
    replacements = [
        page["sections"]["페이지타이틀"], center["locality"], center["center"], center["address"],
        center["region"], center["district"], center["registration"], *center["schools"], *center["grades"],
    ]
    for item in sorted((item for item in replacements if item), key=len, reverse=True):
        text = text.replace(item, " 개별정보 ")
    text = re.sub(r"\d+", " 숫자 ", text)
    tokens = re.findall(r"[가-힣A-Za-z]+", text)
    return {tuple(tokens[index:index + size]) for index in range(max(0, len(tokens) - size + 1))}


def jaccard(left: set, right: set) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def check_link(page_path: Path, href: str) -> bool:
    if not href or href.startswith(("http:", "https:", "tel:", "mailto:", "#", "javascript:")):
        return True
    href = unquote(href.split("#", 1)[0].split("?", 1)[0])
    target = (page_path.parent / href).resolve()
    if href.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target.exists()


def main() -> None:
    manuscripts = generator.read_zip_entries()
    rows = generator.read_center_rows()
    slugs = generator.make_slugs(rows)
    manuscript_map = {generator.normalize(page["locality"]): page for page in manuscripts}
    row_map = {generator.normalize(row["근처 수업가능 동네"]): row for row in rows}
    expected_types = {"WebPage", "ImageObject", "EducationalOrganization", "LocalBusiness", "BreadcrumbList", "Article", "Service", "FAQPage", "ItemList"}
    canonical_values: set[str] = set()
    body_values: set[str] = set()
    faq_values: set[str] = set()
    review_values: set[str] = set()
    meta_values: set[str] = set()
    article_values: set[str] = set()
    shingle_rows: list[tuple[str, set[tuple[str, ...]]]] = []
    center_ids: dict[str, str] = {}
    total_links = 0
    for key, page in manuscript_map.items():
        row = row_map[key]
        slug = slugs[key]
        center = generator.center_payload(row, slug)
        page = generator.sanitize_page(page, center)
        path = TARGET / slug / "index.html"
        if not path.exists():
            fail(f"missing page: {slug}")
            continue
        source = path.read_text(encoding="utf-8")
        if generator.CONFIG["kind"] == "student":
            unsafe_output = generator.UNVERIFIED_OPERATION_RE.search(generator.clean_text(source))
            if unsafe_output:
                fail(f"unverified operation wording remains {unsafe_output.group(0)!r}: {slug}")
            if "검색자의 궁금증은" in source:
                fail(f"search-engine authoring voice remains: {slug}")
        if '<a class="skip-link" href="#main-content">' not in source or '<main id="main-content">' not in source:
            fail(f"skip link/main target missing: {slug}")
        title = generator.clean_text(page["sections"]["페이지타이틀"])
        expected_canonical = generator.absolute_url("과목별학원", generator.CATEGORY, slug)
        title_tag = first(r"<title>(.*?)</title>", source)
        h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.IGNORECASE | re.DOTALL)
        description = first(r'<meta\s+name="description"\s+content="([^"]*)"', source)
        canonical = first(r'<link\s+rel="canonical"\s+href="([^"]+)"', source)
        og_url = first(r'<meta\s+property="og:url"\s+content="([^"]+)"', source)
        if title_tag != f"{title} | {generator.PUBLIC_SITE_NAME}":
            fail(f"title mismatch: {slug}")
        if len(h1s) != 1 or generator.clean_text(h1s[0]) != title:
            fail(f"H1 mismatch/count: {slug}")
        if description != generator.meta_description(page["sections"]["메타설명"], title):
            fail(f"description mismatch: {slug}")
        if canonical != expected_canonical or og_url != expected_canonical:
            fail(f"canonical/og mismatch: {slug}")
        canonical_values.add(canonical)
        meta_values.add(description)
        scripts = re.findall(r'<script\s+type="application/ld\+json">(.*?)</script>', source, re.IGNORECASE | re.DOTALL)
        if len(scripts) != 1:
            fail(f"JSON-LD count: {slug}={len(scripts)}")
        else:
            try:
                graph = json.loads(scripts[0])
                types = graph_types(graph)
                missing = expected_types - types
                if missing:
                    fail(f"schema missing {sorted(missing)}: {slug}")
                article = node_by_type(graph, "Article")
                service = node_by_type(graph, "Service")
                organization = node_by_type(graph, "EducationalOrganization")
                webpage = node_by_type(graph, "WebPage")
                faq_schema = node_by_type(graph, "FAQPage")
                breadcrumb_schema = node_by_type(graph, "BreadcrumbList")
                related_schema = node_by_type(graph, "ItemList")
                for prop in ("about", "mentions", "hasPart", "articleSection"):
                    if not article.get(prop):
                        fail(f"Article {prop} empty: {slug}")
                if center["grades"]:
                    if not service.get("makesOffer") or not organization.get("makesOffer"):
                        fail(f"makesOffer missing despite verified grade availability: {slug}")
                elif service.get("makesOffer") or organization.get("makesOffer"):
                    fail(f"makesOffer present without verified grade availability: {slug}")
                if organization.get("openingHours"):
                    fail(f"unverified openingHours present: {slug}")
                if organization.get("address", {}).get("addressRegion") != center["region"]:
                    fail(f"official addressRegion mismatch: {slug}")
                org_id = organization.get("@id", "")
                center_key = generator.normalize((center["center"] or center["locality"]) + "|" + (center["address"] or center["locality"]))
                if not org_id.startswith(generator.DOMAIN + "/#center-"):
                    fail(f"unstable organization id: {slug}")
                previous_id = center_ids.setdefault(center_key, org_id)
                if previous_id != org_id:
                    fail(f"organization id split: {slug}")
                if service.get("provider", {}).get("@id") != org_id or article.get("author", {}).get("@id") != org_id:
                    fail(f"entity relationship mismatch: {slug}")
                if webpage.get("url") != expected_canonical or article.get("mainEntityOfPage", {}).get("@id") != webpage.get("@id"):
                    fail(f"webpage/article relationship mismatch: {slug}")
                faq_screen = [
                    (generator.clean_text(question), generator.clean_text(answer))
                    for question, answer in re.findall(
                        r'<details class="subject-faq-item"[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>',
                        source,
                        re.DOTALL,
                    )
                ]
                faq_json = [
                    (item.get("name", ""), item.get("acceptedAnswer", {}).get("text", ""))
                    for item in faq_schema.get("mainEntity", [])
                ]
                if faq_screen != faq_json:
                    fail(f"FAQ screen/schema mismatch: {slug}")
                crumb_screen = [generator.clean_text(item) for item in re.findall(r'<(?:a|strong)[^>]*>(.*?)</(?:a|strong)>', first(r'<nav class="mini-breadcrumb"[^>]*>(.*?)</nav>', source))]
                crumb_json = [item.get("name", "") for item in breadcrumb_schema.get("itemListElement", [])]
                if crumb_screen != crumb_json:
                    fail(f"breadcrumb screen/schema mismatch: {slug}")
                related_block = first(r'<div class="related-link-grid">(.*?)</div>', source)
                related_screen = [quote(urljoin(expected_canonical, html.unescape(href)), safe=":/%") for href in re.findall(r'href="([^"]+)"', related_block)]
                related_json = [item.get("url", "") for item in related_schema.get("itemListElement", [])]
                if related_screen != related_json:
                    fail(f"related screen/schema mismatch: {slug}")
            except Exception as exc:
                fail(f"JSON-LD invalid: {slug}: {exc}")
        for href in re.findall(r'<a\b[^>]*href="([^"]+)"', source, re.IGNORECASE):
            total_links += 1
            if not check_link(path, href):
                fail(f"broken link {href}: {slug}")
        for src in re.findall(r'<img\b[^>]*src="([^"]+)"', source, re.IGNORECASE):
            if src.startswith(("http:", "https:")):
                continue
            if not check_link(path, src):
                fail(f"broken image {src}: {slug}")
        intro, body_sections = generator.parse_body(page["sections"]["본문"])
        body_snippets = [intro]
        for heading, paragraphs in body_sections:
            body_snippets.append(heading)
            body_snippets.extend(paragraphs)
        if any(escape_for_check(re.sub(r"\s+", " ", value)) not in source for value in body_snippets if value):
            fail(f"manuscript text missing [본문]: {slug}")
        faq_pairs = generator.parse_faq(page["sections"]["FAQ"])
        if any(escape_for_check(value) not in source for pair in faq_pairs for value in pair):
            fail(f"manuscript text missing [FAQ]: {slug}")
        review_note, reviews = generator.parse_review(page["sections"]["학부모후기"])
        if any(escape_for_check(value) not in source for value in [review_note, *reviews] if value):
            fail(f"manuscript text missing [학부모후기]: {slug}")
        summary = generator.clean_text(page["sections"]["JSON-LD 요약"])
        if json.dumps(summary, ensure_ascii=False)[1:-1] not in source:
            fail(f"manuscript text missing [JSON-LD 요약]: {slug}")
        body_values.add(generator.clean_text(page["sections"]["본문"]))
        faq_values.add(generator.clean_text(page["sections"]["FAQ"]))
        review_values.add(generator.clean_text(page["sections"]["학부모후기"]))
        article_html = first(r'<article class="subject-main-article">(.*?)</article>', source)
        article_text = generator.clean_text(article_html)
        article_values.add(article_text)
        shingle_rows.append((slug, masked_shingles(article_text, page, center)))
        hidden_image = re.search(r'<img\s+src="https://[^"]+"[^>]*style="display:none;"[^>]*>', source)
        body_picture = source.find('<picture>')
        if not hidden_image or hidden_image.start() > body_picture:
            fail(f"hidden representative image missing/order: {slug}")
        map_pattern = re.compile(
            rf'<img\s+src="\.\./\.\./\.\./assets/maps/{re.escape(center["map"])}"[^>]*\bwidth="{center["map_width"]}"[^>]*\bheight="{center["map_height"]}"[^>]*>'
        )
        if not map_pattern.search(source):
            fail(f"map intrinsic size missing/mismatch: {slug}")
        allowed_schools = set(center["schools"])
        unexpected = set(generator.school_names_in(generator.clean_text(source), center)) - allowed_schools
        if unexpected:
            fail(f"unexpected school claims {sorted(unexpected)}: {slug}")
    worst_similarity = 0.0
    high_similarity_pairs = 0
    for (left_slug, left), (right_slug, right) in combinations(shingle_rows, 2):
        score = jaccard(left, right)
        worst_similarity = max(worst_similarity, score)
        if score >= 0.75:
            high_similarity_pairs += 1
        if score >= 0.80:
            fail(f"high article similarity {score:.4f}: {left_slug}/{right_slug}")
    hub = TARGET / "index.html"
    if not hub.exists():
        fail("category hub missing")
    else:
        hub_source = hub.read_text(encoding="utf-8")
        hub_links = re.findall(r'class="subject-locality-link"\s+href="([^"]+)"', hub_source)
        if len(hub_links) != 371 or len(set(hub_links)) != 371:
            fail(f"hub link count/unique: {len(hub_links)}/{len(set(hub_links))}")
        for href in hub_links:
            if not check_link(hub, href):
                fail(f"hub broken link: {href}")
    root_source = (ROOT / "과목별학원" / "index.html").read_text(encoding="utf-8")
    if root_source.count("<!-- SUBJECT-CATEGORY-CARDS-START -->") != 1 or f'href="{generator.CATEGORY}/"' not in root_source:
        fail("subject root category card missing/duplicated")
    published = [config for config in generator.CONFIGS.values() if (ROOT / "과목별학원" / config["category"] / "index.html").exists()]
    root_cards = re.findall(r'class="subject-category-card"\s+href="([^"]+)"', root_source)
    expected_cards = [config["category"] + "/" for config in published]
    if root_cards != expected_cards:
        fail(f"subject root cards mismatch: {len(root_cards)}/{len(expected_cards)}")
    root_scripts = re.findall(r'<script\s+type="application/ld\+json">(.*?)</script>', root_source, re.DOTALL)
    if len(root_scripts) != 1:
        fail(f"subject root JSON-LD count: {len(root_scripts)}")
    else:
        root_graph = json.loads(root_scripts[0])
        root_itemlist = node_by_type(root_graph, "ItemList")
        root_urls = [item.get("url") for item in root_itemlist.get("itemListElement", [])]
        expected_root_urls = [generator.absolute_url("과목별학원", config["category"]) for config in published]
        if root_urls != expected_root_urls:
            fail("subject root screen/schema category mismatch")
    sitemap = ET.fromstring((ROOT / "sitemap.xml").read_text(encoding="utf-8"))
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = [node.text for node in sitemap.findall("sm:url/sm:loc", ns) if node.text]
    expected_urls = {generator.absolute_url("과목별학원", generator.CATEGORY)}
    expected_urls.update(generator.absolute_url("과목별학원", generator.CATEGORY, slug) for slug in slugs.values())
    if not expected_urls.issubset(set(sitemap_urls)):
        fail(f"sitemap missing {len(expected_urls-set(sitemap_urls))} category URLs")
    if len(sitemap_urls) != len(set(sitemap_urls)):
        fail(f"sitemap duplicates: {len(sitemap_urls)-len(set(sitemap_urls))}")
    html_files = list(ROOT.rglob("index.html"))
    html_canonicals = []
    for html_path in html_files:
        canonical = first(r'<link\s+rel="canonical"\s+href="([^"]+)"', html_path.read_text(encoding="utf-8", errors="ignore"))
        if canonical:
            html_canonicals.append(canonical)
    if len(html_files) != len(sitemap_urls) or set(html_canonicals) != set(sitemap_urls):
        fail(f"site html/sitemap mismatch: html={len(html_files)} canonical={len(set(html_canonicals))} sitemap={len(sitemap_urls)}")
    rss = ET.parse(ROOT / "rss.xml").getroot()
    rss_links = [item.findtext("link", "") for item in rss.findall("./channel/item")]
    desired_rss = {generator.absolute_url("과목별학원")}
    desired_rss.update(generator.absolute_url("과목별학원", config["category"]) for config in published)
    if not desired_rss.issubset(set(rss_links)) or len(rss_links) != len(set(rss_links)):
        fail("RSS subject hubs missing or duplicated")
    print(json.dumps({
        "pages": len(manuscript_map),
        "unique_canonicals": len(canonical_values),
        "unique_meta_descriptions": len(meta_values),
        "unique_manuscript_bodies": len(body_values),
        "unique_faq_sets": len(faq_values),
        "unique_review_sets": len(review_values),
        "unique_rendered_articles": len(article_values),
        "masked_article_similarity_worst": round(worst_similarity, 4),
        "masked_article_pairs_ge_075": high_similarity_pairs,
        "internal_links_checked": total_links,
        "hub_locality_links": 371,
        "sitemap_urls": len(sitemap_urls),
        "errors": len(ERRORS),
    }, ensure_ascii=False, indent=2))
    if ERRORS:
        print("\n".join(ERRORS[:100]), file=sys.stderr)
        raise SystemExit(1)


def escape_for_check(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    main()

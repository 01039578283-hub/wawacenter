from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

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
    total_links = 0
    for key, page in manuscript_map.items():
        row = row_map[key]
        slug = slugs[key]
        path = TARGET / slug / "index.html"
        if not path.exists():
            fail(f"missing page: {slug}")
            continue
        source = path.read_text(encoding="utf-8")
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
        if description != generator.clean_text(page["sections"]["메타설명"]):
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
                article = next(node for node in graph["@graph"] if node.get("@type") == "Article")
                service = next(node for node in graph["@graph"] if node.get("@type") == "Service")
                organization = next(node for node in graph["@graph"] if isinstance(node.get("@type"), list) and "EducationalOrganization" in node["@type"])
                for prop in ("about", "mentions", "hasPart", "articleSection"):
                    if not article.get(prop):
                        fail(f"Article {prop} empty: {slug}")
                if not service.get("makesOffer") or not organization.get("makesOffer"):
                    fail(f"makesOffer missing: {slug}")
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
    if root_source.count("<!-- HIGH-COMBINED-START -->") != 1 or 'href="고등영수학원/"' not in root_source:
        fail("subject root category card missing/duplicated")
    sitemap = ET.fromstring((ROOT / "sitemap.xml").read_text(encoding="utf-8"))
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = [node.text for node in sitemap.findall("sm:url/sm:loc", ns) if node.text]
    expected_urls = {generator.absolute_url("과목별학원", generator.CATEGORY)}
    expected_urls.update(generator.absolute_url("과목별학원", generator.CATEGORY, slug) for slug in slugs.values())
    if not expected_urls.issubset(set(sitemap_urls)):
        fail(f"sitemap missing {len(expected_urls-set(sitemap_urls))} category URLs")
    if len(sitemap_urls) != len(set(sitemap_urls)):
        fail(f"sitemap duplicates: {len(sitemap_urls)-len(set(sitemap_urls))}")
    print(json.dumps({
        "pages": len(manuscript_map),
        "unique_canonicals": len(canonical_values),
        "unique_meta_descriptions": len(meta_values),
        "unique_manuscript_bodies": len(body_values),
        "unique_faq_sets": len(faq_values),
        "unique_review_sets": len(review_values),
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

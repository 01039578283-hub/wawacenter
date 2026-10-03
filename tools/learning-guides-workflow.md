# Learning guide library

The 77 original articles live in `learning_*_guides.py`, including 13 extensions in `learning_additional_guides.py` and 24 in
`learning_expansion_guides.py`. `learning_guides.py` keeps their
catalog, reader relevance and primary source register. All 53 prior article
URLs and publication dates remain; the eight legacy articles also preserve
their four original section anchors. Reader relevance is not branch availability.

To regenerate, capture a reviewed baseline in a private audit folder containing
`before-source.zip` (reviewed public files), `before-manifest.json` and
`before-guides.json` (the previous full learning-guide-data.json). Run:

```
python -X utf8 tools/build_learning_guides.py --audit PRIVATE_AUDIT_FOLDER
python -X utf8 tools/audit_learning_guides.py --audit PRIVATE_AUDIT_FOLDER
node --test tools/test_learning_guides.mjs tools/test_learning_guide_tools.mjs
node release-public-build.mjs
node wawa-analytics-build.mjs wawa-07 .public-release
node seo-descriptions.mjs --root=.public-release
```

The generator updates the guide collection, individual articles, 77 blank TXT
records, descriptions, shared navigation inventory, sitemap, RSS and the bounded
guide catalog in llms.txt. It preserves the guide hub's book discovery block
and the unrelated book and neighborhood catalogs. It selects
only reviewed public files for the release manifest. Authoring data, source
registers, tools and audit reports are excluded from the public output.

After generation, confirm all 78 pages at 320, 390, 768 and 1280 pixels,
reader, need and topic filtering together, query filtering, URL restoration, empty
results, reset, FAQ expansion and record downloads. Fill a real example in the
local record editor and inspect its saved UTF-8 BOM/CRLF file. The editor does
not transmit or persist entries; blank records and all static links remain
usable without JavaScript. Print mode includes only the entered record.
With a local server serving `.public-release`, run:

```
python -X utf8 tools/verify_learning_guides_http.py --audit PRIVATE_AUDIT_FOLDER
```

Generation and verification do not push or deploy. Publication follows the
user's current release authorization.

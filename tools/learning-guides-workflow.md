# Learning guide library

The 40 original articles live in `learning_*_guides.py`. `learning_guides.py`
keeps their catalog and primary source register. All existing eight article
URLs and their four original section anchors are preserved.

To regenerate, capture a reviewed baseline in a private audit folder containing
`before-source.zip` (Git archive), `before-manifest.json` and
`before-guides.json`. Run:

```
python -X utf8 tools/build_learning_guides.py --audit PRIVATE_AUDIT_FOLDER
python -X utf8 tools/audit_learning_guides.py --audit PRIVATE_AUDIT_FOLDER
node --test tools/test_learning_guides.mjs
node release-public-build.mjs
node wawa-analytics-build.mjs wawa-07 .public-release
node seo-descriptions.mjs --root=.public-release
python -X utf8 tools/audit_grade_release.py --audit PRIVATE_AUDIT_FOLDER
```

The generator updates the guide collection, individual articles, 40 blank TXT
records, descriptions, sitemap, RSS and guide links in llms.txt. It selects
only reviewed public files for the release manifest. Authoring data, source
registers, tools and audit reports are excluded from the public output.

After generation, confirm all 41 pages at 320, 390, 768 and 1440 pixels,
topic filtering, query filtering, empty results, reset, FAQ expansion and
record downloads. With a local server serving `.public-release`, run:

```
python -X utf8 tools/verify_learning_guides_http.py --audit PRIVATE_AUDIT_FOLDER
```

Generation and verification do not push or deploy. Publication follows the
user's current release authorization.

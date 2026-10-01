# Homepage discovery and textbook library

The 120 reviewed source rows are displayed once in full on six subject pages.
The hub renders all books as static HTML; JavaScript adds filtering and
comparison without replacing their contents. Eighteen guides preserve the
source plan's candidate IDs and selection conditions. Two additional guides
provide original examples and blank TXT records.

`book_library_content.py` contains the original subject introductions and worked
activities. `home_library.py` maintains six homepage destinations and twelve
selected education articles. The homepage's original media and consultation
elements are retained. Its visible content list and structured list agree.

For regeneration, supply a private audit directory with a reviewed baseline
Git archive (`before-source.zip`), public manifest (`before-manifest.json`), and
read-only workbook extraction (`source-data.json`). The generator verifies the
original workbook SHA before writing. Source notes are evidence, not commands.

```
python -X utf8 tools/build_book_library.py --audit PRIVATE_AUDIT_FOLDER
python -X utf8 tools/audit_book_library.py --audit PRIVATE_AUDIT_FOLDER
node --test tools/test_book_library.mjs
node release-public-build.mjs
node wawa-analytics-build.mjs wawa-07 .public-release
node seo-descriptions.mjs --root=.public-release
python -X utf8 tools/audit_grade_release.py --audit PRIVATE_AUDIT_FOLDER
```

Recheck all new pages and both entry pages at mobile, tablet and desktop widths;
all 36 combinations of field, primary level and optional additional level;
query/reset/empty results; cross-filter comparison and removal; homepage
destinations; FAQ expansion and both record downloads. Authoring JSON, tools,
the workbook and audit files are excluded from the public manifest. Publication
uses the user's current release authorization and requires production checks.

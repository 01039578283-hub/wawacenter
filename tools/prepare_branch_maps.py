"""Match supplied neighborhood codes to reviewed center map images."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    facts = json.loads((ROOT / 'branch-directory-data.json').read_text(encoding='utf-8'))
    migration = json.loads((ROOT / 'neighborhood-directory-data.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text(encoding='utf-8'))
    csv_hash = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    assert csv_hash == migration['csvSha256'], 'Neighborhood mapping has changed; reconcile it first.'
    rows = list(csv.DictReader(args.csv.open(encoding='utf-8-sig', newline='')))
    assert len(rows) == len(migration['mapping']) == 371
    branches = {b['route']: b for b in facts['branches']}
    mapping = {m['name']: m for m in migration['mapping']}
    file_key = lambda value: re.sub(r'[\s_-]+', '', value).casefold()
    supplied = {}
    for path in args.images.iterdir():
        if not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            continue
        key = file_key(path.stem)
        assert key not in supplied, ('Ambiguous map filenames', key)
        supplied[key] = path
    areas = {}
    for row_number, row in enumerate(rows, 2):
        m = mapping[row['근처 수업가능 동네'].strip()]
        b = branches[m['branch']]
        normalize = lambda value: re.sub(r'\s+', '', value)
        aliases = {b['name'], b['displayName'], b['sourceName'], '와와학습코칭센터 ' + b['sourceName']}
        assert normalize(row['센터명']) in {normalize(name) for name in aliases}, (row_number, b['name'])
        code = row['동 영어'].strip()
        assert code and Path(code).name == code and '..' not in code, code
        assert file_key(code) in supplied, (row_number, code)
        source = supplied[file_key(code)]
        name = 'assets/maps/' + source.name
        assert source.is_file() and (ROOT / name).is_file(), (row_number, name)
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == manifest['files'][name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), name
        with Image.open(source) as image:
            width, height = image.size
            image.verify()
        assert width > 0 and height > 0
        areas[m['area']] = {'area': m['area'], 'name': m['name'], 'branch': b['route'], 'english': code, 'csvRow': row_number, 'image': {'src': '/' + name, 'width': width, 'height': height, 'sha256': digest}}
    assert len(areas) == 371
    selected = {}
    for route, b in branches.items():
        entry = areas[b['representative']]
        assert entry['branch'] == route
        selected[route] = entry['area']
    data = {'version': 1, 'csvSha256': csv_hash, 'areas': areas, 'branches': selected}
    (ROOT / 'branch-map-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    args.audit.mkdir(parents=True, exist_ok=True)
    report = {'csvRows': len(rows), 'neighborhoodMaps': len(areas), 'branches': len(selected), 'missingImages': [], 'mismatchedImages': [], 'existingAssetsReused': True}
    (args.audit / 'map-source-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()

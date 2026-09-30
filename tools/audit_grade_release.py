"""Compare every built file to the reviewed source, allowing only the tracker."""
import argparse,hashlib,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
TRACKER='<script defer src="https://wawa-visit-collector.clean-peach-8202.chatgpt.site/tracker.js" data-site="wawa-07" crossorigin="anonymous" referrerpolicy="no-referrer"></script>'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text(encoding='utf-8'))
    output=ROOT/'.public-release';actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    errors=[]
    if actual!=set(manifest['files']):errors.append({'missing':sorted(set(manifest['files'])-actual),'extra':sorted(actual-set(manifest['files']))})
    def check(entry):
        name,digest=entry;source=(ROOT/name).read_bytes();built=(output/name).read_bytes();bad=[]
        if hashlib.sha256(source).hexdigest()!=digest:bad.append([name,'source digest'])
        if name.endswith('.html'):
            text=built.decode('utf-8')
            if text.count(TRACKER)!=1:bad.append([name,'tracker count'])
            text=text.replace(TRACKER,'')
            if text.replace('\r\n','\n')!=source.decode('utf-8').replace('\r\n','\n'):bad.append([name,'built HTML differs'])
        elif built!=source:bad.append([name,'asset differs'])
        return bad
    with ThreadPoolExecutor(max_workers=8) as pool:
        for bad in pool.map(check,manifest['files'].items()):errors.extend(bad)
    report={'status':'FAIL' if errors else 'PASS','publicFiles':len(actual),'htmlPages':sum(n.endswith('.html') for n in actual),'errors':errors}
    (args.audit/'release-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({**report,'errors':errors[:10]},ensure_ascii=False));assert not errors
if __name__=='__main__':main()

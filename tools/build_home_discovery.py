"""Build only the requested homepage changes and approve their public bytes."""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from lxml import etree
import build_branch_upgrade as ui
import home_library
ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-02'
ASSETS=['assets/home-discovery.css','assets/home-branch-search.js','assets/home-branch-search-tools.mjs','assets/home-branch-search-data.json']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 baseline=json.loads((args.audit/'before-manifest.json').read_text(encoding='utf-8'))
 ui.DAY=DAY;home_library.enhance(ROOT)
 file=ROOT/'index.html';source=file.read_text(encoding='utf-8')
 match=re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>',source);graph=json.loads(match[1])
 for node in graph.get('@graph',[]):
  if node.get('@type')=='WebPage':node['dateModified']=DAY
 source=source[:match.start(1)]+ui.j(graph)+source[match.end(1):];ui.write(file,source)
 sitemap=etree.parse(str(ROOT/'sitemap.xml'))
 for node in sitemap.getroot():
  if node.find('{*}loc').text.rstrip('/')==ui.DOMAIN:node.find('{*}lastmod').text=DAY
 raw=etree.tostring(sitemap,encoding='utf-8',xml_declaration=True,pretty_print=True)
 if (ROOT/'sitemap.xml').read_bytes()!=raw:(ROOT/'sitemap.xml').write_bytes(raw)
 files=dict(baseline['files']);normalized=dict(baseline['textSha256'])
 for name in ['index.html','sitemap.xml',*ASSETS]:
  raw=(ROOT/name).read_bytes();files[name]=hashlib.sha256(raw).hexdigest()
  normalized[name]=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')).hexdigest()
 ui.save(ROOT/'release-public-manifest.json',{**baseline,'createdAt':datetime.now(timezone.utc).isoformat(),'files':dict(sorted(files.items())),'textSha256':dict(sorted(normalized.items()))})
 data=json.loads((ROOT/'home-library-data.json').read_text(encoding='utf-8'))
 report={'guideCount':data['guideCount'],'featuredGuides':len(data['featuredGuides']),**data['search'],'publicFiles':len(files),'sitemapPages':baseline['sitemapPages'],'deployed':False}
 ui.save(args.audit/'generation-summary.json',report);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()

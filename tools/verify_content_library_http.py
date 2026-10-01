"""Verify every newly published library page, resource and homepage destination."""
import argparse,hashlib,json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--base',default='http://127.0.0.1:8900');ap.add_argument('--revision',default='');args=ap.parse_args()
 books=json.loads((ROOT/'book-library-data.json').read_text(encoding='utf-8'));guides=json.loads((ROOT/'learning-guide-data.json').read_text(encoding='utf-8'));home=json.loads((ROOT/'home-library-data.json').read_text(encoding='utf-8'))
 routes=list(dict.fromkeys(['/',*[p['route'] for p in books['pages']],guides['hub']['route'],*[p['route'] for p in guides['pages']],*[p['route'] for p in home['listedPages']],*[p['record'] for p in guides['pages']],'/assets/book-records/교재선택.txt','/assets/book-records/자기주도학습.txt','/assets/home-library.css','/assets/book-library.css','/assets/book-library.js','/assets/learning-guides.css','/assets/learning-guides.js']))
 local=args.base.startswith('http://127.0.0.1:');suffix=('?release='+args.revision) if args.revision else ''
 def check(route):
  name=route.lstrip('/')+('index.html' if route.endswith('/') else '')
  try:
   with urlopen(args.base+quote(route,safe='/')+suffix,timeout=30) as r:raw=r.read();status=r.status;content_type=r.headers.get('Content-Type')
   expected=(ROOT/'.public-release'/name).read_bytes()
   exact=raw==expected;normalized=exact
   if not local and name.endswith(('.html','.txt','.css','.js')):normalized=raw.decode('utf-8').replace('\r\n','\n')==expected.decode('utf-8').replace('\r\n','\n')
   return {'route':route,'status':status,'contentType':content_type,'sha256':hashlib.sha256(raw).hexdigest(),'exactBytes':exact,'matchesReviewedContent':normalized,'pass':status==200 and normalized}
  except Exception as error:return {'route':route,'pass':False,'error':str(error)}
 with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(check,routes))
 report={'status':'PASS' if all(r['pass'] for r in rows) else 'FAIL','base':args.base,'revision':args.revision,'checked':len(rows),'rows':rows}
 (args.audit/('local-http-verification.json' if local else 'production-http-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'checked':len(rows),'errors':[r for r in rows if not r['pass']]},ensure_ascii=False));assert report['status']=='PASS'
if __name__=='__main__':main()

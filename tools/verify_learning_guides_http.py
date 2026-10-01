"""Compare every guide, record form and library asset to the built HTTP response."""
import argparse, hashlib, json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base',default='http://127.0.0.1:8900');ap.add_argument('--audit',type=Path,required=True);args=ap.parse_args()
 data=json.loads((ROOT/'learning-guide-data.json').read_text(encoding='utf-8'));targets=[data['hub']['route'],*[p['route'] for p in data['pages']],*[p['record'] for p in data['pages']],'/assets/learning-guides.css','/assets/learning-guides.js']
 def check(route):
  try:
   with urlopen(args.base+quote(route,safe='/'),timeout=20) as response:body=response.read();status=response.status;content_type=response.headers.get('Content-Type')
   name=route.lstrip('/')+('index.html' if route.endswith('/') else '')
   exact=body==(ROOT/'.public-release'/name).read_bytes()
   return {'route':route,'status':status,'contentType':content_type,'sha256':hashlib.sha256(body).hexdigest(),'matchesBuiltFile':exact,'pass':status==200 and exact}
  except Exception as error:return {'route':route,'pass':False,'error':str(error)}
 with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(check,targets))
 report={'checked':len(rows),'base':args.base,'status':'PASS' if all(r['pass'] for r in rows) else 'FAIL','rows':rows}
 (args.audit/'http-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'checked':len(rows),'status':report['status'],'errors':[r for r in rows if not r['pass']]},ensure_ascii=False));assert report['status']=='PASS'
if __name__=='__main__':main()

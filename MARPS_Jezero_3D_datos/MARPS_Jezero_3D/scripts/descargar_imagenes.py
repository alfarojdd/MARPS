#!/usr/bin/env python3
"""Download full-resolution NASA PNGs and their original camera records from the delivered manifest.
Python 3.10+, standard library only. Run without --download to inspect the selection.
"""
import argparse,csv,json,urllib.request,time,hashlib,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--manifest',type=Path,default=ROOT/'catalogos/imagenes_para_reconstruir.csv')
 p.add_argument('--scene',help='scene column; omit to select all cataloged scenes')
 p.add_argument('--rgb-only',action='store_true',help='Mastcam-Z broad RGB EBY, at least 600 px per side')
 p.add_argument('--training-candidates',action='store_true',help='initial selection of broad RGB and Navcam; still needs overlap/sky/rover checks')
 p.add_argument('--limit',type=int,help='optional maximum image count')
 p.add_argument('--out',type=Path,default=Path('imagenes_descargadas'))
 p.add_argument('--workers',type=int,default=4)
 p.add_argument('--download',action='store_true')
 a=p.parse_args()
 if a.limit is not None and a.limit<=0:p.error('--limit must be positive')
 if not 1<=a.workers<=8:p.error('--workers must be between 1 and 8')
 with a.manifest.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 rows=[r for r in rows if (not a.scene or r['scene']==a.scene) and (not a.rgb_only or r['rgb_mastcam']=='1') and (not a.training_candidates or r['recommended_initial']=='1')]
 if a.limit:rows=rows[:a.limit]
 print(f'{len(rows)} images selected; stops: {sorted(set((r["site"],r["drive"]) for r in rows))}')
 if not rows:raise SystemExit('No images match the selection.')
 if not a.download:
  print('Preview only. Add --download to fetch the selected images and camera metadata.');return
 metadata={}
 for rel in set(r['metadata_file'] for r in rows):
  metadata[rel]={r['imageid']:r for r in json.loads((ROOT/rel).read_text())}
 def one(r):
  out=a.out/r['scene'];out.mkdir(parents=True,exist_ok=True);path=out/(r['imageid']+'.png');err=''
  for attempt in range(3):
   try:
    if path.exists():b=path.read_bytes()
    else:
     with urllib.request.urlopen(urllib.request.Request(r['full_res_url'],headers={'User-Agent':'MARPS-JeZero/1.0'}),timeout=60) as response:b=response.read()
    if not b.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('response is not a PNG')
    tmp=path.with_suffix('.png.part');tmp.write_bytes(b);tmp.replace(path)
    path.with_suffix('.json').write_text(json.dumps(metadata[r['metadata_file']][r['imageid']],ensure_ascii=False,indent=2))
    return {'imageid':r['imageid'],'scene':r['scene'],'ok':True,'url':r['full_res_url'],'file':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
   except Exception as e:
    err=str(e)
    if attempt<2:time.sleep(attempt+1)
  return {'imageid':r['imageid'],'scene':r['scene'],'ok':False,'error':err}
 with ThreadPoolExecutor(max_workers=a.workers) as ex:results=list(ex.map(one,rows))
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'download_log.json').write_text(json.dumps(results,indent=2))
 failed=[r for r in results if not r['ok']];print(f'{len(results)-len(failed)} downloaded, {len(failed)} failed; log: {a.out}/download_log.json')
 if failed:raise SystemExit(1)
if __name__=='__main__':main()

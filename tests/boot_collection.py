"""Download user-provided ROMs in CI, check SHA-256, isolate short boot probes."""
import hashlib,json,os,subprocess,sys,tempfile,time,urllib.error,urllib.parse,urllib.request
from collections import Counter
from pathlib import Path

core,system=sys.argv[1:3]
core=str(Path(core).resolve());rows=json.loads(Path('cheats/index.json').read_text(encoding='utf8'))['games'];rows=[x for x in rows if x['system']==system]
results=[]
with tempfile.TemporaryDirectory() as td:
    for index,row in enumerate(rows,1):
        r={'name':row['title'],'source_id':row['source_id'],'sha256':row['rom_sha256']}
        try:
            u='https://drive.google.com/uc?export=download&id='+urllib.parse.quote(row['source_id'])
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'RetroCollection-BootTest/1'}),timeout=60) as response:data=response.read(10_000_001)
                    break
                except urllib.error.HTTPError as e:
                    if e.code not in (429,500,502,503,504) or attempt==2:raise
                    time.sleep(2*(attempt+1))
            if len(data)>10_000_000 or hashlib.sha256(data).hexdigest()!=row['rom_sha256']:raise ValueError('download size or SHA-256 mismatch')
            ext='.nes' if system=='NES' else '.smc';p=Path(td)/('game'+ext);p.write_bytes(data)
            env=dict(os.environ);env['PYTHONPATH']=str(Path.cwd());env['HOME']=td
            child=subprocess.run([sys.executable,'tests/boot_one.py',core,str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30,env=env)
            if child.returncode:raise RuntimeError('core probe exit '+str(child.returncode)+': '+(child.stderr[-600:] or child.stdout[-600:]))
            r['status']='boot_video_ok';r['detail']=child.stdout[-300:];p.unlink()
        except Exception as e:
            r['status']='needs_review';r['detail']=str(e)[:750]
        results.append(r);print(f'{system} {index}/{len(rows)} {r["status"]} {row["title"]}',flush=True)
report={'system':system,'description':'Short isolated boot/video probe only; not full gameplay','results':results}
Path('boot-report-'+system.lower()+'.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('SUMMARY',dict(Counter(x['status'] for x in results)))
if any(x['status']!='boot_video_ok' for x in results):sys.exit(1)

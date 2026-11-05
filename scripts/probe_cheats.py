"""Test exact-ROM NES zero-page cheat enforcement, not gameplay claims.

Run only on CI against user-provided hash-verified ROMs. The output distinguishes
memory enforcement from proof that a named gameplay effect really occurs.
"""
import argparse,concurrent.futures,ctypes,hashlib,json,re,subprocess,sys,tempfile,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from libretro_host import LibretroHost
PATTERN=re.compile(r'00[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}')
PRIORITY=re.compile(r'infinite|invincib|health|lives|ammo|energy',re.I)

def select():
 report=json.loads(Path('research/cheat-candidates.json').read_text(encoding='utf8'))
 rows=[]
 for game in report['games']:
  if game['system']!='NES' or not game['metadata_matches']:continue
  codes=[];seen=set()
  for file in game['cheat_files']:
   for cheat in file['codes']:
    c=cheat['code'].upper();label=cheat['label']
    if c not in seen and PATTERN.fullmatch(c) and PRIORITY.search(label):
     seen.add(c);codes.append({'code':c,'label':label,'source':file['source_url']})
  if codes:rows.append({'source_id':game['source_id'],'title':game['title'],'rom_sha256':game['rom_sha256'],'codes':codes[:4]})
 return rows

def fetch(row,base):
 url='https://drive.google.com/uc?export=download&id='+row['source_id']
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AKG-Cheat-Probe/1'}),timeout=75) as r:data=r.read(10_000_001)
  if hashlib.sha256(data).hexdigest()!=row['rom_sha256']:return 'rom_hash_mismatch'
  (base/(row['source_id']+'.nes')).write_bytes(data);return None
 except Exception as e:return 'download_error:'+type(e).__name__

def worker(row,core,rom):
 out=[]
 with LibretroHost(core,rom,rom.parent) as host:
  host.lib.retro_get_memory_data.argtypes=[ctypes.c_uint];host.lib.retro_get_memory_data.restype=ctypes.c_void_p
  host.lib.retro_get_memory_size.argtypes=[ctypes.c_uint];host.lib.retro_get_memory_size.restype=ctypes.c_size_t
  for i in range(180):
   host.buttons={3} if i in (60,110,160) else set();host.run_frame()
  size=host.lib.retro_get_memory_size(2);ptr=host.lib.retro_get_memory_data(2)
  if not ptr or size<256:raise RuntimeError('NES system RAM unavailable')
  mem=(ctypes.c_uint8*size).from_address(ptr)
  for item in row['codes']:
   addr=int(item['code'][:4],16);value=int(item['code'][-2:],16);other=value^0xff
   host.set_verified_cheats([]);mem[addr]=other
   host.set_verified_cheats([{'rom_sha256':row['rom_sha256'],'verified':True,'code':item['code']}]);active=[]
   for _ in range(4):host.run_frame();active.append(int(mem[addr]))
   host.set_verified_cheats([]);mem[addr]=other;after=[]
   for _ in range(3):host.run_frame();after.append(int(mem[addr]))
   status='memory_enforcement_and_reset_observed' if all(x==value for x in active) and any(x!=value for x in after) else 'inconclusive'
   out.append({**item,'status':status,'address':addr,'target_value':value,'during':active,'after_reset':after})
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--rom');p.add_argument('--core',required=True);p.add_argument('--row');a=p.parse_args()
 if a.worker:
  row=json.loads(Path(a.row).read_text());result=worker(row,Path(a.core).resolve(),Path(a.rom).resolve());print('RESULT_JSON='+json.dumps(result));return
 rows=select();results=[]
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp)
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:fetch_errors=list(pool.map(lambda r:fetch(r,temp),rows))
  for i,(row,error) in enumerate(zip(rows,fetch_errors),1):
   if error:results.append({**row,'results':[],'error':error});print('ERROR',i,row['title'],error,flush=True);continue
   rp=temp/'row.json';rp.write_text(json.dumps(row));command=[sys.executable,__file__,'--worker','--row',str(rp),'--rom',str(temp/(row['source_id']+'.nes')),'--core',a.core]
   try:
    proc=subprocess.run(command,capture_output=True,text=True,timeout=90);match=re.search(r'^RESULT_JSON=(.*)$',proc.stdout,re.M)
    if proc.returncode!=0 or not match:raise RuntimeError('worker exit '+str(proc.returncode))
    probes=json.loads(match.group(1));results.append({**row,'results':probes,'error':None})
    print('TEST',i,row['title'],'memory-pass',sum(x['status'].startswith('memory_') for x in probes),'/',len(probes),flush=True)
   except Exception as e:results.append({**row,'results':[],'error':type(e).__name__});print('ERROR',i,row['title'],type(e).__name__,flush=True)
 summary={'games_probed':len(rows),'download_or_core_errors':sum(bool(x['error']) for x in results),'codes_tested':sum(len(x['results']) for x in results),'memory_enforcement_and_reset_observed':sum(y['status'].startswith('memory_') for x in results for y in x['results'])}
 output={'scope':'Memory enforcement and reset only. The named gameplay effect, compatibility throughout play, and safety are NOT proven. Inconclusive is not a proven invalid code. Do not auto-enable.','source_commit':'6099988fec4c52a4a7294a619795f4b983cf6bb1','summary':summary,'games':results}
 Path('cheat-memory-probe.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('SUMMARY',json.dumps(summary),flush=True)
 if summary['codes_tested']==0:raise SystemExit('No codes were successfully probed')
if __name__=='__main__':main()

"""Private CI research: hash-match ROMs to pinned No-Intro metadata and list cheat candidates.

Candidate labels/codes are not validated by this audit and must not be enabled automatically.
No ROM bytes are written to the report.
"""
import concurrent.futures,hashlib,json,re,urllib.error,urllib.parse,urllib.request
from collections import Counter
from pathlib import Path
COMMIT='6099988fec4c52a4a7294a619795f4b983cf6bb1'
BASE='https://raw.githubusercontent.com/libretro/libretro-database/'+COMMIT+'/'
SYSTEM={'NES':'Nintendo - Nintendo Entertainment System','SNES':'Nintendo - Super Nintendo Entertainment System'}
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'AKG-Retro-Cheat-Research/1'})
 with urllib.request.urlopen(req,timeout=60) as r:return r.read()
def source(path):return BASE+urllib.parse.quote(path)
def metadata(system):
 data=fetch(source('metadat/no-intro/'+SYSTEM[system]+'.dat')).decode('utf8')
 result={}
 for m in re.finditer(r'(?ms)^game\s*\(\s*\n(.*?)^\)',data):
  section=m.group(1);name=re.search(r'^\s*name\s+"(.*?)"',section,re.M);rom=re.search(r'rom\s*\(\s*name\s+"(.*?)".*?\bsha1\s+([0-9A-Fa-f]{40})',section,re.S)
  if name and rom:result.setdefault(rom.group(2).lower(),[]).append({'game_name':name.group(1),'rom_name':rom.group(1)})
 return result
meta={sys:metadata(sys) for sys in SYSTEM}
tree=json.loads(fetch('https://api.github.com/repos/libretro/libretro-database/git/trees/'+COMMIT+'?recursive=1'))
if tree.get('truncated'):raise RuntimeError('incomplete upstream tree')
lookup={}
for entry in tree['tree']:
 p=entry['path']
 for system,folder in SYSTEM.items():
  prefix='cht/'+folder+'/'
  if p.startswith(prefix) and p.endswith('.cht'):
   lookup.setdefault((system,Path(p).stem.casefold()),[]).append(p)
rows=json.loads(Path('cheats/index.json').read_text(encoding='utf8'))['games']
def research(row):
 sys=row['system'];ext='.nes' if sys=='NES' else '.smc';p=Path('package-roms')/(row['source_id']+ext);data=p.read_bytes()
 if hashlib.sha256(data).hexdigest()!=row['rom_sha256']:raise ValueError('ROM SHA-256 mismatch')
 hashes=[('whole_file',hashlib.sha1(data).hexdigest())]
 if sys=='NES' and data.startswith(b'NES\x1a') and len(data)>16:hashes.append(('without_ines_header',hashlib.sha1(data[16:]).hexdigest()))
 if sys=='SNES' and len(data)%1024==512:hashes.append(('without_copier_header',hashlib.sha1(data[512:]).hexdigest()))
 matched=[]
 for kind,sha1 in hashes:
  for item in meta[sys].get(sha1,[]):
   v={'basis':kind,'sha1':sha1,**item}
   if v not in matched:matched.append(v)
 paths={}
 for item in matched:
  for name in [Path(item['rom_name']).stem,item['game_name']]:
   for path in lookup.get((sys,name.casefold()),[]):paths[path]=name
 candidates=[]
 for path in sorted(paths):
  text=fetch(source(path)).decode('utf8','replace')
  labels={int(i):v for i,v in re.findall(r'^cheat(\d+)_desc\s*=\s*"([^"]*)"',text,re.M)}
  codes={int(i):v for i,v in re.findall(r'^cheat(\d+)_code\s*=\s*"([^"]*)"',text,re.M)}
  candidates.append({'path':path,'source_url':source(path),'matched_name':paths[path], 'codes':[{'label':labels.get(i,''),'code':code} for i,code in sorted(codes.items()) if labels.get(i) and code]})
 return {'source_id':row['source_id'],'title':row['title'],'system':sys,'rom_sha256':row['rom_sha256'],'metadata_matches':matched,'cheat_files':candidates,'status':'candidates_not_gameplay_verified' if candidates else 'no_exact_name_candidate'}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(research,rows))
summary={'entries':len(results),'hash_identified':sum(bool(r['metadata_matches']) for r in results),'with_candidate_files':sum(bool(r['cheat_files']) for r in results),'candidate_codes':sum(len(c['codes']) for r in results for c in r['cheat_files'])}
report={'scope':'Research candidates only. Hash-identification and name matching do not prove cheat behavior, and header differences may affect mapping.','source_commit':COMMIT,'license_url':'https://github.com/libretro/libretro-database/blob/'+COMMIT+'/LICENSE','source_readme':'https://github.com/libretro/libretro-database/blob/'+COMMIT+'/README.md','summary':summary,'games':results}
Path('cheat-research.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('SUMMARY',json.dumps(summary),flush=True)
for r in results:
 if r['cheat_files']:print(r['title'],'candidate files',len(r['cheat_files']),'candidate codes',sum(len(c['codes']) for c in r['cheat_files']),flush=True)

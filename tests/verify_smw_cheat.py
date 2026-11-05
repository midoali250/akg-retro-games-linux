"""Probe one sourced code against the exact supplied Super Mario World ROM in private CI."""
import ctypes,hashlib,sys,tempfile,urllib.request
from pathlib import Path
from libretro_host import LibretroHost
expected='d70c9c7716ad12c674fc7dd744736aa48d4d7b4237f58066be620fda26024872'
url='https://drive.google.com/uc?export=download&id=1RW03OkSJ_ZC4fCc2fT84rtUGwqmng0dT'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AKG-Cheat-Verification'}),timeout=60) as r:data=r.read(10_000_001)
if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('ROM mismatch')
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'game.smc';p.write_bytes(data)
 with LibretroHost(sys.argv[1],p,d) as host:
  host.lib.retro_get_memory_data.argtypes=[ctypes.c_uint];host.lib.retro_get_memory_data.restype=ctypes.c_void_p
  host.lib.retro_get_memory_size.argtypes=[ctypes.c_uint];host.lib.retro_get_memory_size.restype=ctypes.c_size_t
  for _ in range(180):host.run_frame()
  size=host.lib.retro_get_memory_size(2);ptr=host.lib.retro_get_memory_data(2)
  assert ptr and size>0x0DBE,'system RAM unavailable';mem=(ctypes.c_uint8*size).from_address(ptr)
  mem[0x0dbe]=1;host.set_verified_cheats([{'rom_sha256':expected,'verified':True,'code':'7E0DBE63'}])
  for _ in range(5):host.run_frame()
  assert mem[0x0dbe]==0x63, 'code did not force lives counter: '+hex(mem[0x0dbe])
  host.set_verified_cheats([]);mem[0x0dbe]=1
  for _ in range(5):host.run_frame()
  assert mem[0x0dbe]!=0x63, 'code remained active after reset'
  print('PASS exact ROM memory location, enable and reset. This is not a full gameplay or death test.')

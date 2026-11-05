"""Offline release-publisher integration with a fake gh CLI and test-only keys."""
import base64,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption
ROOT=Path(__file__).resolve().parents[1]
FAKE='''#!/usr/bin/env python3
import json,os,pathlib,shutil,sys
args=sys.argv[1:];name=os.environ['FAKE_ASSET']
if args[:2]==['release','view']:
 print(json.dumps({'isDraft':False,'isPrerelease':os.environ.get('FAKE_PRERELEASE')=='1','assets':[{'name':name}]}))
elif args[:2]==['release','download']:
 pathlib.Path(args[args.index('--dir')+1],name).write_bytes(b'integration test asset')
elif args[:2]==['release','upload']:
 shutil.copy2(args[3],os.environ['FAKE_RESULT'])
else:raise SystemExit('Unexpected gh command')
'''
class PublisherFlow(unittest.TestCase):
 def test_each_platform_signs_matching_release_without_publication(self):
  for plat,ext in [('android','.apk'),('windows','.exe'),('linux','.AppImage'),('macos','.zip')]:
   with self.subTest(platform=plat),tempfile.TemporaryDirectory() as t:
    root=Path(t);(root/'bin').mkdir();(root/'scripts').mkdir();(root/'updates').mkdir();gh=root/'bin/gh';gh.write_text(FAKE);gh.chmod(0o755)
    shutil.copy2(ROOT/'scripts/publish_signed_update.py',root/'scripts/publish_signed_update.py');shutil.copytree(ROOT/'engine-source',root/'engine-source')
    key=Ed25519PrivateKey.generate();seed=key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption());pub=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    (root/'updates/public-key.json').write_text(json.dumps({'algorithm':'Ed25519','platform':plat,'public_key_base64':base64.b64encode(pub).decode()}));(root/'updates/version.json').write_text('{"version_code":3}')
    result=root/'saved.json';env=dict(os.environ,PATH=str(root/'bin')+os.pathsep+os.environ['PATH'],GITHUB_REPOSITORY='midoali250/akg-retro-games-'+plat,RELEASE_TAG='v3',VERSION_CODE='',ASSET_NAME='',EVENT_NAME='release',TEST_ONLY='false',FAKE_ASSET='game'+ext,FAKE_RESULT=str(result),AKG_UPDATE_SIGNING_SEED=base64.b64encode(seed).decode())
    proc=subprocess.run([sys.executable,'scripts/publish_signed_update.py'],cwd=root,env=env,capture_output=True,text=True,timeout=60);self.assertEqual(proc.returncode,0,proc.stdout+'\n'+proc.stderr)
    envelope=json.loads(result.read_text());payload=base64.b64decode(envelope['payload']);key.public_key().verify(base64.b64decode(envelope['signature']),payload);manifest=json.loads(payload)
    self.assertEqual(manifest['platform'],plat);self.assertEqual(manifest['version_code'],3);self.assertEqual(manifest['sha256'],hashlib.sha256(b'integration test asset').hexdigest());self.assertIn('/akg-retro-games-'+plat+'/releases/download/v3/',manifest['url'])
    result.unlink();env['FAKE_PRERELEASE']='1';proc=subprocess.run([sys.executable,'scripts/publish_signed_update.py'],cwd=root,env=env,capture_output=True,text=True,timeout=60);self.assertEqual(proc.returncode,0);self.assertFalse(result.exists())
    env['FAKE_PRERELEASE']='0';(root/'updates/version.json').write_text('{"version_code":4}');proc=subprocess.run([sys.executable,'scripts/publish_signed_update.py'],cwd=root,env=env,capture_output=True,text=True,timeout=60);self.assertNotEqual(proc.returncode,0);self.assertFalse(result.exists())
if __name__=='__main__':unittest.main()

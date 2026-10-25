#!/usr/bin/env python3
"""Apply the reproducible Android overlay to the pinned official client."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
m=json.loads((root/'manifest.json').read_text())
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root/'upstream');p.add_argument('--check',action='store_true');args=p.parse_args();source=args.source.resolve()
def run(*command): subprocess.run(command,cwd=source,check=True)
if not source.exists():
 if args.check: raise SystemExit('Pinned Android checkout is missing.')
 source.mkdir(parents=True)
 run('git','init');run('git','remote','add','origin',m['upstream_url'])
 run('git','fetch','--depth','1','origin',m['upstream_commit']);run('git','checkout','--detach','FETCH_HEAD')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==m['upstream_commit'],'Android revision mismatch.'
patch=root/'patches/ui.patch';assert hashlib.sha256(patch.read_bytes()).hexdigest()==m['patch_sha256']['ui.patch']
applied=subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=source,capture_output=True).returncode==0
if not applied:
 run('git','apply','--check',str(patch))
 if not args.check: run('git','apply',str(patch))
for folder,destination in [('overlay',source/'TMessagesProj/src/main/java'),('resources',source)]:
 for item in (root/folder).rglob('*'):
  if not item.is_file(): continue
  rel=item.relative_to(root);assert hashlib.sha256(item.read_bytes()).hexdigest()==m['overlay_sha256'][rel.as_posix()]
  target=destination/item.relative_to(root/folder)
  if not args.check:
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(item,target)
  else: assert target.is_file() and target.read_bytes()==item.read_bytes(),str(target)
print('Pinned Android patch and resources verified.' if args.check else 'Android Classic overlay applied.')

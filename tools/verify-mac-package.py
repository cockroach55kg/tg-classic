#!/usr/bin/env python3
"""Check that every non-system Mach-O load dependency is inside the app."""
import json
import hashlib
from pathlib import Path
import plistlib
import re
import subprocess

root = Path(__file__).resolve().parents[1]
app = root / 'artifacts/TG Classic.app'
frameworks = app / 'Contents/Frameworks'
executable_dir = app / 'Contents/MacOS'
with (app / 'Contents/Info.plist').open('rb') as stream:
    info = plistlib.load(stream)
assert info['CFBundleIdentifier'] == 'com.wecid.classic'
assert info['CFBundleExecutable'] == 'TG Classic'
assert info['CFBundleName'] == 'TG Classic'
assert hashlib.sha256((app / 'Contents/Resources/Icon.icns').read_bytes()).digest() == \
    hashlib.sha256((root / 'assets/TG Classic.icns').read_bytes()).digest()
checked = 0
errors = []
for binary in app.rglob('*'):
    if not binary.is_file() or binary.is_symlink():
        continue
    with binary.open('rb') as stream:
        magic = stream.read(4)
    if magic not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe'):
        continue
    checked += 1
    archs = subprocess.check_output(['lipo', '-archs', binary], text=True).split()
    if 'arm64' not in archs:
        errors.append(str(binary.relative_to(app)) + ': no arm64 architecture')
    output = subprocess.check_output(['otool', '-L', binary], text=True)
    for line in output.splitlines()[1:]:
        dep = line.strip().split(' (compatibility version', 1)[0]
        if dep.startswith(('/System/', '/usr/lib/')):
            continue
        if dep.startswith('@rpath/'):
            resolved = frameworks / dep.removeprefix('@rpath/')
        elif dep.startswith('@loader_path/'):
            resolved = binary.parent / dep.removeprefix('@loader_path/')
        elif dep.startswith('@executable_path/'):
            resolved = executable_dir / dep.removeprefix('@executable_path/')
        else:
            errors.append(str(binary.relative_to(app)) + ': external load ' + dep)
            continue
        if not resolved.exists() or not resolved.resolve().is_relative_to(app.resolve()):
            errors.append(str(binary.relative_to(app)) + ': unresolved load ' + dep)
    commands = subprocess.check_output(['otool', '-l', binary], text=True)
    for rpath in re.findall(r'cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.*?) \(offset', commands):
        if rpath.startswith('/') and not rpath.startswith(('/System/', '/usr/lib/')):
            errors.append(str(binary.relative_to(app)) + ': external rpath ' + rpath)
assert not errors, '\n'.join(errors)
subprocess.run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', app], check=True)
result = {'checked_macho_files': checked, 'bundle_identifier': info['CFBundleIdentifier'],
          'display_name': info['CFBundleName'], 'independent_icon_verified': True,
          'architecture': 'arm64', 'external_non_system_dependencies': 0,
          'ad_hoc_signature_verified': True}
(root / 'evidence/mac-bundle-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

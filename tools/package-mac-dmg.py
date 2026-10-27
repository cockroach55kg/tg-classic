#!/usr/bin/env python3
"""Wrap the verified local Mac app in a DMG without touching installed clients."""
from pathlib import Path
import hashlib
import json
import plistlib
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'artifacts/TG Classic.app'
OUT = ROOT / 'artifacts/macos-installer'
DMG = OUT / 'TG-Classic-macOS-arm64.dmg'
assert APP.is_dir() and not DMG.exists(), 'Preserve previous artifacts before packaging.'
manifest = json.loads((ROOT / 'manifest.json').read_text())
build = json.loads((APP / 'Contents/Resources/TG-Classic-build.json').read_text())
assert build['build_revision'] == manifest['build_revision']
assert build['patch_sha256'] == manifest['patch_sha256']
with (APP / 'Contents/Info.plist').open('rb') as stream:
    info = plistlib.load(stream)
assert info['CFBundleExecutable'] == 'TG Classic'
assert hashlib.sha256((APP / 'Contents/Resources/Icon.icns').read_bytes()).digest() == hashlib.sha256((ROOT / 'assets/TG Classic.icns').read_bytes()).digest()

def inventory(app):
    result = {}
    for path in sorted(app.rglob('*')):
        relative = path.relative_to(app)
        assert not any(part in ('tdata', '.private', '.git') for part in relative.parts)
        if path.is_symlink():
            result[str(relative)] = {'symlink': path.readlink().as_posix()}
        elif path.is_file():
            result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result

expected = inventory(APP)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(APP)], check=True)
OUT.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='tgclassic-dmg-stage-', dir='/private/tmp') as folder:
    stage = Path(folder)
    subprocess.run(['ditto', str(APP), str(stage / APP.name)], check=True)
    (stage / 'Applications').symlink_to('/Applications')
    (stage / 'README.txt').write_text(
        'TG Classic for macOS\n\n'
        'Apple Silicon (arm64), macOS 14 or newer.\n'
        'Drag TG Classic.app to Applications.\n'
        'This preview uses an ad-hoc signature and is not notarized by Apple.\n'
        'Source and builds: https://github.com/cockroach55kg/tg-classic\n', encoding='utf-8')
    subprocess.run(['hdiutil', 'create', '-volname', 'TG Classic', '-srcfolder', str(stage),
                    '-format', 'UDZO', '-imagekey', 'zlib-level=9', str(DMG)], check=True)
subprocess.run(['hdiutil', 'verify', str(DMG)], check=True)
with tempfile.TemporaryDirectory(prefix='tgclassic-dmg-check-', dir='/private/tmp') as folder:
    subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', folder, str(DMG)], check=True)
    try:
        mounted = Path(folder)
        assert (mounted / 'Applications').is_symlink()
        assert (mounted / 'Applications').readlink().as_posix() == '/Applications'
        assert inventory(mounted / APP.name) == expected, 'DMG app differs from the signed r4 bundle.'
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(mounted / APP.name)], check=True)
    finally:
        subprocess.run(['hdiutil', 'detach', folder], check=True)
result = {
    'file': DMG.name, 'sha256': hashlib.sha256(DMG.read_bytes()).hexdigest(),
    'bytes': DMG.stat().st_size, 'build_revision': build['build_revision'],
    'architecture': 'arm64', 'minimum_macos': info['LSMinimumSystemVersion'],
    'signature': 'ad-hoc', 'notarized': False,
    'dmg_checksum_verified': True, 'mounted_app_byte_identical': True,
    'codesign_verified_inside_dmg': True, 'profile_data_included': False,
}
(OUT / 'package-info.json').write_text(json.dumps(result, indent=2) + '\n')
(OUT / 'SHA256SUMS.txt').write_text(result['sha256'] + '  ' + DMG.name + '\n')
print(json.dumps(result, indent=2))

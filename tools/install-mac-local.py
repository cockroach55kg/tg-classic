#!/usr/bin/env python3
"""Install the verified fork, retaining the old bundle and account data location."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = root / 'artifacts/TG Classic.app'
installed = Path('/Applications/TG Classic.app')
legacy = Path('/Applications/WECID Classic.app')
assert not (installed.exists() and legacy.exists()), 'Two fork bundles exist; choose the upgrade source.'
previous = legacy if legacy.exists() else installed
assert previous.exists(), 'Expected the previously installed fork.'
previous_inode = previous.stat().st_ino
assert {entry.name for entry in previous.iterdir()} == {'Contents'}, str(previous)
backup = root / ('artifacts/previous-r2/WECID Classic.app' if previous == legacy
                 else 'artifacts/previous-r3/TG Classic.app')
assert not backup.exists(), 'The previous bundle is already preserved; do not overwrite it.'
for app, executable in ((source, 'TG Classic'), (previous, previous.stem)):
    with (app / 'Contents/Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    assert info['CFBundleIdentifier'] == 'com.wecid.classic', str(app)
    assert info['CFBundleExecutable'] == executable, str(app)
package = json.loads((root / 'evidence/mac-package.json').read_text())
assert package['launch_verified'] and package['application'] == str(source)

def require_stopped():
    for line in subprocess.check_output(['ps', '-axo', 'pid=,comm='], text=True).splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2:
            assert not any(fields[1].startswith(str(app) + '/') for app in (legacy, installed)), \
                'Close the installed Classic client before updating it. PID: ' + fields[0]

require_stopped()
subprocess.run(['codesign', '--verify', '--deep', '--strict', source], check=True)
stage = Path(tempfile.mkdtemp(prefix='.tg-classic-update-', dir='/Applications'))
staged_app = stage / installed.name
subprocess.run(['ditto', source, staged_app], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', staged_app], check=True)
require_stopped()
backup.parent.mkdir(parents=True, exist_ok=True)
backup.mkdir()
root_renamed = False
try:
    if previous != installed:
        previous.rename(installed)
        root_renamed = True
    (installed / 'Contents').rename(backup / 'Contents')
    (staged_app / 'Contents').rename(installed / 'Contents')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', installed], check=True)
except BaseException:
    if (backup / 'Contents').exists():
        if (installed / 'Contents').exists():
            failed = Path(tempfile.mkdtemp(prefix='failed-r4-', suffix='.app',
                                          dir=root / 'artifacts'))
            (installed / 'Contents').rename(failed / 'Contents')
        (backup / 'Contents').rename(installed / 'Contents')
    if root_renamed:
        installed.rename(previous)
    backup.rmdir()
    raise
staged_app.rmdir()
stage.rmdir()
assert installed.stat().st_ino == previous_inode
subprocess.run(['/System/Library/Frameworks/CoreServices.framework/Frameworks/'
                'LaunchServices.framework/Support/lsregister', '-f', installed], check=True)

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

executable = 'Contents/MacOS/TG Classic'
assert digest(installed / executable) == digest(source / executable)
result = {'installed_application': str(installed), 'previous_application': str(backup),
          'revision': '2026-10-25-r4', 'installed_executable_matches_verified_package': True,
          'signature_verified': True, 'user_data_touched': False,
          'application_launched_with_user_session': False,
          'legacy_data_directory_preserved': True,
          'bundle_directory_inode_preserved': True}
(root / 'evidence/mac-installed-update.json').write_text(json.dumps(result, indent=2) + '\n')
print('Updated:', installed)

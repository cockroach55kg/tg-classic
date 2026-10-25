#!/usr/bin/env python3
"""Launch only the packaged app in an empty profile without build environment paths."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[1]
app = root / 'artifacts/TG Classic.app'
profile = Path(tempfile.mkdtemp(prefix='packaged-launch-', dir=root / 'local-mac'))
env = {key: value for key, value in os.environ.items()
       if not key.startswith(('QT_', 'DYLD_', 'TDESKTOP_TEST_'))}
env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
env['LANG'] = 'en_US.UTF-8'
with (root / 'local-mac/logs/packaged-launch.log').open('w') as log:
    process = subprocess.Popen([str(app / 'Contents/MacOS/TG Classic'),
                                '-workdir', str(profile)], env=env,
                               stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Packaged app exited early: ' + str(process.returncode)
            time.sleep(0.5)
        output = (profile / 'log.txt').read_text(errors='replace')
        assert 'This is the only instance of Telegram, starting server and app...' in output
        assert 'QRhi: backing store primed for window' in output
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
result = {'packaged_application': str(app), 'started_with_empty_profile': True,
          'remained_running_seconds': 15, 'native_window_backing_store_created': True,
          'build_environment_paths_removed': True, 'authenticated_session_tested': False}
(root / 'evidence/mac-packaged-launch.json').write_text(json.dumps(result, indent=2) + '\n')
package = root / 'evidence/mac-package.json'
metadata = json.loads(package.read_text())
metadata['launch_verified'] = True
package.write_text(json.dumps(metadata, indent=2) + '\n')
print('Packaged app startup verified in a disposable empty profile.')

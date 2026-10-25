#!/usr/bin/env python3
"""Temporarily build the upstream Debug harness overlay in a disposable profile."""
import os
import argparse
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--overlay', type=Path, default=root / 'tools/mac-smoke-scenario.cpp')
parser.add_argument('--evidence', type=Path, default=root / 'evidence/mac-smoke')
args = parser.parse_args()
local = root / 'local-mac'
slot = root / 'tdesktop/Telegram/SourceFiles/test/test_scenario.cpp'
overlay = args.overlay.resolve()
original = slot.read_bytes()
profile = Path(tempfile.mkdtemp(prefix='classic-smoke-', dir=local))
(profile / 'testing').touch()
evidence = args.evidence.resolve()
evidence.mkdir(exist_ok=True)
report_path = evidence / 'test_log.txt'
if report_path.exists():
    report_path.replace(evidence / 'previous-test_log.txt')
command = ['/opt/homebrew/bin/cmake', '--build', str(local / 'client-build'),
           '--target', 'Telegram', '--parallel', '2']
try:
    slot.write_bytes(overlay.read_bytes())
    with (local / 'logs/smoke-build.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    env = dict(os.environ)
    env.update({'QT_PLUGIN_PATH': str(local / 'qt/share/qt/plugins'),
                'TDESKTOP_TEST_EVIDENCE_DIR': str(evidence),
                'TDESKTOP_TEST_WATCHDOG': '90', 'LANG': 'en_US.UTF-8',
                'LC_ALL': 'en_US.UTF-8'})
    binary = local / 'client-build/TG Classic.app/Contents/MacOS/TG Classic'
    with (local / 'logs/smoke-launch.log').open('w') as log:
        result = subprocess.run([str(binary), '-workdir', str(profile), '-testagent'],
                                env=env, stdout=log, stderr=subprocess.STDOUT,
                                timeout=120)
    assert result.returncode == 0, 'Application exited with ' + str(result.returncode)
    report = report_path.read_text()
    assert 'SCENARIO_RESULT: PASS' in report and 'TEST_COMPLETE' in report, report
    print('Native scenario passed: ' + overlay.name, flush=True)
finally:
    slot.write_bytes(original)
    with (local / 'logs/smoke-restore-build.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    print('Restored the upstream no-op test scenario and rebuilt the app.', flush=True)

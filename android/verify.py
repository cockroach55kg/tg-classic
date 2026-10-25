#!/usr/bin/env python3
"""Install and launch the signed APK only in the isolated TGClassicQA emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--serial', default='emulator-5556')
p.add_argument('--sdk', type=Path, default=ROOT / 'local/sdk')
p.add_argument('--apk', type=Path, default=ROOT.parent / 'artifacts/android/TG-Classic-Android-arm64.apk')
args = p.parse_args()
assert args.serial.startswith('emulator-'), 'This check never installs on a physical device.'
adb = [str(args.sdk / 'platform-tools/adb'), '-s', args.serial]
def run(*command, binary=False):
    return subprocess.check_output(adb + list(command), text=not binary, timeout=90)
assert 'TGClassicQA' in run('emu', 'avd', 'name'), 'Refusing to use another emulator profile.'
assert run('shell', 'getprop', 'sys.boot_completed').strip() == '1', 'Wait for Android to finish booting.'
out = ROOT.parent / 'evidence/android-r1'
out.mkdir(parents=True, exist_ok=True)
package = 'com.tgclassic.client.web'
component = package + '/org.telegram.ui.LaunchActivity'
print(run('install', '-r', str(args.apk)), flush=True)
run('logcat', '-c')
started = run('shell', 'am', 'start', '-W', '-n', component)
assert 'Error:' not in started, started
time.sleep(15)
pid = run('shell', 'pidof', package).strip()
assert pid, 'The application exited after launch.'
activities = run('shell', 'dumpsys', 'activity', 'activities')
resumed = [line.strip() for line in activities.splitlines() if 'mResumedActivity' in line or 'topResumedActivity' in line]
assert any(package in line for line in resumed), resumed
crashes = run('logcat', '-d', '-b', 'crash')
assert package not in crashes, crashes
(out / 'startup.png').write_bytes(run('exec-out', 'screencap', '-p', binary=True))
(out / 'startup-logcat.txt').write_text(run('logcat', '-d', '--pid=' + pid))
(out / 'crash-buffer.txt').write_text(crashes)
result = {'apk_sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest(), 'serial': args.serial,
          'avd': 'TGClassicQA', 'android_release': run('shell', 'getprop', 'ro.build.version.release').strip(),
          'api_level': run('shell', 'getprop', 'ro.build.version.sdk').strip(), 'pid': pid,
          'launch_result': started, 'foreground': resumed, 'stayed_running_seconds': 15,
          'account': 'empty test profile', 'signature_checked_separately': True}
(out / 'startup.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

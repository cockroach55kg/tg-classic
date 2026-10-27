#!/usr/bin/env python3
"""Check the removed backend switch using only the task-owned offline emulator."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--apk', type=Path, required=True)
args = p.parse_args()
adb = [str(ROOT / 'android/local/sdk/platform-tools/adb'), '-s', 'emulator-5556']
package = 'com.tgclassic.client.web'
out = ROOT / 'evidence/android-r4-login'
out.mkdir(parents=True, exist_ok=True)

def run(*command, **kwargs):
    return subprocess.check_output(adb + list(command), timeout=90, **kwargs)

assert b'TGClassicQA' in run('emu', 'avd', 'name')
assert run('shell', 'getprop', 'sys.boot_completed').strip() == b'1'
run('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable')
run('shell', 'svc', 'wifi', 'disable')
run('shell', 'svc', 'data', 'disable')
assert run('shell', 'settings', 'get', 'global', 'airplane_mode_on').strip() == b'1'

def tree():
    text = run('exec-out', 'uiautomator', 'dump', '/dev/tty').decode()
    return ET.fromstring(text[text.index('<?xml'):text.index('</hierarchy>') + len('</hierarchy>')])

def tap(node):
    bounds = list(map(int, re.findall(r'\d+', node.get('bounds'))))
    run('shell', 'input', 'tap', str((bounds[0] + bounds[2]) // 2), str((bounds[1] + bounds[3]) // 2))
    time.sleep(2)

def launch_login():
    run('logcat', '-c')
    run('shell', 'am', 'start', '-W', '-n', package + '/org.telegram.ui.LaunchActivity')
    time.sleep(3)
    ui = tree()
    for node in ui.iter('node'):
        if node.get('text', '').casefold() in ('start messaging', 'начать общение'):
            tap(node)
            break
    ui = tree()
    assert any(n.get('class') == 'android.widget.EditText' and n.get('package') == package for n in ui.iter('node')), 'Phone entry missing'
    assert run('shell', 'pidof', package).strip()
    assert package.encode() not in run('logcat', '-d', '-b', 'crash')
    return ui

def backend():
    # Config.cpp stores length, config version and TL bool before any session data.
    header = run('exec-out', 'run-as', package, 'head', '-c', '12', 'files/tgnet.dat')
    assert len(header) == 12
    size, version, flag = struct.unpack('<III', header)
    assert size > 4 and 1 <= version <= 100 and flag in (0x997275b5, 0xbc799737)
    return flag == 0x997275b5

run('install', '-r', str(args.baseline.resolve()))
assert run('shell', 'pm', 'clear', package).strip() == b'Success'
ui = launch_login()
switch = [n for n in ui.iter('node') if 'test backend' in n.get('text', '').casefold()]
assert switch, 'Baseline no longer exposes the switch'
assert not backend()
tap(switch[0])
assert backend(), 'Baseline switch did not select the test backend'
run('shell', 'am', 'force-stop', package)
sentinel = b'tg-classic-r4-update-preservation\n'
run('exec-in', 'run-as', package, 'tee', 'files/r4-update-sentinel.txt', input=sentinel)
run('install', '-r', str(args.apk.resolve()))
ui = launch_login()
assert not any('test backend' in n.get('text', '').casefold() or 'тестовый бэкенд' in n.get('text', '').casefold() for n in ui.iter('node'))
assert not backend(), 'Hidden test backend remained selected after the update'
assert run('exec-out', 'run-as', package, 'cat', 'files/r4-update-sentinel.txt') == sentinel
time.sleep(15)
assert run('shell', 'pidof', package).strip()
assert package.encode() not in run('logcat', '-d', '-b', 'crash')
(out / 'phone-entry.png').write_bytes(run('exec-out', 'screencap', '-p'))
(out / 'phone-entry.xml').write_text(ET.tostring(ui, encoding='unicode'))
run('shell', 'am', 'force-stop', package)
launch_login()
assert not backend(), 'Production backend did not survive a restart'
run('shell', 'run-as', package, 'rm', 'files/r4-update-sentinel.txt')
result = {'apk_sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest(),
          'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
          'backend_switch_absent': True, 'previous_test_backend_returned_to_production': True,
          'production_backend_persisted_after_restart': True, 'test_file_preserved_on_update': True,
          'phone_entry_stayed_running_seconds': 15, 'network_disabled': True, 'real_account_used': False,
          'authorization_code_requested': False}
(out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

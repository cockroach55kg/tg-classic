#!/usr/bin/env python3
"""Run offline fixture screens only in the named task-owned emulator."""
from pathlib import Path
import argparse,subprocess,time,json,re,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('screen',choices=['dialogs','settings','chat','group','folders']);p.add_argument('--dark',action='store_true');p.add_argument('--install',action='store_true');args=p.parse_args()
adb=[str(root/'local/sdk/platform-tools/adb'),'-s','emulator-5556']
def run(*a):return subprocess.check_output(adb+list(a),text=True,timeout=90)
assert 'TGClassicQA' in run('emu','avd','name')
assert run('shell','getprop','sys.boot_completed').strip()=='1'
run('shell','cmd','connectivity','airplane-mode','enable');run('shell','svc','wifi','disable');run('shell','svc','data','disable')
assert run('shell','settings','get','global','airplane_mode_on').strip()=='1'
pkg='com.tgclassic.client.web.qa'
if args.install:
 print(run('install','-r',str(root.parent/'artifacts/android-qa/TG-Classic-QA.apk')))
 assert run('shell','pm','clear',pkg).strip()=='Success'
 run('shell','pm','grant',pkg,'android.permission.POST_NOTIFICATIONS')
 run('shell','pm','grant',pkg,'android.permission.READ_CONTACTS')
run('shell','am','force-stop',pkg)
run('shell','cmd','uimode','night','yes' if args.dark else 'no')
run('logcat','-c')
print(run('shell','am','start','-W','-n',pkg+'/org.telegram.ui.classicqa.ClassicQAActivity','--es','screen',args.screen,'--ez','dark',str(args.dark).lower()))
for _ in range(20):
 logs=run('logcat','-d','-s','TG_CLASSIC_QA_FIXTURE_ONLY:I','AndroidRuntime:E')
 if 'READY '+args.screen in logs:break
 if 'FATAL EXCEPTION' in logs or 'FAILED' in logs:raise SystemExit(logs)
 time.sleep(1)
else:raise SystemExit('No fixture readiness signal\n'+logs)
assert 'PASS square bitmap avatar center and corner' in logs,logs
assert 'PASS palette '+('dark' if args.dark else 'light') in logs,logs
if args.screen in ['chat','group']:
 assert 'PASS composer inset' in logs,logs
 assert 'PASS message cells ' in logs,logs
time.sleep(4)
if args.screen=='settings':
 ui=run('exec-out','uiautomator','dump','/dev/tty')
 if 'Chat Settings' not in ui:
  tree=ET.fromstring(ui[ui.index('<?xml'):ui.index('</hierarchy>')+len('</hierarchy>')])
  tabs=[n for n in tree.iter('node') if n.get('text')=='Settings' and n.get('package')==pkg]
  assert tabs,'Settings tab missing'
  b=list(map(int,re.findall(r'\d+',tabs[-1].get('bounds'))))
  run('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(3)
  ui=run('exec-out','uiautomator','dump','/dev/tty')
 assert 'Chat Settings' in ui and 'Privacy &amp; Security' in ui,'Wrong settings screen'
assert run('shell','pidof',pkg).strip()
focus=[line for line in run('shell','dumpsys','window').splitlines() if 'mCurrentFocus' in line]
assert any(pkg in line for line in focus),focus
crashes=run('logcat','-d','-b','crash');assert pkg not in crashes,crashes
out=root.parent/'evidence/android-r3';out.mkdir(exist_ok=True,parents=True);name=args.screen+('-dark' if args.dark else '-light')
(out/(name+'.png')).write_bytes(subprocess.check_output(adb+['exec-out','screencap','-p']))
(out/(name+'.log')).write_text(logs)
print('Saved '+name+'.png; bitmap mask check passed; no app crash.')

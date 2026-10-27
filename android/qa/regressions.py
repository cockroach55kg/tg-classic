from pathlib import Path
import subprocess,time,xml.etree.ElementTree as ET,re,json,hashlib,struct
root=Path(__file__).resolve().parents[2];adb=[str(root/'android/local/sdk/platform-tools/adb'),'-s','emulator-5556'];pkg='com.tgclassic.client.web.qa';out=root/'evidence/android-r3';records=[]
def run(*a):return subprocess.check_output(adb+list(a),text=True,timeout=90)
assert 'TGClassicQA' in run('emu','avd','name')
def check():
 assert run('shell','pidof',pkg).strip()
 assert pkg not in run('logcat','-d','-b','crash')
 focus=[s for s in run('shell','dumpsys','window').splitlines() if 'mCurrentFocus' in s]
 if not any(pkg in s for s in focus):
  assert any('PopupWindow' in s for s in focus),focus
  assert any(n.get('package')==pkg for n in nodes().iter('node'))
  assert any(pkg in s for s in run('shell','dumpsys','activity','activities').splitlines() if 'topResumedActivity' in s or 'mResumedActivity' in s)
def snap(name):
 check()
 raw=subprocess.check_output(adb+['exec-out','screencap'])
 width,height,fmt=struct.unpack_from('<III',raw)
 header=len(raw)-width*height*4
 assert fmt==1 and header in [12,16],(fmt,header)
 def pixel(x,y):return list(raw[header+(y*width+x)*4:header+(y*width+x)*4+3])
 dark=name.endswith('-dark')
 if name.startswith('menu-'):
  popup=list(nodes())[0];assert popup.get('package')==pkg
  b=list(map(int,re.findall(r'\d+',popup.get('bounds'))));body=pixel(b[0]+8,b[1]+8)
 else:body=pixel(1,500)
 expected=[24,34,44] if dark else [192,192,192]
 assert all(abs(a-b)<=2 for a,b in zip(body,expected)),(name,'body palette changed',body,expected)
 entry={'body_rgb':body}
 if name.startswith('composer-'):
  edit=[n for n in nodes().iter('node') if n.get('class')=='android.widget.EditText' and n.get('package')==pkg];assert edit
  b=list(map(int,re.findall(r'\d+',edit[-1].get('bounds'))));color=pixel(b[2]-7,b[3]-7);expected=[32,45,58] if dark else [255,255,255]
  assert all(abs(a-b)<=2 for a,b in zip(color,expected)),(name,'input palette changed',color,expected)
  entry['input_rgb']=color
 p=out/(name+'.png');p.write_bytes(subprocess.check_output(adb+['exec-out','screencap','-p']));entry.update({'screenshot':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});records.append(entry);print('CHECKED '+name,flush=True)
def nodes():
 s=run('exec-out','uiautomator','dump','/dev/tty');return ET.fromstring(s[s.index('<?xml'):s.index('</hierarchy>')+len('</hierarchy>')])
def tap(n):
 b=list(map(int,re.findall(r'\d+',n.get('bounds'))));run('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(1)
for dark in [True,False]:
 palette='dark' if dark else 'light'
 for screen in ['group','chat','folders','settings']:
  command=['python3','android/qa/run.py',screen]+(['--dark'] if dark else [])
  subprocess.run(command,cwd=root,check=True)
  snap(screen+'-'+palette)
  if screen=='chat':
   edit=[n for n in nodes().iter('node') if n.get('class')=='android.widget.EditText' and n.get('package')==pkg];assert edit
   tap(edit[-1]);run('shell','input','text','Classic%slayout%scheck');time.sleep(1);snap('composer-keyboard-'+palette)
   run('shell','input','keyevent','4');time.sleep(1);snap('composer-typed-'+palette)
  if screen=='folders':
   ui=nodes();assert any((n.get('text') or n.get('content-desc'))=='People' for n in ui.iter('node'))
   for _ in range(2):run('shell','input','swipe','500','1050','500','450','400')
   time.sleep(1);snap('folders-scrolled-'+palette)
   options=[n for n in nodes().iter('node') if n.get('content-desc')=='More options'];assert options
   tap(options[-1]);ui=nodes();assert any('Saved Messages' in n.get('text','') for n in ui.iter('node'))
   snap('menu-'+palette);run('shell','input','keyevent','4')
result={'qa_apk_sha256':hashlib.sha256((root/'artifacts/android-qa/TG-Classic-QA.apk').read_bytes()).hexdigest(),'device':'TGClassicQA','resolution':'720x1650','offline_fictional_data_only':True,'records':records,'group_bubble_edges_asserted':True,'composer_edges_and_baselines_asserted':True,'real_account_messaging_tested':False}
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('ALL UI CASES PASSED',flush=True)

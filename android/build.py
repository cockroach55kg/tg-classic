#!/usr/bin/env python3
"""Build the independent arm64 Android preview; signing is done locally."""
import argparse,json,os,subprocess,shutil,hashlib,zipfile,re
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root/'upstream');p.add_argument('--sdk',type=Path);p.add_argument('--check',action='store_true');p.add_argument('--compact',action='store_true',help='Shrink and minify code using upstream R8 keep rules; preserve all resources.');args=p.parse_args();source=args.source.resolve()
sdk=args.sdk or (Path(os.environ['ANDROID_HOME']) if os.environ.get('ANDROID_HOME') else root/'local/sdk');sdk=sdk.resolve()
env=dict(os.environ)
api_file=root.parent/'.private/telegram-api.json'
if api_file.is_file() and not (env.get('TGCLASSIC_API_ID') and env.get('TGCLASSIC_API_HASH')):
 credentials=json.loads(api_file.read_text())
 api_id=str(credentials.get('api_id','')).strip();api_hash=str(credentials.get('api_hash','')).strip()
 assert api_id.isdigit() and int(api_id)>0 and re.fullmatch(r'[0-9a-fA-F]{32}',api_hash),'Invalid Telegram API configuration format.'
 env['TGCLASSIC_API_ID']=api_id;env['TGCLASSIC_API_HASH']=api_hash
if not env.get('JAVA_HOME'):
 homes=list((root/'local/jdk').glob('*/Contents/Home'))
 if homes: env['JAVA_HOME']=str(homes[0])
if env.get('JAVA_HOME'):env['PATH']=env['JAVA_HOME']+'/bin'+os.pathsep+env.get('PATH','')
env.setdefault('GRADLE_USER_HOME',str(root/'local/gradle'));env.setdefault('ANDROID_USER_HOME',str(root/'local/android-user'))
env['TGCLASSIC_DEBUG_KEYSTORE']=str(root/'local/builder-debug.keystore')
env['ANDROID_HOME']=str(sdk);env['ANDROID_SDK_ROOT']=str(sdk);env['CMAKE_BUILD_PARALLEL_LEVEL']='2'
requirements={'java':bool(shutil.which('java',path=env['PATH'])),'sdk_platform':(sdk/'platforms/android-36/android.jar').is_file(),'build_tools':(sdk/'build-tools/36.0.0').is_dir(),'ndk':(sdk/'ndk/27.2.12479018').is_dir(),'own_api_or_explicit_preview':bool(env.get('TGCLASSIC_API_ID') and env.get('TGCLASSIC_API_HASH')) or env.get('TGCLASSIC_TEST_API')=='true'}
if args.check:
 print(json.dumps(requirements,indent=2));raise SystemExit(0 if all(requirements.values()) else 2)
assert all(requirements.values()),requirements
subprocess.run(['python3',str(root/'apply.py'),'--source',str(source)],check=True)
subprocess.run(['git','submodule','update','--init','--recursive','--depth','1'],cwd=source,check=True)
(source/'local.properties').write_text('sdk.dir='+str(sdk).replace('\\','/')+'\n')
# Use the standard temporary debug key on the builder. The final key stays on this Mac.
key=Path(env['TGCLASSIC_DEBUG_KEYSTORE']);key.parent.mkdir(parents=True,exist_ok=True)
if not key.exists():
 subprocess.run(['keytool','-genkeypair','-keystore',str(key),'-storepass','android','-keypass','android','-alias','androiddebugkey','-dname','CN=Android Debug,O=Android,C=US','-keyalg','RSA','-validity','10000'],env=env,check=True,stdout=subprocess.DEVNULL)
subprocess.run(['bash','gradlew',':TMessagesProj:compileDebugJavaWithJavac',':TMessagesProj_AppStandalone:assembleAfatDebug','-PtgclassicCompact='+str(args.compact).lower(),'-PtgclassicQa=false','--no-daemon','--max-workers=2','-Pkotlin.compiler.execution.strategy=in-process','-Dorg.gradle.jvmargs=-Xmx3g -XX:MaxMetaspaceSize=1g'],cwd=source,env=env,check=True)
outputs=list((source/'TMessagesProj_AppStandalone/build/outputs/apk').rglob('*.apk'));assert len(outputs)==1,outputs
out=root.parent/('artifacts/android-compact' if args.compact else 'artifacts/android');out.mkdir(parents=True,exist_ok=True);target=out/'TG-Classic-Android-arm64-builder.apk';shutil.copy2(outputs[0],target)
if args.compact:shutil.copy2(source/'TMessagesProj_AppStandalone/build/outputs/mapping/afatDebug/mapping.txt',out/'mapping.txt')
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 assert 'lib/arm64-v8a/libtmessages.49.so' in z.namelist(),'Missing native Telegram library.'
result={'application':str(target),'architecture':'arm64-v8a','application_id':'com.tgclassic.client.web','configuration':'Debug','test_api':env.get('TGCLASSIC_TEST_API')=='true','local_signing_pending':True,'code_minified':args.compact,'resources_shrunk':False,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()}
(out/'builder-info.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

#!/usr/bin/env python3
"""Create a QA-only manifest from the pinned client manifest; never used by normal builds."""
from pathlib import Path
import json,subprocess,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'manifest.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root/'upstream',text=True).strip()==m['upstream_commit']
ET.register_namespace('android','http://schemas.android.com/apk/res/android')
ET.register_namespace('tools','http://schemas.android.com/tools')
tree=ET.parse(root/'upstream/TMessagesProj/config/release/AndroidManifest_standalone.xml')
ET.SubElement(tree.getroot().find('application'),'activity',{'{http://schemas.android.com/apk/res/android}name':'org.telegram.ui.classicqa.ClassicQAActivity','{http://schemas.android.com/apk/res/android}exported':'true','{http://schemas.android.com/apk/res/android}theme':'@style/Theme.TMessages'})
(root/'local').mkdir(exist_ok=True)
tree.write(root/'local/qa-manifest.xml',encoding='utf-8',xml_declaration=True)
print('QA-only manifest generated under ignored android/local/.')

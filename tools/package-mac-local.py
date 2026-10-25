#!/usr/bin/env python3
"""Package and ad-hoc sign the successfully built local Debug application."""
from pathlib import Path
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'local-mac'
SOURCE_APP = LOCAL / 'client-build/TG Classic.app'
DESTINATION = ROOT / 'artifacts'
APP = DESTINATION / 'TG Classic.app'
FRAMEWORKS = APP / 'Contents/Frameworks'
QT = LOCAL / 'qt'


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def macho(path):
    if not path.is_file() or path.is_symlink():
        return False
    with path.open('rb') as stream:
        return stream.read(4) in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe')


def dependencies(binary):
    output = subprocess.check_output(['otool', '-L', binary], text=True)
    return [line.strip().split(' (compatibility version', 1)[0]
            for line in output.splitlines()[1:]]


if not (SOURCE_APP / 'Contents/MacOS/TG Classic').is_file():
    raise SystemExit('Compile the complete Telegram target first.')
DESTINATION.mkdir(exist_ok=True)
if APP.exists():
    raise SystemExit('The artifact already exists. Preserve or remove that task artifact before repackaging.')
run('ditto', SOURCE_APP, APP)
FRAMEWORKS.mkdir(exist_ok=True)
run(QT / 'bin/macdeployqt', APP, '-always-overwrite', '-no-strip', '-no-codesign',
    '-no-plugins', '-libpath=' + str(LOCAL / 'prefix/lib'))

plugins = {
    'platforms': ['libqcocoa.dylib'],
    'styles': ['libqmacstyle.dylib'],
    'tls': ['libqcertonlybackend.dylib', 'libqopensslbackend.dylib', 'libqsecuretransportbackend.dylib'],
    'networkinformation': ['libqapplenetworkinformation.dylib'],
    'iconengines': ['libqsvgicon.dylib'],
    'imageformats': ['libqgif.dylib', 'libqico.dylib', 'libqjpeg.dylib', 'libqsvg.dylib',
                     'libqwebp.dylib', 'libqtiff.dylib', 'libqmacheif.dylib',
                     'libqicns.dylib', 'libqtga.dylib'],
}
for group, names in plugins.items():
    target = APP / 'Contents/PlugIns' / group
    target.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = QT / 'share/qt/plugins' / group / name
        if source.is_file():
            shutil.copy2(source, target / name)

processed = set()
copied = []
while True:
    pending = [path for path in APP.rglob('*') if macho(path) and path not in processed]
    if not pending:
        break
    for binary in pending:
        processed.add(binary)
        if binary.suffix == '.dylib':
            run('install_name_tool', '-id', '@rpath/' + binary.name, binary)
        changes = []
        for dependency in dependencies(binary):
            if dependency.startswith(('/System/', '/usr/lib/', '@loader_path/', '@executable_path/')):
                continue
            if dependency.startswith('@rpath/'):
                relative = dependency.removeprefix('@rpath/')
                if (FRAMEWORKS / relative).exists():
                    continue
                source = LOCAL / 'prefix/lib' / relative
                if not source.exists():
                    raise SystemExit('Unresolved bundled dependency: ' + dependency + ' in ' + str(binary))
            else:
                source = Path(dependency)
            if '.framework/' in dependency:
                raise SystemExit('Qt framework was not deployed: ' + dependency)
            if not source.exists():
                raise SystemExit('Missing runtime library: ' + str(source))
            target = FRAMEWORKS / source.name
            if not target.exists():
                shutil.copy2(source.resolve(), target)
                run('install_name_tool', '-id', '@rpath/' + target.name, target)
                copied.append(target.name)
            changes += ['-change', dependency, '@rpath/' + target.name]
        if changes:
            run('install_name_tool', *changes, binary)
        load_commands = subprocess.check_output(['otool', '-l', binary], text=True)
        rpaths = re.findall(r'cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.*?) \(offset', load_commands)
        for rpath in rpaths:
            if rpath.startswith('/') and not rpath.startswith(('/System/', '/usr/lib/')):
                run('install_name_tool', '-delete_rpath', rpath, binary)
        if 'path @executable_path/../Frameworks ' not in load_commands:
            run('install_name_tool', '-add_rpath', '@executable_path/../Frameworks', binary)

resources = APP / 'Contents/Resources'
shutil.copy2(ROOT / 'assets/TG Classic.icns', resources / 'Icon.icns')
shutil.copy2(ROOT / 'LICENSE', resources / 'TG-Classic-LICENSE.txt')
manifest = json.loads((ROOT / 'manifest.json').read_text())
build_info = {key: manifest[key] for key in (
    'name', 'build_revision', 'upstream_url', 'upstream_tag',
    'upstream_commit', 'lib_ui_commit', 'patch_sha256', 'local_mac_patch_sha256',
)}
build_info['native_mac'] = {key: manifest['native_mac'][key] for key in (
    'architecture', 'minimum_macos', 'configuration', 'upstream_test_api',
)}
build_info['bundle_identifier'] = 'com.wecid.classic'
(resources / 'TG-Classic-build.json').write_text(json.dumps(build_info, indent=2) + '\n')
shutil.copy2(LOCAL / 'dependencies.json', resources / 'TG-Classic-dependencies.json')
for binary in sorted(processed, key=lambda path: len(path.parts), reverse=True):
    run('codesign', '--force', '--sign', '-', binary)
run('codesign', '--force', '--deep', '--sign', '-', APP)
run('codesign', '--verify', '--deep', '--strict', '--verbose=2', APP)
run('lipo', '-archs', APP / 'Contents/MacOS/TG Classic')
result = {'application': str(APP), 'architecture': 'arm64', 'configuration': 'Debug -O1 -g0',
          'signature': 'ad-hoc', 'notarized': False, 'copied_libraries': copied,
          'launch_verified': False}
(ROOT / 'evidence/mac-package.json').write_text(json.dumps(result, indent=2) + '\n')
print('Packaged:', APP)

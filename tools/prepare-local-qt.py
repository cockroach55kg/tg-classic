#!/usr/bin/env python3
"""Stage a relocatable build copy of Qt; leave the Homebrew installation intact."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
local = root / 'local-mac'
qt = local / 'qt'
prefix = local / 'prefix'
qt.mkdir(exist_ok=True)
for package in ('qtbase', 'qtsvg', 'qtimageformats', 'qtshadertools'):
    subprocess.run(['ditto', str(Path('/opt/homebrew/opt') / package), str(qt)], check=True)

magic = (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe')
changed = 0
for binary in qt.rglob('*'):
    if not binary.is_file() or binary.is_symlink():
        continue
    with binary.open('rb') as stream:
        if stream.read(4) not in magic:
            continue
    dependencies = subprocess.check_output(['otool', '-L', binary], text=True)
    options = []
    for line in dependencies.splitlines()[1:]:
        dependency = line.strip().split(' (compatibility version', 1)[0]
        replacement = None
        if dependency.startswith('/opt/homebrew/') and '.framework/' in dependency:
            replacement = '@rpath/' + dependency.split('/lib/', 1)[1]
        elif dependency.startswith('/opt/homebrew/opt/glib/lib/'):
            replacement = str(prefix / 'lib' / Path(dependency).name)
        elif dependency.endswith('/libharfbuzz.0.dylib'):
            replacement = str(prefix / 'lib/libharfbuzz.dylib')
        elif dependency.endswith('/libmd4c.0.dylib'):
            replacement = str(prefix / 'lib/libmd4c.0.dylib')
        if replacement:
            options += ['-change', dependency, replacement]
    if '.framework/' in str(binary):
        relative = str(binary).split('/lib/', 1)[-1]
        if '.framework/Versions/' in relative and relative.endswith(relative.split('.framework/', 1)[0]):
            options += ['-id', '@rpath/' + relative]
    if options:
        subprocess.run(['install_name_tool', *options, binary], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', binary], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        changed += 1
print('Prepared local Qt:', qt, '; updated binaries:', changed)

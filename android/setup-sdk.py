#!/usr/bin/env python3
"""Install the pinned SDK components from Google's verified repository archives."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, default=ROOT / 'local/sdk')
args = parser.parse_args()
sdk = args.sdk.resolve()
host = {'Darwin': 'macosx', 'Linux': 'linux'}.get(platform.system())
assert host, 'This installer supports macOS and Linux.'
cache = ROOT / 'local/sdk-downloads'
cache.mkdir(parents=True, exist_ok=True)
sdk.mkdir(parents=True, exist_ok=True)
metadata = cache / 'repository.xml'

def download(url, target):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--connect-timeout', '20',
                    '--max-time', '1800', '--silent', '--show-error', url, '-o', str(target)], check=True)

download('https://dl.google.com/android/repository/repository2-1.xml', metadata)
repository = ET.parse(metadata).getroot()
wanted = {'platforms;android-36', 'build-tools;36.0.0', 'ndk;27.2.12479018', 'cmake;3.22.1', 'platform-tools'}
packages = {}
for package in repository.findall('remotePackage'):
    name = package.attrib.get('path')
    if name not in wanted:
        continue
    for archive in package.findall('archives/archive'):
        if archive.findtext('host-os') not in (None, host):
            continue
        complete = archive.find('complete')
        packages[name] = {'path': name, 'url': complete.findtext('url'),
                          'sha1': complete.findtext('checksum'), 'size': int(complete.findtext('size'))}
assert packages.keys() == wanted, 'A required component is missing from the official SDK repository.'

def install(package):
    target = sdk.joinpath(*package['path'].split(';'))
    if (target / 'source.properties').is_file():
        print('Already installed: ' + package['path'], flush=True)
        return package
    assert not target.exists(), 'Inspect the incomplete SDK component: ' + str(target)
    archive = cache / Path(package['url']).name
    print('Downloading: ' + package['path'], flush=True)
    download('https://dl.google.com/android/repository/' + package['url'], archive)
    assert archive.stat().st_size == package['size'], 'SDK archive size mismatch.'
    assert hashlib.sha1(archive.read_bytes()).hexdigest() == package['sha1'], 'SDK archive checksum mismatch.'
    with zipfile.ZipFile(archive) as contents:
        for name in contents.namelist():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts, name
    with tempfile.TemporaryDirectory(prefix='sdk-unpack-', dir=cache) as unpacked:
        unpacked = Path(unpacked)
        command = ['ditto', '-x', '-k', str(archive), str(unpacked)] if host == 'macosx' else ['unzip', '-q', str(archive), '-d', str(unpacked)]
        subprocess.run(command, check=True)
        children = list(unpacked.iterdir())
        content = children[0] if len(children) == 1 and children[0].is_dir() else unpacked
        target.parent.mkdir(parents=True, exist_ok=True)
        assert (content / 'source.properties').is_file(), 'Unexpected SDK archive layout.'
        shutil.move(str(content), str(target))
    archive.unlink()
    print('Verified and installed: ' + package['path'], flush=True)
    return package

with ThreadPoolExecutor(max_workers=3) as pool:
    installed = list(pool.map(install, packages.values()))
(sdk / 'licenses').mkdir(exist_ok=True)
for license in repository.findall('license'):
    digest = hashlib.sha1(license.text.strip().encode()).hexdigest()
    (sdk / 'licenses' / license.attrib['id']).write_text(digest + '\n')
(cache / 'installed.json').write_text(json.dumps(installed, indent=2) + '\n')
print('Pinned Android SDK ready: ' + str(sdk))

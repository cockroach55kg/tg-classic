#!/usr/bin/env python3
"""Sign a builder APK locally with a stable key that never leaves this machine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=ROOT.parent / 'artifacts/android/TG-Classic-Android-arm64-builder.apk')
parser.add_argument('--sdk', type=Path, default=ROOT / 'local/sdk')
parser.add_argument('--output', type=Path, default=ROOT.parent / 'artifacts/android/TG-Classic-Android-arm64.apk')
args = parser.parse_args()
env = dict(os.environ)
if not env.get('JAVA_HOME'):
    homes = sorted((ROOT / 'local/jdk').glob('*/Contents/Home'))
    if homes:
        env['JAVA_HOME'] = str(homes[0])
if env.get('JAVA_HOME'):
    env['PATH'] = env['JAVA_HOME'] + '/bin' + os.pathsep + env.get('PATH', '')
java = shutil.which('java', path=env['PATH'])
keytool = shutil.which('keytool', path=env['PATH'])
tools = args.sdk.resolve() / 'build-tools/36.0.0'
signer = tools / 'lib/apksigner.jar'
assert java and keytool and signer.is_file(), 'Java 17 and Android build tools 36 are required.'
assert args.input.is_file(), 'Build the APK first.'
assert not args.output.exists(), 'Preserve or move the previous signed APK before signing another build.'

private = ROOT.parent / '.private/android'
private.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(private, 0o700)
key = private / 'tg-classic.p12'
password = private / 'keystore-password.txt'
if not key.exists():
    assert not password.exists(), 'An orphan signing password exists; inspect the local signing directory.'
    fd = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(secrets.token_urlsafe(48) + '\n')
    subprocess.run([
        keytool, '-genkeypair', '-storetype', 'PKCS12', '-keystore', str(key),
        '-storepass:file', str(password), '-keypass:file', str(password),
        '-alias', 'tgclassic', '-dname', 'CN=TG Classic,O=TG Classic',
        '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
    ], env=env, check=True)
    os.chmod(key, 0o600)
assert password.is_file(), 'The stable signing password is missing. Do not generate a replacement key.'

args.output.parent.mkdir(parents=True, exist_ok=True)
temporary = args.output.with_suffix('.signing.apk')
assert not temporary.exists(), 'An incomplete signing output exists; inspect it first.'
subprocess.run([
    java, '-jar', str(signer), 'sign', '--ks', str(key), '--ks-key-alias', 'tgclassic',
    '--ks-pass', 'file:' + str(password), '--key-pass', 'file:' + str(password),
    '--out', str(temporary), str(args.input),
], env=env, check=True)
verification = subprocess.check_output([
    java, '-jar', str(signer), 'verify', '--verbose', '--print-certs', str(temporary),
], env=env, text=True)
badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(temporary)], env=env, text=True)
assert "package: name='com.tgclassic.client.web'" in badging, 'Unexpected application identifier.'
assert "sdkVersion:'23'" in badging, 'Unexpected Android minimum version.'
with zipfile.ZipFile(temporary) as archive:
    assert archive.testzip() is None, 'APK archive corruption.'
    native = [name for name in archive.namelist() if name.startswith('lib/') and name.endswith('.so')]
    assert 'lib/arm64-v8a/libtmessages.49.so' in native, 'The Telegram native library is missing.'
    assert all(name.startswith('lib/arm64-v8a/') for name in native), native
digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
certificate = re.search(r'Signer #1 certificate SHA-256 digest: (\w+)', verification)
assert certificate, 'The signing certificate was not reported.'
temporary.rename(args.output)
# APK Signature Scheme v4 creates a companion idsig on some tool versions.
idsig = Path(str(temporary) + '.idsig')
if idsig.exists():
    idsig.rename(Path(str(args.output) + '.idsig'))
info = {
    'apk': str(args.output.resolve()), 'sha256': digest, 'bytes': args.output.stat().st_size,
    'application_id': 'com.tgclassic.client.web', 'architecture': 'arm64-v8a',
    'min_sdk': 23, 'configuration': 'Debug', 'certificate_sha256': certificate.group(1),
    'native_libraries': native, 'signature_verified': True,
}
(args.output.parent / 'signature-verification.txt').write_text(verification)
(args.output.parent / 'package-badging.txt').write_text(badging)
(args.output.parent / 'package-info.json').write_text(json.dumps(info, indent=2) + '\n')
(args.output.parent / 'SHA256SUMS').write_text(digest + '  ' + args.output.name + '\n')
print(json.dumps(info, indent=2))

#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def run(command, cwd):
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def inspect(source):
    system = platform.system()
    checks = []
    checks.append((system in ('Darwin', 'Windows'), 'Windows or macOS build host'))
    for tool in ('git', 'cmake', 'ninja'):
        checks.append((bool(shutil.which(tool)), tool))
    checks.append(((source / 'Telegram/CMakeLists.txt').is_file(), 'Telegram source checkout'))
    if system == 'Darwin':
        xcode = subprocess.run(['xcode-select', '-p'], capture_output=True, text=True)
        checks.append((xcode.returncode == 0 and '/Xcode' in xcode.stdout, 'Full Xcode selected'))
        required = 55_000_000_000
        available = shutil.disk_usage(source if source.exists() else source.parent).free
        checks.append((available >= required, '55 GB free for the official macOS build procedure'))
    elif system == 'Windows':
        checks.append((bool(shutil.which('cl')), 'MSVC x64 Native Tools environment'))
    return checks


def main():
    parser = argparse.ArgumentParser(description='Build the TG Classic native Telegram fork.')
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent / 'tdesktop')
    parser.add_argument('--check', action='store_true', help='Report requirements without downloading or building.')
    parser.add_argument('--prepare', action='store_true', help='Initialize submodules and build upstream dependencies.')
    parser.add_argument('--test-api', action='store_true', help='Use upstream limited credentials for local development only.')
    args = parser.parse_args()
    source = args.source.resolve()
    checks = inspect(source)
    result = {'platform': platform.system(), 'source': str(source), 'requirements': [
        {'requirement': label, 'available': available} for available, label in checks
    ]}
    if args.check:
        print(json.dumps(result, indent=2))
        return 0 if all(available for available, _ in checks) else 2
    missing = [label for available, label in checks if not available]
    if missing:
        raise SystemExit('Missing build requirements: ' + '; '.join(missing))
    api_id = os.environ.get('WECID_TELEGRAM_API_ID', '')
    api_hash = os.environ.get('WECID_TELEGRAM_API_HASH', '')
    if not args.test_api and (not api_id.isdecimal() or not api_hash):
        raise SystemExit('Set WECID_TELEGRAM_API_ID and WECID_TELEGRAM_API_HASH, or choose --test-api for development.')
    toolkit = source / 'Telegram/lib_ui'
    overlay = Path(__file__).resolve().parent / 'patches/lib_ui.patch'
    if args.prepare:
        run(['git', 'submodule', 'update', '--init', '--recursive'], source)
        already_applied = subprocess.run(
            ['git', 'apply', '--reverse', '--check', str(overlay)],
            cwd=toolkit, capture_output=True).returncode == 0
        if not already_applied:
            run(['git', 'apply', '--check', str(overlay)], toolkit)
            run(['git', 'apply', str(overlay)], toolkit)
        if platform.system() == 'Darwin':
            run(['/bin/bash', 'Telegram/build/prepare/mac.sh', 'skip-release', 'silent'], source)
        else:
            run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c',
                 'Telegram\\build\\prepare\\win.bat', 'skip-release', 'silent', 'qt6'], source)
    if not (toolkit / 'ui/classic_style.h').is_file():
        raise SystemExit('Classic toolkit overlay is missing. Run apply.py or build.py --prepare first.')
    options = [
        '-DCMAKE_CONFIGURATION_TYPES=Debug',
        '-DDESKTOP_APP_DISABLE_AUTOUPDATE=ON',
        '-DDESKTOP_APP_DISABLE_CRASH_REPORTS=ON',
    ]
    if platform.system() == 'Darwin':
        options.append('-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO')
    if args.test_api:
        options.append('-DTDESKTOP_API_TEST=ON')
    else:
        options.extend(['-DTDESKTOP_API_ID=' + api_id, '-DTDESKTOP_API_HASH=' + api_hash])
    run([sys.executable, 'configure.py', *options], source / 'Telegram')
    run(['cmake', '--build', 'out', '--config', 'Debug', '--target', 'Telegram', '--parallel', '2'], source)
    print('Build completed. Inspect out/Debug/TG Classic.app or out/Debug/TG Classic.exe.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit('Build command failed with exit code ' + str(error.returncode))

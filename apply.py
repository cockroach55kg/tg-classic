#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def run(command, cwd=None, capture=False):
    return subprocess.run([str(part) for part in command], cwd=cwd, check=True,
                          capture_output=capture, text=True)


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_text())
    parser = argparse.ArgumentParser(description='Apply the pinned TG Classic native client changes.')
    parser.add_argument('--source', type=Path, default=root / 'tdesktop')
    parser.add_argument('--check', action='store_true', help='Check existing sources without changing them.')
    args = parser.parse_args()
    source = args.source.resolve()
    for name, expected in manifest['patch_sha256'].items():
        actual = hashlib.sha256((root / 'patches' / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit('Patch checksum mismatch: ' + name)
    if not source.exists():
        if args.check:
            raise SystemExit('Source checkout is missing.')
        source.parent.mkdir(parents=True, exist_ok=True)
        run(['git', 'clone', '--depth', '1', '--branch', manifest['upstream_tag'],
             manifest['upstream_url'], source])
    head = run(['git', 'rev-parse', 'HEAD'], source, capture=True).stdout.strip()
    if head != manifest['upstream_commit']:
        raise SystemExit('The patch requires the exact upstream revision in manifest.json.')
    toolkit = source / 'Telegram/lib_ui'
    if not (toolkit / 'CMakeLists.txt').is_file():
        if args.check:
            raise SystemExit('Initialize the pinned Telegram/lib_ui submodule first.')
        run(['git', 'submodule', 'update', '--init', '--depth', '1', 'Telegram/lib_ui'], source)
    toolkit_head = run(['git', 'rev-parse', 'HEAD'], toolkit, capture=True).stdout.strip()
    if toolkit_head != manifest['lib_ui_commit']:
        raise SystemExit('The toolkit revision differs from the pinned upstream revision.')
    pending = []
    for repo, name in [(source, 'tdesktop.patch'), (toolkit, 'lib_ui.patch')]:
        patch = root / 'patches' / name
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)],
                                 cwd=repo, capture_output=True).returncode == 0
        if not applied:
            run(['git', 'apply', '--check', str(patch)], repo)
            pending.append((repo, patch))
    if not args.check:
        for repo, patch in pending:
            run(['git', 'apply', str(patch)], repo)
    print('Patches checked.' if args.check else 'Native source changes are applied.')
    print('This does not build or install the Telegram client.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit('Source preparation failed with exit code ' + str(error.returncode))

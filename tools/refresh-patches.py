#!/usr/bin/env python3
"""Export fork patches and reconstruct every modified file from pinned sources."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
manifest_path = root / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
checks = []
for name, repo, revision, exclude in [
    ('tdesktop.patch', root / 'tdesktop', manifest['upstream_commit'],
     [':(exclude)Telegram/lib_ui', ':(exclude)Telegram/SourceFiles/test/test_scenario.cpp']),
    ('lib_ui.patch', root / 'tdesktop/Telegram/lib_ui', manifest['lib_ui_commit'], []),
]:
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == revision
    subprocess.run(['git', 'diff', '--check'], cwd=repo, check=True)
    patch = subprocess.check_output(['git', 'diff', '--binary', '--', '.', *exclude], cwd=repo)
    patch_path = root / 'patches' / name
    patch_path.write_bytes(patch)
    paths = subprocess.check_output(['git', 'diff', '--name-only', '--', '.', *exclude],
                                    cwd=repo, text=True).splitlines()
    with tempfile.TemporaryDirectory(prefix='tg-classic-patch-', dir='/private/tmp') as temp:
        target = Path(temp)
        for path in paths:
            original = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=repo, capture_output=True)
            if original.returncode == 0:
                output = target / path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(original.stdout)
        subprocess.run(['git', 'apply', '--check', str(patch_path)], cwd=target, check=True)
        subprocess.run(['git', 'apply', str(patch_path)], cwd=target, check=True)
        for path in paths:
            assert (target / path).read_bytes() == (repo / path).read_bytes(), path
    checks.append({'patch': name, 'changed_files': len(paths),
                   'forward_apply_on_pinned_files': True, 'byte_reconstruction_matches': True})
manifest['patch_sha256'] = {name: hashlib.sha256((root / 'patches' / name).read_bytes()).hexdigest()
                            for name in ('tdesktop.patch', 'lib_ui.patch')}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
(root / 'evidence/native-patch-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))

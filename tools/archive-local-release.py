#!/usr/bin/env python3
"""Archive the verified local bundle and an explicit, profile-free source list."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'manifest.json').read_text())
revision = manifest['build_revision']
tag = revision.rsplit('-', 1)[-1]
assert tag.startswith('r') and tag[1:].isdigit(), revision
app = root / 'artifacts/TG Classic.app'
app_archive = root / ('artifacts/TG-Classic-macOS-arm64-' + tag + '.zip')
source_archive = root / ('TG-Classic-source-' + tag + '.zip')
assert app.is_dir() and not app_archive.exists() and not source_archive.exists()
subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                str(app), str(app_archive)], check=True)
with zipfile.ZipFile(app_archive) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert 'TG Classic.app/Contents/MacOS/TG Classic' in names
    assert not any('tdata' in Path(name).parts for name in names)
files = [root / name for name in ('.gitignore','LICENSE','README.md','manifest.json','apply.py','build.py',
                                  'local-mac/dependencies.json')]
for folder in ('assets','patches','tools','preview','evidence'):
    for path in (root / folder).rglob('*'):
        if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts \
                and path.name != '.DS_Store' and path not in (root / 'evidence/delivery.json',
                    root / 'evidence/local-release-archives.json'):
            files.append(path)
with zipfile.ZipFile(source_archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(files):
        assert not any(part in ('tdata','.git','.env') for part in path.relative_to(root).parts), path
        z.write(path, 'TG-Classic-source/' + path.relative_to(root).as_posix())
with zipfile.ZipFile(source_archive) as z:
    assert z.testzip() is None
for link, target in [(root / 'artifacts/TG-Classic-macOS-arm64.zip', app_archive),
                     (root / 'TG-Classic-source.zip', source_archive)]:
    assert not link.exists() or link.is_symlink(), link
    link.unlink(missing_ok=True)
    link.symlink_to(target.name)
artifacts = []
for path in (app_archive, source_archive):
    artifacts.append({'path':str(path.relative_to(root)), 'bytes':path.stat().st_size,
                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root / 'evidence/local-release-archives.json').write_text(json.dumps({
    'revision':revision, 'archive_integrity_checked':True, 'archives_contain_no_tdata':True,
    'artifacts':artifacts}, indent=2) + '\n')
print(json.dumps(artifacts,indent=2))

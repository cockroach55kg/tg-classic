#!/usr/bin/env python3
"""Apply Windows product metadata without changing the pinned Mac source overlay."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
source = Path(sys.argv[1]).resolve()
manifest = json.loads((root / 'manifest.json').read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == manifest['upstream_commit']
resource = source / 'Telegram/Resources/winrc/Telegram.rc'
text = resource.read_bytes().decode('utf-8')
for field, old, new in [('CompanyName', 'Telegram FZ-LLC', 'TG Classic contributors'),
                        ('FileDescription', 'Telegram Desktop', 'TG Classic'),
                        ('ProductName', 'Telegram Desktop', 'TG Classic')]:
    original = f'VALUE "{field}", "{old}"'
    replacement = f'VALUE "{field}", "{new}"'
    assert text.count(original) == 1 or text.count(replacement) == 1, field
    text = text.replace(original, replacement)
resource.write_bytes(text.encode('utf-8'))
print('TG Classic Windows product metadata applied.')

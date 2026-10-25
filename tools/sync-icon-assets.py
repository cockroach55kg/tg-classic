#!/usr/bin/env python3
"""Update existing upstream launcher and Qt logo assets from the drawn icon."""
from pathlib import Path
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
source = root / 'assets/TG Classic.png'
art = root / 'tdesktop/Telegram/Resources/art'
iconset = root / 'tdesktop/Telegram/Telegram/Images.xcassets/Icon.iconset'
for target in [*iconset.glob('*.png'), *art.glob('icon*.png'), *art.glob('logo_256*.png')]:
    data = target.read_bytes()
    width, height = struct.unpack('>II', data[16:24])
    subprocess.run(['sips', '-z', str(height), str(width), str(source), '--out', str(target)],
                   check=True, stdout=subprocess.DEVNULL)
for target in art.glob('*.ico'):
    sizes = [16, 32, 64, 128, 256]
    pictures = [(root / 'local-mac/tg-classic.iconset' / (
        f'icon_{size}x{size}.png' if size != 64 else 'icon_32x32@2x.png')).read_bytes()
                for size in sizes]
    offset = 6 + 16 * len(sizes)
    directory = []
    for size, picture in zip(sizes, pictures):
        directory.append(struct.pack('<BBBBHHII', size if size < 256 else 0,
            size if size < 256 else 0, 0, 0, 1, 32, len(picture), offset))
        offset += len(picture)
    target.write_bytes(struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(directory) + b''.join(pictures))
print('Updated existing launcher icons and Qt logos.')

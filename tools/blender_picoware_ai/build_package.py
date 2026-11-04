#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build reproducible install ZIPs from the adjacent editable package folders."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
PACKAGES = (
    ('picoware-blender-1.5.0', 'picoware-blender-1.5.0.zip', ''),
    ('picoware-ai', 'picoware-ai-helper-1.0.0.zip', 'picoware-ai/'),
)


def package_files(folder, prefix):
    files = {}
    for path in folder.rglob('*'):
        relative = path.relative_to(folder)
        if any(part.startswith('.') or part in ('__pycache__', 'tests', 'node_modules')
               for part in relative.parts):
            continue
        if path.is_file() and path.suffix not in ('.pyc', '.zip'):
            files[prefix + relative.as_posix()] = path.read_bytes()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT,
                        help='ZIP destination (default: this directory)')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for folder, archive, prefix in PACKAGES:
        files = package_files(ROOT / folder, prefix)
        with zipfile.ZipFile(args.output / archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                output.writestr(info, data)
    print(args.output)


if __name__ == '__main__':
    main()

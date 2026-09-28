#!/usr/bin/env python3
"""Export only the portable source, excluding generated UI, logs and backups."""
import argparse
import hashlib
import re
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=root/'dist')
args=parser.parse_args()
files=[root/name for name in ['README.md','LICENSE','.gitignore','install.py','install-login.py']]
for directory in ['bin','ui','dock','hypr','assets','systemd','tests']:
    files.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
files.extend(root/'review/login'/name for name in ['README.md','prepare.py','prepare-polkit.py','TouchKeyboard.qml'])
for path in files:
    if path.is_symlink(): raise SystemExit('Refusing source symlink: '+str(path))
    text=path.read_text()
    if re.search(r'/home/[A-Za-z0-9_.-]+/|ipts-[0-9a-f]{4}:[0-9a-f]{4}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}',text):
        raise SystemExit('Private path or credential marker in source: '+str(path))
args.output.mkdir(parents=True,exist_ok=True)
archive=args.output/'omarchy-tablet-mode-source.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for path in sorted(files):
        info=tar.gettarinfo(str(path),'omarchy-tablet-mode/'+str(path.relative_to(root)))
        info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
        with path.open('rb') as stream: tar.addfile(info,stream)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(args.output/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
print(f'Exported {len(files)} portable files: {archive}')

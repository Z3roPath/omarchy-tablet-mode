#!/usr/bin/env python3
"""Install only the generated touch greeter theme; never restart SDDM."""
import argparse
import configparser
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

def digest(path):
    if path.is_dir():
        return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(path.rglob('*')) if p.is_file()}
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'rollback'])
    parser.add_argument('--theme', type=Path, default=Path(__file__).resolve().parent/'review/login/theme')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    target = Path('/usr/local/share/sddm/themes/omarchy-tablet')
    config = Path('/etc/sddm.conf.d/zz-omarchy-tablet.conf')
    state = Path('/var/lib/omarchy-tablet-mode/login-install.json')
    if args.action == 'install':
        settings=configparser.ConfigParser(strict=False)
        settings.read([str(p) for directory in ['/usr/lib/sddm/sddm.conf.d','/etc/sddm.conf.d'] for p in sorted(Path(directory).glob('*.conf'))]+['/etc/sddm.conf'])
        if settings.get('General','DisplayServer',fallback='')!='wayland':
            raise SystemExit('Unsupported greeter: this integration requires SDDM Wayland')
        selected=settings.get('Theme','Current',fallback='')
        if selected not in ['omarchy','omarchy-tablet']:
            raise SystemExit('Selected SDDM theme is not Omarchy; review before changing it')
        if not (args.theme/'Main.qml').is_file() or not (args.theme/'TouchKeyboard.qml').is_file():
            raise SystemExit('Run review/login/prepare.py first to generate the theme')
        for p in args.theme.rglob('*'):
            if p.is_symlink():
                raise SystemExit(f'Theme contains a symlink: {p}')
        text = (args.theme/'Main.qml').read_text()
        if 'sddm.login(root.currentUser, password.text, root.sessionIndex)' not in text:
            raise SystemExit('Unsupported theme authentication entry point')
    print(f'{args.action}: {target} and {config}; SDDM will not be restarted')
    if args.dry_run:
        return
    if os.geteuid() != 0:
        raise SystemExit('Administrator authentication required. Run with sudo or pkexec.')
    if args.action == 'rollback':
        if not state.exists():
            raise SystemExit('No login installation manifest exists')
        record = json.loads(state.read_text())
        for name, path in [('theme',target),('config',config)]:
            if digest(path) != record['installed'][name]:
                raise SystemExit(f'{path} changed after installation; review it before rollback')
        for name, path in [('theme',target),('config',config)]:
            if path.is_dir(): shutil.rmtree(path)
            elif path.exists(): path.unlink()
            saved = Path(record['backup'])/name
            if saved.is_dir(): shutil.copytree(saved,path)
            elif saved.exists(): shutil.copy2(saved,path)
        state.unlink()
        print('Previous greeter selection restored; applies at the next sign-in')
        return
    if state.exists():
        record = json.loads(state.read_text())
        for name, path in [('theme',target),('config',config)]:
            if digest(path) != record['installed'][name]:
                raise SystemExit(f'{path} changed after installation; review before updating')
    else:
        backup = state.parent/'login-backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        backup.mkdir(parents=True,exist_ok=False)
        for name, path in [('theme',target),('config',config)]:
            if path.is_dir(): shutil.copytree(path,backup/name)
            elif path.exists(): shutil.copy2(path,backup/name)
        record = {'backup':str(backup)}
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(args.theme,target)
    config.write_text('[Theme]\nCurrent=omarchy-tablet\nThemeDir=/usr/local/share/sddm/themes\n')
    for p in [target,*target.rglob('*'),config]:
        os.chown(p,0,0)
        p.chmod(0o755 if p.is_dir() else 0o644)
    record['installed'] = {'theme':digest(target),'config':digest(config)}
    state.parent.mkdir(parents=True,exist_ok=True)
    state.write_text(json.dumps(record,indent=2)+'\n')
    print(f'Installed and verified. Backup: {record["backup"]}')

if __name__ == '__main__': main()

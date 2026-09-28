#!/usr/bin/env python3
"""Backed-up installer for Omarchy Quickshell and Hyprland Lua."""
import argparse
import getpass
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
HOME=Path.home()
TARGET=HOME/'.local/share/omarchy-tablet-mode'
STATE=HOME/'.local/state/omarchy-tablet-mode'
MANIFEST=STATE/'install.json'

def run(*args): return subprocess.check_output(args,text=True).strip()

def fingerprint(path):
    if path.is_symlink(): raise RuntimeError(f'Refusing managed symlink: {path}')
    if path.is_dir():
        if any(p.is_symlink() for p in path.rglob('*')): raise RuntimeError(f'Managed directory contains symlinks: {path}')
        return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

class Backup:
    def __init__(self):
        self.data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'backup':str(STATE/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-install')),'files':{}}
        Path(self.data['backup']).mkdir(parents=True,exist_ok=True)
    def save(self): MANIFEST.write_text(json.dumps(self.data,indent=2)+'\n')
    def before(self,path):
        key=str(path)
        if key in self.data['files']:
            if fingerprint(path)!=self.data['files'][key].get('installed'): raise RuntimeError(f'{path} changed since installation; review before updating')
            return
        fingerprint(path)
        saved=Path(self.data['backup'])/str(len(self.data['files']))
        if path.is_dir(): shutil.copytree(path,saved)
        elif path.exists(): shutil.copy2(path,saved)
        self.data['files'][key]={'saved':str(saved),'existed':path.exists()}
        self.save()
    def finish(self):
        for name,record in self.data['files'].items(): record['installed']=fingerprint(Path(name))
        self.save()
    def check(self):
        conflicts=[name for name,record in self.data['files'].items() if fingerprint(Path(name))!=record.get('installed')]
        if conflicts: raise RuntimeError('Edited after installation; review before uninstall: '+', '.join(conflicts))
    def restore(self,force=False):
        if not force: self.check()
        for name,record in reversed(list(self.data['files'].items())):
            path=Path(name)
            if path.is_dir(): shutil.rmtree(path)
            elif path.exists(): path.unlink()
            if record['existed']:
                saved=Path(record['saved']);path.parent.mkdir(parents=True,exist_ok=True)
                if saved.is_dir(): shutil.copytree(saved,path)
                else: shutil.copy2(saved,path)
        MANIFEST.unlink(missing_ok=True)

def detect():
    required=['hyprctl','qs','omarchy','omarchy-shell','omarchy-toggle-bar','systemctl','jq','flock','uwsm-app','omarchy-launch-browser','omarchy-launch-terminal']
    missing=[name for name in required if not shutil.which(name)]
    if missing: raise RuntimeError('Missing dependencies: '+', '.join(missing))
    version=run('hyprctl','version').splitlines()[0]
    if not (HOME/'.config/hypr/hyprland.lua').exists() or not (HOME/'.config/hypr/input.lua').exists(): raise RuntimeError('Requires Omarchy Hyprland Lua with sourced input.lua; legacy .conf unsupported')
    shell_path=Path('/usr/share/omarchy/shell')
    if not (shell_path/'plugins/bar/Bar.qml').exists(): raise RuntimeError('Requires Omarchy Quickshell bar; Waybar and other docks unsupported')
    config=json.loads((HOME/'.config/omarchy/shell.json').read_text())
    if config.get('bar',{}).get('position','top') not in ['left','right']: raise RuntimeError('Side-dock adapter currently requires a left or right Omarchy bar')
    plugins=json.loads(run('hyprctl','-j','plugin','list'))
    gestures=any(p.get('name')=='hyprgrass' for p in plugins)
    devices=json.loads(run('hyprctl','-j','devices'))
    touches=devices.get('touch',devices.get('touchscreens',[]))
    unit=HOME/'.config/systemd/user/tablet-keyboard.service'
    existing=unit.read_text() if unit.exists() else ''
    if existing and 'wvkbd' not in existing: raise RuntimeError('Existing tablet-keyboard.service uses another OSK; review before replacing')
    keyboard=shutil.which('wvkbd-deskintl') or shutil.which('wvkbd-mobintl') or shutil.which('wvkbd')
    if existing:
        match=re.search(r'(?m)^ExecStart=(\S+)',existing)
        if not match: raise RuntimeError('Cannot inspect existing keyboard ExecStart')
        keyboard=match[1]
    if not keyboard or not Path(keyboard).is_file(): raise RuntimeError('Install wvkbd first, or configure a compatible tablet-keyboard.service')
    print(version);print('Quickshell side bar; touchscreen devices:',len(touches));print('OSK:',keyboard,'; Hyprgrass loaded:',gestures)
    if not gestures: print('WARNING: four-finger gestures require Hyprgrass Lua; keyboard button remains available')
    return keyboard,shell_path

def clone(source_id,backup):
    directory=HOME/'.config/omarchy/plugins'
    matches=[p.parent for p in directory.glob('*/manifest.json') if json.loads(p.read_text()).get('omarchy',{}).get('clonedFrom')==source_id]
    if len(matches)>1: raise RuntimeError('Multiple clones for '+source_id+'; review manually')
    path=matches[0] if matches else directory/(getpass.getuser()+'.'+source_id.split('.')[-1])
    if not matches and path.exists(): raise RuntimeError('Unrelated plugin directory exists: '+str(path))
    backup.before(path)
    if not matches: subprocess.run(['omarchy','plugin','clone',source_id],check=True)
    if not path.exists(): raise RuntimeError('Clone path differs from inspected username')
    return path

def install(args):
    keyboard,shell_path=detect()
    anchor='      // A child of the loader, not a sibling of the sections: an ancestor stays'
    if (shell_path/'plugins/bar/Bar.qml').read_text().count(anchor)!=1: raise RuntimeError('Omarchy bar adapter anchor changed; review source first')
    print('Plan: controller, compact OSK/bar, dock icon, passive dock adapter, gesture include'+(', lock keyboard' if args.with_lock else '')+(', administrator-dialog keyboard' if args.with_polkit else ''))
    if args.dry_run:
        print('Dry-run: no desktop files modified');return
    if args.with_lock: subprocess.run(['python3',str(SOURCE/'review/login/prepare.py')],check=True)
    if args.with_polkit: subprocess.run(['python3',str(SOURCE/'review/login/prepare-polkit.py')],check=True)
    backup=Backup()
    if 'keyboard_enabled' not in backup.data:
        previous=subprocess.run(['systemctl','--user','is-enabled','tablet-keyboard.service'],capture_output=True,text=True)
        backup.data['keyboard_enabled']=previous.stdout.strip()=='enabled'
        backup.data['keyboard_active']=subprocess.run(['systemctl','--user','is-active','--quiet','tablet-keyboard.service']).returncode==0
        backup.save()
    if (TARGET/'bin/tablet-mode').exists(): subprocess.run([str(TARGET/'bin/tablet-mode'),'exit'],check=True)
    unit_dir=HOME/'.config/systemd/user';unit_dir.mkdir(parents=True,exist_ok=True)
    for p in [TARGET,HOME/'.config/omarchy/shell.json',HOME/'.config/omarchy/shell.toml',HOME/'.config/hypr/input.lua',unit_dir/'tablet-keyboard.service',unit_dir/'omarchy-tablet-mode-ui.service']: backup.before(p)
    try:
        for folder in ['bin','ui','dock','hypr','assets']: shutil.copytree(SOURCE/folder,TARGET/folder,dirs_exist_ok=True)
        for p in (TARGET/'bin').iterdir(): p.chmod(0o755)
        shutil.copy2(SOURCE/'systemd/omarchy-tablet-mode-ui.service',unit_dir/'omarchy-tablet-mode-ui.service')
        unit=unit_dir/'tablet-keyboard.service'
        if unit.exists():
            text=re.sub(r'(?<= -H )\d+','250',unit.read_text());text=re.sub(r'(?<= -L )\d+','250',text);unit.write_text(text)
        else: unit.write_text(f'[Unit]\nDescription=Touch keyboard for Tablet Mode\nPartOf=graphical-session.target\nAfter=graphical-session.target\n\n[Service]\nExecStart={keyboard} --hidden --wayland-layer top -H 250 -L 250\nRestart=on-failure\n\n[Install]\nWantedBy=graphical-session.target\n')
        bar=clone('omarchy.bar',backup);p=bar/'Bar.qml';text=p.read_text()
        if 'TabletDockTracker {' not in text:
            if text.count(anchor)!=1: raise RuntimeError('Custom bar changed; cannot insert adapter safely')
            p.write_text(text.replace(anchor,'      TabletDockTracker { anchors.fill: parent; bar: root }\n\n'+anchor))
        shutil.copy2(SOURCE/'dock/TabletDockTracker.qml',bar/'TabletDockTracker.qml')
        for flag,source_id,pairs in [(args.with_lock,'omarchy.lock',[('LockView.proposed.qml','LockView.qml'),('Service.proposed.qml','Service.qml')]),(args.with_polkit,'omarchy.polkit',[('PolkitAgent.proposed.qml','PolkitAgent.qml')])]:
            if not flag: continue
            plugin=clone(source_id,backup)
            for source_name,target_name in pairs:
                p=plugin/target_name;original=shell_path/'plugins'/source_id.split('.')[-1]/target_name
                if p.exists() and original.exists() and 'keyboardVisible' not in p.read_text() and 'keyboardRequested' not in p.read_text() and p.read_text()!=original.read_text(): raise RuntimeError('Custom authentication clone changed; review before replacing '+str(p))
                shutil.copy2(SOURCE/'review/login'/source_name,p)
            shutil.copy2(SOURCE/'review/login/TouchKeyboard.qml',plugin/'TouchKeyboard.qml')
        shell_file=HOME/'.config/omarchy/shell.json';config=json.loads(shell_file.read_text())
        entry={'id':'tablet-mode','type':'qml','source':str(TARGET/'dock/TabletButton.qml')};found=False
        for section in ['left','center','right']:
            items=config['bar']['layout'].setdefault(section,[])
            for index,item in enumerate(items):
                if item.get('id')=='tablet-mode': items[index]=entry;found=True
        if not found: config['bar']['layout']['left'].insert(0,entry)
        shell_file.write_text(json.dumps(config,indent=2)+'\n')
        style_file=HOME/'.config/omarchy/shell.toml';style=style_file.read_text() if style_file.exists() else ''
        values={'size-vertical':64,'icon-slot':54,'icon-canvas':28,'icon-font':22,'status-slot':40}
        if '[bar]' not in style: style+='\n[bar]\n'+'\n'.join(f'{k} = {v}' for k,v in values.items())+'\n'
        else:
            for key,value in values.items(): style=re.sub(rf'(?m)^{re.escape(key)}\s*=\s*\d+',f'{key} = {value}',style)
        style_file.write_text(style)
        input_file=HOME/'.config/hypr/input.lua';text=input_file.read_text()
        if '/omarchy-tablet-mode/hypr/keyboard-gestures.lua' not in text: input_file.write_text(text.rstrip()+'\n\n-- Omarchy Tablet Mode keyboard gestures\ndofile(os.getenv("HOME") .. "/.local/share/omarchy-tablet-mode/hypr/keyboard-gestures.lua")\n')
        backup.finish()
    except Exception:
        backup.restore(force=True);raise
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable','tablet-keyboard.service'],check=True)
    subprocess.run(['systemctl','--user','restart','tablet-keyboard.service'],check=True)
    subprocess.run(['hyprctl','reload'],check=True)
    errors=run('hyprctl','configerrors')
    if errors: raise RuntimeError('Hyprland configuration errors: '+errors)
    print('Installed; Tablet Mode starts off. Backup:',backup.data['backup'])
    if args.with_polkit or args.with_lock: print('When unlocked and no authorization dialog is open, run: omarchy restart shell')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ['dry-run','with-lock','with-polkit','uninstall','force']: parser.add_argument('--'+option,action='store_true')
    args=parser.parse_args()
    if not args.uninstall: return install(args)
    if not MANIFEST.exists(): raise RuntimeError('No installer manifest; use the original manual backups')
    if args.dry_run:
        print('Would restore:',*json.loads(MANIFEST.read_text())['files'],sep='\n');return
    backup=Backup()
    if not args.force: backup.check()
    subprocess.run([str(TARGET/'bin/tablet-mode'),'exit'],check=True)
    subprocess.run(['systemctl','--user','stop','tablet-keyboard.service'],check=True)
    subprocess.run(['systemctl','--user','disable','tablet-keyboard.service'],check=True)
    backup.restore(force=args.force)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    if backup.data.get('keyboard_enabled'): subprocess.run(['systemctl','--user','enable','tablet-keyboard.service'],check=True)
    if backup.data.get('keyboard_active'): subprocess.run(['systemctl','--user','start','tablet-keyboard.service'],check=True)
    subprocess.run(['hyprctl','reload'],check=True)
    print('Restored saved configuration; backups retained. Restart unlocked Omarchy shell to restore cloned services.')

if __name__=='__main__':
    try: main()
    except (RuntimeError,subprocess.CalledProcessError) as error: raise SystemExit(str(error))

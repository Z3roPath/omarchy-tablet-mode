#!/usr/bin/env python3
"""Syntax and meaningful non-destructive installer rollback checks."""
import ast
import importlib.util
import subprocess
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for path in root.rglob('*.py'):
    ast.parse(path.read_text(),filename=str(path))
for path in (root/'bin').iterdir():
    subprocess.run(['bash','-n',str(path)],check=True)
spec=importlib.util.spec_from_file_location('tablet_install',root/'install.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as temp:
    base=Path(temp)
    module.STATE=base/'state';module.MANIFEST=module.STATE/'install.json'
    original=base/'config.json';original.write_text('original customization')
    new=base/'new-script'
    backup=module.Backup()
    backup.before(original);backup.before(new)
    original.write_text('installed');new.write_text('new script')
    backup.finish()
    rerun=module.Backup();rerun.before(original);rerun.before(new)
    original.write_text('updated');rerun.finish()
    assert rerun.data['backup']==backup.data['backup']
    original.write_text('later user edit')
    try:
        rerun.restore()
        raise AssertionError('Rollback overwrote a later user edit')
    except RuntimeError:
        assert original.read_text()=='later user edit'
        assert new.exists(), 'Conflict preflight partially removed installed files'
    original.write_text('updated')
    rerun.restore()
    assert original.read_text()=='original customization'
    assert not new.exists()
    assert Path(backup.data['backup']).exists()
print('PASS: source syntax, re-run backups, edit-conflict refusal, exact rollback')

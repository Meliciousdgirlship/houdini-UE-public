"""Publish OBJ/MTL together and retain a recoverable previous bundle."""
import shutil
from pathlib import Path

SUFFIXES=('.obj','.mtl','.spec.json')

def capture(target, backup):
    target,backup=Path(target),Path(backup)
    backup.mkdir(parents=True,exist_ok=True)
    existed={}
    for suffix in SUFFIXES:
        file=target.with_suffix(suffix); existed[suffix]=file.exists()
        if file.exists(): shutil.copy2(file,backup/('previous'+suffix))
    return existed

def publish_geometry(staged,target):
    for suffix in ('.mtl','.obj'):
        src=Path(staged).with_suffix(suffix)
        if not src.is_file() or not src.stat().st_size:
            raise RuntimeError('Missing generated file: '+str(src))
    for suffix in ('.mtl','.obj'):
        dest=Path(target).with_suffix(suffix)
        pending=dest.with_name(dest.name+'.pending')
        shutil.copy2(Path(staged).with_suffix(suffix),pending)
        pending.replace(dest)

def restore(target,backup,existed):
    for suffix in SUFFIXES:
        dest=Path(target).with_suffix(suffix)
        if existed[suffix]: shutil.copy2(Path(backup)/('previous'+suffix),dest)
        else: dest.unlink(missing_ok=True)

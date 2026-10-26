"""Keep Google's signed USB tools loadable by their standalone child process."""
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import uuid

HASHES = {
    'adb.exe': 'b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f',
    'AdbWinApi.dll': 'c1d653030b4bde65d3e07e4d0b0979e17be56df1436cdd15528630f27808050d',
    'AdbWinUsbApi.dll': '0710e894d9b40f71a670c13c694079d564c92c1279da382cfe4850983aaebe1b',
}


@lru_cache(maxsize=1)
def adb_path(root):
    from camera_helper import packaged
    source = Path(root)/'android-tools'/'platform-tools'
    if not packaged():
        return source/'adb.exe'
    version = hashlib.sha256(''.join(HASHES.values()).encode()).hexdigest()[:24]
    folder = Path(os.environ['LOCALAPPDATA'])/'CamTetherUsb'/version
    folder.mkdir(parents=True, exist_ok=True)
    for name, expected in HASHES.items():
        target = folder/name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        data = (source/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('USB tool integrity check failed: '+name)
        temporary = folder/(name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_bytes(data)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return folder/'adb.exe'


def remove_files():
    """Remove only the bundled tool versions; preserve unrelated user files."""
    base = Path(os.environ['LOCALAPPDATA'])/'CamTetherUsb'
    if not base.exists():
        return
    failures = []
    for folder in base.iterdir():
        if folder.is_symlink() or not folder.is_dir() or len(folder.name) != 24 or any(c not in '0123456789abcdef' for c in folder.name):
            continue
        for name, expected in HASHES.items():
            target = folder/name
            if target.is_symlink() or not target.is_file():
                continue
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                continue
            try:
                target.unlink()
            except OSError as error:
                failures.append(error)
        try:
            folder.rmdir()
        except OSError:
            pass
    try:
        base.rmdir()
    except OSError:
        pass
    adb_path.cache_clear()
    if failures or base.exists():
        raise RuntimeError('USB cache cleanup is incomplete. Close apps using ADB and retry. Unrecognized files were preserved at '+str(base))

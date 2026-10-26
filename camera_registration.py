"""Publish the bundled signed camera filter for desktop consumers.

Only CamTether-owned HKCU registrations are removed. Machine-wide OBS keys are
never changed. Small signed filter files live outside WindowsApps because Windows
blocks loading in-process COM servers from ordinary MSIX install directories.
"""
import ctypes as C
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import uuid
import winreg

CLSID = '{A3FCE0F5-3493-419F-958A-ABA1250EC20B}'
CLASS_KEY = 'Software\\Classes\\CLSID\\' + CLSID
KEY = r'Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\CamTether'
VIEWS = (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)
OWNER = 'CamTetherCameraOwner'
ROOT = Path(__file__).resolve().parent
_helper = None


@contextmanager
def _create_key(path, view):
    create = C.WinDLL('advapi32').RegCreateKeyExW
    create.argtypes = [C.c_void_p, C.c_wchar_p, C.c_uint32, C.c_wchar_p,
                       C.c_uint32, C.c_uint32, C.c_void_p,
                       C.POINTER(C.c_void_p), C.POINTER(C.c_uint32)]
    create.restype = C.c_long
    handle = C.c_void_p()
    result = create(C.c_void_p(0xffffffff80000001), path, 0, None, 1,
                    winreg.KEY_WRITE | view, None, C.byref(handle), None)
    if result:
        raise C.WinError(result)
    try:
        yield handle.value
    finally:
        winreg.CloseKey(handle.value)


def _filter_files():
    native = ROOT / 'native'
    manifest = json.loads((native / 'provenance.json').read_text())['files']
    names = ('obs-virtualcam-module64.dll', 'obs-virtualcam-module32.dll', 'placeholder.png')
    version = hashlib.sha256(''.join(manifest[n]['sha256'] for n in names).encode()).hexdigest()[:24]
    folder = Path(os.environ['LOCALAPPDATA']) / 'CamTetherCamera' / version
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = folder / name
        expected = manifest[name]['sha256']
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        data = (native / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Camera component integrity check failed: ' + name)
        temporary = folder / (name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_bytes(data)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return folder


def _owned(view):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLASS_KEY, 0,
                            winreg.KEY_READ | view) as key:
            try:
                if winreg.QueryValueEx(key, OWNER)[0] != 'CamTether':
                    return False
                try:
                    with winreg.OpenKey(key, 'InprocServer32') as child:
                        dll = Path(winreg.QueryValueEx(child, '')[0])
                    base = Path(os.environ['LOCALAPPDATA']) / 'CamTetherCamera'
                    return dll.name in ('obs-virtualcam-module64.dll', 'obs-virtualcam-module32.dll') and dll.resolve().is_relative_to(base.resolve())
                except FileNotFoundError:
                    return True  # a partially created registration
            except FileNotFoundError:
                return None if winreg.QueryInfoKey(key)[:2] == (0, 0) else False
    except FileNotFoundError:
        return None


def _existing_filter(view):
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'CLSID\\' + CLSID + r'\InprocServer32',
                            0, winreg.KEY_READ | view) as key:
            path = Path(winreg.QueryValueEx(key, '')[0].strip('"'))
        if not path.is_file():
            raise RuntimeError('An existing OBS camera registration points to a missing file.')
        return path
    except FileNotFoundError:
        return None


def register():
    global _helper
    from camera_helper import packaged, RegistrationHelper
    if packaged():
        if _helper is None:
            _helper = RegistrationHelper(ROOT, _filter_files())
        return
    existing = {view: None if _owned(view) else _existing_filter(view) for view in VIEWS}
    if any(_owned(view) is False and existing[view] is None for view in VIEWS):
        raise RuntimeError('An incomplete per-user camera registration belongs to another application.')
    folder = _filter_files() if not all(existing.values()) else None
    # Existing OBS registrations are reused without shadowing or changing them.
    try:
        for view, bits in zip(VIEWS, (64, 32)):
            if existing[view] is None:
                with _create_key(CLASS_KEY, view) as key:
                    winreg.SetValueEx(key, OWNER, 0, winreg.REG_SZ, 'CamTether')
                with _create_key(CLASS_KEY + r'\InprocServer32', view) as key:
                    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(folder / f'obs-virtualcam-module{bits}.dll'))
                    winreg.SetValueEx(key, 'ThreadingModel', 0, winreg.REG_SZ, 'Both')
            with _create_key(KEY, view) as key:
                winreg.SetValueEx(key, 'CLSID', 0, winreg.REG_SZ, CLSID)
                winreg.SetValueEx(key, 'FriendlyName', 0, winreg.REG_SZ, 'CamTether')
    except Exception as original:
        try:
            unregister()
        except Exception as cleanup:
            raise ExceptionGroup('Camera setup and cleanup failed', [original, cleanup]) from original
        raise


def unregister():
    global _helper
    if _helper is not None:
        helper, _helper = _helper, None
        helper.close()
        return
    from camera_helper import packaged
    if packaged():
        return
    errors = []
    for view in VIEWS:
        paths = [KEY]
        if _owned(view):
            paths += [CLASS_KEY + r'\InprocServer32', CLASS_KEY]
        for path in paths:
            try:
                winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path, view)
            except FileNotFoundError:
                pass
            except OSError as error:
                errors.append(error)
    if errors:
        raise errors[0]


def check():
    if _helper is not None:
        _helper.check()


def remove_files():
    """Explicit uninstall preparation: delete only hash-verified CamTether files."""
    base = Path(os.environ['LOCALAPPDATA']) / 'CamTetherCamera'
    if not base.exists():
        return
    inventory = json.loads((ROOT / 'native/provenance.json').read_text())['files']
    failures = []
    for folder in base.iterdir():
        if folder.is_symlink() or not folder.is_dir() or len(folder.name) != 24 or any(c not in '0123456789abcdef' for c in folder.name):
            continue
        for name in ('obs-virtualcam-module64.dll', 'obs-virtualcam-module32.dll', 'placeholder.png'):
            path = folder / name
            if not path.is_file() or path.is_symlink():
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != inventory[name]['sha256']:
                continue
            try:
                path.unlink()
            except OSError as error:
                failures.append(error)
        try:
            folder.rmdir()
        except OSError:
            pass  # preserve unrecognized files and still-loaded DLLs
    try:
        base.rmdir()
    except OSError:
        pass
    if failures:
        raise RuntimeError('Close meeting apps and browsers, reopen CamTether, then choose Remove webcam components again.') from failures[0]
    if base.exists():
        raise RuntimeError(f'Unrecognized or older camera files were preserved at {base}. Camera registration was removed, but file cleanup is incomplete.')

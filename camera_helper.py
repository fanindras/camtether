"""Call the Store-covered native registration adapter in the app process."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import uuid


def packaged():
    size = W.DWORD()
    return C.windll.kernel32.GetCurrentPackageFullName(C.byref(size), None) != 15700


class RegistrationHelper:
    def __init__(self, root, folder):
        self.registered = False
        kernel = C.WinDLL('kernel32', use_last_error=True)
        kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
        kernel.GetModuleHandleW.restype = W.HMODULE
        kernel.GetProcAddress.argtypes = [W.HMODULE, C.c_char_p]
        kernel.GetProcAddress.restype = C.c_void_p
        module = kernel.GetModuleHandleW(None)
        start = kernel.GetProcAddress(module, b'CamTetherRegisterCamera')
        stop = kernel.GetProcAddress(module, b'CamTetherUnregisterCamera')
        if not start or not stop:
            raise RuntimeError('The native CamTether launcher is required.')
        self.stop = C.WINFUNCTYPE(W.LONG)(stop)
        register = C.WINFUNCTYPE(W.LONG, W.LPCWSTR, W.LPCWSTR)(start)
        result = register(uuid.uuid4().hex, Path(folder).name)
        if result:
            raise RuntimeError(f'Camera registration failed (Windows code {result}).')
        self.registered = True

    def check(self):
        # There is no continuously running broker to poll.
        pass

    def close(self):
        if self.registered:
            result = self.stop()
            self.registered = False
            if result:
                raise RuntimeError(f'Camera registration cleanup failed (Windows code {result}).')

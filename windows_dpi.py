"""Set DPI awareness in the actual GUI process, before Tk creates any window."""
import ctypes
import sys


def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
    if not user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
        error = ctypes.get_last_error()
        # Access denied means awareness was already set by a host/manifest.
        if error != 5:
            raise ctypes.WinError(error)

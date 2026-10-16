"""Packaged USB entry point with a per-user single-instance guard."""
import ctypes,runpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
kernel.CreateMutexW.restype=ctypes.c_void_p
handle=kernel.CreateMutexW(None,False,'Local\\CamTetherDesktopUSB')
if not handle:raise ctypes.WinError(ctypes.get_last_error())
if ctypes.get_last_error()==183:
    import tkinter.messagebox
    tkinter.messagebox.showinfo('CamTether is already running','Use the existing CamTether window. Close it before starting another copy.')
    sys.exit()
sys.argv=[str(root/'phonecam.py'),'--usb','--port','8765']
runpy.run_path(str(root/'phonecam.py'),run_name='__main__')

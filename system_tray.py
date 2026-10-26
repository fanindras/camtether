"""Windows notification-area integration on a dedicated hidden owner window."""
import ctypes as C
from ctypes import wintypes as W
import queue

LRESULT = C.c_ssize_t
WNDPROC = C.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)


class NotifyIconData(C.Structure):
    _fields_ = [('cbSize', W.DWORD), ('hWnd', W.HWND), ('uID', W.UINT),
                ('uFlags', W.UINT), ('uCallbackMessage', W.UINT), ('hIcon', W.HICON),
                ('szTip', W.WCHAR*128), ('dwState', W.DWORD), ('dwStateMask', W.DWORD),
                ('szInfo', W.WCHAR*256), ('uVersion', W.UINT),
                ('szInfoTitle', W.WCHAR*64), ('dwInfoFlags', W.DWORD),
                ('guidItem', C.c_byte*16), ('hBalloonIcon', W.HICON)]


class SystemTray:
    MESSAGE = 0x8000+52

    def __init__(self, window):
        self.events = queue.SimpleQueue()
        self.user = C.WinDLL('user32', use_last_error=True)
        self.shell = C.WinDLL('shell32', use_last_error=True)
        self.user.GetParent.argtypes = [W.HWND]
        self.user.GetParent.restype = W.HWND
        self.user.SetWindowLongPtrW.argtypes = [W.HWND, C.c_int, C.c_void_p]
        self.user.SetWindowLongPtrW.restype = C.c_void_p
        self.user.CallWindowProcW.argtypes = [C.c_void_p, W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        self.user.CallWindowProcW.restype = LRESULT
        self.user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        self.user.SendMessageW.restype = LRESULT
        self.user.RegisterWindowMessageW.argtypes = [W.LPCWSTR]
        self.user.CreatePopupMenu.restype = W.HMENU
        self.user.AppendMenuW.argtypes = [W.HMENU, W.UINT, C.c_size_t, W.LPCWSTR]
        self.user.TrackPopupMenu.argtypes = [W.HMENU, W.UINT, C.c_int, C.c_int, C.c_int, W.HWND, C.c_void_p]
        self.user.TrackPopupMenu.restype = W.UINT
        self.user.DestroyMenu.argtypes = [W.HMENU]
        self.user.SetForegroundWindow.argtypes = [W.HWND]
        self.user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        self.user.LoadIconW.argtypes = [W.HINSTANCE, C.c_void_p]
        self.user.LoadIconW.restype = W.HICON
        self.shell.Shell_NotifyIconW.argtypes = [W.DWORD, C.POINTER(NotifyIconData)]
        self.shell.Shell_NotifyIconW.restype = W.BOOL
        # Tk may recreate the main wrapper HWND when withdrawing/restoring it.
        # Keep a separate owner alive and unchanged for the lifetime of the icon.
        import tkinter as tk
        self.owner = tk.Toplevel(window)
        self.owner.withdraw()
        self.owner.update_idletasks()
        self.hwnd = self.user.GetParent(self.owner.winfo_id()) or self.owner.winfo_id()
        window.update_idletasks()
        icon_hwnd = self.user.GetParent(window.winfo_id()) or window.winfo_id()
        self.taskbar_created = self.user.RegisterWindowMessageW('TaskbarCreated')
        self.callback = WNDPROC(self._window_proc)
        self.previous = self.user.SetWindowLongPtrW(self.hwnd, -4, C.cast(self.callback, C.c_void_p))
        if not self.previous:
            raise C.WinError(C.get_last_error())
        self.data = NotifyIconData()
        self.data.cbSize = C.sizeof(self.data)
        self.data.hWnd, self.data.uID = self.hwnd, 1
        self.data.uFlags = 1|2|4
        self.data.uCallbackMessage = self.MESSAGE
        self.data.hIcon = self.user.SendMessageW(icon_hwnd, 0x7F, 1, 0) or self.user.LoadIconW(None, C.c_void_p(32512))
        self.data.szTip = 'CamTether — USB webcam'
        self.visible = bool(self.shell.Shell_NotifyIconW(0, C.byref(self.data)))
        if not self.visible:
            self.close()
            raise RuntimeError('The Windows system tray is unavailable.')

    def _window_proc(self, hwnd, message, wparam, lparam):
        try:
            if message == self.taskbar_created:
                self.visible = bool(self.shell.Shell_NotifyIconW(0, C.byref(self.data)))
                if not self.visible:
                    self.events.put('open')
                return 0
            if message == self.MESSAGE:
                if lparam in (0x202, 0x203):  # click or double-click
                    self.events.put('open')
                elif lparam == 0x205:  # right button up
                    point = W.POINT()
                    self.user.GetCursorPos(C.byref(point))
                    menu = self.user.CreatePopupMenu()
                    if menu:
                        try:
                            self.user.AppendMenuW(menu, 0, 1, 'Open CamTether')
                            self.user.AppendMenuW(menu, 0x800, 0, None)
                            self.user.AppendMenuW(menu, 0, 2, 'Exit CamTether')
                            self.user.SetForegroundWindow(hwnd)
                            choice = self.user.TrackPopupMenu(menu, 0x100|0x2, point.x, point.y, 0, hwnd, None)
                            if choice:
                                self.events.put('open' if choice == 1 else 'exit')
                            self.user.PostMessageW(hwnd, 0, 0, 0)
                        finally:
                            self.user.DestroyMenu(menu)
                return 0
        except Exception:
            self.events.put('open')  # Never strand the user with a hidden window.
        return self.user.CallWindowProcW(self.previous, hwnd, message, wparam, lparam)

    def close(self):
        if getattr(self, 'visible', False):
            self.shell.Shell_NotifyIconW(2, C.byref(self.data))
            self.visible = False
        if self.previous:
            self.user.SetWindowLongPtrW(self.hwnd, -4, self.previous)
            self.previous = None
        if getattr(self, "owner", None) is not None:
            self.owner.destroy()
            self.owner = None

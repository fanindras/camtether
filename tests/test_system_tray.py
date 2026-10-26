import queue
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_tray import SystemTray, NotifyIconData


class TrayTests(unittest.TestCase):
    def tray(self):
        tray = SystemTray.__new__(SystemTray)
        tray.events = queue.SimpleQueue()
        tray.user = MagicMock()
        tray.shell = MagicMock()
        tray.previous = 123
        tray.hwnd = 456
        tray.taskbar_created = 900
        tray.data = NotifyIconData()
        tray.visible = True
        return tray

    def test_double_click_queues_restore_on_tk_loop(self):
        tray = self.tray()
        self.assertEqual(tray._window_proc(456, tray.MESSAGE, 1, 0x203), 0)
        self.assertEqual(tray.events.get_nowait(), 'open')

    def test_explorer_restart_failure_restores_window(self):
        tray = self.tray()
        tray.shell.Shell_NotifyIconW.return_value = False
        tray._window_proc(456, tray.taskbar_created, 0, 0)
        self.assertFalse(tray.visible)
        self.assertEqual(tray.events.get_nowait(), 'open')

    def test_exit_menu_always_releases_menu(self):
        tray = self.tray()
        tray.user.CreatePopupMenu.return_value = 42
        tray.user.TrackPopupMenu.return_value = 2
        tray._window_proc(456, tray.MESSAGE, 1, 0x205)
        self.assertEqual(tray.events.get_nowait(), 'exit')
        tray.user.DestroyMenu.assert_called_once_with(42)

    def test_close_restores_window_procedure_once(self):
        tray = self.tray()
        tray.close()
        tray.close()
        tray.user.SetWindowLongPtrW.assert_called_once_with(456, -4, 123)
        tray.shell.Shell_NotifyIconW.assert_called_once()


if __name__ == '__main__':
    unittest.main()

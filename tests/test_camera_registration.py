import ctypes as C
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import camera_registration as registration


class RegistrationTests(unittest.TestCase):
    def test_removal_reports_and_preserves_unknown_cached_files(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'CamTetherCamera' / ('a' * 24)
            folder.mkdir(parents=True)
            cached = folder / 'obs-virtualcam-module64.dll'
            cached.write_bytes(b'older or unrecognized component')
            with patch.dict(registration.os.environ, LOCALAPPDATA=directory):
                with self.assertRaisesRegex(RuntimeError, 'cleanup is incomplete'):
                    registration.remove_files()
            self.assertEqual(cached.read_bytes(), b'older or unrecognized component')

    def test_both_views_use_volatile_keys(self):
        def create(*args):
            self.assertEqual(args[4], 1)  # REG_OPTION_VOLATILE
            C.cast(args[7], C.POINTER(C.c_void_p))[0] = 42
            return 0
        function = MagicMock(side_effect=create)
        with patch.object(registration.C, 'WinDLL') as dll, \
             patch.object(registration.winreg, 'CloseKey'), \
             patch.object(registration.winreg, 'SetValueEx') as write:
            dll.return_value.RegCreateKeyExW = function
            for view in registration.VIEWS:
                with registration._create_key(registration.KEY, view):
                    pass
        self.assertEqual(function.call_count, 2)
        self.assertEqual(write.call_count, 0)
        self.assertEqual([call.args[5] for call in function.call_args_list],
                         [registration.winreg.KEY_WRITE | v for v in registration.VIEWS])

    def test_partial_failure_cleans_both_views(self):
        with patch.object(registration.C, 'WinDLL') as dll, \
             patch.object(registration, '_owned', return_value=None), \
             patch.object(registration, '_existing_filter', return_value=None), \
             patch.object(registration, '_filter_files', return_value=Path('test')), \
             patch.object(registration, 'unregister') as cleanup:
            dll.return_value.RegCreateKeyExW.return_value = 5
            with self.assertRaises(OSError):
                registration.register()
            cleanup.assert_called_once()

    def test_cleanup_attempts_both_views_even_if_one_fails(self):
        with patch.object(registration, '_owned', return_value=False), \
             patch.object(registration.winreg, 'DeleteKeyEx',
                          side_effect=[PermissionError('denied'), None]) as delete:
            with self.assertRaises(PermissionError):
                registration.unregister()
            self.assertEqual(delete.call_count, 2)

    def test_existing_obs_registration_is_not_shadowed(self):
        with patch.object(registration, '_owned', return_value=False), \
             patch.object(registration, '_existing_filter', return_value=Path('existing.dll')), \
             patch.object(registration, '_filter_files') as files, \
             patch.object(registration, '_create_key') as create, \
             patch.object(registration.winreg, 'SetValueEx'):
            registration.register()
        files.assert_not_called()
        self.assertEqual([c.args[0] for c in create.call_args_list], [registration.KEY]*2)

    def test_cleanup_is_idempotent(self):
        with patch.object(registration, '_owned', return_value=False), \
             patch.object(registration.winreg, 'DeleteKeyEx',
                          side_effect=FileNotFoundError) as delete:
            registration.unregister()
            self.assertEqual(delete.call_count, 2)


if __name__ == '__main__':
    unittest.main()

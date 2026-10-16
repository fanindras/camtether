import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app_paths import user_data_dir
from effects import Effects
class StorageTests(unittest.TestCase):
    def test_readonly_install_root_and_persistent_settings(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root=Path(tmp)/'missing-install-dir'
            data=Path(tmp)/'user'/'CamTether'
            with patch.dict(os.environ,{'CAMTETHER_DATA_DIR':str(data)}):
                fx=Effects(root,storage=user_data_dir());fx.set(zoom=1.4);fx.save()
                self.assertFalse(root.exists())
                self.assertEqual(Effects(root,storage=user_data_dir()).snapshot()[0]['zoom'],1.4)

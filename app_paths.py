"""Keep mutable state outside the read-only MSIX installation."""
import os
from pathlib import Path

def user_data_dir():
    override=os.environ.get('CAMTETHER_DATA_DIR')
    base=Path(override) if override else Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'CamTether'
    base.mkdir(parents=True,exist_ok=True)
    return base

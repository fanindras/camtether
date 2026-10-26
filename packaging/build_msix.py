"""Build an unsigned Store-submission candidate from an audited runtime payload."""
import argparse,hashlib,json,shutil,subprocess,sys
import xml.etree.ElementTree as ET
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--payload',type=Path,required=True)
parser.add_argument('--makeappx',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--rc',type=Path,required=True,help='Windows SDK resource compiler for application icon and manifest')
parser.add_argument('--zig',type=Path,required=True,help='Zig compiler for the native launcher; production builds never enable validation-only filter overrides')
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
stage=args.output/'staging'
if stage.exists():raise SystemExit('Use a fresh output directory to avoid stale package contents')
stage.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.local','*.pfx','*.pem','error.log','bin','venvlauncher.exe','venvwlauncher.exe','nmake.exe',
    '*-nmakehlp.exe','pyvirtualcam*','cryptography*','cffi*','_cffi_backend*','pycparser*')
for folder in ('runtime','vendor','models'):
    shutil.copytree(args.payload/folder,stage/folder,ignore=ignore)
adb=stage/'android-tools'/'platform-tools';adb.mkdir(parents=True)
for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll','NOTICE.txt','source.properties'):
    shutil.copy2(args.payload/'android-tools'/'platform-tools'/name,adb/name)
for name in ('phonecam.py','effects.py','desktop.py','ui_theme.py','system_tray.py','video_quality.py','gpu_usage.py','camera_helper.py','usb_runtime.py','auto_keystone.py','phone_control.py','phone.html','app_paths.py','launch.py','obs_camera.py','camera_registration.py','windows_dpi.py','LICENSE','PRIVACY.md','THIRD_PARTY.md'):
    shutil.copy2(repo/name,stage/name)
shutil.copytree(repo/'licenses',stage/'licenses')
(stage/'branding').mkdir()
shutil.copy2(repo/'branding/phone-usb.png',stage/'branding/phone-usb.png')
native_names = {'obs-virtualcam-module32.dll', 'obs-virtualcam-module64.dll',
                'swscale-9.dll', 'avutil-60.dll', 'placeholder.png'}
provenance = json.loads((repo/'native/provenance.json').read_text())
if set(provenance['files']) != native_names:
    raise SystemExit('Native component inventory does not match the release allowlist')
(stage/'native').mkdir()
for name in sorted(native_names):
    source = repo/'native'/name
    if hashlib.sha256(source.read_bytes()).hexdigest() != provenance['files'][name]['sha256']:
        raise SystemExit('Native component hash mismatch: '+name)
    shutil.copy2(source, stage/'native'/name)
shutil.copy2(repo/'native/provenance.json', stage/'native/provenance.json')
shutil.copy2(repo/'packaging'/'AppxManifest.xml',stage/'AppxManifest.xml')
shutil.copytree(repo/'packaging'/'Assets',stage/'Assets')
resource=args.output/'Launcher.res'
subprocess.run([str(args.rc.resolve()),'/nologo','/fo',str(resource),'/I',str(repo/'packaging'),str(repo/'packaging/Launcher.rc')],check=True)
subprocess.run([str(args.zig.resolve()),'cc','-target','x86_64-windows-gnu','-O2',
    '-municode','-Wl,--subsystem,windows',str(repo/'packaging'/'Launcher.c'),str(resource),
    '-o',str(stage/'CamTether.exe'),'-ladvapi32','-lshell32','-luser32','-lole32','-loleaut32'],check=True)
# Linker symbols and import libraries are development artifacts, not app payload.
for extension in ('*.pdb','*.lib'):
    for artifact in stage.glob(extension):
        artifact.unlink()
manifest={str(p.relative_to(stage)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
(args.output/'payload-sha256.json').write_text(json.dumps(manifest,indent=2))
identity=ET.parse(stage/'AppxManifest.xml').getroot().find('{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity')
package=args.output/f"CamTether-{identity.attrib['Version']}-{identity.attrib['ProcessorArchitecture']}.msix"
subprocess.run([str(args.makeappx.resolve()),'pack','/d',str(stage),'/p',str(package),'/o'],check=True)
(args.output/'SHA256.txt').write_text(hashlib.sha256(package.read_bytes()).hexdigest()+'  '+package.name+'\n')
print(package)

"""Build an unsigned Store-submission candidate from an audited runtime payload."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--payload',type=Path,required=True)
parser.add_argument('--makeappx',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
stage=args.output/'staging'
if stage.exists():raise SystemExit('Use a fresh output directory to avoid stale package contents')
stage.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.local','*.pfx','*.pem','error.log')
for folder in ('runtime','vendor','models'):
    shutil.copytree(args.payload/folder,stage/folder,ignore=ignore)
adb=stage/'android-tools'/'platform-tools';adb.mkdir(parents=True)
for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll','NOTICE.txt','source.properties'):
    shutil.copy2(args.payload/'android-tools'/'platform-tools'/name,adb/name)
for name in ('phonecam.py','effects.py','desktop.py','auto_keystone.py','phone_control.py','phone.html','app_paths.py','launch.py','LICENSE','PRIVACY.md','THIRD_PARTY.md'):
    shutil.copy2(repo/name,stage/name)
shutil.copy2(repo/'packaging'/'AppxManifest.xml',stage/'AppxManifest.xml')
shutil.copytree(repo/'packaging'/'Assets',stage/'Assets')
csc=Path(__import__('os').environ['WINDIR'])/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
subprocess.run([str(csc),'/nologo','/target:winexe','/platform:x64','/reference:System.Windows.Forms.dll','/out:'+str(stage/'CamTether.exe'),str(repo/'packaging'/'Launcher.cs')],check=True)
manifest={str(p.relative_to(stage)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
(args.output/'payload-sha256.json').write_text(json.dumps(manifest,indent=2))
package=args.output/'CamTether-1.1.1.0-x64.msix'
subprocess.run([str(args.makeappx.resolve()),'pack','/d',str(stage),'/p',str(package),'/o'],check=True)
(args.output/'SHA256.txt').write_text(hashlib.sha256(package.read_bytes()).hexdigest()+'  '+package.name+'\n')
print(package)

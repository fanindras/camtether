# CamTether

Use an Android phone as a Windows USB webcam with local framing and background controls.
Formerly PhoneCam. Video travels through ADB reverse forwarding to a loopback server
and the CamTether camera endpoint. Keep the phone browser visible and unlocked.

## Release status

Version 1.1.4.0 is an unsigned MSIX submission candidate, not a published Store app.
The Microsoft Store name is reserved (9PLVZCDDDT9H). Do not disable Smart App Control
or install a self-signed certificate. Microsoft signs accepted MSIX submissions.
See [submission preparation](submission/README.md) for remaining release gates.

The Precision-interface candidate uses the Windows registry provider to publish
the current-user camera outside MSIX's private registry view. Installed capture,
cleanup and certification evidence is recorded under submission/ before release.

## Interface

The Precision layout includes a left navigation rail, larger bold controls,
an aligned status footer, and saved Light / Dark appearance. The phone-and-USB
logo appears in both themes. Video stays on the Device.

Close / X keeps the camera running in the Windows system tray. Double-click the
CamTether tray icon to reopen, or right-click it for **Open CamTether** and
**Exit CamTether**. An Exit button is also available in Connect. If the system
tray is unavailable, the app asks before exiting instead of hiding the window.
Hidden preview rendering pauses and UI polling slows; camera output continues.

## Developer setup

Windows 11 x64 and Python 3.13 are required. OBS Studio is not required.
The small camera filters and conversion DLLs are bundled under native/; their
source and hashes are documented in THIRD_PARTY.md and native/provenance.json.
CamTether registers its signed camera filter for the current user when needed.
An existing valid OBS camera registration is reused unchanged. Obtain Android SDK Platform
Tools from https://developer.android.com/tools/releases/platform-tools and extract
platform-tools into android-tools/. Install dependencies and launch:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python phonecam.py --usb --port 8765
```

Enable USB debugging and authorize the laptop. Use Wake phone & start camera, then
grant Chrome camera access. Select CamTether in the receiving app and use
the laptop microphone. Keep OBS's own virtual-camera producer stopped while
CamTether owns the endpoint. A PIN or fingerprint still needs your action.

Background effects require the OpenCV Zoo PP-HumanSeg 2023mar model at
models/humanseg.onnx. See THIRD_PARTY.md for its verified upstream hash.
Original-background mode does not require the model. No personal image is bundled.

Settings and selected background images are stored under %LOCALAPPDATA%\CamTether,
with Windows package virtualization applying when installed. They are not written
into the MSIX install directory. Existing PhoneCam settings are not automatically
imported; choose the background in CamTether once. CAMTETHER_DATA_DIR overrides the
data directory for isolated testing.

## Efficiency and testing

720p output targets 30 fps without lowering JPEG quality. The editor preview is
limited to 10 fps and pauses when hidden. Capture holds one latest pending frame,
not a video queue. Static backgrounds and masks use bounded caches. Actual frame
rate depends on hardware, effects, and concurrent OBS load.

Run `python -m unittest discover -s tests -v` after installing dependencies and
providing the model. CAMTETHER_ASSETS can point to a staged runtime for model tests.
The build recipe is in packaging/build_msix.py; it requires an audited payload
containing runtime/, vendor/, models/ and android-tools/platform-tools/. The native/
components are hash-checked before packaging. Dependencies
are not downloaded silently by the build. See submission/VALIDATION.md.

## License and privacy

Original files retain the MIT license. The OBS-derived adapter and the combined
distribution are GPL-3.0-or-later. pyvirtualcam and cryptography are no longer
bundled. See THIRD_PARTY.md, licenses/GPL-3.0.txt and PRIVACY.md.

See [1.1.1 review and measurements](submission/REVIEW-1.1.1.md) for reconnect fixes and CPU tradeoffs.

## Removing the webcam component

Close meeting apps and browsers, then choose **Remove webcam components** in
CamTether before uninstalling it from Windows Settings. This removes only
CamTether-owned camera registrations and verified component files. Existing OBS
installations are preserved. A forced termination can leave a camera entry until
CamTether runs again and exits normally or removes its components.

### Video quality and performance
Choose 540p (960 x 540), 720p (1280 x 720, default), or 1080p (1920 x 1080) in Frame. All target 30 fps. The saved preference applies while CamTether stays open, with a short video interruption as the output changes. Some meeting apps retain their negotiated format until you reselect the camera. The top-right preview badge shows the active output size and indicates a pending change. Actual phone detail and delivered frame rate depend on the hardware; no automatic resolution downgrade occurs. Higher resolution uses more CPU, memory and USB bandwidth; the meeting app may also use more GPU resources.

Use Start phone camera on the Device to open the camera through the authorized USB connection. Unlock the phone and grant camera access if prompted. The front camera is the initial default; subsequent camera selections are remembered.

### Lighting and flicker
In Adjust, select Auto, 50 Hz or 60 Hz under Anti-flicker lighting. Changes apply during the live stream without restarting CamTether. When the phone browser exposes manual exposure, 50 Hz requests a 10 ms shutter and 60 Hz requests approximately 8.33 ms. CamTether verifies the camera's reported exposure before displaying confirmation. Unsupported settings show unavailable and attempt to restore automatic exposure, with an explicit warning if restoration cannot be confirmed. Auto returns to automatic exposure. Manual shutter timing can change brightness and cannot eliminate every LED/PWM flicker pattern; this is not a guaranteed native camera anti-banding control.

The footer samples the busiest GPU engine across the Device every two seconds using Windows PDH, without launching subprocesses. Unsupported counters show unavailable, never a fabricated zero. Effects and color conversion currently run on the CPU. Processing time appears below the preview; consistently exceeding 33 ms cannot sustain 30 processed frames per second. Performance & optimization explains ways to reduce competing load without reducing output quality.

Registration lifecycle: the installed app uses Windows' local registry provider at startup and shutdown, with no continuously running CamTether broker. Registrations are persistent until normal shutdown removes the entries belonging to that session. A crash can leave an entry until the next successful start and cleanup. Unrecognized entries and values are preserved. Close CamTether and use Remove webcam components before uninstalling if a prior session crashed.

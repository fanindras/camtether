# CamTether

Use an Android phone as a Windows USB webcam with local framing and background controls.
Formerly PhoneCam. Video travels through ADB reverse forwarding to a loopback server
and the OBS Virtual Camera endpoint. Keep the phone browser visible and unlocked.

## Release status

Version 1.1.2.0 is an unsigned MSIX submission candidate, not a published Store app.
The Microsoft Store name is reserved (9PLVZCDDDT9H). Do not disable Smart App Control
or install a self-signed certificate. Microsoft signs accepted MSIX submissions.
See [submission preparation](submission/README.md) for remaining release gates.

## Developer setup

Windows x64, Python 3.13, and OBS Studio 32.2.2 (64-bit) are required.
The adapter currently supports its FFmpeg 8 libraries (swscale-9 / avutil-60);
other ABI versions are rejected with an explicit message. Obtain Android SDK Platform
Tools from https://developer.android.com/tools/releases/platform-tools and extract
platform-tools into android-tools/. Install dependencies and launch:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python phonecam.py --usb --port 8765
```

Enable USB debugging and authorize the laptop. Use Wake phone & start camera, then
grant Chrome camera access. Select OBS Virtual Camera in the receiving app and use
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
containing runtime/, vendor/, models/ and android-tools/platform-tools/. Dependencies
are not downloaded silently by the build. See submission/VALIDATION.md.

## License and privacy

Original files retain the MIT license. The OBS-derived adapter and the combined
distribution are GPL-3.0-or-later. pyvirtualcam and cryptography are no longer
bundled. See THIRD_PARTY.md, licenses/GPL-3.0.txt and PRIVACY.md.

See [1.1.1 review and measurements](submission/REVIEW-1.1.1.md) for reconnect fixes and CPU tradeoffs.

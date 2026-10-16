# PhoneCam

Android-to-Windows USB webcam bridge with a desktop framing and background editor.
Video travels over ADB reverse forwarding to a loopback HTTP server, then to the
OBS Virtual Camera component. The phone browser must remain open and unlocked.

## Status

Source preview. No signed installer or Microsoft Store release is available yet.
Do not disable Smart App Control to run an unsigned build. MSIX Store publication
is planned; certification, packaging changes, dependency licensing and testing
on a protected Windows laptop remain outstanding.

## Developer setup

Use Windows x64 with Python 3.13 and OBS Studio installed. Obtain Android SDK
Platform Tools from https://developer.android.com/tools/releases/platform-tools
and extract the platform-tools folder into android-tools/. Install dependencies:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python phonecam.py --usb --port 8765
```

Enable USB debugging and authorize the laptop on the phone. Use Wake phone &
start camera and grant Chrome camera permission. Select OBS Virtual Camera in
the receiving app. Keep OBS's own virtual-camera producer stopped while
PhoneCam owns that endpoint. Use the laptop microphone.

Original-background mode works without a segmentation model. Background effects
require a compatible HumanSeg ONNX model at models/humanseg.onnx; it is deliberately
not bundled in this source preview pending provenance and redistribution review.

## Efficiency

Camera output targets 1280x720 at 30 fps. The editor preview refreshes at up to
10 fps and pauses when hidden. Capture keeps one latest pending frame instead of
a queue. Background/mask processing uses bounded caches. Actual speed depends
on the laptop and concurrent OBS workload; sustained 30 fps is not guaranteed.

## Licensing and privacy

Original source: MIT. Dependencies retain their own licenses; notably pyvirtualcam
uses GPLv2. The MIT license does not relicense bundled third-party code or remove
obligations for distributing a combined application. See THIRD_PARTY.md.
See PRIVACY.md and SIGNING.md before publishing binary releases.

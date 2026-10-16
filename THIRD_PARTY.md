# CamTether distribution licenses

Original files retain their MIT license (LICENSE). obs_camera.py adapts the OBS
Studio queue implementation and is GPL-3.0-or-later. The combined CamTether
distribution is GPL-3.0-or-later; see licenses/GPL-3.0.txt. It is not MIT-only.
You may run, study, modify and redistribute it under those terms. There is no
warranty. No activation service, DRM, source-access fee or signing secret is
required to run modified source using Python; see README.md for instructions.

## OBS adapter and corresponding source

The queue layout and publication algorithm come from OBS Studio contributors:
https://github.com/obsproject/obs-studio/blob/45643adb036c3bb40a7e400203499abb4ad7a3dd/plugins/win-dshow/shared-memory-queue.c

The upstream README grants GPL version 2 **or any later version**; the preserved
README is licenses/OBS-upstream-README.rst. This Python adaptation elects GPLv3
or later. Changes include ctypes bindings, atomic mapping ownership checks,
reusable FFmpeg conversion buffers, and duplicate-frame conversion avoidance.
No pyvirtualcam wrapper source or binaries are included in version 1.1.2.

All CamTether source, tests, manifest, launcher source and build scripts are at
https://github.com/fanindras/camtether. The release source archive accompanies
 the package. The interpreted adapter source is also inside the package.
The package build does not change or obscure these source files.

OBS Studio is installed separately. CamTether loads swscale-9.dll and avutil-60.dll
only from the registered OBS installation. Tested with OBS 32.2.2; its FFmpeg
libraries report GPL version 3 or later. These libraries and the OBS virtual
camera driver are not redistributed by CamTether. Their upstream source is
https://github.com/obsproject/obs-studio and https://github.com/obsproject/obs-deps
and https://ffmpeg.org/download.html. No OBS trademark endorsement is implied.

## Other bundled components

All upstream notices in runtime/, vendor/ and android-tools/ are retained.
Exact wheel versions and hashes are in submission/dependency-provenance.json.

| Component | License / source |
|---|---|
| Python 3.13 runtime | PSF; runtime/LICENSE.txt; https://www.python.org/downloads/source/ |
| Tcl/Tk | BSD-style notices in runtime/tcl; https://www.tcl.tk/software/tcltk/ |
| NumPy 2.5.4 | BSD and bundled notices; vendor/numpy-2.5.4.dist-info/licenses; https://pypi.org/project/numpy/2.5.4/#files |
| Pillow 12.3.0 | HPND and bundled codec notices; vendor/pillow-12.3.0.dist-info/licenses; https://pypi.org/project/pillow/12.3.0/#files |
| ONNX Runtime 1.31.0 | MIT and ThirdPartyNotices.txt; https://github.com/microsoft/onnxruntime/tree/v1.31.0 |
| qrcode 8.2 | BSD; https://pypi.org/project/qrcode/8.2/#files |
| colorama 0.4.6 | BSD; https://pypi.org/project/colorama/0.4.6/#files |
| Android Platform Tools 37.0.1 | Exact multi-license NOTICE.txt and source.properties in android-tools/platform-tools; https://android.googlesource.com/platform/packages/modules/adb/ |
| PP-HumanSeg 2023mar model | Apache-2.0, PaddlePaddle Authors; upstream notice in models/; https://github.com/opencv/opencv_zoo/tree/main/models/human_segmentation_pphumanseg |

NumPy's notices include OpenBLAS/LAPACK and GPL-3.0-or-later WITH
GCC-exception-3.1 for its GCC runtime portions. The full exception and license
are preserved; this exception permits distribution of eligible compiled target
code under chosen terms. It does not relicense GCC itself. Pillow and ONNX
Runtime bundled-library notices remain intact, not replaced by a single summary.

Android SDK terms section 3.5 directs open-source components to their respective
open-source licenses. Only adb.exe, its two API DLLs, NOTICE.txt and
source.properties are included; no SDK manager, system images or unrelated tools.

The model is 6,163,938 bytes, SHA256
552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24,
matched to the upstream Git LFS pointer on 2026-10-17.

## Changes from the earlier private draft

Removed GPLv2-only pyvirtualcam and its bundled libyuv binary, plus the unused
cryptography/cffi/pycparser stack. This avoids the earlier GPLv2/Apache-2.0
combination. The adapter's explicit GPLv3-or-later grant accommodates the
remaining Apache-2.0 components. This records the engineering license audit;
Microsoft still decides Store certification and restricted-capability approval.

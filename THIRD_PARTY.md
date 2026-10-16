# Third-party components

Original CamTether files are MIT licensed. The assembled runtime is not MIT-only.
All bundled upstream license files must remain in the package.

- Python 3.13: PSF license, runtime/LICENSE.txt; https://www.python.org/downloads/source/
- pyvirtualcam 0.15.0: GPLv2; https://github.com/letmaik/pyvirtualcam/tree/v0.15.0
- NumPy 2.5.4: upstream BSD notices and bundled library notices in its distribution.
- Pillow 12.3.0: upstream HPND/Pillow notices and bundled library notices.
- ONNX Runtime 1.31.0: MIT and bundled third-party notices.
- cryptography 50.0.2 and its dependencies: retain the upstream Apache/BSD and bundled notices.
- qrcode 8.2: BSD distribution notices.
- Android Platform Tools: retain Google's NOTICE.txt and source.properties. The
  release gate includes confirming SDK redistribution terms for the exact payload.
- PP-HumanSeg model: OpenCV Zoo, Apache-2.0 notice by PaddlePaddle Authors;
  https://github.com/opencv/opencv_zoo/tree/main/models/human_segmentation_pphumanseg
  Filename human_segmentation_pphumanseg_2023mar.onnx, 6,163,938 bytes.
  SHA256 552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24.
  The local weights match the upstream Git LFS pointer, checked 2026-10-17.

## Before binary publication

Fulfill corresponding-source and notice obligations for the exact GPL components
and their bundled code, and review compatibility of the combined distribution,
including the Apache-licensed components. Source references above do not by
themselves constitute a complete corresponding-source delivery. The public
repository contains only original source; the candidate MSIX remains local until
these distribution checks and Store certification are complete.

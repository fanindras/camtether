# CamTether 1.1.4.0 validation — 2026-10-26

Store candidate: `CamTether-1.1.4.0-x64.msix`, 60,538,451 bytes.
SHA-256: `57635eacfbf868d604f753758fb5a69d21d1388c178a19b02011eaf82ac5a9f3`.

## Installed camera

- Installed diagnostic MSIX with identical production launcher SHA-256
  `57a2667a3793c5490a57cc1e808e8644b2515437a2171b5236637e9cd5b033e7`.
  Test identity/unsigned-test publisher and startup instrumentation differ;
  instrumentation isolates preferences and exports a local pairing token for tests.
- Fresh Chrome and Edge each enumerate CamTether, select its exact device ID,
  and receive 1280×720 reference frames. Production path: 31 frames in each
  approximately one-second measurement; center RGBA `[254,0,0,255]` from a red JPEG.
- A separate validation build forces the bundled signed filter instead of reusing
  installed OBS: both browsers receive 32 frames with the same size and color.
- Production reuses existing OBS registration without creating an overriding
  per-user CLSID. No full OBS installation is required by the bundled-filter path.
- Normal GUI Exit removes CamTether's owned camera/CLSID entries. Native tests
  cover both registry views, missing values, typed reads, preservation of unknown
  default REG_DWORD/REG_NONE values, and empty-key cleanup.
- Important test setup: the development host's private registry view contained
  stale deletion overlays. Tests launched there missed the camera. The recorded
  passing tests run in a clean Windows process context through Win32_Process.
  No Windows security settings were changed.

## Software and distribution

- 39 Python regression tests pass; JavaScript phone-control tests pass
  (front default, unsupported exposure, 50/60 Hz readback, automatic exposure
  restoration, ignored-constraint fallback, live resolution controls).
- Windows App Certification Kit 10.0.28000.2957: overall **PASS**, full run,
  production package version 1.1.4.0, generated 2026-10-26 22:57 local time.
- Optional test 88, “Blocked executables”, reports runtime process-launch APIs
  and string matches in Python, Tcl/Tk, ADB, ONNX/model and library files.
  These are disclosed for Microsoft review; an overall pass is not Store approval.
- All four bundled native camera/conversion DLL Authenticode signatures are valid.
- Official PyPI metadata for the five pinned Python distributions reports zero
  known advisory entries on 2026-10-26. This is not a comprehensive security audit.
- Combined distribution GPL-3.0-or-later; original MIT notices and upstream
  licenses retained. Corresponding OBS/FFmpeg source archive remains unchanged
  from 1.1.3 because the native binaries are unchanged.

## Remaining external validation

The Android phone was unavailable for this pass. Synthetic browser capture does
not prove physical USB reconnect, phone permission, lens switching or actual
50/60 Hz flicker behavior. Windows Store certification, restricted-capability
approval and Store signing remain Microsoft's decision. Installation on the
second laptop with Smart App Control enabled can only be confirmed using the
Store-delivered build. Do not distribute the unsigned QA package to users.

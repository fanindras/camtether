# CamTether 1.1.2.0 release checks — 2026-10-17

## Verified

- Exact candidate SHA256: ebab889902b6bb2f75f4d44d434b3186ed34be4c93b97bc9f86586c74bc38d22.
- Windows App Certification Kit 10.0.28000.2957: OVERALL_RESULT PASS,
  PARTIAL_RUN FALSE; 23 individual tests PASS and one optional test FAIL.
  DPIAwarenessValidation now PASS. The report identifies version 1.1.2.0.
- Optional Blocked executables finding remains. The launcher starts bundled
  Python; Python and ADB contain process-launch APIs. Runtime/library/model
  string scans also match command names. The app's unused PowerShell network
  discovery was removed. These findings are disclosed, not a claim of zero
  warnings or Microsoft certification. No executable obfuscation was performed.
- 22 regression tests passed, including NV12 BT.601 colors, OBS queue layout,
  duplicate-frame cache, writer collision safety, uint32 wrap, cleanup/reopen,
  frame stop/reconnect handling, effects, persistence, and USB HTTP authorization.
- Packaged Python runtime smoke tests passed: model inference, settings
  persistence, Tk UI, synthetic Edge camera upload, one in-flight slow upload,
  stop/restart, expired pairing rejection and explicit PC auto-start behavior.
- All payload files still match build-time hashes after tests. Temporary caches
  created by testing are not in the MSIX and must not be copied into a release.
- Three actual editor screenshots captured at 1920 x 1032, displaying a labeled
  synthetic test chart. No personal camera image, pairing token or unrelated app
  is present. JPEG capture encoding converted to PNG without altering content.
- Store age-rating summary saved, verified against overview status Complete:
  Everyone / 3+ (regional mappings vary). Owner explicitly approved IARC terms.

## Licensing and supported runtime

pyvirtualcam and cryptography/cffi/pycparser are excluded. Original MIT notices
remain; OBS-derived obs_camera.py and the combined distribution use GPL-3.0-or-later.
The upstream later-version grant and GPL text are retained. See THIRD_PARTY.md.
Source and build scripts accompany this candidate. OBS 32.2.2 x64 is the tested
external dependency; swscale-9 / avutil-60 are required. No OBS DLLs are bundled.

## Limits

The tests do not certify sustained performance from a physical Android phone,
all conferencing clients, or multi-monitor DPI transitions. Store-signed install
on the other laptop with Smart App Control enabled is still an acceptance check
for after Microsoft provides a signed distribution. No security settings changed.
Microsoft must approve runFullTrust and final certification. This local overall
PASS is not Microsoft Store approval. Publication remains manually controlled.

## Store draft update

Version 1.1.2.0 uploaded and marked Validated in submission 1152921505702153933.
The superseded 1.1.1 package is removed. The English listing has three saved
screenshots and shows Complete. Age ratings show Complete. Pricing remains free
in all available markets; publication remains manual. Customer-facing OBS version
requirement and additional GPL license wording require the owner's approval of
the exact text before those listing fields are changed. No final certification
submission has been made.

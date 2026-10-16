# Validation - 2026-10-17

Latest update: see STORE-CHECKS-1.1.1.md for the completed WACK run, isolated
installed-package lifecycle test, dependency provenance audit and private Store
upload. The records below describe the earlier test stage.

Version 1.1.0.0, x64, Store identity FanindraChaubey.CamTether.

Passed:
- Microsoft MakeAppx 10.0.28000.2705 package creation with schema/semantic validation enabled.
- 16 regression tests: authentication and origin rejection, bad/oversized uploads,
  stale/stop clearing, geometry, inference, background persistence, cache invalidation
  and settings saved outside a missing (unwritable) installation location.
- Packaged Python runtime imports, model inference, settings save/reload and hidden Tk editor smoke test.
- Packaged loopback server with Edge fake camera: upload, stop/restart, expired
  pairing rejection, explicit start, and delayed-upload backpressure (one in flight).
- Model SHA256 equals OpenCV Zoo's published Git LFS pointer.

Limits:
- Runtime smoke tests execute the staged package files without Windows package registration.
- No physical phone or live virtual-camera output was started by these tests.
- OBS smoothness, installed MSIX activation/uninstall, WACK and Store certification
  are not verified. No new peak-RAM claim is made.
- This PC reports Smart App Control disabled (policy state 0). It was not changed.
  Protected-machine installation/launch must be tested after Store signing.
- Package is unsigned for Store submission preparation. No development certificate
  was created or trusted. No Windows security policy was weakened.
- Third-party distribution review remains a publication gate; see THIRD_PARTY.md.

## Revision 1.1.1.0

See REVIEW-1.1.1.md: 20 regression tests pass, plus the rebuilt packaged-runtime and fake-camera tests. The original installed-MSIX/Smart App Control/Store gates above still apply. No Store upload was performed.

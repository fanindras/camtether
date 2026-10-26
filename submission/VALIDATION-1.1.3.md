# CamTether 1.1.3 standalone camera validation

No OBS Studio application or runtime installation is required. Five native assets
are bundled: original signed x86/x64 OBS filters, placeholder, swscale and avutil.
No custom unsigned camera proxy, recorder, OBS UI, background OBS process or extra
encoding step is included. Resolution, frame rate, JPEG quality and BT.601 range
remain unchanged. Exact hashes are in native/provenance.json.

## Completed
- 27 regression tests passed, including both registry views and existing-OBS preservation.
- Standalone branch tested using temporary per-user registration with existing
  machine-wide OBS keys untouched. Chrome: 32 frames in about one second; Edge:
  31 frames; 1280x720; reference red received as RGBA 254,0,0,255 in both.
- Standalone test verifies its own keys are absent after cleanup.
- 300-frame conversion benchmark: median 1.07 ms, p95 1.65 ms on this laptop.
- Original four upstream DLL Authenticode signatures valid (OBS Project, LLC).
- PE dependency audit: filter DLLs import only Windows system DLLs. Conversion
  libraries need avutil and VC runtime; Python runtime supplies VC runtime.
- OBS/FFmpeg matching source and dependency build scripts collected in accompanying
  CamTether-1.1.3-third-party-source.zip. No new pyvirtualcam dependency.

## Remaining release gates
- Final installed-MSIX standalone capture and registration cleanup.
- Final Windows App Certification Kit run and Store package validation.
- Store approval of unvirtualizedResources for the exact per-user camera paths.
- Store-signed download tested on the other laptop with Smart App Control enabled.
  Valid upstream signatures and local tests do not establish this last result.

## Deployment and removal
WindowsApps blocks loading a normal packaged in-process DLL into other apps.
CamTether therefore exposes only original signed filters through its narrow
CamTetherCamera per-user directory. Existing valid OBS registrations are reused;
otherwise marked per-user registrations are created in both architecture views.
They are removed on normal exit. Volatile keys do not survive user-hive unload;
forced termination can leave an entry until a subsequent CamTether run or hive
unload. Excluded files are intentionally outside MSIX automatic uninstall cleanup.
To remove them, close meeting apps/browsers, select Remove webcam components in
CamTether, then uninstall CamTether from Windows Settings. Files with unexpected
hashes are preserved rather than deleted. No security settings are weakened.

# Store checks - CamTether 1.1.1.0

Checked 2026-10-17. This supplements VALIDATION.md and REVIEW-1.1.1.md.

## Completed

- Uploaded the 60.60 MB x64 MSIX to the private Partner Center submission draft.
  Partner Center reports **Validated**, Packages **Complete**. This is package
  acceptance, not Store certification or public availability.
- Set free pricing in all 240 currently available markets, desktop device family
  only, and manual publication after certification. Saved the runFullTrust
  justification; Microsoft must still approve that capability.
- Installed Microsoft Windows App Certification Kit 10.0.28000.2957 and ran its
  complete package-path test against the submitted MSIX. Result: WARNING;
  22 tests PASS, one optional test FAIL, one test WARNING. Not a clean pass.
- Installed a separate unsigned-test-identity copy using Microsoft's documented
  publisher OID and Add-AppxPackage -AllowUnsigned. Original payload hashes were
  verified before packaging; only its publisher identity was changed.
- Windows package registration returned Status Ok. Windows app activation started
  the runtime from WindowsApps; its 127.0.0.1:8765 receiver returned HTTP 200.
  Closing the app exited its process and released the port. Test-package removal
  succeeded. No certificate was trusted and no security policy was changed.
- Queried PyPI vulnerability metadata for all nine bundled distributions: zero
  known entries on this date. This does not prove absence of vulnerabilities,
  and does not cover every native library embedded in those wheels.
- Downloaded each exact official PyPI wheel, verified its published SHA-256, and
  compared its files to the staged payload. All shipped wheel files matched;
  missing wheel files were upstream tests only. See dependency-provenance.json.
- Collected pyvirtualcam v0.15.0 source at commit
  dbac4732168c21f1337e30182957130f678aa058, including its libyuv submodule at
  19bbedfd3e37329900d34e104021f04d7205ad78. A source archive is retained locally.
  This is source collection, not a claim that every source obligation is met.

## Findings still requiring resolution

1. WACK optional test 88, Blocked executables, reports process-launch APIs and
   command-name strings. CamTether's launcher and ADB intentionally start desktop
   processes. The unused wireless code path contains a PowerShell invocation.
   Other matches include Python/Tcl tooling and strings inside model weights;
   these string matches alone do not establish prohibited runtime behavior.
   Review the real invocation and trim unnecessary build/developer tools before
   the final candidate; preserve required runtime code and license notices.
2. WACK DPIAwarenessValidation warns that CamTether.exe lacks a PerMonitorV2
   manifest or DPI API call. The launcher exits after starting pythonw.exe, so
   fixing only the launcher would not verify the actual Tk window's scaling.
3. pyvirtualcam advertises GPLv2 and loads in the same Python process as the app.
   The bundled runtime also includes Apache-2.0 components, including OpenSSL 3.
   The precise GPL version grant and combined-distribution compatibility remain
   unresolved. Original MIT source availability alone does not clear this.
   Confirm a compatible grant or change the integration before public release;
   complete corresponding-source and notice delivery for the actual final build.
4. Live Android-to-OBS performance, Store-signed installation with Smart App
   Control enabled, and multi-monitor DPI behavior are not established by the
   package-path and isolated-identity tests. This PC's SAC setting remains off.
5. Store screenshots, age rating, and final owner declarations remain required.

No public release or final certification submission was made by these checks.

## References

- [Unsigned package testing](https://learn.microsoft.com/en-us/windows/msix/package/unsigned-package)
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [Apache GPL compatibility](https://apache.org/licenses/GPL-compatibility.html)
- [pyvirtualcam source](https://github.com/letmaik/pyvirtualcam/tree/v0.15.0)

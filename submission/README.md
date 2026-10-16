# CamTether Store submission preparation

Product: CamTether | Store ID: 9PLVZCDDDT9H | Version: 1.1.0.0 | Architecture: x64
Package identity and publisher are fixed in packaging/AppxManifest.xml.
Minimum Windows version: Windows 10 build 19041.

## Draft listing text

Short description: Turn your Android phone into a USB webcam for Windows.

Description: CamTether connects your Android phone camera to Windows through a USB
cable. Adjust framing, rotation, brightness, contrast, color and background on your
PC. Settings and your chosen background are remembered locally. Video is processed
on your laptop. Background removal can show imperfect edges during fast motion.

Requires Android USB debugging, Chrome camera permission and an unlocked phone
with the camera page visible. Requires separately installed OBS Studio for the
OBS Virtual Camera component. Laptop microphone supplies audio; CamTether carries
video only. This app is not affiliated with OBS, Google or Microsoft. Performance
varies by hardware; 30 fps is a target, not a guarantee. Keystone correction is
limited and cannot recreate a different physical camera viewpoint.

Suggested category: Photo & video. Proposed price: free (owner to confirm).
Privacy URL: https://github.com/fanindras/camtether/blob/main/PRIVACY.md
Support URL: https://github.com/fanindras/camtether/issues

## Full-trust capability justification draft

The desktop app runs a local Python image-processing runtime, communicates with
Android Debug Bridge for explicitly authorized USB forwarding and screen wake,
and sends local frames to the separately installed OBS virtual-camera component.
It requires normal desktop process privileges. It does not install a driver,
change security policy, bypass phone locks or require administrator privileges.

## Reviewer test notes

1. Install OBS Studio separately, leave OBS's virtual-camera producer stopped.
2. Connect an Android phone by USB, enable USB debugging and approve the PC.
3. Launch CamTether, choose Wake phone & start camera, grant phone Chrome camera
   permission, and leave the phone unlocked and its page visible.
4. Select OBS Virtual Camera in a receiving app. Check framing and background.
5. Close and reopen CamTether; verify settings and background persistence.
6. Stop the phone camera; output should clear. Test cable loss and recovery.

## Outstanding before submission

- Test the Store-installed package on Windows with Smart App Control enabled;
  this cannot be claimed from unpacked-runtime tests or unsigned package creation.
- Complete Windows App Certification Kit and actual installed-package lifecycle tests.
- Resolve third-party binary redistribution / corresponding-source obligations.
- Capture real product screenshots without personal camera content.
- Owner completes age rating, markets/pricing, support declarations and any binding
  submission declarations. No answers to those legal declarations are invented here.

No package has been uploaded or submitted for certification in this change.

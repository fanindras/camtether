# CamTether Store submission preparation

Product: CamTether | Store ID: 9PLVZCDDDT9H | Version: 1.1.5.0 | Architecture: x64
Package identity and publisher are fixed in packaging/AppxManifest.xml.
Minimum Windows version: Windows 11 build 22000.

## Draft listing text

Short description: Turn your Android phone into a USB webcam for Windows.

Description: CamTether connects your Android phone camera to Windows through a USB
cable. Adjust framing, rotation, brightness, contrast, color and background on your
PC. Settings and your chosen background are remembered locally. Video is processed
on your laptop. Background removal can show imperfect edges during fast motion.

Requires Android USB debugging, Chrome camera permission and an unlocked phone
with the camera page visible. The small virtual-camera components are included; OBS Studio is not required. Laptop microphone supplies audio; CamTether carries
video only. This app is not affiliated with OBS, Google or Microsoft. Performance
varies by hardware; 30 fps is a target, not a guarantee. Keystone correction is
limited and cannot recreate a different physical camera viewpoint.

Category: Photo & video. Owner-confirmed price: free in all available markets.
Privacy URL: https://github.com/fanindras/camtether/blob/main/PRIVACY.md
Support URL: https://github.com/fanindras/camtether/issues

## Full-trust capability justification draft

The desktop app runs a local Python image-processing runtime, communicates with
Android Debug Bridge for explicitly authorized USB forwarding and screen wake,
and sends local frames to the bundled virtual-camera component.
It requires normal desktop process privileges. It does not install a driver,
change security policy, bypass phone locks or require administrator privileges.

## Reviewer test notes

1. Install CamTether. No OBS Studio installation is required.
2. Connect an Android phone by USB, enable USB debugging and approve the PC.
3. Launch CamTether, choose Wake phone & start camera, grant phone Chrome camera
   permission, and leave the phone unlocked and its page visible.
4. Select CamTether in a receiving app. Check framing and background.
5. Close and reopen CamTether; verify settings and background persistence.
6. Stop the phone camera; output should clear. Test cable loss and recovery.

## Validation and remaining acceptance checks

See VALIDATION-1.1.4.md for the current test record. WACK overall PASS includes
one disclosed optional blocked-executable finding. Age ratings are saved. Three
actual product screenshots use a labeled synthetic chart rather than personal video.
The package still needs Microsoft certification and runFullTrust approval. After
Store signing, verify installation on the target laptop with Smart App Control
enabled. Local unpacked/unsigned tests do not establish that outcome.

Publication remains manually controlled. The package is not publicly released.



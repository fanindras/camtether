# Privacy

PhoneCam does not record video or upload it to a cloud service. Live frames are
processed in RAM and passed to the local virtual-camera consumer. That consumer
(e.g. conferencing software or OBS) has its own recording and transmission policy.
Background images and edit settings are saved locally in .local/. Camera choice
and quality are saved in phone-browser local storage. Pairing tokens authorize
camera requests and must not be shared. USB debugging gives the authorized laptop
Android debugging access. The app does not bypass the phone lock or permissions.
Optional non-USB mode uses the local network. GitHub and Microsoft Store have their
own account, download and telemetry policies. Never upload .local/, device state,
logs, certificates, user backgrounds or personal camera screenshots to this repo.

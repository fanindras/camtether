# Code signing policy

CamTether uses the Microsoft Store MSIX route for intended production distribution.
There is no publicly signed release yet. Store identity is defined in
packaging/AppxManifest.xml using Partner Center's assigned values.

The local unsigned MSIX is for submission preparation, not an end-user installer.
Microsoft re-signs accepted Store packages after certification. We do not ask users
to disable Smart App Control, trust development certificates, or bypass protection.

GitHub hosts source and packaging instructions. Review submission/README.md and
submission/VALIDATION.md before uploading or publishing a binary. Local MakeAppx
validation does not prove Store acceptance or protected-device compatibility.

https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/publish-first-app

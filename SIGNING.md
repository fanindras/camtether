# Code signing policy and setup

No signing provider has approved this project and no signed release is available.

Recommended lowest-cost route (checked 2026-10-17): Microsoft Store MSIX.
Free individual registration and Store signing after certification. An EXE listing
in the Store does not receive this free MSIX-signing treatment.

1. Register at https://storedeveloper.microsoft.com/ using the appropriate account
   type, complete identity verification, and reserve an available app name.
2. Copy the package identity Name, Publisher and PublisherDisplayName from Partner
   Center. These are needed for a real manifest; do not invent production values.
3. Before packaging, move settings, saved backgrounds and logs out of the installed
   app directory into writable per-user data storage. Replace the CMD driver link
   with the official OBS download URL. Keep OBS installation separate.
4. Resolve binary dependency/model licensing and provenance; include required
   notices and corresponding source for the exact GPL component versions.
5. Build an x64 full-trust desktop MSIX with bundled runtime, assets and manifest.
   Document why the full-trust capability is required: desktop virtual camera and ADB.
6. Validate USB, ADB subprocess launch, camera selection, writable settings and
   uninstallation; submit through Partner Center with an accurate privacy policy.
7. After certification, install from the Store on a Smart App Control enabled
   Windows laptop and verify the entire camera flow. Do not claim success earlier.

GitHub hosts source. Store hosts the trusted app. No paid certificate is needed
for the Store MSIX path, but approval is not guaranteed or immediate.

Alternatives: SignPath Foundation is free for accepted established OSS projects,
but excludes signing arbitrary upstream libraries. This is not a complete remedy
for the current unsigned dependency payload. Azure Artifact Signing is about
USD 9.99/month but current public-trust individual eligibility is USA/Canada;
confirm organization eligibility if applying as a company. CA certificates have
additional verification and possible hardware/cloud fees; none has been purchased.

Sources:
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/publish-first-app
- https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/
- https://signpath.org/terms.html
- https://learn.microsoft.com/en-us/azure/artifact-signing/faq

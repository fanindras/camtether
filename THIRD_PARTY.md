# Dependencies and binary release gate

This repository contains original source only, not vendored libraries, Python,
ADB, model weights, user backgrounds, screenshots or installers.

pyvirtualcam 0.15.0 declares GPLv2; see https://github.com/letmaik/pyvirtualcam.
A combined binary release must meet applicable GPL source and notice obligations.
The MIT license applies only to original PhoneCam files. Do not label the entire
bundled installer MIT-only. Audit the exact license and provenance of every
runtime, library, model and tool before binary publication, including compatibility
between the GPL component and the HumanSeg model and any SDK distribution terms.

Pinned dependencies are in requirements.txt. Their upstream packages supply
license files. The existing local HumanSeg license says Apache-2.0; model provenance
and compatibility have not been established for public redistribution, so the
weights are excluded. Obtain ADB separately from Google for developer use.

# CamTether 1.1.1.0 review and efficiency changes

Fixed before further Store work:
- Frame and sequence are now sampled together under the bridge lock. Stream epochs
  prevent processing from a stopped/replaced stream appearing after reconnect.
- Pending JPEG decoding is rejected if the stream was stopped while decoding.
- Output older than two seconds is blanked even while new input keeps arriving.
- Processing waits on frame/settings events instead of polling every 4 ms.
- ONNX intra/inter-op worker spinning is disabled; image resolution and model unchanged.
- Segmentation worker releases completed job/input references while waiting.
- Authenticated /status includes processing_ms and output_age_ms (PC receive-to-now
  age only; this is not a phone-to-OBS end-to-end measurement).

Validation: 20 regression tests passed including a deliberately blocked old frame
across stop/restart, stale-output rejection, idle wakeup and settings-triggered
reprocessing, and releasing segmentation input references. Packaged-runtime and
fake-camera slow-upload/stop/restart tests also passed. Model output masks before/after were byte-identical.

One synthetic 90-inference 30 Hz run: CPU time 3.891 -> 2.109 seconds across about
3 seconds wall time. Median inference 10.99 -> 14.49 ms, p95 16.03 -> 26.25 ms.
This is a CPU/latency tradeoff, not a measured live-OBS FPS improvement or RAM figure.
Whole-app performance still depends on hardware and concurrent OBS workload.

Further recommendations: benchmark live transport/OBS frame age before considering
GPU rendering or transport changes; avoid speculative rewrites before first release.
Keep models and buffers bounded and protect every optimization with output-comparison
tests. Model resolution, camera quality and virtual-camera 30 fps target are unchanged.

Store upload is deferred while these changes are tested, as requested. Existing
installed-package, certification, protected-machine and third-party review gates
remain; this revision does not claim to complete them.

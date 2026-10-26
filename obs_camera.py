"""OBS Windows shared-memory output using bundled conversion DLLs, without OBS Studio.

Queue layout adapted from OBS Studio (GPL-2.0-or-later), commit
45643adb036c3bb40a7e400203499abb4ad7a3dd, plugins/win-dshow/shared-memory-queue.c.
Copyright OBS Studio contributors. This adaptation: GPL-3.0-or-later.
See licenses/GPL-3.0.txt and THIRD_PARTY.md.
"""
import ctypes as C
import os
from pathlib import Path
import time

import numpy as np


def obs_bin():
    """Resolve bundled conversion libraries, independent of PATH and OBS installs."""
    return Path(__file__).resolve().parent / 'native'


class Converter:
    """Persistent FFmpeg RGB24 to limited-range BT.601 NV12 conversion."""
    def __init__(self, width, height):
        self.context = None
        self.directory = None
        self.width, self.height = width, height
        folder = obs_bin()
        # These ABI versions are exercised by the release tests. Fail explicitly
        # for other versions rather than loading an untested ABI or arbitrary DLL.
        scale, util = folder / 'swscale-9.dll', folder / 'avutil-60.dll'
        if not scale.is_file() or not util.is_file():
            raise RuntimeError('CamTether conversion components are missing. Repair the CamTether installation.')
        try:
            self.directory = os.add_dll_directory(str(folder))
            self.util = C.CDLL(str(util))
            self.scale = C.CDLL(str(scale))
            self.util.av_get_pix_fmt.argtypes = [C.c_char_p]
            self.util.av_get_pix_fmt.restype = C.c_int
            sws = self.scale
            sws.sws_getContext.argtypes = [C.c_int]*7 + [C.c_void_p]*3
            sws.sws_getContext.restype = C.c_void_p
            sws.sws_freeContext.argtypes = [C.c_void_p]
            sws.sws_freeContext.restype = None
            sws.sws_getCoefficients.argtypes = [C.c_int]
            sws.sws_getCoefficients.restype = C.POINTER(C.c_int)
            sws.sws_setColorspaceDetails.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.c_int,
                                                    C.POINTER(C.c_int)] + [C.c_int]*4
            sws.sws_setColorspaceDetails.restype = C.c_int
            sws.sws_scale.argtypes = [C.c_void_p, C.POINTER(C.c_void_p), C.POINTER(C.c_int),
                                     C.c_int, C.c_int, C.POINTER(C.c_void_p), C.POINTER(C.c_int)]
            sws.sws_scale.restype = C.c_int
            self.context = sws.sws_getContext(width, height, self.util.av_get_pix_fmt(b'rgb24'),
                                             width, height, self.util.av_get_pix_fmt(b'nv12'),
                                             2, None, None, None)
            if not self.context:
                raise RuntimeError('OBS color converter could not initialize.')
            coefficients = sws.sws_getCoefficients(5)
            if sws.sws_setColorspaceDetails(self.context, coefficients, 1, coefficients, 0, 0, 65536, 65536) < 0:
                raise RuntimeError('OBS color converter rejected BT.601 configuration.')
            self.buffer = np.empty(width*height*3//2, dtype=np.uint8)
            self.dest = (C.c_void_p*4)(self.buffer.ctypes.data, self.buffer.ctypes.data+width*height, 0, 0)
            self.dest_stride = (C.c_int*4)(width, width, 0, 0)
            self.source = (C.c_void_p*4)()
            self.source_stride = (C.c_int*4)(width*3, 0, 0, 0)
        except Exception:
            self.close()
            raise

    def convert(self, frame):
        if frame.dtype != np.uint8 or frame.shape != (self.height, self.width, 3) or not frame.flags.c_contiguous:
            raise ValueError('Camera frame must be a contiguous RGB uint8 image at output size.')
        self.source[0] = frame.ctypes.data
        if self.scale.sws_scale(self.context, self.source, self.source_stride, 0, self.height,
                                self.dest, self.dest_stride) != self.height:
            raise RuntimeError('OBS color conversion did not produce a complete frame.')
        return self.buffer

    def close(self):
        if self.context:
            self.scale.sws_freeContext(self.context)
            self.context = None
        if self.directory:
            self.directory.close()
            self.directory = None


class Camera:
    """Single-writer OBS queue. Call send/close from the owning output thread."""
    def __init__(self, width, height, fps):
        if width <= 0 or height <= 0 or width % 2 or height % 2 or fps <= 0:
            raise ValueError('NV12 requires positive, even dimensions and a positive frame rate.')
        self.converter = None
        self.handle = self.address = None
        self.last_frame = None
        self.period, self.deadline = 1/fps, time.monotonic()
        self.size = width*height*3//2
        self.offsets = [96+i*((self.size+63)&~31) for i in range(3)]
        total = self.offsets[-1]+((self.size+63)&~31)
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.CreateFileMappingW.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint32, C.c_wchar_p]
        k.CreateFileMappingW.restype = C.c_void_p
        k.MapViewOfFile.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint32, C.c_size_t]
        k.MapViewOfFile.restype = C.c_void_p
        k.UnmapViewOfFile.argtypes = [C.c_void_p]
        k.CloseHandle.argtypes = [C.c_void_p]
        k.FlushProcessWriteBuffers.argtypes = []
        k.FlushProcessWriteBuffers.restype = None
        try:
            self.converter = Converter(width, height)
            C.set_last_error(0)
            self.handle = k.CreateFileMappingW(C.c_void_p(-1), None, 4, 0, total, 'OBSVirtualCamVideo')
            error = C.get_last_error()
            if not self.handle:
                raise C.WinError(error)
            if error == 183:
                raise RuntimeError('OBS Virtual Camera is in use. Stop the other camera producer first.')
            self.address = k.MapViewOfFile(self.handle, 0xF001F, 0, 0, total)
            if not self.address:
                raise C.WinError(C.get_last_error())
            C.memset(self.address, 0, 96)
            for index, offset in enumerate(self.offsets):
                self._u32(12+index*4).value = offset
            self._u32(28).value, self._u32(32).value = width, height
            C.c_uint64.from_address(self.address+40).value = round(10_000_000/fps)
            self._u32(8).value = 1
        except Exception:
            self.close()
            raise

    def _u32(self, offset):
        return C.c_uint32.from_address(self.address+offset)

    def send(self, frame):
        if not self.address:
            raise RuntimeError('Camera is closed.')
        # Effects publishes immutable arrays. Duplicate display ticks reuse the
        # converted buffer, but retain fresh queue timestamps for the consumer.
        if frame is not self.last_frame:
            self.converter.convert(frame)
            self.last_frame = frame
        count = (self._u32(0).value+1)&0xffffffff
        self._u32(0).value = count
        slot = self.address+self.offsets[count % 3]
        C.c_uint64.from_address(slot).value = time.perf_counter_ns()
        C.memmove(slot+32, self.converter.buffer.ctypes.data, self.size)
        self.kernel.FlushProcessWriteBuffers()
        self._u32(4).value = count
        self._u32(8).value = 2

    def sleep_until_next_frame(self):
        self.deadline = max(self.deadline+self.period, time.monotonic())
        time.sleep(max(0, self.deadline-time.monotonic()))

    def close(self):
        if self.address:
            self._u32(8).value = 3
            self.kernel.UnmapViewOfFile(self.address)
            self.address = None
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
        if self.converter:
            self.converter.close()
            self.converter = None
        self.last_frame = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

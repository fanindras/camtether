"""Low-frequency Windows GPU engine telemetry; no subprocesses or vendor SDK."""
import ctypes as C
from ctypes import wintypes as W
import math
import re
import threading

class Value(C.Structure):
    _fields_ = [('status', W.DWORD), ('value', C.c_double)]
class Item(C.Structure):
    _fields_ = [('name', W.LPWSTR), ('counter', Value)]

def busiest_engine(samples):
    totals = {}
    for name, value in samples:
        # Instances are per process; combine processes on the same physical engine.
        match = re.search(r'luid_.*?_phys_\d+_eng_\d+', name)
        if match and math.isfinite(value):
            key = match.group(0)
            totals[key] = totals.get(key, 0.) + max(0., value)
    return min(100., max(totals.values())) if totals else None

class GpuMonitor:
    def __init__(self, closed):
        self.label = 'GPU · measuring…'
        threading.Thread(target=self._run, args=(closed,), daemon=True).start()

    def _run(self, closed):
        query = C.c_void_p()
        try:
            pdh = C.WinDLL('pdh')
            pdh.PdhOpenQueryW.argtypes = [W.LPCWSTR, C.c_size_t, C.POINTER(C.c_void_p)]
            pdh.PdhAddEnglishCounterW.argtypes = [C.c_void_p, W.LPCWSTR, C.c_size_t, C.POINTER(C.c_void_p)]
            pdh.PdhCollectQueryData.argtypes = [C.c_void_p]
            pdh.PdhGetFormattedCounterArrayW.argtypes = [C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.c_void_p]
            pdh.PdhCloseQuery.argtypes = [C.c_void_p]
            if pdh.PdhOpenQueryW(None, 0, C.byref(query)):raise RuntimeError('Query unavailable')
            counter = C.c_void_p()
            if pdh.PdhAddEnglishCounterW(query, r'\GPU Engine(*)\Utilization Percentage', 0, C.byref(counter)):raise RuntimeError('Counters unavailable')
            pdh.PdhCollectQueryData(query)
            while not closed.wait(2):
                self.label = 'GPU · unavailable'
                if pdh.PdhCollectQueryData(query):continue
                size, count = W.DWORD(), W.DWORD()
                pdh.PdhGetFormattedCounterArrayW(counter, 0x200, C.byref(size), C.byref(count), None)
                if not 0 < size.value <= 8*1024*1024:continue
                buffer = C.create_string_buffer(size.value)
                if pdh.PdhGetFormattedCounterArrayW(counter, 0x200, C.byref(size), C.byref(count), buffer):continue
                if count.value > size.value // C.sizeof(Item):continue
                items = C.cast(buffer, C.POINTER(Item))
                value = busiest_engine((items[i].name or '', items[i].counter.value) for i in range(count.value) if items[i].counter.status in (0, 1))
                if value is not None:self.label = f'GPU busiest engine · {value:.0f}%'
        except Exception:
            self.label = 'GPU · unavailable'
        finally:
            if query.value:pdh.PdhCloseQuery(query)

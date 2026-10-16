import ctypes as C
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from obs_camera import Camera, Converter


class ConverterTests(unittest.TestCase):
    def test_color_range_and_planes(self):
        converter = Converter(1280, 720)
        try:
            # BT.601 limited range reference values, allow integer rounding.
            for color, expected in [((0,0,0),(16,128,128)), ((255,255,255),(235,128,128)),
                                    ((255,0,0),(81,90,240)), ((0,255,0),(145,54,34)),
                                    ((0,0,255),(41,240,110))]:
                frame = np.empty((720,1280,3),np.uint8);frame[:] = color
                result = converter.convert(frame)
                for actual, reference in zip(result[[100,1280*720+100,1280*720+101]],expected):
                    self.assertLessEqual(abs(int(actual)-reference),1)
            with self.assertRaises(ValueError):
                converter.convert(frame[:,::2])
        finally:
            converter.close()
        self.assertIsNone(converter.context)

    def test_queue_layout_duplicate_cache_collision_and_cleanup(self):
        with Camera(1280,720,30) as camera:
            frame = np.zeros((720,1280,3),np.uint8)
            with patch.object(camera.converter,'convert',wraps=camera.converter.convert) as convert:
                camera.send(frame);camera.send(frame)
                self.assertEqual(convert.call_count,1)
            self.assertEqual(camera._u32(4).value,2)
            self.assertEqual(camera._u32(8).value,2)
            self.assertEqual(camera._u32(28).value,1280)
            self.assertEqual(camera._u32(32).value,720)
            self.assertEqual(C.c_uint64.from_address(camera.address+40).value,333333)
            slot = camera.address+camera.offsets[2]
            self.assertGreater(C.c_uint64.from_address(slot).value,0)
            self.assertEqual(C.c_uint8.from_address(slot+32).value,16)
            self.assertEqual(C.c_uint8.from_address(slot+32+1280*720).value,128)
            with self.assertRaisesRegex(RuntimeError,'in use'):
                Camera(1280,720,30)
            self.assertEqual(camera._u32(8).value,2)  # contender must not stop owner
            camera._u32(0).value = 0xffffffff
            camera.send(frame)
            self.assertEqual(camera._u32(4).value,0)
        self.assertIsNone(camera.last_frame)
        self.assertIsNone(camera.handle)
        with Camera(1280,720,30):
            pass


if __name__ == '__main__':
    unittest.main()

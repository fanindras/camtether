import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from video_quality import load_quality, save_quality, PROFILES
from gpu_usage import busiest_engine
from effects import Effects
import numpy as np

class QualityTests(unittest.TestCase):
    def test_profile_persistence_and_corrupt_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for profile in PROFILES:
                save_quality(root,profile)
                self.assertEqual(load_quality(root),profile)
            with self.assertRaises(ValueError):save_quality(root,'4k')
            (root/'video.json').write_text('[]')
            self.assertEqual(load_quality(root),'720p')

    def test_all_profiles_produce_correct_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            for size in PROFILES.values():
                fx=Effects(Path(folder),output_size=size)
                settings, revision=fx.snapshot()
                output=fx.process(np.full((1080,1920,3),128,dtype=np.uint8),settings,revision)
                self.assertEqual(output.shape,(size[1],size[0],3))
                self.assertEqual(output.dtype,np.uint8)

    def test_live_quality_updates_and_rejects_old_output(self):
        from phonecam import Bridge
        import io
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            bridge=Bridge();bridge.effects=Effects(Path(folder))
            data=io.BytesIO();Image.new('RGB',(32,32),'red').save(data,format='JPEG')
            bridge.accept(data.getvalue(),bridge.token)
            _,_,epoch,received=bridge.raw_snapshot()
            bridge.set_quality('1080p')
            self.assertEqual(bridge.effects.output_size,(1920,1080))
            self.assertEqual(load_quality(Path(folder)/'.local'),'1080p')
            self.assertFalse(bridge.publish_processed(np.zeros((720,1280,3),np.uint8),epoch,received))
            self.assertTrue(bridge.publish_processed(np.zeros((1080,1920,3),np.uint8),epoch,received))
            for mode in ('Auto','50 Hz','60 Hz'):bridge.set_lighting(mode)
            with self.assertRaises(ValueError):bridge.set_lighting('anything')

    def test_output_thread_reopens_without_app_restart(self):
        from phonecam import Bridge
        from unittest.mock import patch
        import threading,time
        opened=[]
        with tempfile.TemporaryDirectory() as folder:
            bridge=Bridge();bridge.effects=Effects(Path(folder))
            class FakeCamera:
                def __init__(self,w,h,fps):opened.append((w,h))
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def send(self,frame):pass
                def sleep_until_next_frame(self):time.sleep(.005)
            with patch('phonecam.Camera',FakeCamera),patch('camera_registration.check'):
                worker=threading.Thread(target=bridge.virtual_camera);worker.start()
                try:
                    end=time.monotonic()+2
                    while len(opened)<1 and time.monotonic()<end:time.sleep(.01)
                    bridge.set_quality('1080p')
                    while len(opened)<2 and time.monotonic()<end:time.sleep(.01)
                    self.assertEqual(opened[:2],[(1280,720),(1920,1080)])
                    self.assertTrue(worker.is_alive())
                finally:bridge.closed.set();worker.join(2)

    def test_native_output_all_profiles(self):
        from obs_camera import Camera
        for width,height in PROFILES.values():
            with Camera(width,height,30) as camera:
                frame=np.zeros((height,width,3),dtype=np.uint8)
                camera.send(frame)
                self.assertEqual(camera._u32(28).value,width)
                self.assertEqual(camera._u32(32).value,height)
                self.assertEqual(camera.converter.buffer.size,width*height*3//2)

    def test_gpu_combines_processes_but_not_engines(self):
        self.assertEqual(busiest_engine([('pid_1_luid_0x1_0x2_phys_0_eng_0_engtype_3D',30),('pid_2_luid_0x1_0x2_phys_0_eng_0_engtype_3D',40),('pid_1_luid_0x1_0x2_phys_0_eng_1_engtype_Copy',50)]),70)
        self.assertIsNone(busiest_engine([('bad',float('nan'))]))

if __name__=='__main__':unittest.main()

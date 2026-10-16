import io,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from effects import Effects
from phonecam import Bridge

def jpeg(color):
    data=io.BytesIO();Image.new('RGB',(32,32),color).save(data,format='JPEG');return data.getvalue()

class LifecycleTests(unittest.TestCase):
    def test_stop_restart_rejects_inflight_old_frame(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            bridge=Bridge();fx=Effects(tmp);bridge.effects=fx
            entered=threading.Event();release=threading.Event();second=threading.Event();release_second=threading.Event()
            calls=[]
            def process(frame,settings,revision):
                calls.append(frame)
                if len(calls)==1:entered.set();release.wait(3)
                else:second.set();release_second.wait(3)
                return frame
            fx.process=process
            bridge.accept(jpeg('red'),bridge.token)
            worker=threading.Thread(target=fx.run,args=(bridge,));worker.start()
            try:
                self.assertTrue(entered.wait(2))
                bridge.stop();bridge.accept(jpeg('blue'),bridge.token)
                release.set();self.assertTrue(second.wait(2))
                self.assertIsNone(bridge.current(),'previous stream frame escaped after restart')
                release_second.set()
                deadline=time.monotonic()+2
                while bridge.current() is None and time.monotonic()<deadline:time.sleep(.01)
                output=bridge.current();self.assertIsNotNone(output)
                self.assertGreater(int(output[0,0,2]),200)
            finally:
                release.set();release_second.set();bridge.closed.set();fx.wake.set();worker.join(2)
                self.assertFalse(worker.is_alive())

    def test_stale_processed_output_is_not_repeated_forever(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            bridge=Bridge();bridge.effects=Effects(tmp)
            bridge.accept(jpeg('red'),bridge.token)
            frame,_,epoch,received=bridge.raw_snapshot()
            self.assertTrue(bridge.publish_processed(frame,epoch,received))
            bridge.effects.output_received_at=time.monotonic()-3
            bridge.accept(jpeg('blue'),bridge.token)
            self.assertIsNone(bridge.current())

    def test_idle_processing_waits_for_event(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            bridge=Bridge();fx=Effects(tmp);bridge.effects=fx
            with patch.object(bridge,'raw_snapshot',wraps=bridge.raw_snapshot) as snapshots:
                worker=threading.Thread(target=fx.run,args=(bridge,));worker.start()
                try:
                    time.sleep(.15)
                    self.assertLessEqual(snapshots.call_count,2)
                    bridge.accept(jpeg('blue'),bridge.token)
                    deadline=time.monotonic()+2
                    while bridge.current() is None and time.monotonic()<deadline:time.sleep(.01)
                    self.assertIsNotNone(bridge.current())
                    old=fx.output_id;fx.set(mirror=True)
                    deadline=time.monotonic()+2
                    while fx.output_id==old and time.monotonic()<deadline:time.sleep(.01)
                    self.assertGreater(fx.output_id,old)
                finally:bridge.closed.set();fx.wake.set();worker.join(2)

    def test_segmentation_worker_releases_input_while_idle(self):
        import weakref,gc
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            fx=Effects(tmp);closed=threading.Event()
            fx.predict=lambda image:Image.new('L',(192,192),255)
            pending=Image.new('RGB',(1280,720));reference=weakref.ref(pending)
            fx.mask_job=(pending,('test',));del pending
            worker=threading.Thread(target=fx.mask_worker,args=(closed,));worker.start();fx.mask_event.set()
            try:
                deadline=time.monotonic()+2
                while fx.mask is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertIsNotNone(fx.mask)
                gc.collect();self.assertIsNone(reference())
            finally:closed.set();fx.mask_event.set();worker.join(2)

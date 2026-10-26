import sys,tempfile,time,unittest,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor'))
from effects import Effects,DEFAULTS,correct_perspective
from PIL import Image
import numpy as np

class EffectsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent);self.root=Path(self.tmp.name);self.fx=Effects(self.root,output_size=(200,100))
    def tearDown(self):self.tmp.cleanup()
    def test_background_survives_source_deletion_and_restart(self):
        source=self.root/'chosen.png';Image.new('RGB',(100,100),'blue').save(source)
        self.fx.choose_background(source);self.fx.set(zoom=1.5,brightness=1.2);self.fx.save();source.unlink()
        restored=Effects(self.root)
        self.assertEqual(restored.settings['background'],'Image');self.assertEqual(restored.settings['zoom'],1.5)
        self.assertEqual(restored.background_image.getpixel((0,0)),(0,0,255))
    def test_crop_mirror_rotation_and_adjustment(self):
        frame=np.zeros((100,200,3),dtype=np.uint8);frame[:,:100,0]=200;frame[:,100:,2]=200
        self.fx.set(mirror=True);s,rev=self.fx.snapshot();out=self.fx.process(frame,s,rev)
        self.assertGreater(out[50,10,2],190)
        self.fx.set(mirror=False,left=40,zoom=2,pan_x=1,rotation=0,brightness=.5)
        s,rev=self.fx.snapshot();out=self.fx.process(frame,s,rev)
        self.assertEqual(out.shape,frame.shape);self.assertGreater(out[50,100,2],90);self.assertLessEqual(out.max(),100)
        self.fx.set(rotation=90);s,rev=self.fx.snapshot();self.assertEqual(self.fx.process(frame,s,rev).shape,frame.shape)
    def test_background_fails_closed_then_composites_mask(self):
        frame=np.full((100,200,3),255,dtype=np.uint8)
        self.fx.set(background='Remove / plain color',color='#0000ff');s,rev=self.fx.snapshot()
        out=self.fx.process(frame,s,rev);self.assertTrue(np.all(out[:,:]==[0,0,255]))
        self.fx.mask=Image.new('L',(200,100),0);self.fx.mask.paste(255,(0,0,100,100))
        self.fx.mask_key=(frame.shape[:2],self.fx.output_size)+tuple(s[k] for k in ('zoom','pan_x','pan_y','left','right','top','bottom','rotation','mirror','framing','keystone_v','keystone_h','level'))+(0,)
        self.fx.mask_time=time.monotonic();out=self.fx.process(frame,s,rev)
        self.assertTrue(np.all(out[50,30]==[255,255,255]));self.assertTrue(np.all(out[50,170]==[0,0,255]))
    def test_cached_background_and_mask_invalidate(self):
        frame=np.full((100,200,3),255,dtype=np.uint8)
        self.fx.background_image=Image.new('RGB',(400,300),'blue')
        self.fx.set(background='Image');s,rev=self.fx.snapshot()
        self.fx.mask=Image.new('L',(192,192),0)
        self.fx.mask_key=(frame.shape[:2],self.fx.output_size)+tuple(s[k] for k in ('zoom','pan_x','pan_y','left','right','top','bottom','rotation','mirror','framing','keystone_v','keystone_h','level'))+(0,)
        self.fx.mask_time=time.monotonic()
        first=self.fx.process(frame,s,rev)
        cached_bg=self.fx._background_cache;cached_mask=self.fx._mask_cache
        np.testing.assert_array_equal(first,self.fx.process(frame,s,rev))
        self.assertIs(cached_bg,self.fx._background_cache);self.assertIs(cached_mask,self.fx._mask_cache)
        self.fx.background_image=Image.new('RGB',(400,300),'red')
        changed=self.fx.process(frame,s,rev);self.assertTrue(np.all(changed==[255,0,0]))
        self.fx.mask=Image.new('L',(192,192),255)
        changed=self.fx.process(frame,s,rev);self.assertTrue(np.all(changed==255))
        s['edge']=1.;self.fx.process(frame,s,rev)
        self.assertEqual(self.fx._mask_cache[1],1.)
        self.fx.mask_time=0
        expired=self.fx.process(frame,s,rev);self.assertTrue(np.all(expired==[255,0,0]))
        s['background']='Original';self.fx.process(frame,s,rev)
        self.assertIsNone(self.fx._mask_cache);self.assertIsNone(self.fx._background_cache)
        self.assertIsNone(self.fx.mask_job);self.assertIsNone(self.fx.mask)

    def test_model_inference_and_speed(self):
        self.fx.root=Path(__import__('os').environ.get('CAMTETHER_ASSETS',ROOT))
        image=Image.fromarray(np.random.default_rng(123).integers(0,255,(540,960,3),dtype=np.uint8))
        self.fx.predict(image)
        start=time.perf_counter();mask=self.fx.predict(image);elapsed=time.perf_counter()-start
        self.assertEqual(mask.size,(192,192));print(f'Background model warm inference: {elapsed*1000:.0f} ms')

    def test_portrait_fit_and_fill_without_baked_in_bars(self):
        portrait=np.full((320,180,3),170,dtype=np.uint8)
        s,rev=self.fx.snapshot();fit=self.fx.process(portrait,s,rev)
        self.assertEqual(fit.shape,(100,200,3));self.assertTrue(np.all(fit[:,0]==0))
        self.fx.set(framing='Fill frame');s,rev=self.fx.snapshot();fill=self.fx.process(portrait,s,rev)
        self.assertTrue(np.all(fill==170))
        # Vertical position must move the fill crop even at 1x zoom.
        portrait[:100]=10;portrait[220:]=240
        self.fx.set(pan_y=-1);s,rev=self.fx.snapshot();top=self.fx.process(portrait,s,rev)
        self.fx.set(pan_y=1);s,rev=self.fx.snapshot();bottom=self.fx.process(portrait,s,rev)
        self.assertLess(float(top.mean()),float(bottom.mean()))

    def test_keystone_and_level_do_not_create_black_borders(self):
        image=Image.new('RGB',(320,180),(140,170,200))
        for v,h,roll in [(0,0,0),(.08,0,0),(-.25,.25,12),(.25,-.25,-12)]:
            output=correct_perspective(image,v,h,roll)
            self.assertEqual(output.size,image.size)
            self.assertGreaterEqual(np.asarray(output).min(),139)

if __name__=='__main__':unittest.main(verbosity=2)

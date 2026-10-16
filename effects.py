"""Nonblocking local video editing and persistent background settings."""
import json, os, threading, time, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

DEFAULTS = dict(zoom=1., pan_x=0., pan_y=0., left=0., right=0., top=0., bottom=0.,
                rotation=0, mirror=False, brightness=1., contrast=1., saturation=1.,
                background='Original', color='#263b49', blur=16., edge=.5, framing='Fit entire image',
                keystone_v=0.,keystone_h=0.,level=0.,auto_keystone=False)

def correct_perspective(image,vertical=0.,horizontal=0.,level=0.):
    """Resample an inscribed quadrilateral; no synthetic face or missing pixels."""
    w,h=image.size
    if abs(level)>.001:
        radians=math.radians(abs(level))
        scale=math.cos(radians)+max(w/h,h/w)*math.sin(radians)
        image=image.resize((math.ceil(w*scale),math.ceil(h*scale)),Image.Resampling.BILINEAR)
        image=image.rotate(level,resample=Image.Resampling.BILINEAR,expand=False)
        x=(image.width-w)//2;y=(image.height-h)//2;image=image.crop((x,y,x+w,y+h))
    if abs(vertical)+abs(horizontal)<1e-6:return image
    v=max(-.3,min(.3,vertical));q=max(-.3,min(.3,horizontal))
    top=max(0,v)*w/2;bottom=max(0,-v)*w/2
    left=max(0,q)*h/2;right=max(0,-q)*h/2
    source=[(top,left),(w-top,right),(w-bottom,h-right),(bottom,h-left)]
    dest=[(0,0),(w,0),(w,h),(0,h)]
    rows=[];values=[]
    for (x,y),(u,z) in zip(dest,source):
        rows.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-z*x,-z*y]])
        values.extend([u,z])
    coeff=np.linalg.solve(np.asarray(rows,dtype=np.float64),np.asarray(values,dtype=np.float64))
    return image.transform((w,h),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BILINEAR)

class Effects:
    def __init__(self, root, output_size=(1280,720), storage=None):
        self.output_size=output_size
        self.root=Path(root)
        self.storage=Path(storage) if storage is not None else self.root/'.local'
        self.storage.mkdir(parents=True,exist_ok=True)
        self.config=self.storage/'edits.json'
        self.settings=DEFAULTS.copy()
        try:
            saved=json.loads(self.config.read_text())
            self.settings.update({k:v for k,v in saved.items() if k in DEFAULTS})
        except (OSError,ValueError):pass
        self.lock=threading.RLock()
        self.wake=threading.Event()
        self.output_epoch=-1;self.output_received_at=0.;self.processing_ms=0.
        self.revision=0;self.output=None;self.output_id=0;self.fps=0.;self.status='Edits saved automatically'
        self.background_image=None;self.session=None;self.mask=None;self.mask_key=None;self.mask_time=0.
        self.mask_job=None;self.mask_event=threading.Event();self.error=''
        self._background_cache=None;self._mask_cache=None
        self.auto_generation=0;self.auto_value=0.;self.auto_status='Automatic keystone off'
        self._load_background()

    def _load_background(self):
        try:
            with Image.open(self.storage/'background.png') as im:
                self.background_image=im.convert('RGB').copy()
        except OSError:pass

    def snapshot(self):
        with self.lock:return self.settings.copy(),self.revision

    def set(self, **changes):
        with self.lock:
            self.settings.update(changes);self.revision+=1;self.wake.set()
            if any(k in changes for k in ('rotation','mirror','auto_keystone')):
                self.auto_generation+=1;self.auto_value=0.

    def recalibrate(self):
        with self.lock:
            self.auto_generation+=1;self.auto_value=0.;self.revision+=1;self.wake.set()

    def auto_worker(self,bridge):
        from auto_keystone import estimate,consensus
        signature=None;samples=[];last_count=-1;finished=False
        while not bridge.closed.wait(.7):
            frame=bridge.raw_current();s,_=self.snapshot()
            if not s['auto_keystone']:
                self.auto_status='Automatic keystone off';signature=None;continue
            if frame is None:
                signature=None;self.auto_status='Auto keystone: waiting for camera';continue
            current=(frame.shape[:2],s['rotation'],s['mirror'],self.auto_generation)
            if current!=signature:
                signature=current;samples=[];finished=False
                with self.lock:self.auto_value=0.;self.revision+=1
            if finished or bridge.count==last_count:continue
            last_count=bridge.count
            try:
                image=Image.fromarray(frame)
                if s['rotation']:image=image.rotate(-int(s['rotation']),expand=True)
                if s['mirror']:image=ImageOps.mirror(image)
                samples.append(estimate(image))
                self.auto_status=f'Auto keystone: checking room lines ({len(samples)}/5)'
                if len(samples)<5:continue
                value=consensus(samples);finished=True
                with self.lock:
                    if self.auto_generation!=current[-1]:continue
                    self.auto_value=value if value is not None else 0.;self.revision+=1;self.wake.set()
                self.auto_status=('Auto keystone: insufficient reliable lines; unchanged' if value is None else
                                  f'Auto keystone locked: {value:+.3f} (mild correction)')
            except Exception:
                finished=True
                with self.lock:self.auto_value=0.;self.revision+=1
                self.auto_status='Auto keystone unavailable; image unchanged'

    def save(self):
        with self.lock:
            temp=self.config.with_suffix('.tmp')
            temp.write_text(json.dumps(self.settings,indent=2),encoding='utf-8')
            temp.replace(self.config)

    def choose_background(self, path):
        with Image.open(path) as image:
            image=ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1920,1080))
            temp=self.storage/'background.tmp.png';image.save(temp)
            temp.replace(self.storage/'background.png')
        with self.lock:
            self.background_image=image.copy();self.set(background='Image');self.save()

    @staticmethod
    def geometry(image,s,size=(1280,720)):
        if s['rotation']:image=image.rotate(-int(s['rotation']),expand=True)
        if s['mirror']:image=ImageOps.mirror(image)
        image=correct_perspective(image,s.get('keystone_v',0),s.get('keystone_h',0),s.get('level',0))
        w,h=image.size
        l,t=int(w*s['left']/100),int(h*s['top']/100)
        r,b=int(w*(1-s['right']/100)),int(h*(1-s['bottom']/100))
        if (l,t,r,b)!=(0,0,w,h):image=image.crop((l,t,max(l+1,r),max(t+1,b)))
        w,h=image.size;zoom=max(1.,float(s['zoom']))
        cw,ch=max(1,int(w/zoom)),max(1,int(h/zoom))
        x=int((w-cw)*(s['pan_x']+1)/2);y=int((h-ch)*(s['pan_y']+1)/2)
        if (x,y,cw,ch)!=(0,0,w,h):image=image.crop((x,y,x+cw,y+ch))
        if s['framing']=='Fill frame':
            return ImageOps.fit(image,size,method=Image.Resampling.BILINEAR,centering=((s['pan_x']+1)/2,(s['pan_y']+1)/2))
        return ImageOps.pad(image,size,method=Image.Resampling.BILINEAR,color='black')

    def predict(self,image):
        if self.session is None:
            os.environ['ORT_DISABLE_TELEMETRY']='1'
            import onnxruntime as ort
            ort.disable_telemetry_events()
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            options.add_session_config_entry("session.intra_op.allow_spinning", "0")
            options.add_session_config_entry("session.inter_op.allow_spinning", "0")
            self.session=ort.InferenceSession(str(self.root/'models'/'humanseg.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        data=np.asarray(image.resize((192,192),Image.Resampling.BILINEAR),dtype=np.float32)/127.5-1.
        tensor=np.ascontiguousarray(data.transpose(2,0,1)[None])
        prediction=self.session.run(None,{self.session.get_inputs()[0].name:tensor})[0][0,1]
        return Image.fromarray(np.uint8(np.clip(prediction,0,1)*255))

    def mask_worker(self,closed):
        while not closed.is_set():
            if not self.mask_event.wait(.2):continue
            self.mask_event.clear()
            with self.lock:
                job=self.mask_job
                self.mask_job=None
            if job is None:continue
            image,key=job
            try:
                mask=self.predict(image)
                with self.lock:
                    self.mask,self.mask_key,self.mask_time=mask,key,time.monotonic()
                    self.error=''
            except Exception as error:
                self.error='Background processing unavailable: '+str(error)
                closed.wait(1)
            finally:
                job=None;image=None

    def process(self,frame,s,revision):
        image=self.geometry(Image.fromarray(frame),s,self.output_size)
        mode=s['background']
        if mode!='Original':
            key=(frame.shape[:2],)+tuple(s[k] for k in ('zoom','pan_x','pan_y','left','right','top','bottom','rotation','mirror','framing','keystone_v','keystone_h','level'))+(s.get('_stream_epoch',0),)
            with self.lock:
                # PIL operations below return new images; the worker can share this immutable input.
                self.mask_job=(image,key)
                self.mask_event.set()
                mask=self.mask if self.mask is not None and self.mask_key==key and time.monotonic()-self.mask_time<1.5 else None
                bg=self.background_image
            if mode=='Blur':
                background=image.resize((320,180)).filter(ImageFilter.GaussianBlur(s['blur']/4)).resize(image.size)
            elif mode=='Image' and bg is not None:
                cache=self._background_cache
                if cache is None or cache[0] is not bg or cache[1]!=image.size:
                    cache=(bg,image.size,ImageOps.fit(bg,image.size,method=Image.Resampling.BILINEAR))
                    self._background_cache=cache
                background=cache[2]
            else:background=Image.new('RGB',image.size,s['color'])
            if mask is not None:
                # Adjustable foreground cutoff with a soft edge.
                cache=self._mask_cache
                if cache is None or cache[0] is not mask or cache[1:3]!=(s['edge'],image.size):
                    cutoff=float(s['edge'])*255
                    prepared=mask.point(lambda p:max(0,min(255,(p-cutoff)*3+128)))
                    prepared=prepared.resize(image.size,Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(1))
                    cache=(mask,s['edge'],image.size,prepared)
                    self._mask_cache=cache
                mask=cache[3]
                image=Image.composite(image,background,mask)
                self.status=self.error or 'Background active · settings saved on this laptop'
            else:
                # Never reveal the original room while a removal mask is unavailable.
                image=background if mode!='Blur' else image.filter(ImageFilter.GaussianBlur(24))
                self.status=self.error or 'Preparing background mask…'
        else:
            self._background_cache=None;self._mask_cache=None
            with self.lock:
                self.mask_job=None
                self.mask=None;self.mask_key=None
            self.status='Original background · settings saved on this laptop'
        if s['brightness']!=1:image=ImageEnhance.Brightness(image).enhance(s['brightness'])
        if s['contrast']!=1:image=ImageEnhance.Contrast(image).enhance(s['contrast'])
        if s['saturation']!=1:image=ImageEnhance.Color(image).enhance(s['saturation'])
        return np.asarray(image).copy()

    def run(self,bridge):
        threading.Thread(target=self.mask_worker,args=(bridge.closed,),daemon=True).start()
        threading.Thread(target=self.auto_worker,args=(bridge,),daemon=True).start()
        last=None;count=0;began=time.monotonic()
        while not bridge.closed.is_set():
            self.wake.clear()
            frame,number,epoch,received_at=bridge.raw_snapshot()
            s,rev=self.snapshot();key=(number,rev,epoch)
            s['_stream_epoch']=epoch
            if s['auto_keystone']:
                s.update(keystone_v=self.auto_value,keystone_h=0.,level=0.)
            if frame is None:
                self.output=None;last=None;self.wake.wait(.5);continue
            if key==last:self.wake.wait(.5);continue
            start=time.monotonic()
            try:
                output=self.process(frame,s,rev)
                # Don't publish a frame from a previous pairing or stopped stream.
                bridge.publish_processed(output,epoch,received_at)
                self.processing_ms=(time.monotonic()-start)*1000
                last=key;count+=1
            except Exception as error:
                self.status='Edit error: '+str(error);self.output=None;bridge.closed.wait(.1)
            elapsed=time.monotonic()-began
            if elapsed>=1:self.fps=count/elapsed;count=0;began=time.monotonic()
            bridge.closed.wait(max(0,1/30-(time.monotonic()-start)))

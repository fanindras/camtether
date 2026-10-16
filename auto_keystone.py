"""Conservative vertical-line calibration; no face landmarks or generated pixels."""
import numpy as np
from PIL import Image

def estimate(image):
    """Return a mild vertical correction only when distributed long lines agree.

    The middle half is excluded to keep the usual seated subject out of the
    estimate. This is a scene heuristic, not a camera/depth calibration.
    """
    image=image.convert('L');image.thumbnail((320,240))
    a=np.asarray(image,dtype=float);h,w=a.shape
    if min(h,w)<60:return None
    gy,gx=np.gradient(a)
    edge=(np.abs(gx)>max(18.,float(np.percentile(np.abs(gx),90)))) & (np.abs(gx)>2*np.abs(gy))
    edge[:,int(w*.25):int(w*.75)]=False
    edge[:4]=False;edge[-4:]=False;edge[:,:4]=False;edge[:,-4:]=False
    y,x=np.nonzero(edge)
    if len(x)<h:return None
    # Hough voting for x = midpoint + slope * (y - h/2).
    candidates=[]
    for slope in np.linspace(-.4,.4,161):
        bins=np.rint(x-slope*(y-h/2)).astype(int)
        valid=(bins>=0)&(bins<w)
        votes=np.bincount(bins[valid],minlength=w)
        for midpoint in np.argpartition(votes,-3)[-3:]:
            if votes[midpoint]<h*.35:continue
            hit=np.abs(x-midpoint-slope*(y-h/2))<1.6
            ys=y[hit]
            if len(ys)<h*.4 or np.ptp(ys)<h*.6:continue
            coverage=len(np.unique((ys*10//h)))
            if coverage<8:continue
            fitted,center=np.linalg.lstsq(np.column_stack((ys-h/2,np.ones(len(ys)))),x[hit],rcond=None)[0]
            residual=float(np.std(x[hit]-(center+fitted*(ys-h/2))))
            candidates.append((len(np.unique(ys))-10*residual,float(center),float(fitted)))
    lines=[]
    for score,midpoint,slope in sorted(candidates,reverse=True):
        if all(abs(midpoint-p)>w*.045 for p,_ in lines):lines.append((midpoint,slope))
        if len(lines)==12:break
    if len(lines)<3:return None
    points=np.array(lines);xx=points[:,0]/w;ss=points[:,1]*h/w
    if xx.min()>.25 or xx.max()<.75:return None
    # Parallel real-world verticals share a vanishing point. Reject outliers.
    best=None
    for i in range(len(xx)):
        for j in range(i):
            if abs(xx[i]-xx[j])<.4:continue
            k=(ss[i]-ss[j])/(xx[i]-xx[j]);b=ss[i]-k*(xx[i]-.5)
            keep=np.abs(ss-(k*(xx-.5)+b))<.015
            if keep.sum()>=3 and np.ptp(xx[keep])>.5:
                if best is None or keep.sum()>best.sum():best=keep
    if best is None:return None
    k,b=np.linalg.lstsq(np.column_stack((xx[best]-.5,np.ones(best.sum()))),ss[best],rcond=None)[0]
    # Strong roll/off-center vanishing points need calibrated 3D geometry.
    if abs(b)>.04 or abs(k)>.5:return None
    v=k/(1+abs(k)/2)
    return float(np.clip(v,-.06,.06))

def consensus(samples):
    """Require three consistent observations before locking calibration."""
    valid=[v for v in samples if v is not None]
    if len(valid)<3 or max(valid)-min(valid)>.015:return None
    return float(np.median(valid))

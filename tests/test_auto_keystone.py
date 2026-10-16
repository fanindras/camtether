import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
from PIL import Image,ImageDraw
from auto_keystone import estimate,consensus
class AutoTests(unittest.TestCase):
 def scene(self,k):
  im=Image.new('RGB',(320,240),'#777777');d=ImageDraw.Draw(im)
  for x in [25,65,255,295]:
   slope=k*(x/320-.5)*320/240
   d.line((x-slope*120,0,x+slope*120,239),fill='white',width=3)
  return im
 def test_sign_and_limit(self):
  for k in [-.25,-.04,0,.04,.25]:
   v=estimate(self.scene(k));print(k,v)
   self.assertIsNotNone(v);self.assertLessEqual(abs(v),.06)
   if k:self.assertGreater(v*k,0)
   else:self.assertLess(abs(v),.01)
 def test_reject_blank_and_single_edge(self):
  im=Image.new('RGB',(320,240),'gray');self.assertIsNone(estimate(im))
  ImageDraw.Draw(im).line((30,0,55,239),fill='white',width=3)
  self.assertIsNone(estimate(im))
 def test_consensus(self):
  self.assertIsNone(consensus([None,None,.03,None,.03]))
  self.assertIsNone(consensus([.06,-.06,.03]))
  self.assertAlmostEqual(consensus([.03,.032,None,.031,None]),.031)
if __name__=='__main__':unittest.main(verbosity=2)

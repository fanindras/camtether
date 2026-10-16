import sys, io, ssl, threading, unittest, urllib.request, urllib.error, time, http.client
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phonecam as app

class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge=app.Bridge()
        cls.server=app.make_server(cls.bridge,0,['127.0.0.1'])
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.context=ssl._create_unverified_context()
        b=io.BytesIO();app.Image.new('RGB',(320,240),'red').save(b,format='JPEG');cls.jpeg=b.getvalue()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def request(self,path,data=None,token=None,extra=None):
        headers={'X-CamTether-Token':token or self.bridge.token,'Content-Type':'image/jpeg'}
        headers.update(extra or {})
        req=urllib.request.Request(self.base+path,data=data,headers=headers)
        try:
            with urllib.request.urlopen(req,context=self.context,timeout=10) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()

    def test_upload_fit_stop(self):
        self.assertEqual(self.request('/frame',self.jpeg)[0],204)
        frame=self.bridge.current();self.assertEqual(frame.shape,(240,320,3))
        self.assertGreater(int(frame[120,160,0]),240)
        self.assertGreater(int(frame[120,0,0]),240)
        self.assertEqual(self.request('/stop',b'')[0],204)
        self.assertIsNone(self.bridge.current())

    def test_invalid_token_and_origin(self):
        self.assertEqual(self.request('/frame',self.jpeg,token='wrong')[0],403)
        self.assertEqual(self.request('/frame',self.jpeg,extra={'Origin':'https://other.example'})[0],403)

    def test_bad_and_oversized_frames(self):
        self.assertEqual(self.request('/frame',b'not jpeg')[0],400)
        # Server rejects an oversized declared body before accepting any bytes.
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        conn.putrequest('POST','/frame')
        conn.putheader('X-CamTether-Token',self.bridge.token)
        conn.putheader('Content-Length','1500001')
        conn.endheaders()
        self.assertEqual(conn.getresponse().status,413)
        conn.close()

    def test_disconnect_and_stale(self):
        old=self.bridge.token;self.bridge.rotate_pairing()
        self.assertEqual(self.request('/frame',self.jpeg,token=old)[0],403)
        self.assertEqual(self.request('/frame',self.jpeg)[0],204)
        self.bridge.last_frame=time.monotonic()-3
        self.assertIsNone(self.bridge.current())

    def test_web_page_and_private_status(self):
        code,body=self.request('/');self.assertEqual(code,200)
        self.assertIn(b'getUserMedia',body)
        self.assertNotIn(self.bridge.token.encode(),body)
        self.assertEqual(self.request('/status',token='wrong')[0],404)
        self.assertEqual(self.request('/status')[0],200)

if __name__=='__main__':unittest.main(verbosity=2)

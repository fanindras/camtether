"""Local phone-to-Windows webcam bridge. Video stays in RAM; no cloud services."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import argparse, hmac, io, json, os, secrets, socket, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from obs_camera import Camera
import qrcode

from app_paths import user_data_dir

WIDTH, HEIGHT, FPS = 1280, 720, 30
Image.MAX_IMAGE_PIXELS = 4_000_000

class Bridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.token = secrets.token_urlsafe(24)
        self.frame = None
        self.last_frame = 0.0
        self.count = 0
        self.epoch = 0
        self.driver_status = 'Starting webcam output…'
        self.driver_ready = False
        self.closed = threading.Event()
        self.effects = None
        self.active_output_size = None
        self.lighting = 'Auto'
        self.camera_info = {}

    def set_quality(self, profile):
        from video_quality import PROFILES, save_quality
        if profile not in PROFILES:raise ValueError('Unsupported video quality')
        save_quality(self.effects.storage, profile)
        self.effects.set_output_size(PROFILES[profile])

    def set_lighting(self, mode):
        if mode not in ('Auto','50 Hz','60 Hz'):raise ValueError('Invalid lighting frequency')
        with self.lock:self.lighting=mode


    def accept(self, data, token):
        with self.lock:
            epoch = self.epoch
            if not hmac.compare_digest(token, self.token):
                return False
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'JPEG' or image.width*image.height > 4_000_000:
                raise ValueError('JPEG frame too large or invalid')
            image.load()
            # Keep original pixels: framing belongs in the editor, before padding.
            image = image.convert('RGB')
            frame = np.asarray(image).copy()
        with self.lock:
            if epoch != self.epoch or not hmac.compare_digest(token, self.token):
                return False
            if self.last_frame and time.monotonic()-self.last_frame >= 2:
                self.epoch += 1
            self.frame, self.last_frame = frame, time.monotonic()
            self.count += 1
            if self.effects:self.effects.wake.set()
        return True

    def stop(self):
        with self.lock:
            self.frame, self.last_frame = None, 0
            self.epoch += 1
            if self.effects:self.effects.wake.set()

    def rotate_pairing(self):
        with self.lock:
            self.token = secrets.token_urlsafe(24)
            self.frame, self.last_frame = None, 0
            self.epoch += 1
            if self.effects:self.effects.wake.set()

    def raw_snapshot(self):
        with self.lock:
            frame = self.frame if time.monotonic()-self.last_frame < 2 else None
            return frame, self.count, self.epoch, self.last_frame

    def raw_current(self):
        return self.raw_snapshot()[0]

    def publish_processed(self, frame, epoch, received_at):
        with self.lock:
            if epoch != self.epoch or self.frame is None or time.monotonic()-received_at >= 2:
                return False
            if frame.shape[:2] != self.effects.output_size[::-1]:return False
            self.effects.output = frame
            self.effects.output_epoch = epoch
            self.effects.output_received_at = received_at
            self.effects.output_id += 1
            return True

    def current(self):
        with self.lock:
            if self.frame is None or time.monotonic()-self.last_frame >= 2:return None
            if self.effects is None:return self.frame
            if self.effects.output_epoch != self.epoch:return None
            if time.monotonic()-self.effects.output_received_at >= 2:return None
            return self.effects.output

    def virtual_camera(self):
        import camera_registration
        while not self.closed.is_set():
            width, height = self.effects.output_size if self.effects else (WIDTH, HEIGHT)
            blank = np.zeros((height, width, 3), dtype=np.uint8)
            try:
                with Camera(width, height, FPS) as cam:
                    camera_registration.check()
                    next_check = time.monotonic()+1
                    self.active_output_size = (width, height)
                    self.driver_ready = True
                    self.driver_status = 'Ready · select CamTether in your meeting app'
                    while not self.closed.is_set():
                        if self.effects and self.effects.output_size != (width,height):
                            self.driver_ready=False
                            self.driver_status='Applying video quality...'
                            break
                        if time.monotonic() >= next_check:
                            camera_registration.check()
                            next_check = time.monotonic()+1
                        frame = self.current()
                        cam.send(frame if frame is not None and frame.shape == blank.shape else blank)
                        cam.sleep_until_next_frame()
                # Readers release the old shared queue after observing STOPPING.
                self.closed.wait(.1)
            except Exception as error:
                self.driver_ready = False
                self.driver_status = 'Webcam output unavailable: '+str(error)
                self.closed.wait(3)
        self.driver_ready = False

def make_server(bridge, port, ips, usb=True):
    if not usb:
        raise ValueError("CamTether supports direct USB loopback only.")
    html = (ROOT/'phone.html').read_bytes()
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def setup(self):
            super().setup()
            self.connection.settimeout(6)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        def log_message(self, *args):
            pass  # Never log pairing tokens or video.

        def reply(self, status, body=b'', content_type='text/plain; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            if status >= 400:
                self.send_header('Connection', 'close')
                self.close_connection = True
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; media-src blob:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            if body: self.wfile.write(body)

        def authorized(self):
            supplied = self.headers.get('X-CamTether-Token', '')
            return bool(supplied) and hmac.compare_digest(supplied, bridge.token)

        def do_GET(self):
            if urlsplit(self.path).path == '/':
                self.reply(200, html, 'text/html; charset=utf-8')
            elif self.path == '/status' and self.authorized():
                data = {'lighting': bridge.lighting, 'output_size': bridge.effects.output_size if bridge.effects else [WIDTH, HEIGHT], 'frames': bridge.count, 'live': bridge.current() is not None,
                        'virtual_camera': bridge.driver_ready,
                        'processed_fps': round(bridge.effects.fps,1) if bridge.effects else None,
                        'editor_status': bridge.effects.status if bridge.effects else None,
                        'processing_ms': round(bridge.effects.processing_ms,1) if bridge.effects else None,
                        'output_age_ms': round((time.monotonic()-bridge.effects.output_received_at)*1000,1) if bridge.effects and bridge.current() is not None else None}
                self.reply(200, json.dumps(data).encode(), 'application/json')
            else:
                self.reply(404)

        def do_POST(self):
            if not self.authorized():
                self.reply(403); return
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.reply(403); return
            if self.path == '/camera-info':
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0 < size <= 4096 or self.headers.get('Content-Type') != 'application/json':
                        self.reply(400);return
                    info=json.loads(self.rfile.read(size))
                    if not isinstance(info,dict):raise ValueError('Invalid camera status')
                    clean={}
                    for key in ('width','height'):
                        value=info.get(key,0)
                        if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=8192:raise ValueError('Invalid size')
                        clean[key]=value
                    clean['lighting_status']=str(info.get('lighting_status',''))[:240]
                    with bridge.lock:bridge.camera_info=clean
                    self.reply(204)
                except (ValueError,TypeError,OSError):self.reply(400)
                return
            if self.path == '/stop':
                bridge.stop(); self.reply(204); return
            if self.path != '/frame':
                self.reply(404); return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 1 or size > 1_500_000:
                    self.reply(413); return
                data = self.rfile.read(size)
                if len(data) != size or self.headers.get('Content-Type') != 'image/jpeg':
                    self.reply(400); return
                accepted = bridge.accept(data, self.headers.get('X-CamTether-Token', ''))
                self.reply(204 if accepted else 403)
            except (ValueError, OSError, Image.DecompressionBombError):
                self.reply(400)

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        def handle_error(self, request, client_address):
            if not isinstance(sys.exc_info()[1], OSError):
                super().handle_error(request, client_address)
        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(6)
            return sock, address

    return Server(('127.0.0.1', port), Handler)


def adb_command(*args):
    from usb_runtime import adb_path
    adb = adb_path(ROOT)
    if not adb.exists():
        raise RuntimeError('Android USB tools are missing from the app folder.')
    result = subprocess.run([str(adb), '-d', *args], capture_output=True, text=True,
                            timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError('USB connection is not ready. Enable USB debugging and accept "Allow USB debugging" on your OPPO.\n\n'+detail)
    return result.stdout.strip()

def show_window(bridge, port, ips, usb=True):
    from desktop import show
    show(bridge, port, ips, usb, ROOT, adb_command)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--usb', action='store_true', default=True, help='Direct USB forwarding; requires USB debugging')
    args = parser.parse_args()
    ips, bridge = ['127.0.0.1'], Bridge()
    from effects import Effects
    from video_quality import load_quality, PROFILES
    bridge.effects = Effects(ROOT, output_size=PROFILES[load_quality(user_data_dir())], storage=user_data_dir())
    threading.Thread(target=bridge.effects.run,args=(bridge,),daemon=True).start()
    server = make_server(bridge, args.port, ips, usb=args.usb)
    if args.usb:
        try:
            adb_command('reverse', f'tcp:{server.server_port}', f'tcp:{server.server_port}')
        except Exception:
            if args.headless:
                server.server_close()
                raise
            bridge.driver_status = 'Connect your phone, then click Wake phone & start camera.'
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import camera_registration
    try:
        camera_registration.register()
        threading.Thread(target=bridge.virtual_camera, daemon=True).start()
        if args.state_file:
            args.state_file.write_text(json.dumps({'port':server.server_port, 'token':bridge.token, 'ips':ips, 'usb':args.usb}))
        if args.headless:
            while not bridge.closed.wait(1): pass
        else:
            show_window(bridge, server.server_port, ips, usb=args.usb)
    finally:
        bridge.closed.set(); bridge.stop(); server.shutdown(); server.server_close()
        try:
            camera_registration.unregister()
        finally:
            if args.usb:
                try:
                    adb_command('reverse', '--remove', f'tcp:{server.server_port}')
                except Exception:
                    pass
        if getattr(bridge, 'remove_camera_files', False):
            import usb_runtime
            errors = []
            for remove in (camera_registration.remove_files, usb_runtime.remove_files):
                try:
                    remove()
                except Exception as error:
                    errors.append(error)
            if errors:
                raise ExceptionGroup('Component cleanup needs attention', errors)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        (user_data_dir()/'error.log').write_text(f'{type(error).__name__}: {error}\n', encoding='utf-8')
        if '--headless' in sys.argv: raise
        import tkinter.messagebox
        tkinter.messagebox.showerror('CamTether could not start', str(error)+'\n\nClose any other CamTether window and try again. Details: error.log')

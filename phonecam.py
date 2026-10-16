"""Local phone-to-Windows webcam bridge. Video stays in RAM; no cloud services."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import argparse, datetime, hmac, io, ipaddress, json, os, secrets, socket, ssl, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import numpy as np
from PIL import Image, ImageOps, ImageDraw
import pyvirtualcam, qrcode
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app_paths import user_data_dir

WIDTH, HEIGHT, FPS = 1280, 720, 30
Image.MAX_IMAGE_PIXELS = 4_000_000

def local_ips():
    ips = []
    usb_ips = []
    if sys.platform == 'win32':
        try:
            command = "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and ($_.InterfaceDescription -match 'Remote NDIS|RNDIS|Internet Sharing|USB NCM' -or $_.PnPDeviceID -like 'USB\\VID_22D9*') } | ForEach-Object { Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue } | Select-Object -ExpandProperty IPAddress"
            result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command], capture_output=True, text=True, timeout=12, creationflags=subprocess.CREATE_NO_WINDOW)
            for value in result.stdout.splitlines():
                value = value.strip()
                try:
                    ip = ipaddress.ip_address(value)
                    if ip.version == 4 and not ip.is_link_local:
                        usb_ips.append(value)
                except ValueError:
                    pass
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        # UDP connect selects the route without transmitting application data.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('192.0.2.1', 80))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    ips = list(dict.fromkeys(ip for ip in ips if not ip.startswith('127.'))) or ['127.0.0.1']
    try:
        preferred = json.loads((user_data_dir()/'preferences.json').read_text()).get('preferred_ip')
        if preferred in ips:
            ips.remove(preferred); ips.insert(0, preferred)
    except (OSError, ValueError):
        pass
    return list(dict.fromkeys(usb_ips + ips))

def certificate(ips):
    folder = user_data_dir()
    folder.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'CamTether local camera')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5))
            .not_valid_after(now+datetime.timedelta(days=30))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]+[
                x509.IPAddress(ipaddress.ip_address(ip)) for ip in set(ips+['127.0.0.1'])]), critical=False)
            .sign(key, hashes.SHA256()))
    keyfile, certfile = folder/'key.pem', folder/'cert.pem'
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return certfile, keyfile

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
        blank = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        while not self.closed.is_set():
            try:
                with pyvirtualcam.Camera(WIDTH, HEIGHT, FPS, backend='obs') as cam:
                    self.driver_ready = True
                    self.driver_status = 'Ready · select OBS Virtual Camera in your meeting app'
                    while not self.closed.is_set():
                        frame = self.current()
                        cam.send(frame if frame is not None else blank)
                        cam.sleep_until_next_frame()
            except Exception:
                self.driver_ready = False
                self.driver_status = 'Webcam driver unavailable. Install OBS Studio; keep its virtual camera stopped.'
                self.closed.wait(3)
        self.driver_ready = False

def make_server(bridge, port, ips, usb=False):
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
                data = {'frames': bridge.count, 'live': bridge.current() is not None,
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
            if origin and origin != ('http://' if usb else 'https://') + self.headers.get('Host', ''):
                self.reply(403); return
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
            # Expected when the phone/browser initially rejects the local certificate.
            if not isinstance(sys.exc_info()[1], (OSError, ssl.SSLError)):
                super().handle_error(request, client_address)
        # Complete TLS handshakes in request threads, not the accept loop.
        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(6)
            if usb:
                return sock, address
            return self.context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False), address

    if usb:
        return Server(('127.0.0.1', port), Handler)
    cert, key = certificate(ips)
    server = Server(('0.0.0.0', port), Handler)
    server.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.context.minimum_version = ssl.TLSVersion.TLSv1_2
    server.context.load_cert_chain(cert, key)
    return server

def adb_command(*args):
    adb = ROOT/'android-tools'/'platform-tools'/'adb.exe'
    if not adb.exists():
        raise RuntimeError('Android USB tools are missing from the app folder.')
    result = subprocess.run([str(adb), '-d', *args], capture_output=True, text=True,
                            timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError('USB connection is not ready. Enable USB debugging and accept "Allow USB debugging" on your OPPO.\n\n'+detail)
    return result.stdout.strip()

def show_window(bridge, port, ips, usb=False):
    from desktop import show
    show(bridge, port, ips, usb, ROOT, adb_command)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--usb', action='store_true', help='Direct USB forwarding; requires USB debugging')
    args = parser.parse_args()
    ips, bridge = (['127.0.0.1'] if args.usb else local_ips()), Bridge()
    from effects import Effects
    bridge.effects = Effects(ROOT, storage=user_data_dir())
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
    threading.Thread(target=bridge.virtual_camera, daemon=True).start()
    if args.state_file:
        args.state_file.write_text(json.dumps({'port':server.server_port, 'token':bridge.token, 'ips':ips, 'usb':args.usb}))
    try:
        if args.headless:
            while not bridge.closed.wait(1): pass
        else:
            show_window(bridge, server.server_port, ips, usb=args.usb)
    finally:
        bridge.closed.set(); bridge.stop(); server.shutdown(); server.server_close()
        if args.usb:
            try:
                adb_command('reverse', '--remove', f'tcp:{server.server_port}')
            except Exception:
                pass

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        (user_data_dir()/'error.log').write_text(f'{type(error).__name__}: {error}\n', encoding='utf-8')
        if '--headless' in sys.argv: raise
        import tkinter.messagebox
        tkinter.messagebox.showerror('CamTether could not start', str(error)+'\n\nClose any other CamTether window and try again. Details: error.log')

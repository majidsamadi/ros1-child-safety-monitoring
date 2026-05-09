#!/usr/bin/env python3
# Optional helper for laptop testing, not required on Jupiter robot.
import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2

latest_jpeg = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_jpeg
        if self.path in ['/', '/health']:
            self.send_response(200); self.end_headers(); self.wfile.write(b'OK. Use /video')
            return
        if self.path != '/video':
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        while True:
            if latest_jpeg is None:
                time.sleep(0.05); continue
            try:
                frame_data = latest_jpeg
                header = (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n'
                    b'\r\n'
                )
                self.wfile.write(header)
                self.wfile.write(frame_data)
                self.wfile.write(b'\r\n')
                time.sleep(0.03)
            except Exception:
                break
    def log_message(self, *args):
        return

def main():
    global latest_jpeg
    ap = argparse.ArgumentParser()
    ap.add_argument('--camera', type=int, default=0)
    ap.add_argument('--port', type=int, default=8090)
    args = ap.parse_args()
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError('Could not open camera')
    server = ThreadingHTTPServer(('0.0.0.0', args.port), Handler)
    import threading
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f'Open http://127.0.0.1:{args.port}/video')
    try:
        while True:
            ok, frame = cap.read()
            if ok:
                ok, jpg = cv2.imencode('.jpg', frame)
                if ok: latest_jpeg = jpg.tobytes()
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release(); server.shutdown()

if __name__ == '__main__':
    main()

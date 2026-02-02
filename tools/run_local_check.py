import threading, time, json
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

class SimpleExpert(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *a): pass

srv = HTTPServer(('127.0.0.1',8005), SimpleExpert)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print('started')
for i in range(5):
    try:
        r = requests.get('http://127.0.0.1:8005/health', timeout=1)
        print('status', r.status_code, r.text)
    except Exception as e:
        print('err', e)
    time.sleep(0.5)
srv.shutdown()
print('stopped')

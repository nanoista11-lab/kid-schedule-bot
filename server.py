import subprocess
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

DATA_FILE = Path("data/events.json")
DATA_FILE.parent.mkdir(exist_ok=True)
PORT = int(os.environ.get("PORT", 8080))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/events":
            data = DATA_FILE.read_text(encoding="utf-8") if DATA_FILE.exists() else "[]"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(Path("index.html").read_bytes())

    def do_POST(self):
        if urlparse(self.path).path == "/api/events":
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            events = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else []
            events.append(body)
            DATA_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/events/"):
            event_id = int(path.split("/")[-1])
            events = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else []
            events = [e for e in events if e["id"] != event_id]
            DATA_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass

HTTPServer(("", PORT), Handler).serve_forever()



"""Local preview with live reload: serves site/ and reloads the page when a file changes.
Standard library only. For development only (not used by the published site).

    python site/dev.py [--host 0.0.0.0] [--port 8790]
"""
import argparse
import functools
import http.server
import os
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SNIPPET = b"""<script>(()=>{const s=new EventSource('/__reload');s.onmessage=()=>location.reload();})();</script>"""
state = {"stamp": 0.0}
# Published copies of repo images (the workflow copies the same files): one source, docs/.
ALIASES = {"/assets/controller.webp": "docs/xbox-controller.webp", "/assets/remap-screen.png": "docs/remap-screen.png"}


def scan():
    latest = 0.0
    for d, _, files in os.walk(ROOT):
        for f in files:
            try:
                latest = max(latest, os.path.getmtime(os.path.join(d, f)))
            except OSError:
                pass
    return latest


def watch():
    while True:
        state["stamp"] = scan()
        time.sleep(0.4)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/__reload":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            seen = state["stamp"]
            try:
                while True:
                    time.sleep(0.4)
                    if state["stamp"] != seen:
                        self.wfile.write(b"data: reload\n\n")
                        self.wfile.flush()
                        return
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
        alias = ALIASES.get(self.path.split("?")[0])
        if alias:
            full = os.path.join(ROOT, "..", alias)
            data = open(full, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(full))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.endswith(".html") and os.path.isfile(path):
            body = open(path, "rb").read().replace(b"</body>", SNIPPET + b"</body>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8790)
    a = ap.parse_args()
    threading.Thread(target=watch, daemon=True).start()
    srv = http.server.ThreadingHTTPServer((a.host, a.port), functools.partial(Handler, directory=ROOT))
    srv.daemon_threads = True
    print(f"preview: http://{a.host}:{a.port}/")
    srv.serve_forever()


if __name__ == "__main__":
    main()

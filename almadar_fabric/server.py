"""Loopback-only demo server. Deliberately has no production deployment mode."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
from .models import Order
from .runtime import SCENARIOS, run, sample_order

WEB = Path(__file__).parent / "web"


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/scenarios":
            return self.respond(200, {"scenarios": SCENARIOS, "order": vars(sample_order())})
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "application/javascript; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path in assets:
            name, mime = assets[path]
            return self.respond(200, (WEB / name).read_bytes(), mime)
        self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/run":
            return self.respond(404, {"error": "Not found"})
        origin = self.headers.get("Origin")
        allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        if origin and origin not in allowed:
            return self.respond(403, {"error": "Cross-origin requests are not supported"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.respond(415, {"error": "Expected application/json"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                return self.respond(413, {"error": "Request must be between 1 and 16,384 bytes"})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) - {"scenario", "order"}:
                raise ValueError("Expected scenario and optional order")
            order = Order.from_dict(body["order"]) if "order" in body else sample_order()
            result = run(order, body.get("scenario", "ready"))
        except (ValueError, TypeError, UnicodeError) as exc:
            return self.respond(400, {"error": str(exc)})
        self.respond(200, result)


def serve(port=8080):
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Almadar service fulfilment: http://127.0.0.1:{server.server_port}", flush=True)
        print("Synthetic data only. Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

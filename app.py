"""Local web interface. Run: python app.py"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from crop_advisory.engine import ROOT, Ollama, AdvisoryError, advise

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.respond(200, json.dumps({"status": "ok", "offline": True}))
        elif path == "/api/models":
            try:
                self.respond(200, json.dumps(Ollama(timeout=3).request("/api/tags")))
            except (ValueError, AdvisoryError) as exc:
                self.respond(503, json.dumps({"error": str(exc)}))
        elif path in ("/", "/app.js", "/style.css"):
            name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[path]
            mime = {"/": "text/html", "/app.js": "text/javascript", "/style.css": "text/css"}[path]
            self.respond(200, (ROOT / "web" / name).read_text(encoding="utf-8"), mime + "; charset=utf-8")
        else:
            self.respond(404, '{"error":"Not found"}')

    def do_POST(self):
        if self.path != "/api/advice":
            return self.respond(404, '{"error":"Not found"}')
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self.respond(403, '{"error":"Cross-origin requests are not allowed"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16000:
                raise ValueError("Request body must be 1–16000 bytes.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Input must be an object.")
            model = payload.get("model")
            if model is not None and (not isinstance(model, str) or not model.strip() or len(model) > 200):
                raise ValueError("Invalid local model name.")
            result = advise(payload, model=model, mode=payload.get("mode", "llm"))
            self.respond(200, json.dumps(result, ensure_ascii=False))
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self.respond(400, json.dumps({"error": str(exc)}))
        except AdvisoryError as exc:
            self.respond(503, json.dumps({"error": str(exc)}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"CropAdvisory: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

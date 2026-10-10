"""Deterministic mock webhook service.

Accepts POST requests and returns a stable, predictable response. Used by the
playbook `mock_webhook` step in local development and tests so the stack never
depends on a paid external API.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class WebhookHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            received = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            received = {"raw": raw.decode("utf-8", errors="replace")}
        self._send(200, {"ok": True, "received": received, "path": self.path})

    def do_GET(self) -> None:  # noqa: N802
        self._send(200, {"ok": True, "service": "mock-webhook"})

    def log_message(self, *args) -> None:  # silence default logging
        pass


def main() -> None:
    port = int(os.environ.get("PORT", "9000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), WebhookHandler)
    print(f"mock-webhook listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

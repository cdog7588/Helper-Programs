#!/usr/bin/env python3
"""Local relay for Mediator <-> Figma plugin payload exchange."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

LATEST_PAYLOAD: dict[str, Any] = {
    "meta": {
        "source": "relay",
        "timestamp": "",
        "operation": "update",
    },
    "textBindings": {},
}
CACHE_PATH: Path | None = None


class RelayHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/figma-plugin":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return
        self._send_json(200, LATEST_PAYLOAD)

    def do_POST(self) -> None:  # noqa: N802
        global LATEST_PAYLOAD

        if self.path != "/figma-plugin":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"ok": False, "error": "Invalid Content-Length"})
            return

        try:
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"ok": False, "error": "Invalid JSON body"})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "error": "Payload must be a JSON object"})
            return

        LATEST_PAYLOAD = payload
        if CACHE_PATH is not None:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(LATEST_PAYLOAD, indent=2), encoding="utf-8")

        self._send_json(200, {"ok": True, "message": "Payload stored"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Local relay for Figma plugin payload fetch/apply.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--cache",
        default=".mediator/figma_payload.latest.json",
        help="Path to cache latest payload JSON.",
    )
    args = parser.parse_args()

    global CACHE_PATH
    CACHE_PATH = Path(args.cache).resolve()
    if CACHE_PATH.exists():
        try:
            existing = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                global LATEST_PAYLOAD
                LATEST_PAYLOAD = existing
        except (OSError, json.JSONDecodeError):
            pass

    server = ThreadingHTTPServer((args.host, args.port), RelayHandler)
    print(f"Relay listening on http://{args.host}:{args.port}/figma-plugin")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

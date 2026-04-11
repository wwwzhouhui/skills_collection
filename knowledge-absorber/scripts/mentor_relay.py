from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

from openai_compatible_client import OpenAICompatibleError, forward_request, normalize_connection


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8760


def build_test_messages() -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": "You are a connection probe. Reply with OK."},
        {"role": "user", "content": "Reply with OK."},
    ]


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "MentorRelay/1.0"

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "mentor-relay"})
            return
        self._send_json(404, {"ok": False, "message": "Not found"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send_json(400, {"ok": False, "message": "Invalid JSON body"})
            return

        try:
            if self.path == "/v1/test-connection":
                connection = normalize_connection(payload.get("connection") or {})
                result = forward_request(
                    connection,
                    build_test_messages(),
                    {"temperature": 0, "maxTokens": 16, "allowEmptyContent": True},
                )
                self._send_json(200, {"ok": True, **result})
                return

            if self.path == "/v1/chat":
                connection = normalize_connection(payload.get("connection") or {})
                messages = payload.get("messages") or []
                options = payload.get("options") or {}
                if not isinstance(messages, list) or not messages:
                    raise OpenAICompatibleError("messages 不能为空。", 400)
                result = forward_request(connection, messages, options)
                self._send_json(200, {"ok": True, **result})
                return

            self._send_json(404, {"ok": False, "message": "Not found"})
        except OpenAICompatibleError as exc:
            self._send_json(exc.status_code, {"ok": False, "message": exc.message})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local relay for mentor-mode HTML pages.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RelayHandler)
    print(f"Mentor relay listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

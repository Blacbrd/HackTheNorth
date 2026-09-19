from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProxyHandler(BaseHTTPRequestHandler):
    upstream = "http://192.168.0.38:8000"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def do_DELETE(self) -> None:
        self._proxy()

    def _proxy(self) -> None:
        body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "origin", "referer", "connection"}
        }
        request = Request(
            f"{self.upstream}{self.path}",
            data=body if body else None,
            headers=headers,
            method=self.command,
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = response.read()
                self.send_response(response.status)
                self._cors()
                for key, value in response.headers.items():
                    if key.lower() not in {"connection", "transfer-encoding"}:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)
        except HTTPError as error:
            payload = error.read()
            self.send_response(error.code)
            self._cors()
            self.send_header("content-type", error.headers.get("content-type", "text/plain"))
            self.end_headers()
            self.wfile.write(payload)
        except URLError as error:
            payload = f"Cannot reach robot API: {error.reason}".encode()
            self.send_response(502)
            self._cors()
            self.send_header("content-type", "text/plain")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def _cors(self) -> None:
        origin = self.headers.get("origin") or "*"
        self.send_header("access-control-allow-origin", origin)
        self.send_header("access-control-allow-credentials", "true")
        self.send_header("access-control-allow-methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("access-control-allow-headers", "content-type,accept")
        self.send_header("access-control-allow-private-network", "true")

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--upstream", default="http://192.168.0.38:8000")
    args = parser.parse_args()
    ProxyHandler.upstream = args.upstream.rstrip("/")
    server = ThreadingHTTPServer((args.host, args.port), ProxyHandler)
    print(f"Proxying http://{args.host}:{args.port} -> {ProxyHandler.upstream}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

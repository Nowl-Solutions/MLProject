"""
Pure-Python Local Static HTTP Server for NaviBay (serves dist/).

Usage:
  python server.py          # tries port 8000, falls back automatically if reserved/busy
  python server.py 8080     # use a specific port
"""

from __future__ import annotations

import functools
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
DIST_DIR = Path(__file__).resolve().parent / "dist"


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()


def main() -> None:
    handler = functools.partial(NoCacheHandler, directory=str(DIST_DIR))
    ports = [int(sys.argv[1])] if len(sys.argv) > 1 else [8000, 8080, 8888, 5000, 4173, 0]
    httpd = None
    last_err: OSError | None = None
    for port in ports:
        try:
            httpd = ThreadingHTTPServer((HOST, port), handler)
            break
        except OSError as err:
            last_err = err
    if httpd is None:
        raise last_err or RuntimeError("Could not bind to any local port")

    actual_port = httpd.server_address[1]
    with httpd:
        print(f"Serving NaviBay at http://{HOST}:{actual_port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

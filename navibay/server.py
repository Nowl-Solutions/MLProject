"""
Pure-Python Local Static HTTP Server for NaviBay (serves dist/ on http://127.0.0.1:4173).

Usage:
  python server.py
"""

from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 4173
DIST_DIR = Path(__file__).resolve().parent / "dist"


def main() -> None:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DIST_DIR))
    with ThreadingHTTPServer((HOST, PORT), handler) as httpd:
        print(f"Serving NaviBay at http://{HOST}:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Lightweight HTTP reverse proxy for TP-Link Router AP web management."""

import http.client
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .constants import CONFIG
from .context import Context

# Use ThreadingHTTPServer so hanging requests never block other clients
HTTPServer = ThreadingHTTPServer
_upstream_lock = threading.Lock()


class RouterProxyHandler(BaseHTTPRequestHandler):
    target_host: str = "10.43.0.2"
    alias_ip: str = "192.168.100.2"

    def log_message(self, format: str, *args: object) -> None:
        pass  # Quiet logging

    def do_HEAD(self) -> None:
        self._proxy("HEAD")

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_POST(self) -> None:
        self._proxy("POST")

    def _proxy(self, method: str) -> None:
        # Browser probes that TP-Link embedded server drops/resets
        if self.path in [
            "/favicon.ico",
            "/apple-touch-icon.png",
            "/apple-touch-icon-precomposed.png",
            "/robots.txt",
        ]:
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        url = f"http://{self.target_host}{self.path}"
        length = self.headers.get("Content-Length")
        body = self.rfile.read(int(length)) if length and length.isdigit() else None
        # TP-Link embedded server hangs on HEAD; convert upstream to GET
        upstream_method = "GET" if method == "HEAD" else method
        req = urllib.request.Request(url, data=body, method=upstream_method)

        for k, v in self.headers.items():
            if k.lower() in ["host", "referer"]:
                continue
            req.add_header(k, v)

        req.add_header("Host", self.target_host)
        referer = self.headers.get("Referer")
        if referer:
            for alias in [self.alias_ip, "192.168.100.69:8092", "192.168.100.69"]:
                referer = referer.replace(alias, self.target_host)
            req.add_header("Referer", referer)
        else:
            req.add_header("Referer", f"http://{self.target_host}/userRpm/Index.htm")

        try:
            with _upstream_lock:
                for attempt in range(2):
                    try:
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            self.send_response(resp.status)
                            content = resp.read()
                            ct = resp.headers.get("Content-Type", "")
                            if "text" in ct or "javascript" in ct:
                                content = content.replace(
                                    f"http://{self.target_host}".encode(),
                                    f"http://{self.alias_ip}".encode(),
                                )
                                content = content.replace(
                                    self.target_host.encode(),
                                    self.alias_ip.encode(),
                                )

                            for hk, hv in resp.headers.items():
                                hkl = hk.lower()
                                if hkl in ["transfer-encoding", "content-length"]:
                                    continue
                                if hkl == "location":
                                    hv = hv.replace(self.target_host, self.alias_ip)
                                self.send_header(hk, hv)
                            self.send_header("Content-Length", str(len(content)))
                            self.end_headers()
                            if method != "HEAD":
                                self.wfile.write(content)
                            break
                    except (http.client.RemoteDisconnected, ConnectionResetError):
                        if attempt == 0:
                            time.sleep(0.1)
                            continue
                        raise
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for hk, hv in e.headers.items():
                if hk.lower() not in ["transfer-encoding", "content-length"]:
                    self.send_header(hk, hv)
            err = e.read()
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(err)
        except Exception as e:
            self.send_error(502, f"Router Proxy Error: {e}")


def run_proxy(port: int = 8092, host: str = "0.0.0.0") -> None:
    ctx = Context.get()
    cfg = getattr(ctx, "CONFIG", CONFIG)
    RouterProxyHandler.target_host = cfg.get("router_ap_router_ip", "10.43.0.2")
    RouterProxyHandler.alias_ip = cfg.get("router_ap_alias_ip", "192.168.100.2")
    server = HTTPServer((host, port), RouterProxyHandler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8092
    run_proxy(p)

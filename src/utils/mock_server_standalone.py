#!/usr/bin/env python3
"""Embedded mock server for standalone operation"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        responses = {
            "/api/health": {"status": "healthy", "mode": "standalone"},
            "/api/devices": {"devices": [{"id": "1", "name": "Mock-Device"}]},
            "/api/policies": {"policies": []},
        }

        response = responses.get(self.path, {"error": "Not found"})
        self.send_response(200 if self.path in responses else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        self.do_GET()

    def log_message(self, format, *args):
        pass  # Suppress logs


def run_mock_server(port=6666):
    server = HTTPServer(("localhost", port), MockHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f"Mock server running on port {port}")


if __name__ == "__main__":
    run_mock_server()
    import time

    while True:
        time.sleep(1)

#!/usr/bin/env python3
"""
Simple HTTP server for debugging container issues
"""

import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = int(os.getenv('WEB_APP_PORT', 7777))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "server": "simple-python-server",
                "port": PORT,
                "container": True,
                "message": "Container is working!"
            }
            
            self.wfile.write(json.dumps(health_data, indent=2).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Fortinet Simple Server</title></head>
            <body>
                <h1>🎉 Container is Working!</h1>
                <p>Port: {PORT}</p>
                <p>Time: {datetime.now()}</p>
                <p><a href="/api/health">Health Check</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

if __name__ == "__main__":
    print(f"🚀 Starting simple server on port {PORT}")
    print(f"📍 Current directory: {os.getcwd()}")
    print(f"📁 Files: {os.listdir('.')}")
    
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        print(f"✅ Server running at http://0.0.0.0:{PORT}")
        print(f"🌐 Access: http://0.0.0.0:{PORT} or http://0.0.0.0:{PORT}/api/health")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
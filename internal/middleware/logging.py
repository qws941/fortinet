"""
internal.middleware.logging - Logging Middleware

Cloud native logging middleware for observability and monitoring.
"""

from flask import Flask, request, g
import time
import json
import os
import sys

# Add src to path for backward compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)


class LoggingMiddleware:
    """Logging middleware for cloud native observability"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.setup_request_logging()
    
    def setup_request_logging(self):
        """Setup request/response logging for cloud native monitoring"""
        
        @self.app.before_request
        def log_request_start():
            g.start_time = time.time()
            g.request_id = self.generate_request_id()
            
            # Log incoming request
            if os.getenv('LOG_LEVEL', 'INFO') == 'DEBUG':
                self.log_request_details()
        
        @self.app.after_request
        def log_request_end(response):
            # Calculate request duration
            duration = time.time() - g.get('start_time', time.time())
            
            # Log request completion
            log_data = {
                'request_id': g.get('request_id', ''),
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'user_agent': request.headers.get('User-Agent', ''),
                'remote_addr': request.remote_addr
            }
            
            # Add to response headers for tracing
            response.headers['X-Request-ID'] = g.get('request_id', '')
            
            # Log in JSON format for cloud native log aggregation
            if os.getenv('LOG_FORMAT', 'json') == 'json':
                print(json.dumps(log_data))
            else:
                print(f"[{log_data['request_id']}] {log_data['method']} {log_data['path']} "
                      f"{log_data['status_code']} {log_data['duration_ms']}ms")
            
            return response
    
    def generate_request_id(self) -> str:
        """Generate unique request ID for tracing"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def log_request_details(self):
        """Log detailed request information for debugging"""
        details = {
            'request_id': g.get('request_id', ''),
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'args': dict(request.args),
            'remote_addr': request.remote_addr
        }
        
        print(f"DEBUG: Request details: {json.dumps(details, indent=2)}")
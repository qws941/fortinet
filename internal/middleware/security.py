"""
internal.middleware.security - Security Middleware

Cloud native security middleware for headers, CORS, and authentication.
"""

from flask import Flask, request, jsonify
import os


class SecurityMiddleware:
    """Security middleware for cloud native deployments"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.setup_security_headers()
        self.setup_cors()
    
    def setup_security_headers(self):
        """Setup security headers for all responses"""
        
        @self.app.after_request
        def add_security_headers(response):
            # Basic security headers for cloud native environments
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Content Security Policy for cloud native
            csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            response.headers['Content-Security-Policy'] = csp
            
            return response
    
    def setup_cors(self):
        """Setup CORS for cloud native microservices"""
        
        @self.app.after_request
        def add_cors_headers(response):
            # Allow cross-origin requests in cloud native environments
            origin = request.headers.get('Origin')
            
            # In production, this should be more restrictive
            if os.getenv('APP_MODE', 'production').lower() == 'development':
                response.headers['Access-Control-Allow-Origin'] = '*'
            else:
                # In production, whitelist specific origins
                allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
                if origin in allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin
            
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Max-Age'] = '3600'
            
            return response
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key for external API access"""
        # In production, implement proper API key validation
        if not api_key:
            return False
        
        # Basic validation - in production, check against database/cache
        return len(api_key) >= 16
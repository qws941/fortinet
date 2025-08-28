"""
internal.app.server - Cloud Native Flask Application Factory

Creates and configures Flask application following cloud native best practices.
"""

import os
import sys
from flask import Flask, jsonify
from typing import Dict, Any

# Add src to path for backward compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Import existing application components
from web_app import create_app as create_legacy_app
from pkg.config.settings import Configuration
from internal.middleware.health import HealthMiddleware
from internal.middleware.security import SecurityMiddleware
from internal.middleware.logging import LoggingMiddleware


def create_app(config: Configuration = None) -> Flask:
    """
    Cloud Native Flask Application Factory
    
    Creates Flask application with cloud native middleware and configuration.
    Maintains backward compatibility with existing codebase.
    """
    
    # Create base application using existing factory
    app = create_legacy_app()
    
    # Apply cloud native configuration if provided
    if config:
        configure_app(app, config)
    
    # Add cloud native middleware
    add_cloud_native_middleware(app)
    
    # Add cloud native routes
    add_cloud_native_routes(app)
    
    return app


def configure_app(app: Flask, config: Configuration):
    """Configure Flask app with cloud native settings"""
    
    # Basic Flask configuration
    app.config['DEBUG'] = config.debug
    app.config['TESTING'] = config.app_mode.lower() == 'test'
    
    if config.secret_key:
        app.config['SECRET_KEY'] = config.secret_key
    
    # Cloud native specific configuration
    app.config['CLOUD_NATIVE'] = True
    app.config['CONFIG_OBJECT'] = config
    
    # JSON configuration for cloud native APIs
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = config.is_development()
    app.config['JSON_SORT_KEYS'] = False


def add_cloud_native_middleware(app: Flask):
    """Add cloud native middleware to Flask app"""
    
    # Security middleware (CORS, headers, etc.)
    SecurityMiddleware(app)
    
    # Health check middleware
    HealthMiddleware(app)
    
    # Logging middleware for observability
    LoggingMiddleware(app)


def add_cloud_native_routes(app: Flask):
    """Add cloud native routes for health checks and metrics"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Kubernetes health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'fortinet',
            'version': get_app_version()
        })
    
    @app.route('/ready', methods=['GET'])
    def readiness_check():
        """Kubernetes readiness check endpoint"""
        # Check if app is ready to serve traffic
        config = app.config.get('CONFIG_OBJECT')
        
        if config and config.offline_mode:
            return jsonify({'status': 'ready', 'mode': 'offline'})
        
        # Add actual readiness checks here
        return jsonify({
            'status': 'ready',
            'dependencies': {
                'redis': 'connected',  # Add actual check
                'filesystem': 'accessible'
            }
        })
    
    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Prometheus metrics endpoint"""
        # Return basic metrics in Prometheus format
        metrics_data = [
            '# HELP fortinet_requests_total Total number of requests',
            '# TYPE fortinet_requests_total counter',
            'fortinet_requests_total 0',  # Placeholder
            '# HELP fortinet_up Application up status',
            '# TYPE fortinet_up gauge',
            'fortinet_up 1'
        ]
        
        response = '\n'.join(metrics_data) + '\n'
        return response, 200, {'Content-Type': 'text/plain'}
    
    @app.route('/version', methods=['GET'])
    def version():
        """Version information endpoint"""
        return jsonify({
            'version': get_app_version(),
            'build': 'cloud-native',
            'architecture': 'cncf-compliant'
        })


def get_app_version() -> str:
    """Get application version from VERSION file"""
    try:
        version_file = os.path.join(project_root, 'VERSION')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    return 'development'
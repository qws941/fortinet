"""
internal.middleware.health - Health Check Middleware

Cloud native health checking middleware for Kubernetes probes.
"""

from flask import Flask, current_app
import os
import sys
from typing import Dict, Any

# Add src to path for backward compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)


class HealthMiddleware:
    """Health check middleware for cloud native deployments"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.setup_health_checks()
    
    def setup_health_checks(self):
        """Setup health check endpoints"""
        pass  # Health endpoints are added in server.py
    
    def check_redis_connectivity(self) -> bool:
        """Check Redis connectivity"""
        try:
            from utils.unified_cache_manager import UnifiedCacheManager
            cache = UnifiedCacheManager()
            # Try a simple operation
            cache.set("health_check", "ok", ttl=1)
            result = cache.get("health_check")
            return result == "ok"
        except Exception:
            return False
    
    def check_filesystem_access(self) -> bool:
        """Check filesystem accessibility"""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile() as tmp:
                tmp.write(b"health_check")
                tmp.flush()
            return True
        except Exception:
            return False
    
    def check_external_apis(self) -> Dict[str, bool]:
        """Check external API connectivity"""
        results = {}
        
        try:
            from api.clients.fortigate_api_client import FortiGateAPIClient
            client = FortiGateAPIClient()
            results['fortigate'] = client.test_connection()
        except Exception:
            results['fortigate'] = False
        
        try:
            from api.clients.fortimanager_api_client import FortiManagerAPIClient
            client = FortiManagerAPIClient()
            results['fortimanager'] = client.test_connection()
        except Exception:
            results['fortimanager'] = False
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        return {
            'redis': self.check_redis_connectivity(),
            'filesystem': self.check_filesystem_access(),
            'external_apis': self.check_external_apis()
        }
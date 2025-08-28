"""
API route modules

This package contains modular components for API routes,
split by functionality to maintain the 500-line limit per file.
"""

from .device_routes import device_bp
from .monitoring_routes import monitoring_bp
from .settings_routes import settings_bp
from .system_routes import system_bp

__all__ = ["system_bp", "device_bp", "settings_bp", "monitoring_bp"]

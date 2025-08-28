"""
API routes (Modularized for maintainability)

This file serves as a main router that aggregates route modules to maintain
the 500-line limit per file. Each functional area is split into separate modules.
"""

from flask import Blueprint

from utils.unified_logger import get_logger

from .api_modules import settings_bp, system_bp
from .api_modules.itsm_routes import itsm_bp
from .api_modules.logs_routes import logs_bp
from .api_modules.performance_routes import performance_bp

logger = get_logger(__name__)

# Main API blueprint that aggregates all sub-modules
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Register all sub-module blueprints
api_bp.register_blueprint(system_bp)
api_bp.register_blueprint(settings_bp)
api_bp.register_blueprint(logs_bp)
api_bp.register_blueprint(itsm_bp)
api_bp.register_blueprint(performance_bp)

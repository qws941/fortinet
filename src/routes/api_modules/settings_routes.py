"""
Settings-related API routes
"""

from flask import Blueprint, jsonify, request

from config.unified_settings import unified_settings
from utils.unified_logger import get_logger

logger = get_logger(__name__)

settings_bp = Blueprint("api_settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    """설정 조회"""
    try:
        from utils.api_utils import is_test_mode

        settings_data = unified_settings.get_all_settings()

        # Add test mode information for compatibility with tests
        response_data = {
            "success": True,
            "data": settings_data,
            "app_mode": "test" if is_test_mode() else "production",
            "is_test_mode": is_test_mode(),
        }

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        return jsonify({"success": False, "message": str(e)})


@settings_bp.route("/settings", methods=["POST"])
def update_settings():
    """설정 업데이트"""
    try:
        data = request.get_json() or {}
        result = unified_settings.update_settings(data)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return jsonify({"success": False, "message": str(e)})

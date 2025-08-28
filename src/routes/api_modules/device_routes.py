"""
Device-related API routes
"""

from flask import Blueprint, jsonify

from utils.api_utils import get_api_manager
from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

device_bp = Blueprint("api_device", __name__)


@device_bp.route("/devices", methods=["GET"])
@cached(ttl=120)
def get_devices():
    """장치 목록 조회"""
    try:
        api_manager = get_api_manager()
        fortigate_client = api_manager.get_fortigate_client()

        if not fortigate_client:
            return jsonify({"success": False, "message": "FortiGate not configured"})

        devices = fortigate_client.get_managed_devices()
        return jsonify({"success": True, "data": devices or []})

    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        return jsonify({"success": False, "message": str(e)})


@device_bp.route("/device/<device_id>", methods=["GET"])
@cached(ttl=300)
def get_device_details(device_id):
    """특정 장치 상세 정보 조회"""
    try:
        api_manager = get_api_manager()
        fortigate_client = api_manager.get_fortigate_client()

        if not fortigate_client:
            return jsonify({"success": False, "message": "FortiGate not configured"})

        device_info = fortigate_client.get_device_info(device_id)
        return jsonify({"success": True, "data": device_info or {}})

    except Exception as e:
        logger.error(f"Failed to get device {device_id}: {e}")
        return jsonify({"success": False, "message": str(e)})

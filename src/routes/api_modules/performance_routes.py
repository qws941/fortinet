"""
Performance API routes
"""

import random
import time

from flask import Blueprint, jsonify

from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

performance_bp = Blueprint("api_performance", __name__)


@performance_bp.route("/performance/history", methods=["GET"])
@cached(ttl=60)
def get_performance_history():
    """성능 히스토리 조회"""
    try:
        history = []
        for i in range(24):  # 24 hours of data
            history.append(
                {
                    "timestamp": time.time() - (i * 3600),
                    "cpu": round(random.uniform(20, 70), 1),
                    "memory": round(random.uniform(30, 80), 1),
                    "disk": round(random.uniform(40, 60), 1),
                    "network_in": round(random.uniform(100, 500), 2),
                    "network_out": round(random.uniform(80, 400), 2),
                }
            )

        return jsonify({"success": True, "data": history})
    except Exception as e:
        logger.error(f"Failed to get performance history: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

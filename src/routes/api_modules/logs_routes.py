"""
Logs API routes
"""

import random
import time

from flask import Blueprint, jsonify

from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

logs_bp = Blueprint("api_logs", __name__)


@logs_bp.route("/logs/recent", methods=["GET"])
@cached(ttl=30)
def get_recent_logs():
    """최근 로그 조회"""
    try:
        logs = []
        for i in range(20):
            logs.append(
                {
                    "id": i + 1,
                    "timestamp": time.time() - (i * 60),
                    "level": random.choice(["info", "warning", "error", "debug"]),
                    "source": random.choice(["system", "application", "security", "network"]),
                    "message": f"Log entry {i + 1}: System event occurred",
                    "details": {
                        "pid": random.randint(1000, 9999),
                        "module": random.choice(["web", "api", "database", "cache"]),
                    },
                }
            )

        return jsonify({"success": True, "data": logs, "total": len(logs)})
    except Exception as e:
        logger.error(f"Failed to get recent logs: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

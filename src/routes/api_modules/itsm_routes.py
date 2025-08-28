"""
ITSM API routes
"""

import random
import time

from flask import Blueprint, jsonify

from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

itsm_bp = Blueprint("api_itsm", __name__)


@itsm_bp.route("/itsm/tickets", methods=["GET"])
@cached(ttl=60)
def get_itsm_tickets():
    """ITSM 티켓 목록 조회"""
    try:
        tickets = []
        for i in range(10):
            tickets.append(
                {
                    "id": f"TICK-{1000 + i}",
                    "title": f"Issue #{i + 1}",
                    "status": random.choice(["open", "in_progress", "resolved", "closed"]),
                    "priority": random.choice(["low", "medium", "high", "critical"]),
                    "assignee": f"User{random.randint(1, 5)}",
                    "created_at": time.time() - (i * 3600),
                    "updated_at": time.time() - (i * 1800),
                }
            )

        return jsonify({"success": True, "data": tickets, "total": len(tickets)})
    except Exception as e:
        logger.error(f"Failed to get ITSM tickets: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@itsm_bp.route("/itsm/stats", methods=["GET"])
@cached(ttl=120)
def get_itsm_stats():
    """ITSM 통계 조회"""
    try:
        stats = {
            "total_tickets": random.randint(100, 500),
            "open_tickets": random.randint(10, 50),
            "resolved_today": random.randint(5, 20),
            "avg_resolution_time": round(random.uniform(2.5, 8.5), 1),
            "satisfaction_rate": round(random.uniform(85, 98), 1),
            "sla_compliance": round(random.uniform(90, 99), 1),
        }

        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error(f"Failed to get ITSM stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

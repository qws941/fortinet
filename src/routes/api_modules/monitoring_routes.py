"""
Monitoring-related API routes
"""

from flask import Blueprint, jsonify

from utils.api_utils import get_api_manager
from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

monitoring_bp = Blueprint("api_monitoring", __name__)


@monitoring_bp.route("/monitoring", methods=["GET"])
@cached(ttl=60)
def get_monitoring_data():
    """모니터링 데이터 조회"""
    try:
        api_manager = get_api_manager()
        fortigate_client = api_manager.get_fortigate_client()

        if not fortigate_client:
            return jsonify({"success": False, "message": "FortiGate not configured"})

        monitoring_data = {
            "system_status": fortigate_client.get_system_status() or {},
            "interface_stats": fortigate_client.get_interface_stats() or [],
            "session_count": fortigate_client.get_session_count() or 0,
        }

        return jsonify({"success": True, "data": monitoring_data})

    except Exception as e:
        logger.error(f"Failed to get monitoring data: {e}")
        return jsonify({"success": False, "message": str(e)})


@monitoring_bp.route("/dashboard", methods=["GET"])
@cached(ttl=120)
def get_dashboard_data():
    """대시보드 데이터 조회"""
    try:
        api_manager = get_api_manager()
        fortigate_client = api_manager.get_fortigate_client()

        if not fortigate_client:
            return jsonify({"success": False, "message": "FortiGate not configured"})

        dashboard_data = {
            "system_info": fortigate_client.get_system_info() or {},
            "policy_count": len(fortigate_client.get_firewall_policies() or []),
            "device_status": "connected",
        }

        return jsonify({"success": True, "data": dashboard_data})

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        return jsonify({"success": False, "message": str(e)})


@monitoring_bp.route("/monitoring/metrics", methods=["GET"])
@cached(ttl=30)
def get_monitoring_metrics():
    """모니터링 메트릭 조회"""
    try:
        import random
        import time

        metrics = {
            "cpu_usage": round(random.uniform(20, 60), 1),
            "memory_usage": round(random.uniform(30, 70), 1),
            "disk_usage": round(random.uniform(40, 80), 1),
            "network_in": round(random.uniform(100, 500), 2),
            "network_out": round(random.uniform(80, 400), 2),
            "active_connections": random.randint(50, 200),
            "timestamp": time.time(),
        }
        return jsonify({"success": True, "data": metrics})
    except Exception as e:
        logger.error(f"Failed to get monitoring metrics: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@monitoring_bp.route("/monitoring/alerts", methods=["GET"])
@cached(ttl=60)
def get_monitoring_alerts():
    """모니터링 알림 조회"""
    try:
        import random
        import time

        alerts = [
            {
                "id": i,
                "level": random.choice(["info", "warning", "error", "critical"]),
                "message": f"Alert {i}: System event detected",
                "timestamp": time.time() - random.randint(0, 3600),
                "source": random.choice(["system", "network", "security", "application"]),
            }
            for i in range(1, random.randint(5, 15))
        ]
        return jsonify({"success": True, "data": alerts})
    except Exception as e:
        logger.error(f"Failed to get monitoring alerts: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

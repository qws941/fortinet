#!/usr/bin/env python3
"""
WebSocket routes for real-time updates
Enhanced implementation for live dashboard and monitoring
"""

from datetime import datetime
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from monitoring.realtime_dashboard import EnhancedMonitoringDashboard
from utils.unified_logger import get_logger

logger = get_logger(__name__)

# Create blueprint for WebSocket routes
websocket_bp = Blueprint("websocket", __name__, url_prefix="/ws")

# Initialize monitoring dashboard
dashboard = EnhancedMonitoringDashboard()
dashboard.start()

# SocketIO instance (will be initialized by app)
socketio: Optional[SocketIO] = None


def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    global socketio

    # Configure SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", logger=True, engineio_logger=False)

    # Register event handlers
    register_socketio_events()

    logger.info("WebSocket support initialized")
    return socketio


def register_socketio_events():
    """Register SocketIO event handlers"""

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection"""
        client_id = request.sid
        logger.info(f"Client connected: {client_id}")

        # Send initial dashboard data
        initial_data = dashboard.get_dashboard_data()
        emit("dashboard_init", initial_data)

        # Join default room
        join_room("monitoring")
        emit("connection_status", {"status": "connected", "client_id": client_id})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection"""
        client_id = request.sid
        logger.info(f"Client disconnected: {client_id}")
        leave_room("monitoring")

    @socketio.on("subscribe")
    def handle_subscribe(data):
        """Handle metric subscription"""
        metrics = data.get("metrics", [])
        interval = data.get("interval", 1000)
        client_id = request.sid

        logger.info(f"Client {client_id} subscribed to metrics: {metrics}")

        # Join metric-specific rooms
        for metric in metrics:
            join_room(f"metric_{metric}")

        emit("subscription_confirmed", {"metrics": metrics, "interval": interval})

    @socketio.on("unsubscribe")
    def handle_unsubscribe(data):
        """Handle metric unsubscription"""
        metrics = data.get("metrics", [])
        client_id = request.sid

        logger.info(f"Client {client_id} unsubscribed from metrics: {metrics}")

        # Leave metric-specific rooms
        for metric in metrics:
            leave_room(f"metric_{metric}")

        emit("unsubscription_confirmed", {"metrics": metrics})

    @socketio.on("get_metrics")
    def handle_get_metrics(data):
        """Handle metrics request"""
        metric_type = data.get("type", "all")
        limit = data.get("limit", 50)

        if metric_type == "all":
            metrics_data = dashboard.get_dashboard_data()
        else:
            metrics_data = {
                "type": metric_type,
                "data": dashboard.metrics_collector.get_historical_metrics(metric_type, limit),
                "timestamp": datetime.now().isoformat(),
            }

        emit("metrics_response", metrics_data)

    @socketio.on("get_alerts")
    def handle_get_alerts(data):
        """Handle alerts request"""
        limit = data.get("limit", 10)
        severity = data.get("severity", "all")

        alerts = dashboard.metrics_collector.get_alerts(limit)

        # Filter by severity if specified
        if severity != "all":
            alerts = [a for a in alerts if a.get("type") == severity]

        emit("alerts_response", {"alerts": alerts, "timestamp": datetime.now().isoformat()})

    @socketio.on("get_health")
    def handle_get_health():
        """Handle health status request"""
        health_status = dashboard.get_health_status()
        emit("health_response", health_status)

    @socketio.on("command")
    def handle_command(data):
        """Handle dashboard commands"""
        command = data.get("command")
        params = data.get("params", {})

        response = execute_dashboard_command(command, params)
        emit("command_response", response)


def execute_dashboard_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute dashboard command"""
    try:
        if command == "start_collection":
            dashboard.metrics_collector.start_collection()
            return {"success": True, "message": "Metrics collection started"}

        elif command == "stop_collection":
            dashboard.metrics_collector.stop_collection()
            return {"success": True, "message": "Metrics collection stopped"}

        elif command == "set_interval":
            interval = params.get("interval", 1)
            dashboard.metrics_collector.collection_interval = interval
            return {"success": True, "message": f"Collection interval set to {interval}s"}

        elif command == "clear_alerts":
            dashboard.metrics_collector.alerts.clear()
            return {"success": True, "message": "Alerts cleared"}

        elif command == "get_config":
            return {"success": True, "config": dashboard.dashboard_config}

        elif command == "update_config":
            for key, value in params.items():
                if key in dashboard.dashboard_config:
                    dashboard.dashboard_config[key] = value
            return {"success": True, "message": "Configuration updated"}

        else:
            return {"success": False, "message": f"Unknown command: {command}"}

    except Exception as e:
        logger.error(f"Error executing command {command}: {e}")
        return {"success": False, "message": str(e)}


def broadcast_metrics_update():
    """Broadcast metrics update to all connected clients"""
    if socketio:
        metrics_data = dashboard.get_dashboard_data()
        socketio.emit("metrics_update", metrics_data, room="monitoring")


def broadcast_alert(alert: Dict[str, Any]):
    """Broadcast alert to all connected clients"""
    if socketio:
        socketio.emit("alert", alert, room="monitoring")


# REST API endpoints for WebSocket status
@websocket_bp.route("/status", methods=["GET"])
def get_websocket_status():
    """Get WebSocket service status"""
    status = {
        "enabled": socketio is not None,
        "dashboard_active": dashboard.metrics_collector.is_collecting,
        "health": dashboard.get_health_status(),
        "timestamp": datetime.now().isoformat(),
    }
    return jsonify(status)


@websocket_bp.route("/metrics", methods=["GET"])
def get_metrics_api():
    """Get current metrics via REST API"""
    metric_type = request.args.get("type", "all")
    limit = int(request.args.get("limit", 50))

    if metric_type == "all":
        data = dashboard.get_dashboard_data()
    else:
        data = {
            "type": metric_type,
            "data": dashboard.metrics_collector.get_historical_metrics(metric_type, limit),
            "timestamp": datetime.now().isoformat(),
        }

    return jsonify(data)


@websocket_bp.route("/alerts", methods=["GET"])
def get_alerts_api():
    """Get alerts via REST API"""
    limit = int(request.args.get("limit", 10))
    alerts = dashboard.metrics_collector.get_alerts(limit)

    return jsonify({"alerts": alerts, "count": len(alerts), "timestamp": datetime.now().isoformat()})


@websocket_bp.route("/health", methods=["GET"])
def get_health_api():
    """Get health status via REST API"""
    health = dashboard.get_health_status()
    return jsonify(health)

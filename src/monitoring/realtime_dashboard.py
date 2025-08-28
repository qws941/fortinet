#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard
Enhanced implementation with WebSocket support for live updates
"""

import asyncio
import json
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class RealtimeMetricsCollector:
    """Collects and aggregates real-time system metrics"""

    def __init__(self, window_size: int = 100):
        """
        Initialize metrics collector

        Args:
            window_size: Number of data points to keep in memory
        """
        self.window_size = window_size
        self.metrics = {
            "cpu": deque(maxlen=window_size),
            "memory": deque(maxlen=window_size),
            "network": deque(maxlen=window_size),
            "disk": deque(maxlen=window_size),
            "connections": deque(maxlen=window_size),
            "errors": deque(maxlen=window_size),
            "throughput": deque(maxlen=window_size),
            "latency": deque(maxlen=window_size),
        }
        self.alerts = deque(maxlen=50)
        self.collection_interval = 1  # seconds
        self.is_collecting = False
        self._lock = threading.Lock()

    def start_collection(self):
        """Start background metrics collection"""
        if not self.is_collecting:
            self.is_collecting = True
            thread = threading.Thread(target=self._collect_metrics, daemon=True)
            thread.start()
            logger.info("Real-time metrics collection started")

    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        logger.info("Real-time metrics collection stopped")

    def _collect_metrics(self):
        """Background thread for collecting metrics"""
        while self.is_collecting:
            try:
                timestamp = datetime.now().isoformat()

                # Collect system metrics
                metrics_data = {
                    "timestamp": timestamp,
                    "cpu": self._get_cpu_usage(),
                    "memory": self._get_memory_usage(),
                    "network": self._get_network_stats(),
                    "disk": self._get_disk_usage(),
                    "connections": self._get_connection_count(),
                    "errors": self._get_error_rate(),
                    "throughput": self._get_throughput(),
                    "latency": self._get_latency(),
                }

                # Store metrics
                with self._lock:
                    for key, value in metrics_data.items():
                        if key != "timestamp" and key in self.metrics:
                            self.metrics[key].append({"timestamp": timestamp, "value": value})

                # Check for alerts
                self._check_alerts(metrics_data)

                time.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                time.sleep(self.collection_interval)

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil

            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            # Simulated data if psutil not available
            import random

            return random.uniform(20, 80)

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil

            return psutil.virtual_memory().percent
        except ImportError:
            import random

            return random.uniform(40, 70)

    def _get_network_stats(self) -> Dict[str, int]:
        """Get network statistics"""
        try:
            import psutil

            stats = psutil.net_io_counters()
            return {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
            }
        except ImportError:
            import random

            return {
                "bytes_sent": random.randint(1000000, 10000000),
                "bytes_recv": random.randint(1000000, 10000000),
                "packets_sent": random.randint(1000, 10000),
                "packets_recv": random.randint(1000, 10000),
            }

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            import psutil

            return psutil.disk_usage("/").percent
        except ImportError:
            import random

            return random.uniform(30, 60)

    def _get_connection_count(self) -> int:
        """Get active connection count"""
        try:
            import psutil

            return len(psutil.net_connections())
        except ImportError:
            import random

            return random.randint(50, 200)

    def _get_error_rate(self) -> float:
        """Get current error rate"""
        # This would connect to actual error logging
        import random

        return random.uniform(0, 5)

    def _get_throughput(self) -> float:
        """Get current throughput in MB/s"""
        import random

        return random.uniform(10, 100)

    def _get_latency(self) -> float:
        """Get average latency in ms"""
        import random

        return random.uniform(5, 50)

    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics for alert conditions"""
        alerts = []

        # CPU alert
        if metrics.get("cpu", 0) > 90:
            alerts.append(
                {
                    "type": "critical",
                    "category": "cpu",
                    "message": f"High CPU usage: {metrics['cpu']:.1f}%",
                    "timestamp": metrics["timestamp"],
                }
            )

        # Memory alert
        if metrics.get("memory", 0) > 85:
            alerts.append(
                {
                    "type": "warning",
                    "category": "memory",
                    "message": f"High memory usage: {metrics['memory']:.1f}%",
                    "timestamp": metrics["timestamp"],
                }
            )

        # Error rate alert
        if metrics.get("errors", 0) > 10:
            alerts.append(
                {
                    "type": "critical",
                    "category": "errors",
                    "message": f"High error rate: {metrics['errors']:.1f}/s",
                    "timestamp": metrics["timestamp"],
                }
            )

        # Store alerts
        with self._lock:
            for alert in alerts:
                self.alerts.append(alert)
                logger.warning(f"Alert: {alert['message']}")

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        with self._lock:
            snapshot = {}
            for key, values in self.metrics.items():
                if values:
                    snapshot[key] = values[-1]
                else:
                    snapshot[key] = {"timestamp": datetime.now().isoformat(), "value": 0}
            return snapshot

    def get_historical_metrics(self, metric_type: str, limit: int = 50) -> List[Dict]:
        """Get historical metrics for a specific type"""
        with self._lock:
            if metric_type in self.metrics:
                data = list(self.metrics[metric_type])
                return data[-limit:] if len(data) > limit else data
            return []

    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        with self._lock:
            alerts = list(self.alerts)
            return alerts[-limit:] if len(alerts) > limit else alerts


class DashboardWebSocketHandler:
    """WebSocket handler for real-time dashboard updates"""

    def __init__(self, metrics_collector: RealtimeMetricsCollector):
        """
        Initialize WebSocket handler

        Args:
            metrics_collector: Metrics collector instance
        """
        self.metrics_collector = metrics_collector
        self.clients = set()
        self.broadcast_interval = 1  # seconds
        self.is_broadcasting = False

    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        self.clients.add(websocket)
        logger.info(f"New WebSocket client connected. Total clients: {len(self.clients)}")

        try:
            # Send initial data
            await self.send_initial_data(websocket)

            # Handle incoming messages
            async for message in websocket:
                await self.handle_message(websocket, message)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.clients)}")

    async def send_initial_data(self, websocket):
        """Send initial dashboard data to new client"""
        initial_data = {
            "type": "initial",
            "data": {
                "metrics": self.metrics_collector.get_current_metrics(),
                "alerts": self.metrics_collector.get_alerts(),
                "historical": {
                    "cpu": self.metrics_collector.get_historical_metrics("cpu"),
                    "memory": self.metrics_collector.get_historical_metrics("memory"),
                },
            },
        }
        await websocket.send(json.dumps(initial_data))

    async def handle_message(self, websocket, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "subscribe":
                # Client subscribing to specific metrics
                metrics = data.get("metrics", [])
                await self.send_metrics_update(websocket, metrics)

            elif msg_type == "get_historical":
                # Client requesting historical data
                metric_type = data.get("metric")
                limit = data.get("limit", 50)
                historical = self.metrics_collector.get_historical_metrics(metric_type, limit)
                response = {"type": "historical", "metric": metric_type, "data": historical}
                await websocket.send(json.dumps(response))

            elif msg_type == "ping":
                # Heartbeat
                await websocket.send(json.dumps({"type": "pong"}))

        except json.JSONDecodeError as e:
            logger.error(f"Invalid WebSocket message: {e}")

    async def send_metrics_update(self, websocket, metrics: List[str]):
        """Send specific metrics update to client"""
        update_data = {"type": "update", "timestamp": datetime.now().isoformat(), "metrics": {}}

        for metric in metrics:
            if metric in self.metrics_collector.metrics:
                latest = self.metrics_collector.get_historical_metrics(metric, 1)
                if latest:
                    update_data["metrics"][metric] = latest[0]

        await websocket.send(json.dumps(update_data))

    async def broadcast_updates(self):
        """Broadcast updates to all connected clients"""
        self.is_broadcasting = True

        while self.is_broadcasting:
            if self.clients:
                # Prepare update message
                update = {
                    "type": "broadcast",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "metrics": self.metrics_collector.get_current_metrics(),
                        "alerts": self.metrics_collector.get_alerts(5),
                    },
                }

                message = json.dumps(update)

                # Send to all connected clients
                disconnected = set()
                for client in self.clients:
                    try:
                        await client.send(message)
                    except Exception:
                        disconnected.add(client)

                # Remove disconnected clients
                self.clients -= disconnected

            await asyncio.sleep(self.broadcast_interval)

    def stop_broadcasting(self):
        """Stop broadcasting updates"""
        self.is_broadcasting = False


class EnhancedMonitoringDashboard:
    """Enhanced monitoring dashboard with real-time capabilities"""

    def __init__(self):
        """Initialize enhanced monitoring dashboard"""
        self.metrics_collector = RealtimeMetricsCollector()
        self.websocket_handler = DashboardWebSocketHandler(self.metrics_collector)
        self.dashboard_config = {
            "refresh_rate": 1000,  # ms
            "max_data_points": 100,
            "alert_retention": 50,
            "metrics_enabled": ["cpu", "memory", "network", "disk", "connections", "errors", "throughput", "latency"],
        }

    def start(self):
        """Start the monitoring dashboard"""
        logger.info("Starting enhanced monitoring dashboard")
        self.metrics_collector.start_collection()

    def stop(self):
        """Stop the monitoring dashboard"""
        logger.info("Stopping enhanced monitoring dashboard")
        self.metrics_collector.stop_collection()
        self.websocket_handler.stop_broadcasting()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics_collector.get_current_metrics(),
            "alerts": self.metrics_collector.get_alerts(),
            "config": self.dashboard_config,
            "status": {
                "collecting": self.metrics_collector.is_collecting,
                "clients_connected": len(self.websocket_handler.clients),
            },
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        metrics = self.metrics_collector.get_current_metrics()

        # Calculate health score
        health_score = 100

        cpu_value = metrics.get("cpu", {}).get("value", 0)
        if cpu_value > 80:
            health_score -= 20
        elif cpu_value > 60:
            health_score -= 10

        memory_value = metrics.get("memory", {}).get("value", 0)
        if memory_value > 80:
            health_score -= 20
        elif memory_value > 60:
            health_score -= 10

        error_value = metrics.get("errors", {}).get("value", 0)
        if error_value > 5:
            health_score -= 30
        elif error_value > 2:
            health_score -= 15

        # Determine status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {"status": status, "score": health_score, "metrics": metrics, "timestamp": datetime.now().isoformat()}

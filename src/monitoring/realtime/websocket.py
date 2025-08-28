#!/usr/bin/env python3
"""
Real-time WebSocket handlers for FortiGate Nextrade
Provides real-time monitoring and data streaming via WebSocket
"""

import json
import threading
import time

from flask import request
from flask_socketio import emit, join_room, leave_room

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class RealtimeMonitoringHandler:
    """실시간 모니터링 WebSocket 핸들러"""

    def __init__(self, socketio, redis_cache=None):
        self.socketio = socketio
        self.redis_cache = redis_cache
        self.monitoring_clients = {}  # {room_id: {clients: set(), monitor_thread: thread}}
        self.device_monitors = {}  # {device_id: api_client}

    def register_handlers(self):
        """WebSocket 이벤트 핸들러 등록"""

        @self.socketio.on("join_monitoring")
        def handle_join_monitoring(data):
            """모니터링 룸 참가"""
            room = data.get("room", "default")
            device_id = data.get("device_id")

            join_room(room)

            # 룸 초기화
            if room not in self.monitoring_clients:
                self.monitoring_clients[room] = {
                    "clients": set(),
                    "monitor_thread": None,
                    "device_id": device_id,
                }

            self.monitoring_clients[room]["clients"].add(request.sid)

            # 모니터링 스레드 시작
            if not self.monitoring_clients[room]["monitor_thread"]:
                thread = threading.Thread(
                    target=self._monitoring_loop,
                    args=(room, device_id),
                    daemon=True,
                )
                thread.start()
                self.monitoring_clients[room]["monitor_thread"] = thread

            emit(
                "monitoring_joined",
                {
                    "room": room,
                    "device_id": device_id,
                    "message": "실시간 모니터링이 시작되었습니다.",
                },
            )

            logger.info(f"Client {request.sid} joined monitoring room {room}")

        @self.socketio.on("leave_monitoring")
        def handle_leave_monitoring(data):
            """모니터링 룸 나가기"""
            room = data.get("room", "default")

            leave_room(room)

            if room in self.monitoring_clients:
                self.monitoring_clients[room]["clients"].discard(request.sid)

                # 클라이언트가 없으면 모니터링 중지
                if not self.monitoring_clients[room]["clients"]:
                    del self.monitoring_clients[room]

            emit(
                "monitoring_left",
                {"room": room, "message": "실시간 모니터링이 중지되었습니다."},
            )

            logger.info(f"Client {request.sid} left monitoring room {room}")

        @self.socketio.on("request_device_status")
        def handle_device_status(data):
            """특정 장치 상태 요청"""
            device_id = data.get("device_id")

            if device_id in self.device_monitors:
                monitor = self.device_monitors[device_id]
                try:
                    # 장치 상태 가져오기
                    status = monitor.get_system_info()
                    performance = monitor.get_monitoring_data()

                    emit(
                        "device_status_update",
                        {
                            "device_id": device_id,
                            "status": status,
                            "performance": performance["performance"],
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    logger.error(f"Error getting device status: {str(e)}")
                    emit(
                        "device_status_error",
                        {"device_id": device_id, "error": str(e)},
                    )
            else:
                emit(
                    "device_status_error",
                    {"device_id": device_id, "error": "장치가 연결되지 않았습니다."},
                )

        @self.socketio.on("request_traffic_stats")
        def handle_traffic_stats(data):
            """트래픽 통계 요청"""
            device_id = data.get("device_id")
            interface = data.get("interface")
            period = data.get("period", "1hour")

            if device_id in self.device_monitors:
                monitor = self.device_monitors[device_id]
                try:
                    # 트래픽 통계 가져오기
                    stats = monitor.get_traffic_statistics(interface, period)

                    emit(
                        "traffic_stats_update",
                        {
                            "device_id": device_id,
                            "interface": interface,
                            "stats": stats,
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    logger.error(f"Error getting traffic stats: {str(e)}")
                    emit(
                        "traffic_stats_error",
                        {"device_id": device_id, "error": str(e)},
                    )

        @self.socketio.on("request_security_events")
        def handle_security_events(data):
            """보안 이벤트 요청"""
            device_id = data.get("device_id")
            limit = data.get("limit", 100)

            if device_id in self.device_monitors:
                monitor = self.device_monitors[device_id]
                try:
                    # 보안 이벤트 가져오기
                    events = monitor.get_security_events(limit=limit)

                    emit(
                        "security_events_update",
                        {
                            "device_id": device_id,
                            "events": events,
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    logger.error(f"Error getting security events: {str(e)}")
                    emit(
                        "security_events_error",
                        {"device_id": device_id, "error": str(e)},
                    )

    def _monitoring_loop(self, room, device_id):
        """모니터링 루프"""
        logger.info(f"Starting monitoring loop for room {room}, device {device_id}")

        # 캐시 키
        cache_key = f"monitoring:{device_id}"

        while room in self.monitoring_clients:
            try:
                # 장치 모니터 가져오기
                if device_id and device_id in self.device_monitors:
                    monitor = self.device_monitors[device_id]

                    # 캐시에서 먼저 확인
                    if self.redis_cache:
                        cached_data = self.redis_cache.get(cache_key)
                        if cached_data:
                            monitoring_data = json.loads(cached_data)
                        else:
                            # 실시간 데이터 수집
                            monitoring_data = monitor.get_monitoring_data()
                            # 캐시에 저장 (5초 TTL)
                            self.redis_cache.set(cache_key, json.dumps(monitoring_data), ttl=5)
                    else:
                        # Redis가 없으면 직접 수집
                        monitoring_data = monitor.get_monitoring_data()

                    # 데이터 브로드캐스트
                    self.socketio.emit(
                        "monitoring_update",
                        {
                            "room": room,
                            "device_id": device_id,
                            "data": monitoring_data,
                            "timestamp": time.time(),
                        },
                        room=room,
                    )

                else:
                    # 장치가 연결되지 않은 경우 더미 데이터
                    monitoring_data = self._get_dummy_monitoring_data()

                    self.socketio.emit(
                        "monitoring_update",
                        {
                            "room": room,
                            "device_id": device_id or "demo",
                            "data": monitoring_data,
                            "timestamp": time.time(),
                        },
                        room=room,
                    )

                # 5초 대기
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(10)  # 오류 시 더 긴 대기

        logger.info(f"Stopping monitoring loop for room {room}")

    def _get_dummy_monitoring_data(self):
        """더미 모니터링 데이터 생성"""
        import random

        return {
            "timestamp": time.time(),
            "device_info": {
                "hostname": "FortiGate-Demo",
                "model": "FortiGate-200E",
                "version": "7.2.4",
                "status": "connected",
            },
            "performance": {
                "cpu_usage": random.randint(20, 80),
                "memory_usage": random.randint(30, 70),
                "disk_usage": random.randint(20, 50),
                "temperature": random.randint(30, 60),
            },
            "sessions": {
                "total": random.randint(1000, 5000),
                "active": random.randint(500, 2000),
            },
            "interfaces": [
                {
                    "name": "port1",
                    "status": "up",
                    "rx_bytes": random.randint(1000000, 10000000),
                    "tx_bytes": random.randint(1000000, 10000000),
                },
                {
                    "name": "port2",
                    "status": "up",
                    "rx_bytes": random.randint(1000000, 10000000),
                    "tx_bytes": random.randint(1000000, 10000000),
                },
            ],
            "threats": [
                {
                    "id": random.randint(1000, 9999),
                    "type": random.choice(["malware", "intrusion", "botnet", "spam"]),
                    "severity": random.choice(["low", "medium", "high", "critical"]),
                    "timestamp": time.time() - random.randint(0, 3600),
                    "source_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    "status": random.choice(["blocked", "monitored", "quarantined"]),
                }
                for _ in range(random.randint(0, 5))
            ],
        }

    def add_device_monitor(self, device_id, api_client):
        """장치 모니터 추가"""
        self.device_monitors[device_id] = api_client

        # 실시간 모니터링 콜백 등록
        def monitoring_callback(data):
            # 모든 관련 룸에 데이터 브로드캐스트
            for room, info in self.monitoring_clients.items():
                if info.get("device_id") == device_id:
                    self.socketio.emit(
                        "monitoring_update",
                        {
                            "room": room,
                            "device_id": device_id,
                            "data": data,
                            "timestamp": time.time(),
                        },
                        room=room,
                    )

        # API 클라이언트에 콜백 등록
        api_client.start_realtime_monitoring(monitoring_callback)

        logger.info(f"Added device monitor for {device_id}")

    def remove_device_monitor(self, device_id):
        """장치 모니터 제거"""
        if device_id in self.device_monitors:
            monitor = self.device_monitors[device_id]
            monitor.stop_realtime_monitoring()
            del self.device_monitors[device_id]
            logger.info(f"Removed device monitor for {device_id}")

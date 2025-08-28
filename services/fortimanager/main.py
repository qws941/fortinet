#!/usr/bin/env python3
"""
FortiManager Microservice
FortiManager 연동, 정책 관리, 컴플라이언스 담당
"""

import json
import logging
import os
import sys
from datetime import datetime
from functools import wraps

import consul
import pika
import psycopg2
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 환경 변수
SERVICE_NAME = os.getenv("SERVICE_NAME", "fortimanager-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8082))
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://fortimanager:fm123@localhost:5432/fortimanager"
)
CONSUL_URL = os.getenv("CONSUL_URL", "http://localhost:8500")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://fortinet:fortinet123@localhost:5672/")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")

# PostgreSQL 연결
try:
    db_conn = psycopg2.connect(DATABASE_URL)
    db_conn.autocommit = True
    logger.info("PostgreSQL 연결 성공")

    # 테이블 생성
    with db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fortimanager_policies (
                id SERIAL PRIMARY KEY,
                policy_name VARCHAR(255) NOT NULL,
                policy_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fortimanager_devices (
                id SERIAL PRIMARY KEY,
                device_name VARCHAR(255) NOT NULL,
                device_type VARCHAR(100) NOT NULL,
                ip_address INET NOT NULL,
                status VARCHAR(50) DEFAULT 'unknown',
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        logger.info("데이터베이스 테이블 초기화 완료")

except Exception as e:
    logger.error(f"PostgreSQL 연결 실패: {e}")
    db_conn = None

# RabbitMQ 연결
try:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    # 큐 선언
    channel.queue_declare(queue="fortimanager.events", durable=True)
    channel.queue_declare(queue="policy.changes", durable=True)

    logger.info("RabbitMQ 연결 성공")
except Exception as e:
    logger.error(f"RabbitMQ 연결 실패: {e}")
    channel = None

# Consul 연결
try:
    consul_client = consul.Consul(host=CONSUL_URL.split("://")[1].split(":")[0])
    consul_client.agent.service.register(
        name=SERVICE_NAME,
        service_id=f"{SERVICE_NAME}-{SERVICE_PORT}",
        address="localhost",
        port=SERVICE_PORT,
        check=consul.Check.http(
            f"http://localhost:{SERVICE_PORT}/health", interval="10s"
        ),
    )
    logger.info("Consul 서비스 등록 성공")
except Exception as e:
    logger.error(f"Consul 연결 실패: {e}")
    consul_client = None


def require_auth(f):
    """인증 데코레이터 - Auth Service와 연동"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]
            try:
                # Auth Service에 토큰 검증 요청
                response = requests.post(
                    f"{AUTH_SERVICE_URL}/auth/verify", json={"token": token}, timeout=5
                )
                if response.status_code == 200 and response.json().get("valid"):
                    request.user = response.json()
                    return f(*args, **kwargs)
                else:
                    return jsonify({"error": "Invalid token"}), 401
            except Exception as e:
                logger.error(f"Auth verification error: {e}")
                return jsonify({"error": "Authentication service unavailable"}), 503
        return jsonify({"error": "Authentication required"}), 401

    return decorated_function


def publish_event(queue_name: str, event_data: dict):
    """이벤트 발행"""
    if channel:
        try:
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(event_data),
                properties=pika.BasicProperties(delivery_mode=2),  # 메시지 영속화
            )
            logger.info(f"Event published to {queue_name}: {event_data}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")


class FortiManagerService:
    """FortiManager 서비스 핵심 클래스"""

    def __init__(self, db_conn):
        self.db = db_conn

    def get_policies(self, limit: int = 100, offset: int = 0) -> list:
        """정책 목록 조회"""
        if not self.db:
            return []

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "SELECT id, policy_name, policy_data, created_at FROM fortimanager_policies "
                    "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                results = cursor.fetchall()

                policies = []
                for row in results:
                    policies.append(
                        {
                            "id": row[0],
                            "policy_name": row[1],
                            "policy_data": row[2],
                            "created_at": row[3].isoformat() if row[3] else None,
                        }
                    )

                return policies
        except Exception as e:
            logger.error(f"Failed to get policies: {e}")
            return []

    def create_policy(self, policy_name: str, policy_data: dict) -> dict:
        """정책 생성"""
        if not self.db:
            raise Exception("Database connection not available")

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO fortimanager_policies (policy_name, policy_data) VALUES (%s, %s) RETURNING id",
                    (policy_name, json.dumps(policy_data)),
                )
                policy_id = cursor.fetchone()[0]

                # 이벤트 발행
                event_data = {
                    "event_type": "policy_created",
                    "policy_id": policy_id,
                    "policy_name": policy_name,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("policy.changes", event_data)

                return {
                    "id": policy_id,
                    "policy_name": policy_name,
                    "policy_data": policy_data,
                    "created_at": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            raise

    def get_devices(self) -> list:
        """디바이스 목록 조회"""
        if not self.db:
            return []

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "SELECT id, device_name, device_type, ip_address, status, last_seen "
                    "FROM fortimanager_devices ORDER BY device_name"
                )
                results = cursor.fetchall()

                devices = []
                for row in results:
                    devices.append(
                        {
                            "id": row[0],
                            "device_name": row[1],
                            "device_type": row[2],
                            "ip_address": str(row[3]),
                            "status": row[4],
                            "last_seen": row[5].isoformat() if row[5] else None,
                        }
                    )

                return devices
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []

    def analyze_packet_path(
        self, source_ip: str, dest_ip: str, protocol: str = "tcp"
    ) -> dict:
        """패킷 경로 분석"""
        # 실제 구현에서는 FortiManager API 호출
        # 여기서는 모의 데이터 반환
        analysis_result = {
            "source_ip": source_ip,
            "destination_ip": dest_ip,
            "protocol": protocol,
            "path": [
                {
                    "hop": 1,
                    "device": "FortiGate-1",
                    "interface": "port1",
                    "action": "allow",
                    "rule_id": 1001,
                },
                {
                    "hop": 2,
                    "device": "FortiGate-2",
                    "interface": "port2",
                    "action": "allow",
                    "rule_id": 2001,
                },
            ],
            "analysis_time": datetime.utcnow().isoformat(),
            "status": "completed",
        }

        # 분석 완료 이벤트 발행
        event_data = {
            "event_type": "packet_analysis_completed",
            "analysis_id": f"analysis_{datetime.utcnow().timestamp()}",
            "source_ip": source_ip,
            "destination_ip": dest_ip,
            "timestamp": datetime.utcnow().isoformat(),
        }
        publish_event("fortimanager.events", event_data)

        return analysis_result


# FortiManager 서비스 인스턴스 생성
fm_service = FortiManagerService(db_conn)


@app.route("/health")
def health():
    """헬스체크 엔드포인트"""
    status = {
        "service": SERVICE_NAME,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_conn is not None,
        "rabbitmq": channel is not None,
        "consul": consul_client is not None,
    }
    return jsonify(status)


@app.route("/fortimanager/policies", methods=["GET"])
@require_auth
def get_policies():
    """정책 목록 조회"""
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        policies = fm_service.get_policies(limit, offset)

        return jsonify({"success": True, "policies": policies, "count": len(policies)})

    except Exception as e:
        logger.error(f"Get policies error: {e}")
        return jsonify({"error": "Failed to get policies"}), 500


@app.route("/fortimanager/policies", methods=["POST"])
@require_auth
def create_policy():
    """정책 생성"""
    try:
        data = request.get_json()
        policy_name = data.get("policy_name")
        policy_data = data.get("policy_data", {})

        if not policy_name:
            return jsonify({"error": "policy_name required"}), 400

        policy = fm_service.create_policy(policy_name, policy_data)

        return jsonify({"success": True, "policy": policy}), 201

    except Exception as e:
        logger.error(f"Create policy error: {e}")
        return jsonify({"error": "Failed to create policy"}), 500


@app.route("/fortimanager/devices", methods=["GET"])
@require_auth
def get_devices():
    """디바이스 목록 조회"""
    try:
        devices = fm_service.get_devices()

        return jsonify({"success": True, "devices": devices, "count": len(devices)})

    except Exception as e:
        logger.error(f"Get devices error: {e}")
        return jsonify({"error": "Failed to get devices"}), 500


@app.route("/fortimanager/analyze-packet-path", methods=["POST"])
@require_auth
def analyze_packet_path():
    """패킷 경로 분석"""
    try:
        data = request.get_json()
        source_ip = data.get("source_ip")
        dest_ip = data.get("destination_ip")
        protocol = data.get("protocol", "tcp")

        if not source_ip or not dest_ip:
            return jsonify({"error": "source_ip and destination_ip required"}), 400

        analysis = fm_service.analyze_packet_path(source_ip, dest_ip, protocol)

        return jsonify({"success": True, "analysis": analysis})

    except Exception as e:
        logger.error(f"Packet path analysis error: {e}")
        return jsonify({"error": "Failed to analyze packet path"}), 500


@app.route("/fortimanager/status")
@require_auth
def service_status():
    """서비스 상태 확인"""
    return jsonify(
        {
            "service": SERVICE_NAME,
            "authenticated_user": request.user.get("user_id"),
            "version": "1.0.0",
            "features": [
                "policy_management",
                "device_monitoring",
                "packet_analysis",
                "compliance_checking",
            ],
        }
    )


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="127.0.0.1", port=SERVICE_PORT, debug=False)

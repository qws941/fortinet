#!/usr/bin/env python3
"""
ITSM Microservice
ITSM 티켓 처리, 정책 자동화, 승인 워크플로우 담당
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from enum import Enum
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
SERVICE_NAME = os.getenv("SERVICE_NAME", "itsm-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8083))
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://itsm:itsm123@localhost:5432/itsm"
)
CONSUL_URL = os.getenv("CONSUL_URL", "http://localhost:8500")
RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://fortinet:fortinet123@localhost:5672/")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
FORTIMANAGER_SERVICE_URL = os.getenv(
    "FORTIMANAGER_SERVICE_URL", "http://localhost:8082"
)


class ITSMTicketStatus(Enum):
    """ITSM 티켓 상태"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    CLOSED = "closed"


class ITSMTicketType(Enum):
    """ITSM 티켓 유형"""

    FIREWALL_RULE = "firewall_rule"
    ACCESS_REQUEST = "access_request"
    POLICY_CHANGE = "policy_change"
    SECURITY_EXCEPTION = "security_exception"


# PostgreSQL 연결
try:
    db_conn = psycopg2.connect(DATABASE_URL)
    db_conn.autocommit = True
    logger.info("PostgreSQL 연결 성공")

    # 테이블 생성
    with db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itsm_tickets (
                id SERIAL PRIMARY KEY,
                ticket_number VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                ticket_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'new',
                priority VARCHAR(20) DEFAULT 'medium',
                requester VARCHAR(100) NOT NULL,
                assignee VARCHAR(100),
                firewall_rules JSONB,
                approval_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itsm_approvals (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER REFERENCES itsm_tickets(id),
                approver VARCHAR(100) NOT NULL,
                approval_status VARCHAR(20) DEFAULT 'pending',
                approval_date TIMESTAMP,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itsm_deployments (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER REFERENCES itsm_tickets(id),
                deployment_status VARCHAR(50) DEFAULT 'pending',
                deployment_date TIMESTAMP,
                deployment_details JSONB,
                rollback_plan JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        logger.info("ITSM 데이터베이스 테이블 초기화 완료")

except Exception as e:
    logger.error(f"PostgreSQL 연결 실패: {e}")
    db_conn = None

# RabbitMQ 연결
try:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    # 큐 선언
    channel.queue_declare(queue="itsm.tickets", durable=True)
    channel.queue_declare(queue="itsm.approvals", durable=True)
    channel.queue_declare(queue="itsm.deployments", durable=True)

    logger.info("RabbitMQ 연결 성공")
except Exception as e:
    logger.error(f"RabbitMQ 연결 실패: {e}")
    channel = None

# Consul 연결
try:
    consul_client = consul.Consul(
        host=CONSUL_URL.split("://")[1].split(":")[0])
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
                return jsonify(
                    {"error": "Authentication service unavailable"}), 503
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
                properties=pika.BasicProperties(delivery_mode=2),
            )
            logger.info(f"Event published to {queue_name}: {event_data}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")


class ITSMService:
    """ITSM 서비스 핵심 클래스"""

    def __init__(self, db_conn):
        self.db = db_conn

    def generate_ticket_number(self) -> str:
        """티켓 번호 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"ITSM-{timestamp}"

    def create_ticket(self, ticket_data: dict, requester: str) -> dict:
        """티켓 생성"""
        if not self.db:
            raise Exception("Database connection not available")

        try:
            ticket_number = self.generate_ticket_number()

            with self.db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO itsm_tickets
                    (ticket_number, title, description, ticket_type, priority, requester, firewall_rules, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        ticket_number,
                        ticket_data.get("title"),
                        ticket_data.get("description"),
                        ticket_data.get("ticket_type", "firewall_rule"),
                        ticket_data.get("priority", "medium"),
                        requester,
                        json.dumps(ticket_data.get("firewall_rules", {})),
                        datetime.now() + timedelta(days=ticket_data.get("due_days", 7)),
                    ),
                )

                ticket_id = cursor.fetchone()[0]

                # 이벤트 발행
                event_data = {
                    "event_type": "ticket_created",
                    "ticket_id": ticket_id,
                    "ticket_number": ticket_number,
                    "ticket_type": ticket_data.get("ticket_type"),
                    "requester": requester,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("itsm.tickets", event_data)

                return {
                    "id": ticket_id,
                    "ticket_number": ticket_number,
                    "status": ITSMTicketStatus.NEW.value,
                    "created_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            raise

    def get_tickets(
        self, status: str = None, requester: str = None, limit: int = 100
    ) -> list:
        """티켓 목록 조회"""
        if not self.db:
            return []

        try:
            with self.db.cursor() as cursor:
                query = """
                    SELECT id, ticket_number, title, description, ticket_type, status,
                           priority, requester, assignee, created_at, updated_at, due_date
                    FROM itsm_tickets
                    WHERE 1=1
                """
                params = []

                if status:
                    query += " AND status = %s"
                    params.append(status)

                if requester:
                    query += " AND requester = %s"
                    params.append(requester)

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)
                results = cursor.fetchall()

                tickets = []
                for row in results:
                    tickets.append(
                        {
                            "id": row[0],
                            "ticket_number": row[1],
                            "title": row[2],
                            "description": row[3],
                            "ticket_type": row[4],
                            "status": row[5],
                            "priority": row[6],
                            "requester": row[7],
                            "assignee": row[8],
                            "created_at": row[9].isoformat() if row[9] else None,
                            "updated_at": row[10].isoformat() if row[10] else None,
                            "due_date": row[11].isoformat() if row[11] else None,
                        }
                    )

                return tickets

        except Exception as e:
            logger.error(f"Failed to get tickets: {e}")
            return []

    def update_ticket_status(
        self, ticket_id: int, new_status: str, assignee: str = None
    ) -> bool:
        """티켓 상태 업데이트"""
        if not self.db:
            return False

        try:
            with self.db.cursor() as cursor:
                if assignee:
                    cursor.execute(
                        """
                        UPDATE itsm_tickets
                        SET status = %s, assignee = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (new_status, assignee, ticket_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE itsm_tickets
                        SET status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (new_status, ticket_id),
                    )

                # 이벤트 발행
                event_data = {
                    "event_type": "ticket_status_updated",
                    "ticket_id": ticket_id,
                    "new_status": new_status,
                    "assignee": assignee,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("itsm.tickets", event_data)

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update ticket status: {e}")
            return False

    def submit_for_approval(self, ticket_id: int, approvers: list) -> bool:
        """승인 요청 제출"""
        if not self.db:
            return False

        try:
            with self.db.cursor() as cursor:
                # 티켓 상태를 승인 대기로 변경
                cursor.execute(
                    """
                    UPDATE itsm_tickets
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (ITSMTicketStatus.PENDING_APPROVAL.value, ticket_id),
                )

                # 승인자들에게 승인 요청 생성
                for approver in approvers:
                    cursor.execute(
                        """
                        INSERT INTO itsm_approvals (ticket_id, approver)
                        VALUES (%s, %s)
                    """,
                        (ticket_id, approver),
                    )

                # 이벤트 발행
                event_data = {
                    "event_type": "approval_requested",
                    "ticket_id": ticket_id,
                    "approvers": approvers,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("itsm.approvals", event_data)

                return True

        except Exception as e:
            logger.error(f"Failed to submit for approval: {e}")
            return False

    def process_approval(
        self, ticket_id: int, approver: str, approved: bool, comments: str = None
    ) -> bool:
        """승인 처리"""
        if not self.db:
            return False

        try:
            with self.db.cursor() as cursor:
                # 승인 상태 업데이트
                approval_status = "approved" if approved else "rejected"
                cursor.execute(
                    """
                    UPDATE itsm_approvals
                    SET approval_status = %s, approval_date = CURRENT_TIMESTAMP, comments = %s
                    WHERE ticket_id = %s AND approver = %s
                """,
                    (approval_status, comments, ticket_id, approver),
                )

                # 모든 승인이 완료되었는지 확인
                cursor.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN approval_status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                           SUM(CASE WHEN approval_status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
                    FROM itsm_approvals
                    WHERE ticket_id = %s
                """,
                    (ticket_id,),
                )

                result = cursor.fetchone()
                total, approved_count, rejected_count = result[0], result[1], result[2]

                # 승인 결과에 따라 티켓 상태 업데이트
                if rejected_count > 0:
                    new_status = ITSMTicketStatus.REJECTED.value
                elif approved_count == total:
                    new_status = ITSMTicketStatus.APPROVED.value
                else:
                    new_status = ITSMTicketStatus.PENDING_APPROVAL.value

                if new_status != ITSMTicketStatus.PENDING_APPROVAL.value:
                    cursor.execute(
                        """
                        UPDATE itsm_tickets
                        SET status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (new_status, ticket_id),
                    )

                # 이벤트 발행
                event_data = {
                    "event_type": "approval_processed",
                    "ticket_id": ticket_id,
                    "approver": approver,
                    "approved": approved,
                    "final_status": new_status,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("itsm.approvals", event_data)

                return True

        except Exception as e:
            logger.error(f"Failed to process approval: {e}")
            return False

    def deploy_policy(self, ticket_id: int) -> dict:
        """정책 배포"""
        if not self.db:
            raise Exception("Database connection not available")

        try:
            with self.db.cursor() as cursor:
                # 티켓 정보 조회
                cursor.execute(
                    """
                    SELECT firewall_rules, title FROM itsm_tickets
                    WHERE id = %s AND status = %s
                """,
                    (ticket_id, ITSMTicketStatus.APPROVED.value),
                )

                result = cursor.fetchone()
                if not result:
                    raise Exception("Ticket not found or not approved")

                firewall_rules, title = result

                # FortiManager 서비스에 정책 배포 요청
                try:
                    response = requests.post(
                        f"{FORTIMANAGER_SERVICE_URL}/fortimanager/policies",
                        json={
                            "policy_name": f"ITSM-{ticket_id}-{title}",
                            "policy_data": firewall_rules,
                        },
                        headers={
                            "Authorization": request.headers.get("Authorization")},
                        timeout=30,
                    )

                    if response.status_code in [200, 201]:
                        deployment_status = "success"
                        deployment_details = response.json()
                    else:
                        deployment_status = "failed"
                        deployment_details = {
                            "error": f"FortiManager API error: {response.status_code}"
                        }

                except Exception as e:
                    deployment_status = "failed"
                    deployment_details = {"error": str(e)}

                # 배포 결과 저장
                cursor.execute(
                    """
                    INSERT INTO itsm_deployments (ticket_id, deployment_status, deployment_date, deployment_details)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                    RETURNING id
                """,
                    (ticket_id, deployment_status, json.dumps(deployment_details)),
                )

                deployment_id = cursor.fetchone()[0]

                # 티켓 상태 업데이트
                new_ticket_status = (
                    ITSMTicketStatus.DEPLOYED.value
                    if deployment_status == "success"
                    else ITSMTicketStatus.APPROVED.value
                )
                cursor.execute(
                    """
                    UPDATE itsm_tickets
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (new_ticket_status, ticket_id),
                )

                # 이벤트 발행
                event_data = {
                    "event_type": "policy_deployed",
                    "ticket_id": ticket_id,
                    "deployment_id": deployment_id,
                    "deployment_status": deployment_status,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                publish_event("itsm.deployments", event_data)

                return {
                    "deployment_id": deployment_id,
                    "status": deployment_status,
                    "details": deployment_details,
                    "deployed_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to deploy policy: {e}")
            raise


# ITSM 서비스 인스턴스 생성
itsm_service = ITSMService(db_conn)


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


@app.route("/itsm/tickets", methods=["GET"])
@require_auth
def get_tickets():
    """티켓 목록 조회"""
    try:
        status = request.args.get("status")
        requester = request.args.get("requester")
        limit = int(request.args.get("limit", 100))

        tickets = itsm_service.get_tickets(status, requester, limit)

        return jsonify(
            {"success": True, "tickets": tickets, "count": len(tickets)})

    except Exception as e:
        logger.error(f"Get tickets error: {e}")
        return jsonify({"error": "Failed to get tickets"}), 500


@app.route("/itsm/tickets", methods=["POST"])
@require_auth
def create_ticket():
    """티켓 생성"""
    try:
        ticket_data = request.get_json()
        requester = request.user.get("user_id")

        required_fields = ["title", "ticket_type"]
        missing_fields = [
            field for field in required_fields if not ticket_data.get(field)
        ]

        if missing_fields:
            return (
                jsonify(
                    {
                        "error": f'Missing required fields: {", ".join(missing_fields)}'}
                ),
                400,
            )

        ticket = itsm_service.create_ticket(ticket_data, requester)

        return jsonify({"success": True, "ticket": ticket}), 201

    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        return jsonify({"error": "Failed to create ticket"}), 500


@app.route("/itsm/tickets/<int:ticket_id>/status", methods=["PUT"])
@require_auth
def update_ticket_status(ticket_id):
    """티켓 상태 업데이트"""
    try:
        data = request.get_json()
        new_status = data.get("status")
        assignee = data.get("assignee")

        if not new_status:
            return jsonify({"error": "Status is required"}), 400

        success = itsm_service.update_ticket_status(
            ticket_id, new_status, assignee)

        if success:
            return jsonify(
                {"success": True, "message": "Ticket status updated successfully"}
            )
        else:
            return jsonify({"error": "Failed to update ticket status"}), 500

    except Exception as e:
        logger.error(f"Update ticket status error: {e}")
        return jsonify({"error": "Failed to update ticket status"}), 500


@app.route("/itsm/tickets/<int:ticket_id>/approve", methods=["POST"])
@require_auth
def submit_for_approval(ticket_id):
    """승인 요청 제출"""
    try:
        data = request.get_json()
        approvers = data.get("approvers", [])

        if not approvers:
            return jsonify({"error": "At least one approver is required"}), 400

        success = itsm_service.submit_for_approval(ticket_id, approvers)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Ticket submitted for approval",
                    "approvers": approvers,
                }
            )
        else:
            return jsonify({"error": "Failed to submit for approval"}), 500

    except Exception as e:
        logger.error(f"Submit for approval error: {e}")
        return jsonify({"error": "Failed to submit for approval"}), 500


@app.route("/itsm/tickets/<int:ticket_id>/approval", methods=["POST"])
@require_auth
def process_approval(ticket_id):
    """승인 처리"""
    try:
        data = request.get_json()
        approved = data.get("approved", False)
        comments = data.get("comments", "")
        approver = request.user.get("user_id")

        success = itsm_service.process_approval(
            ticket_id, approver, approved, comments)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Approval processed successfully",
                    "approved": approved,
                }
            )
        else:
            return jsonify({"error": "Failed to process approval"}), 500

    except Exception as e:
        logger.error(f"Process approval error: {e}")
        return jsonify({"error": "Failed to process approval"}), 500


@app.route("/itsm/tickets/<int:ticket_id>/deploy", methods=["POST"])
@require_auth
def deploy_policy(ticket_id):
    """정책 배포"""
    try:
        deployment_result = itsm_service.deploy_policy(ticket_id)

        return jsonify({"success": True, "deployment": deployment_result})

    except Exception as e:
        logger.error(f"Deploy policy error: {e}")
        return jsonify({"error": "Failed to deploy policy"}), 500


@app.route("/itsm/status")
@require_auth
def service_status():
    """서비스 상태 확인"""
    return jsonify(
        {
            "service": SERVICE_NAME,
            "authenticated_user": request.user.get("user_id"),
            "version": "1.0.0",
            "features": [
                "ticket_management",
                "approval_workflow",
                "policy_deployment",
                "automation_integration",
            ],
        }
    )


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="127.0.0.1", port=SERVICE_PORT, debug=False)

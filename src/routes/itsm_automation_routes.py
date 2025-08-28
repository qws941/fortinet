#!/usr/bin/env python3

"""
ITSM 자동화 API 라우트
외부 ITSM 연동 및 자동 정책 배포 관련 API 엔드포인트
"""

import asyncio
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request

from itsm.automation_service import get_automation_service
from utils.security import rate_limit, validate_request
from utils.unified_logger import get_logger

logger = get_logger(__name__)

itsm_automation_bp = Blueprint("itsm_automation", __name__, url_prefix="/api/itsm/automation")


def async_route(f):
    """비동기 라우트 데코레이터"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()

    return wrapper


@itsm_automation_bp.route("/status", methods=["GET"])
@rate_limit(max_requests=30, window=60)
def get_automation_status():
    """자동화 서비스 상태 조회"""
    try:
        service = get_automation_service()
        status = service.get_service_status()

        return jsonify({"status": "success", "data": status})

    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/start", methods=["POST"])
@rate_limit(max_requests=5, window=300)  # 5분에 5번만 허용
@async_route
async def start_automation_service():
    """자동화 서비스 시작"""
    try:
        service = get_automation_service()

        if service.is_running:
            return jsonify({"status": "warning", "message": "Service is already running"})

        # 비동기로 서비스 시작 (백그라운드에서 실행)
        asyncio.create_task(service.start_service())

        return jsonify({"status": "success", "message": "Automation service started"})

    except Exception as e:
        logger.error(f"Error starting automation service: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/stop", methods=["POST"])
@rate_limit(max_requests=10, window=60)
@async_route
async def stop_automation_service():
    """자동화 서비스 중지"""
    try:
        service = get_automation_service()

        if not service.is_running:
            return jsonify({"status": "warning", "message": "Service is not running"})

        await service.stop_service()

        return jsonify({"status": "success", "message": "Automation service stopped"})

    except Exception as e:
        logger.error(f"Error stopping automation service: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/manual-process", methods=["POST"])
@rate_limit(max_requests=10, window=300)  # 5분에 10번만 허용
@async_route
async def manual_process():
    """수동 처리 (즉시 실행)"""
    try:
        data = request.get_json() or {}
        since_hours = data.get("since_hours", 1)

        # 최대 24시간으로 제한
        since_hours = min(since_hours, 24)

        service = get_automation_service()
        reports = await service.manual_process(since_hours)

        # 결과 요약
        successful = len([r for r in reports if r.result.value == "success"])
        failed = len(reports) - successful

        return jsonify(
            {
                "status": "success",
                "message": "Manual processing completed",
                "data": {
                    "total_processed": len(reports),
                    "successful": successful,
                    "failed": failed,
                    "since_hours": since_hours,
                    "reports": [
                        {
                            "request_id": r.request_id,
                            "result": r.result.value,
                            "affected_firewalls": r.affected_firewalls,
                            "deployment_time": r.deployment_time.isoformat(),
                            "errors": r.error_messages,
                        }
                        for r in reports
                    ],
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in manual processing: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/statistics", methods=["GET"])
@rate_limit(max_requests=60, window=60)
def get_deployment_statistics():
    """배포 통계 조회"""
    try:
        service = get_automation_service()
        stats = service.get_deployment_statistics()

        return jsonify({"status": "success", "data": stats})

    except Exception as e:
        logger.error(f"Error getting deployment statistics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/deployments/recent", methods=["GET"])
@rate_limit(max_requests=60, window=60)
def get_recent_deployments():
    """최근 배포 기록 조회"""
    try:
        limit = request.args.get("limit", 20, type=int)
        limit = min(limit, 100)  # 최대 100개로 제한

        service = get_automation_service()
        deployments = service.get_recent_deployments(limit)

        return jsonify(
            {
                "status": "success",
                "data": {
                    "deployments": deployments,
                    "count": len(deployments),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting recent deployments: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/test-connection", methods=["POST"])
@rate_limit(max_requests=10, window=300)
@async_route
async def test_itsm_connection():
    """ITSM 연결 테스트"""
    try:
        service = get_automation_service()
        result = await service.test_itsm_connection()

        if result["success"]:
            return jsonify(
                {
                    "status": "success",
                    "message": "ITSM connection test successful",
                    "data": result,
                }
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "ITSM connection test failed",
                        "data": result,
                    }
                ),
                400,
            )

    except Exception as e:
        logger.error(f"Error testing ITSM connection: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/config", methods=["GET"])
@rate_limit(max_requests=30, window=60)
def get_automation_config():
    """자동화 설정 조회 (민감한 정보 제외)"""
    try:
        service = get_automation_service()

        # 민감한 정보는 마스킹
        config_data = {
            "itsm": {
                "platform": (service.connector.config.platform.value if service.connector else None),
                "base_url": (service.connector.config.base_url if service.connector else None),
                "poll_interval": (service.connector.config.poll_interval if service.connector else None),
                "username": ("***" if service.connector and service.connector.config.username else None),
            },
            "fortimanager": {
                "enabled": service.fortimanager_client is not None,
                "host": (service.fortimanager_client.host if service.fortimanager_client else None),
            },
            "automation_engine": {
                "initialized": service.automation_engine is not None,
                "firewall_count": (len(service.automation_engine.firewall_devices) if service.automation_engine else 0),
                "zone_count": (len(service.automation_engine.network_zones) if service.automation_engine else 0),
            },
        }

        return jsonify({"status": "success", "data": config_data})

    except Exception as e:
        logger.error(f"Error getting automation config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/config", methods=["PUT"])
@rate_limit(max_requests=5, window=300)
@validate_request(["itsm"])
def update_automation_config():
    """자동화 설정 업데이트"""
    try:
        data = request.get_json()

        service = get_automation_service()
        success = service.update_configuration(data)

        if success:
            return jsonify(
                {
                    "status": "success",
                    "message": "Configuration updated successfully",
                }
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Failed to update configuration",
                    }
                ),
                400,
            )

    except Exception as e:
        logger.error(f"Error updating automation config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/firewall-devices", methods=["GET"])
@rate_limit(max_requests=60, window=60)
def get_firewall_devices():
    """방화벽 장치 목록 조회"""
    try:
        service = get_automation_service()

        if not service.automation_engine:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Automation engine not initialized",
                    }
                ),
                500,
            )

        devices = []
        for device in service.automation_engine.firewall_devices:
            devices.append(
                {
                    "id": device.id,
                    "name": device.name,
                    "host": device.host,
                    "zones": device.zones,
                    "management_ip": device.management_ip,
                    "priority": device.priority,
                    "api_connected": device.api_client is not None,
                }
            )

        return jsonify(
            {
                "status": "success",
                "data": {"devices": devices, "count": len(devices)},
            }
        )

    except Exception as e:
        logger.error(f"Error getting firewall devices: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/network-zones", methods=["GET"])
@rate_limit(max_requests=60, window=60)
def get_network_zones():
    """네트워크 존 목록 조회"""
    try:
        service = get_automation_service()

        if not service.automation_engine:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Automation engine not initialized",
                    }
                ),
                500,
            )

        zones = []
        for zone in service.automation_engine.network_zones:
            zones.append(
                {
                    "name": zone.name,
                    "cidr": zone.cidr,
                    "description": zone.description,
                    "security_level": zone.security_level,
                    "allowed_outbound": zone.allowed_outbound,
                }
            )

        return jsonify(
            {
                "status": "success",
                "data": {"zones": zones, "count": len(zones)},
            }
        )

    except Exception as e:
        logger.error(f"Error getting network zones: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_automation_bp.route("/simulate-request", methods=["POST"])
@rate_limit(max_requests=20, window=300)
@validate_request(["source_ip", "destination_ip", "port", "protocol"])
def simulate_policy_request():
    """정책 요청 시뮬레이션 (테스트용)"""
    try:
        data = request.get_json()

        service = get_automation_service()

        if not service.automation_engine:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Automation engine not initialized",
                    }
                ),
                500,
            )

        # 시뮬레이션용 요청 객체 생성
        from itsm.external_connector import FirewallPolicyRequest

        sim_request = FirewallPolicyRequest(
            ticket_id=f"SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            source_ip=data["source_ip"],
            destination_ip=data["destination_ip"],
            port=data["port"],
            protocol=data["protocol"],
            action=data.get("action", "allow"),
            description=data.get("description", "Simulation request"),
            business_justification=data.get("justification", "Testing automation"),
            requester="simulation_user",
        )

        # 분석 및 계획 수립
        plan = service.automation_engine.analyze_firewall_request(sim_request)

        # 시뮬레이션 결과 반환 (실제 배포하지 않음)
        result = {
            "request": {
                "ticket_id": sim_request.ticket_id,
                "source_ip": sim_request.source_ip,
                "destination_ip": sim_request.destination_ip,
                "port": sim_request.port,
                "protocol": sim_request.protocol,
            },
            "analysis": {
                "target_firewalls": [fw.id for fw in plan.target_firewalls],
                "deployment_order": plan.deployment_order,
                "risk_assessment": plan.risk_assessment,
                "auto_approve": plan.auto_approve,
                "estimated_rules_count": len(plan.estimated_rules),
            },
            "estimated_rules": plan.estimated_rules,
        }

        return jsonify(
            {
                "status": "success",
                "message": "Policy request simulation completed",
                "data": result,
            }
        )

    except Exception as e:
        logger.error(f"Error in policy request simulation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

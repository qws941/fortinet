#!/usr/bin/env python3
"""
고급 FortiGate API 통합 라우트
새로운 AdvancedFortiGateAPI 클라이언트를 웹 애플리케이션에 통합

제공 기능:
- 고급 방화벽 정책 관리 API 엔드포인트
- VPN 연결 관리 API 엔드포인트
- NAT 정책 관리 API 엔드포인트
- 보안 프로필 관리 API 엔드포인트
- 실시간 로그 모니터링 API 엔드포인트
- 트래픽 분석 및 보안 위협 탐지 API 엔드포인트
- API 검증 및 테스트 엔드포인트
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import request

from api.advanced_fortigate_api import (
    AdvancedFortiGateAPI,
    batch_policy_operations,
    get_fortigate_api_client,
    initialize_global_api_client,
)
from api.fortigate_api_validator import create_test_report, validate_fortigate_api
from config.unified_settings import unified_settings
from utils.common_imports import Blueprint, jsonify
from utils.unified_cache_manager import cached
from utils.unified_logger import get_logger

logger = get_logger(__name__)

# Blueprint 생성
advanced_fortigate_bp = Blueprint("advanced_fortigate", __name__)


# ===== 유틸리티 함수들 =====


def get_api_client() -> Optional[AdvancedFortiGateAPI]:
    """현재 API 클라이언트 인스턴스 반환"""
    try:
        client = get_fortigate_api_client()
        if not client:
            # 설정에서 API 클라이언트 초기화
            config = {
                "host": unified_settings.fortigate_host,
                "api_key": unified_settings.fortigate_api_key,
                "port": getattr(unified_settings, "fortigate_port", 443),
                "verify_ssl": getattr(unified_settings, "fortigate_verify_ssl", False),
                "timeout": getattr(unified_settings, "fortigate_timeout", 30),
            }

            if config["host"] and config["api_key"]:
                client = initialize_global_api_client(config)
            else:
                logger.warning("FortiGate API configuration not available")

        return client

    except Exception as e:
        logger.error(f"Failed to get FortiGate API client: {e}")
        return None


def handle_async_route(async_func):
    """비동기 함수를 Flask 라우트에서 사용할 수 있도록 래핑"""

    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()

    wrapper.__name__ = async_func.__name__
    return wrapper


def validate_json_request(required_fields: List[str] = None) -> Dict[str, Any]:
    """JSON 요청 데이터 검증"""
    if not request.is_json:
        raise ValueError("Content-Type must be application/json")

    data = request.get_json()
    if not data:
        raise ValueError("Request body is empty")

    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

    return data


# ===== API 연결 및 상태 =====


@advanced_fortigate_bp.route("/connection/test", methods=["GET"])
@handle_async_route
async def test_api_connection():
    """API 연결 테스트"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not configured"}), 500

        result = await client.test_connection()

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/connection/status", methods=["GET"])
def get_connection_status():
    """API 연결 상태 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify(
                {"success": True, "data": {"status": "not_configured", "message": "API client not configured"}}
            )

        stats = client.get_api_statistics()

        return jsonify(
            {
                "success": True,
                "data": {"status": "configured", "host": client.host, "port": client.port, "statistics": stats},
            }
        )

    except Exception as e:
        logger.error(f"Failed to get connection status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 방화벽 정책 관리 =====


@advanced_fortigate_bp.route("/policies", methods=["GET"])
@cached(ttl=60)  # 1분 캐시
@handle_async_route
async def get_firewall_policies():
    """방화벽 정책 목록 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        # 쿼리 파라미터 처리
        vdom = request.args.get("vdom", "root")
        filters = {}

        # 필터링 파라미터 처리
        for param in ["srcintf", "dstintf", "action", "status"]:
            value = request.args.get(param)
            if value:
                filters[param] = value

        policies = await client.get_firewall_policies(vdom=vdom, filters=filters)

        return jsonify(
            {"success": True, "data": {"policies": policies, "count": len(policies), "vdom": vdom, "filters": filters}}
        )

    except Exception as e:
        logger.error(f"Failed to get firewall policies: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/policies", methods=["POST"])
@handle_async_route
async def create_firewall_policy():
    """새로운 방화벽 정책 생성"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        # 요청 데이터 검증
        required_fields = ["name", "srcintf", "dstintf", "srcaddr", "dstaddr", "service", "action"]
        data = validate_json_request(required_fields)

        vdom = data.pop("vdom", "root")

        result = await client.create_firewall_policy(data, vdom=vdom)

        return (
            jsonify(
                {"success": True, "message": f"Firewall policy '{data['name']}' created successfully", "data": result}
            ),
            201,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to create firewall policy: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/policies/<int:policy_id>", methods=["PUT"])
@handle_async_route
async def update_firewall_policy(policy_id: int):
    """방화벽 정책 업데이트"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        data = validate_json_request()
        vdom = data.pop("vdom", "root")

        result = await client.update_firewall_policy(policy_id, data, vdom=vdom)

        return jsonify(
            {"success": True, "message": f"Firewall policy {policy_id} updated successfully", "data": result}
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to update firewall policy {policy_id}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/policies/<int:policy_id>", methods=["DELETE"])
@handle_async_route
async def delete_firewall_policy(policy_id: int):
    """방화벽 정책 삭제"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")

        result = await client.delete_firewall_policy(policy_id, vdom=vdom)

        return jsonify(
            {"success": True, "message": f"Firewall policy {policy_id} deleted successfully", "data": result}
        )

    except Exception as e:
        logger.error(f"Failed to delete firewall policy {policy_id}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/policies/batch", methods=["POST"])
@handle_async_route
async def batch_policy_operations_route():
    """배치 정책 작업 실행"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        data = validate_json_request(["operations"])
        operations = data["operations"]

        if not isinstance(operations, list):
            raise ValueError("operations must be a list")

        results = await batch_policy_operations(client, operations)

        # 결과 집계
        successful_ops = sum(1 for r in results if r["status"] == "success")
        failed_ops = len(results) - successful_ops

        return jsonify(
            {
                "success": True,
                "message": f"Batch operations completed: {successful_ops} successful, {failed_ops} failed",
                "data": {
                    "results": results,
                    "summary": {"total": len(results), "successful": successful_ops, "failed": failed_ops},
                },
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Batch policy operations failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== VPN 관리 =====


@advanced_fortigate_bp.route("/vpn/ipsec/tunnels", methods=["GET"])
@cached(ttl=300)  # 5분 캐시
@handle_async_route
async def get_ipsec_vpn_tunnels():
    """IPSec VPN 터널 목록 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        tunnels = await client.get_ipsec_vpn_tunnels(vdom=vdom)

        return jsonify({"success": True, "data": {"tunnels": tunnels, "count": len(tunnels), "vdom": vdom}})

    except Exception as e:
        logger.error(f"Failed to get IPSec VPN tunnels: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/vpn/ssl/settings", methods=["GET"])
@cached(ttl=300)  # 5분 캐시
@handle_async_route
async def get_ssl_vpn_settings():
    """SSL VPN 설정 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        settings = await client.get_ssl_vpn_settings(vdom=vdom)

        return jsonify({"success": True, "data": {"settings": settings, "vdom": vdom}})

    except Exception as e:
        logger.error(f"Failed to get SSL VPN settings: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/vpn/ipsec/tunnels", methods=["POST"])
@handle_async_route
async def create_ipsec_vpn_tunnel():
    """새로운 IPSec VPN 터널 생성"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        required_fields = ["name", "interface", "remote-gw", "psksecret"]
        data = validate_json_request(required_fields)

        vdom = data.pop("vdom", "root")

        result = await client.create_ipsec_vpn_tunnel(data, vdom=vdom)

        return (
            jsonify(
                {"success": True, "message": f"IPSec VPN tunnel '{data['name']}' created successfully", "data": result}
            ),
            201,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to create IPSec VPN tunnel: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== NAT 정책 관리 =====


@advanced_fortigate_bp.route("/nat/policies", methods=["GET"])
@cached(ttl=120)  # 2분 캐시
@handle_async_route
async def get_nat_policies():
    """NAT 정책 목록 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        policy_type = request.args.get("type", "ipv4")

        policies = await client.get_nat_policies(policy_type=policy_type, vdom=vdom)

        return jsonify(
            {
                "success": True,
                "data": {"policies": policies, "count": len(policies), "vdom": vdom, "policy_type": policy_type},
            }
        )

    except Exception as e:
        logger.error(f"Failed to get NAT policies: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/nat/snat", methods=["POST"])
@handle_async_route
async def create_snat_policy():
    """Source NAT 정책 생성"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        required_fields = ["name", "srcintf", "dstintf", "srcaddr", "dstaddr", "service"]
        data = validate_json_request(required_fields)

        vdom = data.pop("vdom", "root")

        result = await client.create_snat_policy(data, vdom=vdom)

        return (
            jsonify({"success": True, "message": f"SNAT policy '{data['name']}' created successfully", "data": result}),
            201,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to create SNAT policy: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 보안 프로필 관리 =====


@advanced_fortigate_bp.route("/security/profiles/<profile_type>", methods=["GET"])
@cached(ttl=300)  # 5분 캐시
@handle_async_route
async def get_security_profiles(profile_type: str):
    """보안 프로필 목록 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        valid_types = ["ips", "antivirus", "webfilter", "application"]
        if profile_type not in valid_types:
            return jsonify({"success": False, "message": f"Invalid profile type. Valid types: {valid_types}"}), 400

        vdom = request.args.get("vdom", "root")
        profiles = await client.get_security_profiles(profile_type, vdom=vdom)

        return jsonify(
            {
                "success": True,
                "data": {"profiles": profiles, "count": len(profiles), "profile_type": profile_type, "vdom": vdom},
            }
        )

    except Exception as e:
        logger.error(f"Failed to get {profile_type} profiles: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/security/profiles/apply", methods=["POST"])
@handle_async_route
async def apply_security_profiles():
    """방화벽 정책에 보안 프로필 적용"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        required_fields = ["policy_id", "security_profiles"]
        data = validate_json_request(required_fields)

        policy_id = data["policy_id"]
        security_profiles = data["security_profiles"]
        vdom = data.get("vdom", "root")

        if not isinstance(security_profiles, dict):
            raise ValueError("security_profiles must be a dictionary")

        result = await client.apply_security_profile_to_policy(policy_id, security_profiles, vdom=vdom)

        return jsonify(
            {
                "success": True,
                "message": f"Security profiles applied to policy {policy_id} successfully",
                "data": result,
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to apply security profiles: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 실시간 로그 모니터링 =====


@advanced_fortigate_bp.route("/logs/<log_type>", methods=["GET"])
@handle_async_route
async def get_realtime_logs(log_type: str):
    """실시간 로그 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        valid_types = ["traffic", "security", "system"]
        if log_type not in valid_types:
            return jsonify({"success": False, "message": f"Invalid log type. Valid types: {valid_types}"}), 400

        # 쿼리 파라미터 처리
        limit = int(request.args.get("limit", 100))
        filters = {}

        # 필터 파라미터 처리
        for param in ["srcip", "dstip", "action", "app", "severity"]:
            value = request.args.get(param)
            if value:
                filters[param] = value

        logs = await client.get_realtime_logs(log_type=log_type, filters=filters, limit=limit)

        return jsonify(
            {
                "success": True,
                "data": {"logs": logs, "count": len(logs), "log_type": log_type, "filters": filters, "limit": limit},
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to get {log_type} logs: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 시스템 모니터링 =====


@advanced_fortigate_bp.route("/system/status", methods=["GET"])
@cached(ttl=30)  # 30초 캐시
@handle_async_route
async def get_system_status():
    """시스템 상태 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        status = await client.get_system_status(vdom=vdom)

        return jsonify({"success": True, "data": status})

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/system/performance", methods=["GET"])
@cached(ttl=60)  # 1분 캐시
@handle_async_route
async def get_performance_stats():
    """성능 통계 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        stats = await client.get_performance_stats(vdom=vdom)

        return jsonify({"success": True, "data": stats})

    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/system/interfaces", methods=["GET"])
@cached(ttl=120)  # 2분 캐시
@handle_async_route
async def get_interface_stats():
    """네트워크 인터페이스 통계 조회"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        vdom = request.args.get("vdom", "root")
        interface_name = request.args.get("interface")

        stats = await client.get_interface_stats(interface_name=interface_name, vdom=vdom)

        return jsonify(
            {"success": True, "data": {"interface_stats": stats, "interface_name": interface_name, "vdom": vdom}}
        )

    except Exception as e:
        logger.error(f"Failed to get interface stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 고급 분석 기능 =====


@advanced_fortigate_bp.route("/analysis/traffic", methods=["GET"])
@handle_async_route
async def analyze_traffic_patterns():
    """트래픽 패턴 분석"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        time_range = int(request.args.get("time_range", 3600))  # 1시간 기본값
        vdom = request.args.get("vdom", "root")

        analysis = await client.analyze_traffic_patterns(time_range=time_range, vdom=vdom)

        return jsonify({"success": True, "data": analysis})

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to analyze traffic patterns: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/analysis/threats", methods=["GET"])
@handle_async_route
async def detect_security_threats():
    """보안 위협 탐지"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        time_range = int(request.args.get("time_range", 3600))  # 1시간 기본값
        severity_threshold = request.args.get("severity", "medium")

        valid_severities = ["low", "medium", "high", "critical"]
        if severity_threshold not in valid_severities:
            return jsonify({"success": False, "message": f"Invalid severity. Valid values: {valid_severities}"}), 400

        threats = await client.detect_security_threats(time_range=time_range, severity_threshold=severity_threshold)

        return jsonify(
            {
                "success": True,
                "data": {
                    "threats": threats,
                    "count": len(threats),
                    "time_range": time_range,
                    "severity_threshold": severity_threshold,
                },
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to detect security threats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== API 검증 및 테스트 =====


@advanced_fortigate_bp.route("/validation/run", methods=["POST"])
@handle_async_route
async def run_api_validation():
    """API 유효성 검사 실행"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        # 요청 데이터 처리 (선택적)
        data = request.get_json() or {}
        test_categories = data.get("categories")  # None이면 모든 카테고리 실행
        save_results = data.get("save_results")  # 결과 저장 파일 경로

        # 유효성 검사 실행
        results = await validate_fortigate_api(client, test_categories=test_categories, save_results=save_results)

        return jsonify(
            {
                "success": True,
                "data": results,
                "message": f"Validation completed - {results['summary']['overall_status']}",
            }
        )

    except Exception as e:
        logger.error(f"API validation failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/validation/report", methods=["POST"])
@handle_async_route
async def generate_validation_report():
    """검증 리포트 생성"""
    try:
        client = get_api_client()
        if not client:
            return jsonify({"success": False, "message": "API client not available"}), 500

        # 검증 실행
        results = await validate_fortigate_api(client)

        # 텍스트 리포트 생성
        report = create_test_report(results)

        return jsonify(
            {
                "success": True,
                "data": {
                    "report_text": report,
                    "validation_results": results,
                    "generated_at": datetime.now().isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate validation report: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/validation/categories", methods=["GET"])
def get_validation_categories():
    """사용 가능한 검증 카테고리 목록 조회"""
    categories = [
        {"name": "connection", "description": "API 연결 및 인증 테스트"},
        {"name": "authentication", "description": "인증 및 권한 테스트"},
        {"name": "basic_operations", "description": "기본 API 작업 테스트"},
        {"name": "performance", "description": "성능 및 응답 시간 테스트"},
        {"name": "security", "description": "보안 설정 및 위협 탐지 테스트"},
        {"name": "functionality", "description": "고급 기능 테스트 (VPN, NAT, 보안 프로필)"},
        {"name": "monitoring", "description": "모니터링 및 로그 스트리밍 테스트"},
    ]

    return jsonify({"success": True, "data": {"categories": categories, "total_categories": len(categories)}})


# ===== 설정 관리 =====


@advanced_fortigate_bp.route("/config", methods=["GET"])
def get_api_config():
    """현재 API 설정 조회"""
    try:
        client = get_api_client()

        if client:
            config = {
                "host": client.host,
                "port": client.port,
                "verify_ssl": client.verify_ssl,
                "timeout": client.timeout,
                "max_retries": client.max_retries,
                "configured": True,
            }
        else:
            config = {"configured": False, "message": "API client not configured"}

        return jsonify({"success": True, "data": config})

    except Exception as e:
        logger.error(f"Failed to get API config: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@advanced_fortigate_bp.route("/config", methods=["POST"])
def update_api_config():
    """API 설정 업데이트"""
    try:
        data = validate_json_request(["host"])

        # 새로운 설정으로 API 클라이언트 초기화
        config = {
            "host": data["host"],
            "api_key": data.get("api_key"),
            "port": data.get("port", 443),
            "verify_ssl": data.get("verify_ssl", False),
            "timeout": data.get("timeout", 30),
            "max_retries": data.get("max_retries", 3),
        }

        if not config["api_key"]:
            return jsonify({"success": False, "message": "API key is required"}), 400

        # 전역 API 클라이언트 초기화
        client = initialize_global_api_client(config)

        return jsonify(
            {
                "success": True,
                "message": "API configuration updated successfully",
                "data": {"host": client.host, "port": client.port, "configured": True},
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to update API config: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== 에러 핸들러 =====


@advanced_fortigate_bp.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({"success": False, "message": "API endpoint not found", "error": "Not Found"}), 404


@advanced_fortigate_bp.errorhandler(405)
def method_not_allowed(error):
    """405 에러 핸들러"""
    return (
        jsonify(
            {"success": False, "message": "HTTP method not allowed for this endpoint", "error": "Method Not Allowed"}
        ),
        405,
    )


@advanced_fortigate_bp.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"success": False, "message": "Internal server error", "error": "Internal Server Error"}), 500


# Blueprint 등록 시 로깅
logger.info("Advanced FortiGate API routes blueprint created")

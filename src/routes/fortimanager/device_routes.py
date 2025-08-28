"""
FortiManager 장치 관리 라우트

장치 조회, 상태 확인, 인터페이스 관리 등 장치 관련 기능을 담당합니다.
"""

from flask import Blueprint, jsonify

from utils.api_utils import get_api_manager
from utils.unified_cache_manager import cached
from utils.unified_logger import setup_logger

# Note: Test mode functionality removed for production stability


# Temporary compatibility functions for removed test mode
def is_test_mode():
    """Test mode removed for production stability"""
    return False


def get_dummy_generator():
    """Dummy generator removed for production stability"""
    return None


logger = setup_logger("device_routes")
device_bp = Blueprint("devices", __name__, url_prefix="/devices")


@device_bp.route("/status", methods=["GET"])
@cached(ttl=60)
def get_fortimanager_status():
    """FortiManager 연결 상태 조회"""
    try:
        if is_test_mode():
            return jsonify(
                {
                    "status": "connected",
                    "mode": "test",
                    "message": "Test mode - Mock FortiManager",
                    "version": "7.0.5",
                    "hostname": "FortiManager-Test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify(
                {
                    "status": "not_configured",
                    "mode": "production",
                    "message": "FortiManager not configured",
                }
            )

        try:
            if fm_client.login():
                status = fm_client.get_system_status()
                return jsonify(
                    {
                        "status": "connected",
                        "mode": "production",
                        "version": status.get("version", "Unknown"),
                        "hostname": status.get("hostname", "Unknown"),
                    }
                )
            else:
                return jsonify(
                    {
                        "status": "disconnected",
                        "mode": "production",
                        "message": "Authentication failed",
                    }
                )
        except Exception as e:
            logger.error(f"FortiManager 연결 확인 중 오류: {str(e)}")
            return jsonify(
                {
                    "status": "error",
                    "mode": "production",
                    "message": f"Connection error: {str(e)}",
                }
            )

    except Exception as e:
        logger.error(f"FortiManager 상태 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@device_bp.route("/", methods=["GET"])
@cached(ttl=120)
def get_devices():
    """관리되는 모든 장치 목록 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            devices = dummy_generator.generate_dummy_devices(5)
            return jsonify({"devices": devices, "total": len(devices), "mode": "test"})

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        devices = fm_client.get_devices()
        return jsonify(
            {
                "devices": devices or [],
                "total": len(devices) if devices else 0,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"장치 목록 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<device_id>", methods=["GET"])
@cached(ttl=300)
def get_device_info(device_id):
    """특정 장치의 상세 정보 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            device_info = dummy_generator.generate_device_info(device_id)
            return jsonify({"device": device_info, "mode": "test"})

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        device_info = fm_client.get_device_info(device_id)
        if not device_info:
            return jsonify({"error": f"Device {device_id} not found"}), 404

        return jsonify({"device": device_info, "mode": "production"})

    except Exception as e:
        logger.error(f"장치 정보 조회 중 오류 ({device_id}): {str(e)}")
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<device_id>/interfaces", methods=["GET"])
@cached(ttl=180)
def get_device_interfaces(device_id):
    """장치의 네트워크 인터페이스 정보 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            interfaces = dummy_generator.generate_device_interfaces(device_id)
            return jsonify(
                {
                    "device_id": device_id,
                    "interfaces": interfaces,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        interfaces = fm_client.get_device_interfaces(device_id)
        return jsonify(
            {
                "device_id": device_id,
                "interfaces": interfaces or [],
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"장치 인터페이스 조회 중 오류 ({device_id}): {str(e)}")
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<device_id>/monitoring", methods=["GET"])
@cached(ttl=30)
def get_device_monitoring(device_id):
    """장치 모니터링 정보 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            monitoring_data = dummy_generator.generate_monitoring_data(device_id)
            return jsonify(
                {
                    "device_id": device_id,
                    "monitoring": monitoring_data,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        monitoring_data = fm_client.get_device_monitoring(device_id)
        return jsonify(
            {
                "device_id": device_id,
                "monitoring": monitoring_data or {},
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"장치 모니터링 조회 중 오류 ({device_id}): {str(e)}")
        return jsonify({"error": str(e)}), 500


@device_bp.route("/dashboard", methods=["GET"])
@cached(ttl=60)
def get_dashboard_data():
    """FortiManager 대시보드 데이터 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            dashboard_data = dummy_generator.generate_dashboard_data()
            return jsonify({"dashboard": dashboard_data, "mode": "test"})

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        dashboard_data = fm_client.get_dashboard_data()
        return jsonify({"dashboard": dashboard_data or {}, "mode": "production"})

    except Exception as e:
        logger.error(f"대시보드 데이터 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Mock 관련 엔드포인트들
@device_bp.route("/mock/system-status", methods=["GET"])
def mock_system_status():
    """Mock 시스템 상태 (테스트용)"""
    if not is_test_mode():
        return (
            jsonify({"error": "Mock endpoints only available in test mode"}),
            403,
        )

    return jsonify(
        {
            "hostname": "FortiManager-Mock",
            "version": "7.0.5-test",
            "serial": "FMGMOCK000001",
            "uptime": "5 days, 12:34:56",
            "cpu_usage": 15.3,
            "memory_usage": 42.7,
            "disk_usage": 28.5,
        }
    )


@device_bp.route("/mock/interfaces", methods=["GET"])
def mock_interfaces():
    """Mock 인터페이스 정보 (테스트용)"""
    if not is_test_mode():
        return (
            jsonify({"error": "Mock endpoints only available in test mode"}),
            403,
        )

    return jsonify(
        {
            "interfaces": [
                {
                    "name": "port1",
                    "ip": "192.168.1.1",
                    "mask": "255.255.255.0",
                    "status": "up",
                    "speed": "1000",
                },
                {
                    "name": "port2",
                    "ip": "10.0.0.1",
                    "mask": "255.255.255.0",
                    "status": "up",
                    "speed": "1000",
                },
            ]
        }
    )

"""
FortiManager 분석 라우트

패킷 캡처, 트렌드 분석, 보안 분석 등 고급 분석 기능을 담당합니다.
"""

import time

from flask import Blueprint, jsonify, request

from fortimanager.advanced_hub import FortiManagerAdvancedHub
from utils.api_utils import get_api_manager
from utils.security import rate_limit
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


logger = setup_logger("analytics_routes")
analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/packet-capture/start", methods=["POST"])
@rate_limit(max_requests=5, window=300)
def start_packet_capture():
    """패킷 캡처 시작"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Capture configuration is required"}), 400

        device_id = data.get("device_id", "default")
        interface = data.get("interface", "any")
        filter_expr = data.get("filter", "")
        duration = data.get("duration", 60)

        if is_test_mode():
            capture_id = f"test_capture_{int(time.time())}"
            return jsonify(
                {
                    "success": True,
                    "capture_id": capture_id,
                    "message": "Packet capture started (test mode)",
                    "duration": duration,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        result = fm_client.start_packet_capture(device_id, interface, filter_expr, duration)

        if result:
            return jsonify(
                {
                    "success": True,
                    "capture_id": result.get("capture_id"),
                    "message": "Packet capture started successfully",
                    "duration": duration,
                    "mode": "production",
                }
            )
        else:
            return jsonify({"error": "Failed to start packet capture"}), 500

    except Exception as e:
        logger.error(f"패킷 캡처 시작 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/packet-capture/stop", methods=["POST"])
@rate_limit(max_requests=10, window=60)
def stop_packet_capture():
    """패킷 캡처 중지"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Capture ID is required"}), 400

        capture_id = data.get("capture_id")

        if not capture_id:
            return jsonify({"error": "capture_id is required"}), 400

        if is_test_mode():
            return jsonify(
                {
                    "success": True,
                    "capture_id": capture_id,
                    "message": "Packet capture stopped (test mode)",
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        result = fm_client.stop_packet_capture(capture_id)

        if result:
            return jsonify(
                {
                    "success": True,
                    "capture_id": capture_id,
                    "message": "Packet capture stopped successfully",
                    "mode": "production",
                }
            )
        else:
            return jsonify({"error": "Failed to stop packet capture"}), 500

    except Exception as e:
        logger.error(f"패킷 캡처 중지 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/packet-capture/results/<capture_id>", methods=["GET"])
@cached(ttl=60)
def get_capture_results(capture_id):
    """패킷 캡처 결과 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            capture_results = dummy_generator.generate_capture_results(capture_id)
            return jsonify(
                {
                    "capture_id": capture_id,
                    "results": capture_results,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        results = fm_client.get_capture_results(capture_id)

        if results:
            return jsonify(
                {
                    "capture_id": capture_id,
                    "results": results,
                    "mode": "production",
                }
            )
        else:
            return jsonify({"error": "Capture results not found"}), 404

    except Exception as e:
        logger.error(f"캡처 결과 조회 중 오류 ({capture_id}): {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/advanced/trends", methods=["POST"])
@rate_limit(max_requests=20, window=300)
async def analyze_trends():
    """고급 트렌드 분석"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Analysis parameters are required"}), 400

        devices = data.get("devices", [])
        time_range = data.get("time_range", "24h")
        metrics = data.get("metrics", ["traffic", "threats"])

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            trends_data = dummy_generator.generate_trends_analysis(devices, time_range, metrics)
            return jsonify(
                {
                    "trends": trends_data,
                    "devices": devices,
                    "time_range": time_range,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 트렌드 분석 수행
        trends_result = await hub.analytics_engine.analyze_trends_async(
            devices=devices, time_range=time_range, metrics=metrics
        )

        return jsonify(
            {
                "trends": trends_result,
                "devices": devices,
                "time_range": time_range,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"트렌드 분석 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/advanced/anomalies", methods=["POST"])
@rate_limit(max_requests=15, window=300)
async def detect_anomalies():
    """이상 행위 탐지"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Detection parameters are required"}), 400

        devices = data.get("devices", [])
        detection_types = data.get("types", ["traffic", "login", "policy"])
        sensitivity = data.get("sensitivity", "medium")

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            anomalies = dummy_generator.generate_anomaly_detection(devices, detection_types)
            return jsonify(
                {
                    "anomalies": anomalies,
                    "devices": devices,
                    "sensitivity": sensitivity,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 이상 탐지 수행
        anomalies_result = await hub.analytics_engine.detect_anomalies(
            devices=devices,
            detection_types=detection_types,
            sensitivity=sensitivity,
        )

        return jsonify(
            {
                "anomalies": anomalies_result,
                "devices": devices,
                "sensitivity": sensitivity,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"이상 탐지 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/advanced/capacity-planning", methods=["POST"])
@rate_limit(max_requests=10, window=600)
async def analyze_capacity():
    """용량 계획 분석"""
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Capacity analysis parameters are required"}),
                400,
            )

        devices = data.get("devices", [])
        forecast_period = data.get("forecast_period", "3months")
        resources = data.get("resources", ["cpu", "memory", "bandwidth"])

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            capacity_data = dummy_generator.generate_capacity_analysis(devices, forecast_period)
            return jsonify(
                {
                    "capacity_analysis": capacity_data,
                    "devices": devices,
                    "forecast_period": forecast_period,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 용량 분석 수행
        capacity_result = await hub.analytics_engine.predict_capacity(
            devices=devices,
            forecast_period=forecast_period,
            resources=resources,
        )

        return jsonify(
            {
                "capacity_analysis": capacity_result,
                "devices": devices,
                "forecast_period": forecast_period,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"용량 계획 분석 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/security/threats", methods=["POST"])
@rate_limit(max_requests=25, window=300)
async def detect_threats():
    """위협 탐지 분석"""
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Threat detection parameters are required"}),
                400,
            )

        devices = data.get("devices", [])
        threat_types = data.get("threat_types", ["malware", "intrusion", "botnet"])
        time_window = data.get("time_window", "1h")

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            threats = dummy_generator.generate_threat_detection(devices, threat_types)
            return jsonify(
                {
                    "threats": threats,
                    "devices": devices,
                    "threat_types": threat_types,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 위협 탐지 수행
        threats_result = await hub.security_fabric.detect_threats(
            devices=devices, threat_types=threat_types, time_window=time_window
        )

        return jsonify(
            {
                "threats": threats_result,
                "devices": devices,
                "threat_types": threat_types,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"위협 탐지 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/security/incident-response", methods=["POST"])
@rate_limit(max_requests=5, window=300)
async def coordinate_incident_response():
    """보안 사고 대응 조정"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Incident data is required"}), 400

        incident_id = data.get("incident_id")
        devices = data.get("devices", [])
        response_actions = data.get("actions", ["isolate", "block", "log"])

        if not incident_id:
            return jsonify({"error": "incident_id is required"}), 400

        if is_test_mode():
            return jsonify(
                {
                    "success": True,
                    "incident_id": incident_id,
                    "response_actions": response_actions,
                    "message": "Incident response coordinated (test mode)",
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 사고 대응 조정
        response_result = await hub.security_fabric.coordinate_response(
            incident_id=incident_id, devices=devices, actions=response_actions
        )

        return jsonify(
            {
                "success": response_result.get("success", False),
                "incident_id": incident_id,
                "response_actions": response_actions,
                "details": response_result,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"사고 대응 조정 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

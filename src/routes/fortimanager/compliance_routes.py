"""
FortiManager 컴플라이언스 라우트

컴플라이언스 검사, 정책 템플릿 적용, 규정 준수 보고서 등 컴플라이언스 관련 기능을 담당합니다.
"""

from flask import Blueprint, jsonify, request

from fortimanager.advanced_hub import FortiManagerAdvancedHub
from utils.api_utils import get_api_manager

# Note: Test mode functionality removed for production stability
from utils.security import rate_limit
from utils.unified_cache_manager import cached
from utils.unified_logger import setup_logger

logger = setup_logger("compliance_routes")
compliance_bp = Blueprint("compliance", __name__, url_prefix="/compliance")


# Temporary compatibility functions for removed test mode
def is_test_mode():
    """Test mode removed for production stability"""
    return False


def get_dummy_generator():
    """Dummy generator removed for production stability"""
    return None


@compliance_bp.route("/check", methods=["POST"])
@rate_limit(max_requests=20, window=300)
async def check_compliance():
    """컴플라이언스 검사 수행"""
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Compliance check parameters are required"}),
                400,
            )

        devices = data.get("devices", [])
        frameworks = data.get("frameworks", ["PCI-DSS"])
        auto_remediate = data.get("auto_remediate", False)

        if not devices:
            return jsonify({"error": "At least one device is required"}), 400

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            compliance_results = dummy_generator.generate_compliance_check(devices, frameworks)
            return jsonify(
                {
                    "compliance_check": compliance_results,
                    "devices": devices,
                    "frameworks": frameworks,
                    "auto_remediate": auto_remediate,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 컴플라이언스 검사 수행
        compliance_result = await hub.compliance_framework.check_compliance(
            devices=devices,
            frameworks=frameworks,
            auto_remediate=auto_remediate,
        )

        return jsonify(
            {
                "compliance_check": compliance_result,
                "devices": devices,
                "frameworks": frameworks,
                "auto_remediate": auto_remediate,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"컴플라이언스 검사 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/remediate", methods=["POST"])
@rate_limit(max_requests=10, window=600)
async def remediate_violations():
    """컴플라이언스 위반 사항 자동 수정"""
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Remediation parameters are required"}),
                400,
            )

        devices = data.get("devices", [])
        violations = data.get("violations", [])
        dry_run = data.get("dry_run", True)  # 기본값: 테스트 실행

        if not devices or not violations:
            return (
                jsonify({"error": "Devices and violations are required"}),
                400,
            )

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            remediation_results = dummy_generator.generate_remediation_results(violations)
            return jsonify(
                {
                    "remediation": remediation_results,
                    "devices": devices,
                    "violations_count": len(violations),
                    "dry_run": dry_run,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 위반 사항 수정
        remediation_result = await hub.compliance_framework.remediate_violations(
            devices=devices, violations=violations, dry_run=dry_run
        )

        return jsonify(
            {
                "remediation": remediation_result,
                "devices": devices,
                "violations_count": len(violations),
                "dry_run": dry_run,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"컴플라이언스 수정 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/templates", methods=["GET"])
@cached(ttl=600)
def get_policy_templates():
    """정책 템플릿 목록 조회"""
    try:
        category = request.args.get("category", "all")
        framework = request.args.get("framework", "all")

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            templates = dummy_generator.generate_policy_templates(category, framework)
            return jsonify(
                {
                    "templates": templates,
                    "category": category,
                    "framework": framework,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        templates = hub.policy_orchestrator.get_available_templates(category=category, framework=framework)

        return jsonify(
            {
                "templates": templates or [],
                "category": category,
                "framework": framework,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"정책 템플릿 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/templates/apply", methods=["POST"])
@rate_limit(max_requests=5, window=300)
async def apply_policy_template():
    """정책 템플릿 적용"""
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Template application parameters are required"}),
                400,
            )

        template_name = data.get("template_name")
        devices = data.get("devices", [])
        parameters = data.get("parameters", {})
        dry_run = data.get("dry_run", True)

        if not template_name:
            return jsonify({"error": "template_name is required"}), 400

        if not devices:
            return jsonify({"error": "At least one device is required"}), 400

        if is_test_mode():
            return jsonify(
                {
                    "success": True,
                    "template_name": template_name,
                    "devices": devices,
                    "applied_policies": len(devices) * 3,  # 가정: 장치당 3개 정책
                    "dry_run": dry_run,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        # 비동기 템플릿 적용
        application_result = await hub.policy_orchestrator.apply_template(
            template_name=template_name,
            devices=devices,
            parameters=parameters,
            dry_run=dry_run,
        )

        return jsonify(
            {
                "success": application_result.get("success", False),
                "template_name": template_name,
                "devices": devices,
                "details": application_result,
                "dry_run": dry_run,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"정책 템플릿 적용 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/reports", methods=["GET"])
@cached(ttl=300)
def get_compliance_reports():
    """컴플라이언스 보고서 조회"""
    try:
        devices = request.args.getlist("devices")
        frameworks = request.args.getlist("frameworks")
        date_range = request.args.get("date_range", "30days")
        report_format = request.args.get("format", "json")

        if is_test_mode():
            dummy_generator = get_dummy_generator()
            reports = dummy_generator.generate_compliance_reports(devices, frameworks, date_range)
            return jsonify(
                {
                    "reports": reports,
                    "devices": devices,
                    "frameworks": frameworks,
                    "date_range": date_range,
                    "format": report_format,
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        reports = hub.compliance_framework.generate_report(
            devices=devices,
            frameworks=frameworks,
            date_range=date_range,
            report_format=report_format,
        )

        return jsonify(
            {
                "reports": reports or {},
                "devices": devices,
                "frameworks": frameworks,
                "date_range": date_range,
                "format": report_format,
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"컴플라이언스 보고서 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/schedules", methods=["GET"])
@cached(ttl=120)
def get_scheduled_checks():
    """예약된 컴플라이언스 검사 목록 조회"""
    try:
        if is_test_mode():
            dummy_generator = get_dummy_generator()
            schedules = dummy_generator.generate_scheduled_checks()
            return jsonify({"schedules": schedules, "mode": "test"})

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        schedules = hub.compliance_framework.get_scheduled_checks()

        return jsonify({"schedules": schedules or [], "mode": "production"})

    except Exception as e:
        logger.error(f"예약된 검사 조회 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500


@compliance_bp.route("/schedules", methods=["POST"])
@rate_limit(max_requests=10, window=300)
def create_scheduled_check():
    """컴플라이언스 검사 예약"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Schedule parameters are required"}), 400

        name = data.get("name")
        devices = data.get("devices", [])
        frameworks = data.get("frameworks", [])
        schedule = data.get("schedule")  # cron 형식
        auto_remediate = data.get("auto_remediate", False)

        if not name or not devices or not frameworks or not schedule:
            return (
                jsonify({"error": "Name, devices, frameworks, and schedule are required"}),
                400,
            )

        if is_test_mode():
            schedule_id = f"test_schedule_{hash(name) % 10000}"
            return jsonify(
                {
                    "success": True,
                    "schedule_id": schedule_id,
                    "name": name,
                    "message": "Compliance check scheduled (test mode)",
                    "mode": "test",
                }
            )

        api_manager = get_api_manager()
        fm_client = api_manager.get_fortimanager_client()

        if not fm_client:
            return jsonify({"error": "FortiManager client not available"}), 503

        # FortiManager 고급 허브 사용
        hub = FortiManagerAdvancedHub(fm_client)

        schedule_result = hub.compliance_framework.schedule_check(
            name=name,
            devices=devices,
            frameworks=frameworks,
            schedule=schedule,
            auto_remediate=auto_remediate,
        )

        if schedule_result:
            return jsonify(
                {
                    "success": True,
                    "schedule_id": schedule_result.get("schedule_id"),
                    "name": name,
                    "message": "Compliance check scheduled successfully",
                    "mode": "production",
                }
            )
        else:
            return (
                jsonify({"error": "Failed to schedule compliance check"}),
                500,
            )

    except Exception as e:
        logger.error(f"컴플라이언스 검사 예약 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

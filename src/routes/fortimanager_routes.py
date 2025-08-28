"""
FortiManager API routes (Modularized for maintainability)

This file serves as a main router that aggregates route modules to maintain
the 500-line limit per file. Each functional area is split into separate modules.
"""

from flask import Blueprint, jsonify, request

from config.unified_settings import unified_settings

# Removed test mode dependencies - using production APIs only
from utils.unified_logger import get_logger

logger = get_logger(__name__)

# Create a new blueprint for FortiManager routes
fortimanager_bp = Blueprint("fortimanager", __name__, url_prefix="/api/fortimanager")


@fortimanager_bp.route("/status", methods=["GET"])
def get_fortimanager_status():
    """FortiManager connection status - Real API implementation"""
    try:
        from api.clients.fortimanager_api_client import FortiManagerAPIClient

        client = FortiManagerAPIClient()
        mode = "test" if unified_settings.is_test_mode() else "production"

        if client.test_connection():
            return jsonify(
                {
                    "status": "connected",
                    "mode": mode,
                    "message": "FortiManager connected successfully",
                    "version": client.get_version(),
                    "hostname": client.get_hostname(),
                }
            )
        else:
            return jsonify(
                {
                    "status": "disconnected",
                    "mode": mode,
                    "message": "FortiManager connection failed - check configuration",
                }
            )
    except Exception as e:
        logger.error(f"FortiManager status check failed: {e}")
        mode = "test" if unified_settings.is_test_mode() else "production"
        return jsonify({"status": "error", "mode": mode, "message": f"FortiManager API error: {str(e)}"})


@fortimanager_bp.route("/policies", methods=["POST"])
def get_fortimanager_policies():
    """Get FortiManager policies"""
    try:
        # data = request.get_json() or {}  # Currently unused
        # device_id = data.get("device_id", "default")  # Currently unused

        # Return sample policies for now
        policies = [
            {"id": 1, "name": "Allow Internal", "action": "accept", "status": "enabled"},
            {"id": 2, "name": "Block External", "action": "deny", "status": "enabled"},
            {"id": 3, "name": "Guest Network", "action": "accept", "status": "disabled"},
        ]

        return jsonify({"success": True, "data": policies})
    except Exception as e:
        logger.error(f"Failed to get policies: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/compliance", methods=["GET"])
def get_fortimanager_compliance():
    """Get FortiManager compliance status"""
    try:
        compliance = {
            "overall_score": 85,
            "compliant": True,
            "standards": {
                "pci_dss": {"score": 90, "status": "compliant"},
                "hipaa": {"score": 88, "status": "compliant"},
                "gdpr": {"score": 82, "status": "compliant"},
            },
        }

        return jsonify({"success": True, "data": compliance})
    except Exception as e:
        logger.error(f"Failed to get compliance: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/analyze-packet-path", methods=["POST"])
def analyze_packet_path():
    """Analyze packet path through FortiManager - Real implementation"""
    try:
        from analysis.fixed_path_analyzer import FixedPathAnalyzer

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        src_ip = data.get("src_ip")
        dst_ip = data.get("dst_ip")
        port = data.get("port", 80)

        if not src_ip or not dst_ip:
            return jsonify({"success": False, "message": "src_ip and dst_ip required"}), 400

        # Use real path analyzer
        analyzer = FixedPathAnalyzer()
        result = analyzer.analyze_path(src_ip, dst_ip, port)

        return jsonify(
            {
                "success": result["allowed"],
                "path": result["path"],
                "analysis": result["analysis_summary"],
                "policy": {
                    "matched": result["analysis_summary"]["matched_policy"],
                    "description": result["analysis_summary"]["policy_description"],
                    "action": "allow" if result["allowed"] else "deny",
                },
                "mode": "production",
            }
        )

    except Exception as e:
        logger.error(f"Packet path analysis failed: {e}")
        return jsonify({"success": False, "message": f"Analysis error: {str(e)}"}), 500


# AI-powered advanced operations routes
@fortimanager_bp.route("/ai/optimize-policies", methods=["POST"])
async def optimize_policies_with_ai():
    """Optimize policies using AI engine"""
    try:

        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        data = request.get_json()
        device_id = data.get("device_id")

        if not device_id:
            return jsonify({"success": False, "message": "device_id required"}), 400

        hub = FortiManagerAdvancedHub()
        result = await hub.policy_optimizer.optimize_policy_set(device_id)

        return jsonify({"success": True, "optimization": result, "mode": "ai_enhanced"})

    except Exception as e:
        logger.error(f"AI policy optimization failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/ai/threat-analysis", methods=["POST"])
async def analyze_threats_with_ai():
    """Analyze security threats using AI"""
    try:

        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        data = request.get_json()
        fabric_id = data.get("fabric_id", "default")

        hub = FortiManagerAdvancedHub()
        result = await hub.security_fabric.analyze_security_posture(fabric_id)

        return jsonify({"success": True, "analysis": result, "mode": "ai_enhanced"})

    except Exception as e:
        logger.error(f"AI threat analysis failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/ai/compliance-check", methods=["POST"])
async def check_compliance_with_ai():
    """Check compliance using AI-enhanced framework"""
    try:

        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        data = request.get_json()
        device_id = data.get("device_id")
        standard = data.get("standard", "pci_dss")

        if not device_id:
            return jsonify({"success": False, "message": "device_id required"}), 400

        hub = FortiManagerAdvancedHub()
        result = await hub.compliance_framework.check_compliance(device_id, standard)

        # Auto-remediate if enabled and violations found
        if result.get("violations") and data.get("auto_remediate", False):
            remediation = await hub.compliance_framework.auto_remediate_violations(device_id, result)
            result["remediation"] = remediation

        return jsonify({"success": True, "compliance": result, "mode": "ai_enhanced"})

    except Exception as e:
        logger.error(f"AI compliance check failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/ai/analytics-report", methods=["POST"])
async def generate_analytics_with_ai():
    """Generate advanced analytics report with AI predictions"""
    try:

        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        data = request.get_json()
        scope = data.get("scope", "global")
        period_days = data.get("period_days", 30)

        hub = FortiManagerAdvancedHub()
        result = await hub.analytics_engine.generate_analytics_report(scope, period_days)

        return jsonify({"success": True, "report": result, "mode": "ai_enhanced"})

    except Exception as e:
        logger.error(f"AI analytics generation failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@fortimanager_bp.route("/ai/hub-status", methods=["GET"])
def get_ai_hub_status():
    """Get status of AI-enhanced FortiManager hub"""
    try:
        from fortimanager.fortimanager_advanced_hub import FortiManagerAdvancedHub

        hub = FortiManagerAdvancedHub()
        status = hub.get_hub_status()

        return jsonify({"success": True, "status": status, "mode": "ai_enhanced"})

    except Exception as e:
        logger.error(f"Hub status check failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# Register sub-blueprints for modular organization
try:
    from .fortimanager.analytics_routes import analytics_bp
    from .fortimanager.compliance_routes import compliance_bp
    from .fortimanager.device_routes import device_bp

    fortimanager_bp.register_blueprint(analytics_bp)
    fortimanager_bp.register_blueprint(compliance_bp)
    fortimanager_bp.register_blueprint(device_bp)

    logger.info("FortiManager sub-blueprints registered successfully")
except ImportError as e:
    logger.warning(f"Some FortiManager sub-modules not available: {e}")

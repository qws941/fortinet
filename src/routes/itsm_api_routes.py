"""
ITSM API routes
"""

from flask import Blueprint, jsonify, request

itsm_api_bp = Blueprint("itsm_api", __name__, url_prefix="/api/itsm")


@itsm_api_bp.route("/scrape-requests", methods=["GET"])
def scrape_itsm_requests():
    """ITSM에서 방화벽 요청 스크래핑"""
    try:
        # Production mode - fetch actual ITSM data
        # Actual scraping logic
        from itsm.scraper import ITSMScraper

        scraper = ITSMScraper()
        requests = scraper.get_firewall_requests()

        return jsonify({"status": "success", "requests": requests, "total": len(requests)})

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "requests": [],
                    "total": 0,
                }
            ),
            500,
        )


@itsm_api_bp.route("/process-request", methods=["POST"])
def process_itsm_request():
    """ITSM 요청 처리"""
    try:
        data = request.get_json()
        request_id = data.get("request_id")

        if not request_id:
            return jsonify({"error": "request_id is required"}), 400

        # 실제 처리 로직
        from itsm.processor import ITSMProcessor

        processor = ITSMProcessor()
        result = processor.process_request(request_id)

        return jsonify({"status": "success", "result": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@itsm_api_bp.route("/status/<request_id>", methods=["GET"])
def get_request_status(request_id):
    """요청 상태 조회"""
    try:
        from itsm.scraper import ITSMScraper

        scraper = ITSMScraper()
        status = scraper.get_request_status(request_id)

        return jsonify({"status": "success", "request_id": request_id, "data": status})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

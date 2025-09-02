#!/usr/bin/env python3
"""
Nextrade Fortigate - 모듈화된 웹 애플리케이션
Flask + Socket.IO 기반 웹 애플리케이션 (모듈화 버전)
"""

# Gevent monkey patching이 필요한 경우 가장 먼저 실행
import os

if os.environ.get("WORKER_CLASS") == "gevent":
    from gevent import monkey

    monkey.patch_all(ssl=False)  # SSL 패치를 비활성화하여 경고 방지

import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request

# 통합 설정에서 시스템 설정 가져오기
from config.unified_settings import unified_settings
from routes.api_routes import api_bp
from routes.fortimanager_routes import fortimanager_bp
from routes.itsm_api_routes import itsm_api_bp
from routes.itsm_routes import itsm_bp
from routes.main_routes import main_bp
from utils.security import (add_security_headers, csrf_protect,
                            generate_csrf_token, rate_limit)
from utils.unified_logger import get_logger

OFFLINE_MODE = unified_settings.system.offline_mode
DISABLE_SOCKETIO = unified_settings.system.disable_socketio

if OFFLINE_MODE:
    print("🔒 OFFLINE MODE ACTIVATED - 외부 연결 차단됨")
    os.environ["DISABLE_SOCKETIO"] = "true"
    os.environ["DISABLE_UPDATES"] = "true"
    os.environ["DISABLE_TELEMETRY"] = "true"

if not DISABLE_SOCKETIO:
    try:
        from flask_socketio import SocketIO

        print("Socket.IO enabled")
    except ImportError:
        print("Warning: flask-socketio not available, disabling Socket.IO")
        DISABLE_SOCKETIO = True
else:
    print("Socket.IO disabled by environment variable")

# Route imports removed (using direct imports in create_app)


def create_app():
    """Flask 애플리케이션 팩토리"""

    from analysis.analyzer import FirewallRuleAnalyzer

    try:
        from analysis.fixed_path_analyzer import FixedPathAnalyzer
    except ImportError:
        # Fallback for import issues in container
        FixedPathAnalyzer = None
    from config.unified_settings import unified_settings
    from routes.itsm_automation_routes import itsm_automation_bp
    from routes.logs_routes import logs_bp
    from routes.performance_routes import performance_bp
    from utils.unified_cache_manager import get_cache_manager

    # 로거 설정 (다른 코드보다 먼저 초기화)
    logger = get_logger(__name__)

    app = Flask(__name__)

    # 보안 강화: SECRET_KEY 필수 설정
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if os.environ.get("APP_MODE", "production").lower() == "production":
            raise ValueError("🚨 보안 오류: 프로덕션 환경에서는 SECRET_KEY 환경변수가 필수입니다")
        else:
            # 개발/테스트 환경에서만 임시 키 생성
            import secrets

            secret_key = secrets.token_hex(32)
            logger.warning("⚠️  개발 환경: 임시 SECRET_KEY 생성됨. 프로덕션에서는 환경변수를 설정하세요")

    app.config["SECRET_KEY"] = secret_key

    # 보안 강화: 세션 쿠키 보안 설정
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("APP_MODE", "production").lower() == "production"
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 900  # 15분 세션 만료

    # JSON 한글 인코딩 설정
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

    # 애플리케이션 시작 시간 설정 (uptime 계산용)
    app.start_time = time.time()

    # 통합 캐시 매니저 설정
    if OFFLINE_MODE:
        print("🔒 Redis 캐시 비활성화 (오프라인 모드)")
        # 메모리 캐시만 사용
        os.environ["REDIS_ENABLED"] = "false"

    try:
        cache_manager = get_cache_manager()
        print(f"통합 캐시 매니저 로드 성공: {cache_manager.get_stats()['backends']}개 백엔드")
    except Exception as e:
        print(f"캐시 매니저 로드 실패: {e}")
        cache_manager = None

    # Security headers
    @app.after_request
    def after_request(response):
        return add_security_headers(response)

    # Context processor for global variables
    @app.context_processor
    def inject_global_vars():
        # 운영 환경에서는 테스트 모드 숨김
        show_test_mode = unified_settings.app_mode != "production"

        return {
            "APP_MODE": unified_settings.app_mode,
            "OFFLINE_MODE": OFFLINE_MODE,
            "show_test_mode": show_test_mode,
            "build_time": os.getenv("BUILD_TIME", "Development"),
            "csrf_token": generate_csrf_token(),
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}")
        return render_template("500.html"), 500

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(itsm_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(fortimanager_bp)
    app.register_blueprint(itsm_api_bp)

    # 성능 최적화 라우트 등록
    try:
        app.register_blueprint(performance_bp)
        logger.info("Performance optimization routes registered")
    except ImportError as e:
        logger.warning(f"Performance routes not available: {e}")

    # ITSM 자동화 라우트 등록
    try:
        app.register_blueprint(itsm_automation_bp)
        logger.info("ITSM automation routes registered")
    except ImportError as e:
        logger.warning(f"ITSM automation routes not available: {e}")

    # 로그 관리 라우트 등록
    try:
        app.register_blueprint(logs_bp)
        logger.info("Docker logs management routes registered")
    except ImportError as e:
        logger.warning(f"Logs routes not available: {e}")

    # Advanced FortiGate API 라우트 등록
    try:
        from routes.api_modules.advanced_fortigate_routes import \
            advanced_fortigate_bp

        app.register_blueprint(
            advanced_fortigate_bp, url_prefix="/api/advanced_fortigate"
        )
        logger.info("Advanced FortiGate API routes registered")
    except ImportError as e:
        logger.warning(f"Advanced FortiGate API routes not available: {e}")

    # Legacy routes for backward compatibility
    @rate_limit(max_requests=30, window=60)
    @csrf_protect
    @app.route("/analyze_path", methods=["POST"])
    def analyze_path():
        """경로 분석 (레거시 호환성)"""
        try:
            data = request.get_json()

            analyzer = FirewallRuleAnalyzer()
            result = analyzer.analyze_path(data)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Firewall policy routes
    @rate_limit(max_requests=30, window=60)
    @csrf_protect
    @app.route("/api/firewall-policy/analyze", methods=["POST"])
    def analyze_firewall_policy():
        """방화벽 정책 분석"""
        try:
            data = request.get_json()

            if FixedPathAnalyzer:
                analyzer = FixedPathAnalyzer()
                _result = analyzer.analyze_path(
                    src_ip=data.get("src_ip"),
                    dst_ip=data.get("dst_ip"),
                    protocol=data.get("protocol", "tcp"),
                    port=data.get("port"),
                )
            else:
                # Fallback when FixedPathAnalyzer is not available
                _result = {
                    "status": "mock",
                    "message": "Path analyzer temporarily unavailable",
                    "path": f"{data.get('src_ip')} -> {data.get('dst_ip')}",
                    "allowed": True,
                }

            return jsonify({"status": "success", "analysis": _result})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @rate_limit(max_requests=30, window=60)
    @csrf_protect
    @app.route("/api/firewall-policy/create-ticket", methods=["POST"])
    def create_firewall_ticket():
        """방화벽 정책 티켓 생성"""
        try:
            data = request.get_json()

            # 티켓 생성 로직
            ticket = {
                "id": f"FW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "title": data.get("title", "방화벽 정책 요청"),
                "description": data.get("description", ""),
                "src_ip": data.get("src_ip"),
                "dst_ip": data.get("dst_ip"),
                "protocol": data.get("protocol"),
                "port": data.get("port"),
                "status": "Created",
                "created_at": datetime.now().isoformat(),
            }

            return jsonify({"status": "success", "ticket": ticket})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @rate_limit(max_requests=60, window=60)
    @csrf_protect
    @app.route("/api/firewall-policy/zones")
    def get_firewall_zones():
        """방화벽 존 정보 조회"""
        try:
            zones = [
                {"name": "internal", "description": "내부 네트워크"},
                {"name": "dmz", "description": "DMZ 네트워크"},
                {"name": "external", "description": "외부 네트워크"},
                {"name": "branch", "description": "지사 네트워크"},
                {"name": "management", "description": "관리 네트워크"},
            ]

            return jsonify({"status": "success", "zones": zones})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return app


def main():
    """메인 실행 함수"""
    app = create_app()

    # Socket.IO 설정
    socketio = None
    if not DISABLE_SOCKETIO:
        try:
            socketio = SocketIO(
                app,
                cors_allowed_origins="*",
                async_mode="threading",
                ping_timeout=60,
                ping_interval=25,
            )
            print("Socket.IO 초기화 완료")
        except Exception as e:
            print(f"Socket.IO 초기화 실패: {e}")
            socketio = None

    # 서버 설정
    from config.services import APP_CONFIG
    from config.unified_settings import unified_settings

    host = os.environ.get("HOST_IP", unified_settings.webapp.host)
    port = int(os.environ.get("FLASK_PORT", APP_CONFIG["web_port"]))
    debug = os.environ.get("FLASK_ENV") == "development"

    print(f"🌐 서버 시작: http://{host}:{port}")
    print(f"📊 모드: {os.getenv('APP_MODE', 'production')}")
    print(f"🔒 오프라인 모드: {OFFLINE_MODE}")

    # 서버 실행
    if socketio and not DISABLE_SOCKETIO:
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=debug)


# Create app instance for import
app = create_app()

if __name__ == "__main__":
    main()

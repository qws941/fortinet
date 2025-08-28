#!/usr/bin/env python3

"""
Nextrade FortiGate - Main Application Entry Point
Clean, refactored main application using the existing app factory pattern
"""

import argparse

# 프로젝트 특정 임포트 (중복 try-except 제거)
from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient

# 공통 임포트 사용
from utils.common_imports import json, os, setup_module_logger, sys

# 분석 도구 임포트 (조건부로 사용)
try:
    from analysis.analyzer import FirewallRuleAnalyzer
    from analysis.visualizer import PathVisualizer
except ImportError:
    FirewallRuleAnalyzer = None
    PathVisualizer = None

logger = setup_module_logger("main")


def determine_target_environment() -> str:
    """CLAUDE.md v8.7.0: Determine target environment based on configuration"""
    # Check explicit environment variable
    node_env = os.getenv("NODE_ENV", "").lower()
    app_mode = os.getenv("APP_MODE", "").lower()

    # Development environment indicators
    if node_env == "development" or app_mode == "test" or os.getenv("FLASK_DEBUG", "false").lower() == "true":
        return "dev"

    # Production environment (default)
    return "prd"


def get_env_port(environment: str) -> int:
    """CLAUDE.md v8.7.0: Get port based on environment"""
    from config.services import APP_CONFIG

    if environment == "dev":
        return int(os.getenv("DEV_PORT", os.getenv("PORT", str(APP_CONFIG["web_port"]))))
    else:
        return int(os.getenv("PRD_PORT", os.getenv("PORT", str(APP_CONFIG["web_port"]))))


def is_docker_environment() -> bool:
    """Check if running in Docker container"""
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER", "false").lower() == "true"


def load_environment_config():
    """Load environment configuration from .env file"""
    from pathlib import Path

    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")


def validate_environment_consistency():
    """CLAUDE.md v8.7.0: Validate environment consistency"""
    environment = determine_target_environment()
    is_docker = is_docker_environment()

    logger.info(f"Environment validation: {environment.upper()}, Docker: {is_docker}")

    # Log configuration for debugging
    logger.info(f"NODE_ENV: {os.getenv('NODE_ENV', 'not_set')}")
    logger.info(f"APP_MODE: {os.getenv('APP_MODE', 'not_set')}")
    logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'not_set')}")
    logger.info(f"PORT: {get_env_port(environment)}")

    return environment


def parse_args():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description="FortiGate 방화벽 경로 분석 도구")
    parser.add_argument("--src", help="출발지 IP 주소/네트워크", required=False)
    parser.add_argument("--dst", help="목적지 IP 주소/네트워크", required=False)
    parser.add_argument("--port", help="포트 번호", type=int, required=False)
    parser.add_argument(
        "--protocol",
        help="프로토콜 (tcp, udp, icmp)",
        choices=["tcp", "udp", "icmp"],
        default="tcp",
        required=False,
    )
    parser.add_argument("--output", help="출력 파일 경로", required=False)
    parser.add_argument("--web", help="웹 인터페이스 시작", action="store_true")
    parser.add_argument("--host", help="FortiManager 또는 FortiGate 호스트", required=False)
    parser.add_argument("--token", help="API 토큰", required=False)
    parser.add_argument("--username", help="사용자 이름", required=False)
    parser.add_argument("--password", help="비밀번호", required=False)
    parser.add_argument("--manager", help="FortiManager 사용", action="store_true")
    parser.add_argument(
        "--log-level",
        help="로그 레벨",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )

    return parser.parse_args()


def analyze_packet_path(src_ip, dst_ip, port, protocol, api_client, manager=False):
    """패킷 경로 분석"""
    try:
        if FirewallRuleAnalyzer is None:
            logger.warning("FirewallRuleAnalyzer not available")
            return None
        analyzer = FirewallRuleAnalyzer(
            fortigate_client=None if manager else api_client,
            fortimanager_client=api_client if manager else None,
        )

        # 방화벽 데이터 로드
        if manager:
            logger.info("FortiManager를 통해 모든 방화벽 데이터 로드 중...")
            if not analyzer.load_all_firewalls():
                logger.error("방화벽 데이터 로드 실패")
                return None
        else:
            logger.info("FortiGate 데이터 로드 중...")
            if not analyzer.load_data():
                logger.error("방화벽 데이터 로드 실패")
                return None

        # 경로 분석
        logger.info(f"패킷 경로 분석 중: {src_ip} -> {dst_ip}, 포트: {port}, 프로토콜: {protocol}")
        path_data = analyzer.trace_packet_path(src_ip, dst_ip, port, protocol)

        return path_data

    except Exception as e:
        logger.error(f"패킷 경로 분석 중 오류: {str(e)}")
        return None


def visualize_path(path_data):
    """경로 시각화"""
    try:
        if PathVisualizer is None:
            logger.warning("PathVisualizer not available")
            return None
        visualizer = PathVisualizer()
        visualization_data = visualizer.generate_visualization_data(path_data)

        return visualization_data

    except Exception as e:
        logger.error(f"경로 시각화 중 오류: {str(e)}")
        return None


def save_output(data, output_path):
    """결과를 파일로 저장"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"결과가 {output_path}에 저장되었습니다.")
        return True
    except Exception as e:
        logger.error(f"결과 저장 중 오류: {str(e)}")
        return False


def main():
    """메인 함수"""
    # CLAUDE.md v8.7.0: Load environment configuration first
    load_environment_config()

    args = parse_args()

    # 로그 레벨 설정
    os.environ["LOG_LEVEL"] = args.log_level

    # Validate environment consistency
    environment = validate_environment_consistency()

    # 웹 인터페이스 시작
    if args.web:
        logger.info("웹 인터페이스 시작...")

        # Use web_app module
        from config.unified_settings import unified_settings
        from web_app import create_app

        # Create app with factory pattern
        app = create_app()

        # CLAUDE.md v8.7.0: Environment-based port configuration
        environment = determine_target_environment()
        port = get_env_port(environment)
        host = unified_settings.webapp.host
        # 보안 강화: 프로덕션에서 디버그 모드 비활성화
        debug = False
        if environment == "dev":
            debug = unified_settings.webapp.debug or args.log_level == "DEBUG"
        elif os.environ.get("FORCE_DEBUG", "false").lower() == "true":
            logger.warning("⚠️  강제 디버그 모드 활성화됨 - 프로덕션에서는 권장하지 않습니다")
            debug = True

        build_time = os.getenv("BUILD_TIME", "Development")
        logger.info(f"Starting FortiGate Nextrade in {environment.upper()} environment on port {port}")
        logger.info(f"Build: {build_time}, Docker: {is_docker_environment()}")
        logger.info(f"Project: {os.getenv('PROJECT_NAME', 'fortinet')}")

        # Check if Socket.IO is enabled
        socketio_enabled = not os.getenv("DISABLE_SOCKETIO", "false").lower() == "true"

        if socketio_enabled:
            try:
                from flask_socketio import SocketIO

                socketio = SocketIO(
                    app,
                    async_mode="threading",
                    cors_allowed_origins="*",
                    logger=debug,
                    engineio_logger=debug,
                    ping_timeout=60,
                    ping_interval=25,
                )
                logger.info("Socket.IO enabled - using socketio.run()")
                socketio.run(
                    app,
                    host=host,
                    port=port,
                    debug=debug,
                    allow_unsafe_werkzeug=True,
                )
            except ImportError:
                logger.warning("flask-socketio not available, falling back to standard Flask")
                app.run(host=host, port=port, debug=debug)
        else:
            logger.info("Socket.IO disabled - using standard Flask")
            app.run(host=host, port=port, debug=debug)
        return

    # CLI 모드에서는 필수 인수 확인
    if not all([args.src, args.dst, args.port]):
        print("오류: 출발지 IP(--src), 목적지 IP(--dst), 포트(--port)는 필수 인수입니다.")
        return 1

    # API 클라이언트 설정
    if args.manager:
        # FortiManager API 클라이언트
        api_client = FortiManagerAPIClient(
            host=args.host,
            api_token=args.token,
            username=args.username,
            password=args.password,
        )
    else:
        # FortiGate API 클라이언트
        api_client = FortiGateAPIClient(host=args.host, api_token=args.token)

    # 분석 실행
    path_data = analyze_packet_path(args.src, args.dst, args.port, args.protocol, api_client, args.manager)

    if not path_data:
        error_msg = "패킷 경로 분석 실패"
        logger.error(error_msg)

        return 1

    # 시각화 데이터 생성
    visualization_data = visualize_path(path_data)

    if not visualization_data:
        error_msg = "경로 시각화 실패"
        logger.error(error_msg)

        return 1

    # 결과 출력 또는 저장
    allowed = path_data.get("allowed", False)
    status = "허용됨" if allowed else "차단됨"
    hop_count = len(path_data.get("path", []))

    # 분석 결과 요약
    result_summary = {
        "출발지": args.src,
        "목적지": args.dst,
        "포트": args.port,
        "프로토콜": args.protocol,
        "상태": status,
        "홉 수": hop_count,
    }

    # 차단된 경우 차단 정보 추가
    if not allowed and path_data.get("blocked_by"):
        blocker = path_data["blocked_by"]
        result_summary["차단 방화벽"] = blocker.get("firewall_name", blocker.get("firewall_id"))
        result_summary["차단 정책 ID"] = blocker.get("policy_id", "N/A")

    # 분석 완료 로깅
    logger.info(f"분석 완료 - 트래픽 {status}")

    if args.output:
        if save_output(visualization_data, args.output):
            print(f"결과가 {args.output}에 저장되었습니다.")
        else:
            print("결과 저장 실패")
            return 1
    else:
        # 간단한 요약 출력
        print(f"트래픽 상태: {status}")
        print(f"홉 수: {hop_count}")

        if not allowed and path_data.get("blocked_by"):
            blocker = path_data["blocked_by"]
            print(
                f"차단 위치: 방화벽 {blocker.get('firewall_name', blocker.get('firewall_id'))}, "
                f"정책 ID: {blocker.get('policy_id', 'N/A')}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

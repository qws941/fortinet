#!/usr/bin/env python3

"""
Docker 컨테이너 로그 관리 라우트
컨테이너 로그, 애플리케이션 로그, 시스템 로그를 웹에서 조회할 수 있는 API 제공
"""

import json
import os
import select
import subprocess
import time
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request

from utils.security import csrf_protect, rate_limit

# 보안 및 유틸리티 임포트
from utils.unified_logger import get_logger

# Blueprint 생성
logs_bp = Blueprint("logs", __name__, url_prefix="/api/logs")
logger = get_logger(__name__)


def docker_available():
    """Docker 명령어 사용 가능 여부 확인"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        subprocess.SubprocessError,
    ):
        return False


def admin_required(f):
    """관리자 권한 확인 데코레이터"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Production authentication (currently bypassed for demo)
        # auth_token = request.headers.get('Authorization')
        # if not validate_admin_token(auth_token):
        #     return jsonify({'error': 'Unauthorized'}), 401

        return f(*args, **kwargs)

    return decorated_function


@logs_bp.route("/container", methods=["GET"])
@rate_limit(max_requests=30, window=60)
@csrf_protect
@admin_required
def get_container_logs():
    """Docker 컨테이너 로그 조회"""
    try:
        # 파라미터 처리
        container_name = request.args.get("container", "fortinet")
        lines = min(int(request.args.get("lines", 100)), 1000)  # 최대 1000줄
        since = request.args.get("since", "1h")  # 기본 1시간
        follow = request.args.get("follow", "false").lower() == "true"

        if not docker_available():
            return (
                jsonify(
                    {
                        "error": "Docker not available",
                        "logs": [],
                        "container": container_name,
                    }
                ),
                503,
            )

        # Docker logs 명령어 구성
        cmd = ["docker", "logs"]
        if since:
            cmd.extend(["--since", since])
        if not follow:
            cmd.extend(["--tail", str(lines)])
        cmd.append(container_name)

        # 로그 실행
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.error(f"Docker logs 실행 실패: {result.stderr}")
            return (
                jsonify(
                    {
                        "error": f"Container logs unavailable: {result.stderr}",
                        "logs": [],
                        "container": container_name,
                    }
                ),
                404,
            )

        # 로그 파싱
        log_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # 로그 구조화
        structured_logs = []
        for line in log_lines[-lines:]:  # 최근 lines개만
            if line.strip():
                # 타임스탬프 추출 시도
                timestamp = None
                if " - - [" in line:  # Flask 로그 패턴
                    try:
                        parts = line.split(" - - [")
                        if len(parts) > 1:
                            timestamp = parts[1].split("]")[0]
                    except Exception:
                        pass

                structured_logs.append(
                    {
                        "timestamp": timestamp,
                        "raw": line,
                        "level": detect_log_level(line),
                    }
                )

        return jsonify(
            {
                "container": container_name,
                "lines_requested": lines,
                "lines_returned": len(structured_logs),
                "since": since,
                "logs": structured_logs,
                "retrieved_at": datetime.now().isoformat(),
            }
        )

    except subprocess.TimeoutExpired:
        return (
            jsonify(
                {
                    "error": "Request timeout",
                    "logs": [],
                    "container": container_name,
                }
            ),
            408,
        )
    except Exception as e:
        logger.error(f"컨테이너 로그 조회 실패: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"Failed to retrieve logs: {str(e)}",
                    "logs": [],
                    "container": container_name,
                }
            ),
            500,
        )


@logs_bp.route("/application", methods=["GET"])
@rate_limit(max_requests=30, window=60)
@csrf_protect
@admin_required
def get_application_logs():
    """애플리케이션 로그 파일 조회"""
    try:
        log_type = request.args.get("type", "main")  # main, error, cache 등
        lines = min(int(request.args.get("lines", 100)), 1000)

        # 로그 파일 매핑
        log_files = {
            "main": "/app/logs/main.log",
            "error": "/app/logs/error.log",
            "cache": "/app/logs/src.utils.unified_cache_manager.log",
            "web": "/app/logs/src.web_app.log",
            "api": "/app/logs/src.routes.api_routes.log",
        }

        if log_type not in log_files:
            return (
                jsonify(
                    {
                        "error": f"Invalid log type. Available: {list(log_files.keys())}",
                        "available_types": list(log_files.keys()),
                    }
                ),
                400,
            )

        log_file_path = log_files[log_type]

        # Docker exec으로 로그 파일 읽기
        cmd = [
            "docker",
            "exec",
            "fortinet",
            "tail",
            f"-{lines}",
            log_file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return (
                jsonify(
                    {
                        "error": f"Failed to read log file: {result.stderr}",
                        "log_type": log_type,
                        "file_path": log_file_path,
                    }
                ),
                404,
            )

        # 로그 파싱
        log_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        structured_logs = []
        for line in log_lines:
            if line.strip():
                structured_logs.append(
                    {
                        "timestamp": extract_timestamp(line),
                        "raw": line,
                        "level": detect_log_level(line),
                        "module": extract_module(line),
                    }
                )

        return jsonify(
            {
                "log_type": log_type,
                "file_path": log_file_path,
                "lines_requested": lines,
                "lines_returned": len(structured_logs),
                "logs": structured_logs,
                "retrieved_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"애플리케이션 로그 조회 실패: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"Failed to retrieve application logs: {str(e)}",
                    "log_type": log_type,
                }
            ),
            500,
        )


@logs_bp.route("/files", methods=["GET"])
@rate_limit(max_requests=10, window=60)
@csrf_protect
@admin_required
def list_log_files():
    """사용 가능한 로그 파일 목록 조회"""
    try:
        cmd = [
            "docker",
            "exec",
            "fortinet",
            "find",
            "/app/logs",
            "-name",
            "*.log",
            "-type",
            "f",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return (
                jsonify({"error": "Failed to list log files", "files": []}),
                500,
            )

        log_files = []
        for file_path in result.stdout.strip().split("\n"):
            if file_path.strip():
                # 파일 크기 확인
                size_cmd = [
                    "docker",
                    "exec",
                    "fortinet",
                    "stat",
                    "-c",
                    "%s",
                    file_path,
                ]
                size_result = subprocess.run(size_cmd, capture_output=True, text=True, timeout=5)

                file_size = 0
                if size_result.returncode == 0:
                    try:
                        file_size = int(size_result.stdout.strip())
                    except ValueError:
                        pass

                log_files.append(
                    {
                        "path": file_path,
                        "name": os.path.basename(file_path),
                        "size_bytes": file_size,
                        "size_human": format_bytes(file_size),
                        "has_content": file_size > 0,
                    }
                )

        return jsonify(
            {
                "log_files": sorted(log_files, key=lambda x: x["name"]),
                "total_files": len(log_files),
                "retrieved_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"로그 파일 목록 조회 실패: {str(e)}")
        return (
            jsonify({"error": f"Failed to list log files: {str(e)}", "files": []}),
            500,
        )


@logs_bp.route("/search", methods=["POST"])
@rate_limit(max_requests=20, window=60)
@csrf_protect
@admin_required
def search_logs():
    """로그에서 특정 패턴 검색"""
    try:
        data = request.get_json()
        if not data or "pattern" not in data:
            return jsonify({"error": "Search pattern required"}), 400

        pattern = data["pattern"]
        log_type = data.get("type", "container")  # container 또는 application
        lines = min(int(data.get("lines", 100)), 500)
        case_sensitive = data.get("case_sensitive", False)

        if log_type == "container":
            # Docker logs에서 검색
            cmd = ["docker", "logs", "--tail", str(lines), "fortinet"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            content = result.stdout
        else:
            # 애플리케이션 로그 파일에서 검색
            log_file = data.get("file", "/app/logs/main.log")
            cmd = ["docker", "exec", "fortinet", "tail", f"-{lines}", log_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            content = result.stdout

        if result.returncode != 0:
            return (
                jsonify({"error": "Failed to read logs for search", "matches": []}),
                500,
            )

        # 패턴 검색
        matches = []
        lines_list = content.split("\n") if content else []

        for line_num, line in enumerate(lines_list, 1):
            if case_sensitive:
                found = pattern in line
            else:
                found = pattern.lower() in line.lower()

            if found:
                matches.append(
                    {
                        "line_number": line_num,
                        "content": line,
                        "timestamp": extract_timestamp(line),
                        "level": detect_log_level(line),
                    }
                )

        return jsonify(
            {
                "pattern": pattern,
                "log_type": log_type,
                "case_sensitive": case_sensitive,
                "total_matches": len(matches),
                "matches": matches,
                "searched_lines": len(lines_list),
                "retrieved_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"로그 검색 실패: {str(e)}")
        return (
            jsonify({"error": f"Search failed: {str(e)}", "matches": []}),
            500,
        )


@logs_bp.route("/stats", methods=["GET"])
@rate_limit(max_requests=10, window=60)
@csrf_protect
@admin_required
def get_log_stats():
    """로그 통계 정보"""
    try:
        stats = {}

        # Docker 컨테이너 상태
        if docker_available():
            cmd = [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}",
                "fortinet",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:  # 헤더 + 데이터
                    data = lines[1].split("\t")
                    if len(data) >= 4:
                        stats["container"] = {
                            "name": data[0],
                            "cpu_percent": data[1],
                            "memory_usage": data[2],
                            "memory_percent": data[3],
                        }

        # 로그 파일 통계
        log_files_cmd = [
            "docker",
            "exec",
            "fortinet",
            "find",
            "/app/logs",
            "-name",
            "*.log",
            "-exec",
            "wc",
            "-l",
            "{}",
            "+",
        ]
        result = subprocess.run(log_files_cmd, capture_output=True, text=True, timeout=15)

        log_stats = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        line_count = parts[0]
                        file_path = " ".join(parts[1:])
                        file_name = os.path.basename(file_path)
                        try:
                            log_stats[file_name] = int(line_count)
                        except ValueError:
                            pass

        stats["log_files"] = log_stats
        stats["retrieved_at"] = datetime.now().isoformat()

        return jsonify(stats)

    except Exception as e:
        logger.error(f"로그 통계 조회 실패: {str(e)}")
        return (
            jsonify({"error": f"Failed to get log stats: {str(e)}", "stats": {}}),
            500,
        )


# 헬퍼 함수들


def detect_log_level(line):
    """로그 레벨 감지"""
    line_upper = line.upper()
    if "ERROR" in line_upper or "[31m" in line:
        return "ERROR"
    elif "WARNING" in line_upper or "WARN" in line_upper or "[33m" in line:
        return "WARNING"
    elif "INFO" in line_upper or "[32m" in line:
        return "INFO"
    elif "DEBUG" in line_upper:
        return "DEBUG"
    elif "500" in line or "404" in line or "403" in line:
        return "ERROR"
    elif "200" in line or "201" in line or "308" in line:
        return "INFO"
    else:
        return "UNKNOWN"


def extract_timestamp(line):
    """로그에서 타임스탬프 추출"""
    import re

    # ISO 형식: 2025-06-26 04:49:33,376
    iso_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d{3})"
    match = re.search(iso_pattern, line)
    if match:
        return match.group(1)

    # Apache 형식: [26/Jun/2025 05:38:51]
    apache_pattern = r"\[(\d{2}/\w{3}/\d{4} \d{2}:\d{2}:\d{2})\]"
    match = re.search(apache_pattern, line)
    if match:
        return match.group(1)

    return None


def extract_module(line):
    """로그에서 모듈명 추출"""
    import re

    # Python 로거 형식: 2025-06-26 04:49:33,376 - module_name - INFO
    pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d{3} - ([^-]+) -"
    match = re.search(pattern, line)
    if match:
        return match.group(1).strip()

    return None


def format_bytes(bytes_size):
    """바이트를 인간이 읽기 쉬운 형식으로 변환"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


@logs_bp.route("/stream", methods=["GET"])
@rate_limit(max_requests=5, window=60)
@csrf_protect
@admin_required
def stream_logs():
    """실시간 로그 스트리밍 (Server-Sent Events)"""
    try:
        container_name = request.args.get("container", "fortinet")
        log_type = request.args.get("type", "container")

        def generate_log_stream():
            """로그 스트림 생성기"""
            try:
                if log_type == "container":
                    # Docker logs --follow 사용
                    cmd = [
                        "docker",
                        "logs",
                        "--follow",
                        "--tail",
                        "10",
                        container_name,
                    ]
                else:
                    # tail -f 사용
                    log_files = {
                        "main": "/app/logs/main.log",
                        "error": "/app/logs/error.log",
                        "cache": "/app/logs/src.utils.unified_cache_manager.log",
                        "web": "/app/logs/src.web_app.log",
                        "api": "/app/logs/src.routes.api_routes.log",
                    }
                    log_file = log_files.get(log_type, "/app/logs/main.log")
                    cmd = [
                        "docker",
                        "exec",
                        container_name,
                        "tail",
                        "-f",
                        log_file,
                    ]

                # 프로세스 시작
                import subprocess

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,
                )

                # SSE 헤더 전송
                yield 'data: {"type": "connected", "message": "로그 스트림 연결됨"}\n\n'

                # 타임아웃 설정
                start_time = time.time()
                timeout = 300  # 5분

                while True:
                    # 타임아웃 체크
                    if time.time() - start_time > timeout:
                        yield 'data: {"type": "timeout", "message": "스트림 타임아웃"}\n\n'
                        break

                    # 프로세스 상태 체크
                    if process.poll() is not None:
                        yield 'data: {"type": "disconnected", "message": "프로세스 종료됨"}\n\n'
                        break

                    # 출력 읽기 (논블로킹)
                    try:
                        # select를 사용한 논블로킹 읽기 (Unix/Linux만)
                        if hasattr(select, "select"):
                            ready, _, _ = select.select([process.stdout], [], [], 1.0)
                            if ready:
                                line = process.stdout.readline()
                                if line:
                                    log_data = {
                                        "type": "log",
                                        "timestamp": datetime.now().isoformat(),
                                        "content": line.strip(),
                                        "level": detect_log_level(line),
                                        "source": log_type,
                                    }
                                    yield f"data: {json.dumps(log_data)}\n\n"
                        else:
                            # Windows 호환성을 위한 폴백
                            time.sleep(1)
                            continue

                    except Exception as e:
                        logger.error(f"스트림 읽기 오류: {e}")
                        yield f'data: {{"type": "error", "message": "{str(e)}"}}\n\n'
                        break

                    # 하트비트
                    if int(time.time()) % 30 == 0:
                        yield 'data: {"type": "heartbeat"}\n\n'

                # 정리
                process.terminate()
                process.wait()

            except Exception as e:
                logger.error(f"로그 스트림 오류: {e}")
                yield f'data: {{"type": "error", "message": "{str(e)}"}}\n\n'

        from flask import current_app as app

        return app.response_class(
            generate_log_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    except Exception as e:
        logger.error(f"로그 스트리밍 시작 실패: {str(e)}")
        return (
            jsonify({"error": f"Failed to start log streaming: {str(e)}"}),
            500,
        )


@logs_bp.route("/live", methods=["GET"])
@admin_required
def live_logs_page():
    """실시간 로그 페이지"""
    return render_template("live_logs.html")


# Blueprint 등록 시 사용할 모든 라우트 목록
__all__ = ["logs_bp"]

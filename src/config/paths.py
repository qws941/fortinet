"""
File paths configuration module

모든 파일 경로 설정을 중앙화하여 관리합니다.
환경에 따라 동적으로 경로를 설정할 수 있습니다.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# 기본 디렉토리 설정 - 단일 BASE_DIR 사용
# 프로덕션 환경에서는 컨테이너 경로 사용, 개발 환경에서는 프로젝트 루트 사용
BASE_DIR = (
    "/app"
    if os.path.exists("/app")
    else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# 환경변수로 오버라이드 가능
BASE_DIR = os.getenv("APP_BASE_DIR", BASE_DIR)
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# 테스트 환경일 경우 test 디렉토리 추가
if ENVIRONMENT == "test":
    BASE_DIR = os.path.join(BASE_DIR, "test")

# 애플리케이션 경로
APP_PATHS: Dict[str, str] = {
    "base": BASE_DIR,
    "src": os.path.join(BASE_DIR, "src"),
    "data": os.path.join(BASE_DIR, "data"),
    "logs": os.path.join(BASE_DIR, "logs"),
    "config": os.path.join(BASE_DIR, "data"),
    "static": os.path.join(BASE_DIR, "src", "static"),
    "templates": os.path.join(BASE_DIR, "src", "templates"),
    "tests": os.path.join(BASE_DIR, "tests"),
    "docs": os.path.join(BASE_DIR, "docs"),
    "scripts": os.path.join(BASE_DIR, "scripts"),
    "migrations": os.path.join(BASE_DIR, "migrations"),
}

# 설정 파일 경로
CONFIG_FILES: Dict[str, str] = {
    "main": os.path.join(APP_PATHS["config"], "config.json"),
    "default": os.path.join(APP_PATHS["config"], "default_config.json"),
    "env": os.path.join(BASE_DIR, ".env"),
    "env_example": os.path.join(BASE_DIR, ".env.example"),
    "docker_compose": os.path.join(BASE_DIR, "docker-compose.yml"),
    "dockerfile": os.path.join(BASE_DIR, "Dockerfile"),
    "requirements": os.path.join(BASE_DIR, "requirements.txt"),
    "package_json": os.path.join(BASE_DIR, "package.json"),
}

# 로그 파일 경로
LOG_FILES: Dict[str, str] = {
    "app": os.path.join(APP_PATHS["logs"], "app.log"),
    "error": os.path.join(APP_PATHS["logs"], "error.log"),
    "access": os.path.join(APP_PATHS["logs"], "access.log"),
    "api": os.path.join(APP_PATHS["logs"], "api.log"),
    "security": os.path.join(APP_PATHS["logs"], "security.log"),
    "performance": os.path.join(APP_PATHS["logs"], "performance.log"),
    "audit": os.path.join(APP_PATHS["logs"], "audit.log"),
    "fortigate": os.path.join(APP_PATHS["logs"], "fortigate.log"),
    "fortimanager": os.path.join(APP_PATHS["logs"], "fortimanager.log"),
}

# 임시 파일 경로
TEMP_PATHS: Dict[str, str] = {
    "base": os.getenv("TEMP_DIR", "/tmp"),
    "upload": os.getenv("UPLOAD_DIR", "/tmp/uploads"),
    "download": os.getenv("DOWNLOAD_DIR", "/tmp/downloads"),
    "cache": os.path.join(os.getenv("TEMP_DIR", "/tmp"), "cache"),
    "sessions": os.path.join(os.getenv("TEMP_DIR", "/tmp"), "sessions"),
    "export": os.path.join(os.getenv("TEMP_DIR", "/tmp"), "export"),
    "backup": os.path.join(os.getenv("TEMP_DIR", "/tmp"), "backup"),
}

# 시스템 로그 경로 (모니터링용)
# 시스템 로그는 OS 표준 경로 사용
SYSTEM_LOG_BASE = os.getenv("SYSTEM_LOG_PATH", "/var/log")
SYSTEM_LOG_PATHS: Dict[str, str] = {
    "auth": os.path.join(SYSTEM_LOG_BASE, "auth.log"),
    "syslog": os.path.join(SYSTEM_LOG_BASE, "syslog"),
    "messages": os.path.join(SYSTEM_LOG_BASE, "messages"),
    "docker": os.path.join(SYSTEM_LOG_BASE, "docker.log"),
    "nginx_access": os.path.join(SYSTEM_LOG_BASE, "nginx", "access.log"),
    "nginx_error": os.path.join(SYSTEM_LOG_BASE, "nginx", "error.log"),
}

# 배포 관련 경로
DEPLOYMENT_PATHS: Dict[str, str] = {
    "monitor_log": os.path.join(TEMP_PATHS["base"], "deployment_monitor.log"),
    "pipeline_log": os.path.join(TEMP_PATHS["base"], "pipeline_monitor.log"),
    "deploy_script": os.path.join(BASE_DIR, "deploy.sh"),
    "docker_socket": os.getenv("DOCKER_SOCKET", "/var/run/docker.sock"),
    "pid_file": os.path.join(
        os.getenv("RUN_PATH", "/var/run"), "fortigate-nextrade.pid"
    ),
}

# 서비스별 로그 경로
SERVICE_LOG_PATHS: Dict[str, str] = {
    "fortigate": os.path.join(APP_PATHS["logs"], "service", "fortigate"),
    "fortimanager": os.path.join(APP_PATHS["logs"], "service", "fortimanager"),
    "fortianalyzer": os.path.join(APP_PATHS["logs"], "service", "fortianalyzer"),
    "mock_server": os.path.join(APP_PATHS["logs"], "service", "mock"),
}


def ensure_directory(path: str) -> str:
    """
    디렉토리가 존재하지 않으면 생성합니다.

    Args:
        path: 확인/생성할 디렉토리 경로

    Returns:
        디렉토리 경로
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_log_file_path(log_type: str) -> str:
    """
    로그 파일 경로를 반환합니다.

    Args:
        log_type: 로그 타입 (app, error, api 등)

    Returns:
        로그 파일 경로
    """
    log_dir = ensure_directory(APP_PATHS["logs"])
    return LOG_FILES.get(log_type, os.path.join(log_dir, f"{log_type}.log"))


def get_temp_file_path(filename: str, category: str = "base") -> str:
    """
    임시 파일 경로를 생성합니다.

    Args:
        filename: 파일명
        category: 카테고리 (upload, download, cache 등)

    Returns:
        임시 파일 경로
    """
    temp_dir = ensure_directory(TEMP_PATHS.get(category, TEMP_PATHS["base"]))
    return os.path.join(temp_dir, filename)


def get_enhanced_temp_file_path(
    prefix: str = "fortinet",
    suffix: str = ".tmp",
    category: str = "base",
    include_timestamp: bool = True,
    include_pid: bool = True,
) -> str:
    """
    향상된 임시 파일 경로를 생성합니다.
    타임스탬프와 프로세스 ID를 포함하여 파일명 충돌을 방지합니다.

    Args:
        prefix: 파일명 접두사 (기본: "fortinet")
        suffix: 파일 확장자 (기본: ".tmp")
        category: 카테고리 (upload, download, cache 등)
        include_timestamp: 타임스탬프 포함 여부
        include_pid: 프로세스 ID 포함 여부

    Returns:
        향상된 임시 파일 경로

    Example:
        fortinet_20250724_143052_12345.tmp
        fortinet_upload_20250724_143052_12345.json
    """
    temp_dir = ensure_directory(TEMP_PATHS.get(category, TEMP_PATHS["base"]))

    # 파일명 구성 요소
    filename_parts = [prefix]

    # 카테고리가 base가 아니면 포함
    if category != "base":
        filename_parts.append(category)

    # 타임스탬프 추가
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_parts.append(timestamp)

    # 프로세스 ID 추가
    if include_pid:
        pid = str(os.getpid())
        filename_parts.append(pid)

    # 파일명 생성 (접두사_카테고리_타임스탬프_PID.확장자)
    filename = "_".join(filename_parts) + suffix

    return os.path.join(temp_dir, filename)


def get_secure_temp_file_path(
    operation: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    file_type: str = "data",
) -> str:
    """
    보안 강화된 임시 파일 경로를 생성합니다.
    사용자 ID와 세션 ID를 포함하여 보안성을 높입니다.

    Args:
        operation: 작업명 (예: "export", "backup", "upload")
        user_id: 사용자 ID (선택사항)
        session_id: 세션 ID (선택사항)
        file_type: 파일 타입 (data, config, log 등)

    Returns:
        보안 강화된 임시 파일 경로

    Example:
        fortinet_export_data_user123_sess456_20250724_143052_12345.tmp
    """
    # 기본 prefix
    filename_parts = ["fortinet", operation, file_type]

    # 사용자 ID 추가
    if user_id:
        filename_parts.append(f"user{user_id}")

    # 세션 ID 추가 (보안을 위해 처음 8자리만)
    if session_id:
        short_session = session_id[:8] if len(session_id) > 8 else session_id
        filename_parts.append(f"sess{short_session}")

    # 타임스탬프와 PID 추가
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = str(os.getpid())
    filename_parts.extend([timestamp, pid])

    # 파일명 생성
    filename = "_".join(filename_parts) + ".tmp"

    # 적절한 카테고리 선택
    if operation in ["upload", "import"]:
        category = "upload"
    elif operation in ["export", "backup"]:
        category = "export"
    elif operation in ["cache", "session"]:
        category = "cache"
    else:
        category = "base"

    temp_dir = ensure_directory(TEMP_PATHS.get(category, TEMP_PATHS["base"]))
    return os.path.join(temp_dir, filename)


def get_config_file_path(config_type: str = "main") -> str:
    """
    설정 파일 경로를 반환합니다.

    Args:
        config_type: 설정 파일 타입

    Returns:
        설정 파일 경로
    """
    return CONFIG_FILES.get(config_type, CONFIG_FILES["main"])


def is_safe_path(path: str, base_path: Optional[str] = None) -> bool:
    """
    경로가 안전한지 확인합니다 (디렉토리 트래버설 방지).

    Args:
        path: 확인할 경로
        base_path: 기본 경로 (없으면 BASE_DIR 사용)

    Returns:
        안전한 경로 여부
    """
    if base_path is None:
        base_path = BASE_DIR

    try:
        # 절대 경로로 변환
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_path)

        # 경로가 base_path 내에 있는지 확인
        return abs_path.startswith(abs_base)
    except Exception:
        return False


# 모든 디렉토리 생성
def initialize_directories():
    """애플리케이션 시작 시 필요한 모든 디렉토리를 생성합니다."""
    for path in APP_PATHS.values():
        ensure_directory(path)

    for path in TEMP_PATHS.values():
        ensure_directory(path)

    for path in SERVICE_LOG_PATHS.values():
        ensure_directory(path)


# 모든 설정값 내보내기
__all__ = [
    "BASE_DIR",
    "ENVIRONMENT",
    "APP_PATHS",
    "CONFIG_FILES",
    "LOG_FILES",
    "TEMP_PATHS",
    "SYSTEM_LOG_PATHS",
    "DEPLOYMENT_PATHS",
    "SERVICE_LOG_PATHS",
    "ensure_directory",
    "get_log_file_path",
    "get_temp_file_path",
    "get_enhanced_temp_file_path",
    "get_secure_temp_file_path",
    "get_config_file_path",
    "is_safe_path",
    "initialize_directories",
]

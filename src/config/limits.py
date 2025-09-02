"""
Limits and constants configuration module

모든 숫자 제한, 타임아웃, 크기 제한 등의 설정을 관리합니다.
"""

import os
from typing import Any, Dict

# 디스플레이 제한
DISPLAY_LIMITS: Dict[str, int] = {
    "top_items": int(os.getenv("DISPLAY_TOP_ITEMS", "10")),
    "max_table_rows": int(os.getenv("MAX_TABLE_ROWS", "100")),
    "preview_length": int(os.getenv("PREVIEW_LENGTH", "200")),
    "truncate_length": int(os.getenv("TRUNCATE_LENGTH", "50")),
    "max_log_entries": int(os.getenv("MAX_LOG_ENTRIES", "1000")),
    "pagination_size": int(os.getenv("PAGINATION_SIZE", "20")),
    "max_search_results": 500,
    "dashboard_widgets": 6,
    "recent_items": 5,
    "notification_limit": 50,
}

# 타임아웃 설정 (초)
TIMEOUTS: Dict[str, int] = {
    "default": int(os.getenv("DEFAULT_TIMEOUT", "30")),
    "api_request": int(os.getenv("API_REQUEST_TIMEOUT", "60")),
    "health_check": int(os.getenv("HEALTH_CHECK_TIMEOUT", "5")),
    "internet_check": int(os.getenv("INTERNET_CHECK_TIMEOUT", "5")),
    "long_operation": int(os.getenv("LONG_OPERATION_TIMEOUT", "300")),
    "session": int(os.getenv("SESSION_TIMEOUT", "3600")),
    "cache_ttl": int(os.getenv("CACHE_TTL", "300")),
    "connection": 10,
    "read": 30,
    "write": 30,
    "websocket": 300,
    "file_upload": 600,
    "backup_operation": 1800,
}

# 크기 제한 (바이트)
SIZE_LIMITS: Dict[str, int] = {
    "max_file_size": int(os.getenv("MAX_FILE_SIZE", "104857600")),  # 100MB
    "max_upload_size": int(os.getenv("MAX_UPLOAD_SIZE", "52428800")),  # 50MB
    "max_payload_size": int(os.getenv("MAX_PAYLOAD_SIZE", "10485760")),  # 10MB
    "max_log_file_size": int(os.getenv("MAX_LOG_FILE_SIZE", "1073741824")),  # 1GB
    "buffer_size": int(os.getenv("BUFFER_SIZE", "8192")),  # 8KB
    "chunk_size": int(os.getenv("CHUNK_SIZE", "4096")),  # 4KB
    "max_json_size": 5242880,  # 5MB
    "max_csv_rows": 1000000,
    "max_export_size": 209715200,  # 200MB
    "max_import_size": 104857600,  # 100MB
    "max_backup_size": 5368709120,  # 5GB
}

# 암호화 관련 설정
CRYPTO_LIMITS: Dict[str, int] = {
    "hash_truncate_length": int(os.getenv("HASH_TRUNCATE_LENGTH", "16")),
    "token_length": int(os.getenv("TOKEN_LENGTH", "32")),
    "session_id_length": int(os.getenv("SESSION_ID_LENGTH", "8")),
    "password_min_length": int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
    "salt_length": int(os.getenv("SALT_LENGTH", "16")),
    "api_key_length": 40,
    "otp_length": 6,
    "recovery_code_length": 12,
    "encryption_key_bits": 256,
    "rsa_key_bits": 2048,
}

# 성능 관련 설정
PERFORMANCE_LIMITS: Dict[str, int] = {
    "max_concurrent_connections": int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "1000")),
    "max_queue_size": int(os.getenv("MAX_QUEUE_SIZE", "10000")),
    "batch_size": int(os.getenv("BATCH_SIZE", "100")),
    "worker_threads": int(os.getenv("WORKER_THREADS", "4")),
    "connection_pool_size": int(os.getenv("CONNECTION_POOL_SIZE", "10")),
    "max_retry_attempts": 3,
    "rate_limit_requests": 100,
    "rate_limit_window": 60,  # seconds
    "cache_max_entries": 10000,
    "db_connection_pool": 20,
}

# 모니터링 임계값
MONITORING_THRESHOLDS: Dict[str, float] = {
    "cpu_warning": float(os.getenv("ALERT_THRESHOLD_CPU", "80.0")),
    "memory_warning": float(os.getenv("ALERT_THRESHOLD_MEMORY", "85.0")),
    "disk_warning": float(os.getenv("ALERT_THRESHOLD_DISK", "90.0")),
    "cpu_critical": 95.0,
    "memory_critical": 95.0,
    "disk_critical": 98.0,
    "response_time_warning": 1.0,  # seconds
    "response_time_critical": 5.0,  # seconds
    "error_rate_warning": 5.0,  # percent
    "error_rate_critical": 10.0,  # percent
}

# 비즈니스 규칙
BUSINESS_RULES: Dict[str, Any] = {
    "business_hours_start": os.getenv("BUSINESS_HOURS_START", "09:00"),
    "business_hours_end": os.getenv("BUSINESS_HOURS_END", "18:00"),
    "business_timezone": os.getenv("BUSINESS_TIMEZONE", "Asia/Seoul"),
    "retention_days": int(os.getenv("METRICS_RETENTION_DAYS", "30")),
    "backup_retention_days": 90,
    "log_retention_days": 180,
    "audit_retention_days": 365,
    "session_idle_minutes": 30,
    "password_expiry_days": 90,
    "max_failed_login_attempts": 5,
    "lockout_duration_minutes": 30,
}

# 재시도 설정
RETRY_CONFIG: Dict[str, Any] = {
    "max_retries": int(os.getenv("MAX_RETRIES", "3")),
    "retry_delay": int(os.getenv("RETRY_DELAY", "1")),
    "retry_backoff_factor": float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0")),
    "max_retry_delay": int(os.getenv("MAX_RETRY_DELAY", "60")),
    "retry_on_status_codes": [429, 500, 502, 503, 504],
    "retry_on_exceptions": ["ConnectionError", "Timeout", "RequestException"],
}

# 배열 슬라이싱 제한
ARRAY_LIMITS: Dict[str, int] = {
    "max_array_display": 100,
    "truncate_small": 5,
    "truncate_medium": 10,
    "truncate_large": 20,
    "max_nested_depth": 10,
    "max_json_depth": 20,
}

# 메트릭 제한
METRICS_LIMITS: Dict[str, int] = {
    "max_metrics_per_request": int(os.getenv("MAX_METRICS_PER_REQUEST", "1000")),
    "metrics_buffer_size": 10000,
    "metrics_flush_interval": 60,  # seconds
    "histogram_buckets": 10,
    "percentile_precision": 2,
}


def get_display_limit(limit_type: str) -> int:
    """
    디스플레이 제한값을 반환합니다.

    Args:
        limit_type: 제한 타입

    Returns:
        제한값
    """
    return DISPLAY_LIMITS.get(limit_type, 10)


def get_timeout(timeout_type: str) -> int:
    """
    타임아웃 값을 반환합니다.

    Args:
        timeout_type: 타임아웃 타입

    Returns:
        타임아웃 값 (초)
    """
    return TIMEOUTS.get(timeout_type, TIMEOUTS["default"])


def get_size_limit(limit_type: str) -> int:
    """
    크기 제한값을 반환합니다.

    Args:
        limit_type: 제한 타입

    Returns:
        크기 제한 (바이트)
    """
    return SIZE_LIMITS.get(limit_type, 0)


def format_bytes(bytes_value: float) -> str:
    """
    바이트 값을 사람이 읽기 쉬운 형식으로 변환합니다.

    Args:
        bytes_value: 바이트 값

    Returns:
        포맷된 문자열 (예: "10.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def is_within_limit(
    value: int, limit_type: str, limit_category: str = "SIZE_LIMITS"
) -> bool:
    """
    값이 제한 내에 있는지 확인합니다.

    Args:
        value: 확인할 값
        limit_type: 제한 타입
        limit_category: 제한 카테고리

    Returns:
        제한 내 여부
    """
    limits = globals().get(limit_category, {})
    limit = limits.get(limit_type, float("inf"))
    return value <= limit


# 모든 설정값 내보내기
__all__ = [
    "DISPLAY_LIMITS",
    "TIMEOUTS",
    "SIZE_LIMITS",
    "CRYPTO_LIMITS",
    "PERFORMANCE_LIMITS",
    "MONITORING_THRESHOLDS",
    "BUSINESS_RULES",
    "RETRY_CONFIG",
    "ARRAY_LIMITS",
    "METRICS_LIMITS",
    "get_display_limit",
    "get_timeout",
    "get_size_limit",
    "format_bytes",
    "is_within_limit",
]

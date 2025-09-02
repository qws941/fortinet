#!/usr/bin/env python3
"""
대시보드 기본 설정 및 하드코딩 값 관리
"""

import os
from typing import Any, Dict, List

# 통계 카드 기본값
DEFAULT_STATS = {
    "total_devices": int(os.getenv("DEFAULT_TOTAL_DEVICES", "48")),
    "uptime_percentage": float(os.getenv("DEFAULT_UPTIME_PERCENTAGE", "99.8")),
    "network_traffic": os.getenv("DEFAULT_NETWORK_TRAFFIC", "2.4 Gbps"),
    "active_alerts": int(os.getenv("DEFAULT_ACTIVE_ALERTS", "3")),
    "trend_device_increase": int(os.getenv("DEFAULT_TREND_DEVICE_INCREASE", "12")),
    "trend_uptime_increase": float(os.getenv("DEFAULT_TREND_UPTIME_INCREASE", "0.2")),
    "trend_traffic_decrease": int(os.getenv("DEFAULT_TREND_TRAFFIC_DECREASE", "8")),
}

# 차트 설정
CHART_CONFIG = {
    "performance_chart": {
        "hours_display": int(os.getenv("CHART_HOURS_DISPLAY", "24")),
        "inbound_color": os.getenv("CHART_INBOUND_COLOR", "#22c55e"),
        "outbound_color": os.getenv("CHART_OUTBOUND_COLOR", "#3b82f6"),
        "grid_color": os.getenv("CHART_GRID_COLOR", "rgba(148, 163, 184, 0.1)"),
        "text_color": os.getenv("CHART_TEXT_COLOR", "#94a3b8"),
    }
}

# CDN 및 외부 리소스
EXTERNAL_RESOURCES = {
    "chartjs_cdn": os.getenv(
        "CHARTJS_CDN_URL", "https://cdn.jsdelivr.net/npm/chart.js"
    ),
    "socketio_cdn": os.getenv(
        "SOCKETIO_CDN_URL", "https://cdn.socket.io/4.5.4/socket.io.min.js"
    ),
    "fallback_enabled": os.getenv("CDN_FALLBACK_ENABLED", "true").lower() == "true",
}

# 알림 템플릿
ALERT_TEMPLATES = [
    {
        "type": "critical",
        "icon": "exclamation-circle",
        "color": os.getenv("ALERT_CRITICAL_COLOR", "var(--danger)"),
        "title_template": os.getenv("ALERT_CRITICAL_TITLE", "높은 CPU 사용률"),
        "description_template": os.getenv(
            "ALERT_CRITICAL_DESC",
            "{device}에서 CPU 사용률이 {threshold}%를 초과했습니다.",
        ),
        "threshold": int(os.getenv("CPU_CRITICAL_THRESHOLD", "85")),
    },
    {
        "type": "warning",
        "icon": "exclamation-triangle",
        "color": os.getenv("ALERT_WARNING_COLOR", "var(--warning)"),
        "title_template": os.getenv("ALERT_WARNING_TITLE", "메모리 사용량 경고"),
        "description_template": os.getenv(
            "ALERT_WARNING_DESC",
            "{device}에서 메모리 사용률이 {threshold}%를 초과했습니다.",
        ),
        "threshold": int(os.getenv("MEMORY_WARNING_THRESHOLD", "75")),
    },
    {
        "type": "info",
        "icon": "info-circle",
        "color": os.getenv("ALERT_INFO_COLOR", "var(--info)"),
        "title_template": os.getenv("ALERT_INFO_TITLE", "장치 연결 해제"),
        "description_template": os.getenv(
            "ALERT_INFO_DESC", "{device}가 네트워크에서 연결 해제되었습니다."
        ),
    },
]

# 장치 목록 설정
DEVICE_LIST_CONFIG = {
    "top_devices_limit": int(os.getenv("TOP_DEVICES_LIMIT", "5")),
    "bandwidth_display_unit": os.getenv("BANDWIDTH_DISPLAY_UNIT", "Mbps"),
    "trend_calculation_enabled": os.getenv("DEVICE_TREND_ENABLED", "true").lower()
    == "true",
    "trend_max_percentage": int(os.getenv("DEVICE_TREND_MAX_PCT", "20")),
}

# 보안 이벤트 설정
SECURITY_EVENTS_CONFIG = {
    "max_events_display": int(os.getenv("MAX_SECURITY_EVENTS", "10")),
    "event_retention_hours": int(os.getenv("SECURITY_EVENT_RETENTION_HOURS", "24")),
    "severity_colors": {
        "critical": os.getenv("SEVERITY_CRITICAL_COLOR", "#FF6B6B"),
        "high": os.getenv("SEVERITY_HIGH_COLOR", "#FF8E53"),
        "medium": os.getenv("SEVERITY_MEDIUM_COLOR", "#FF6B35"),
        "low": os.getenv("SEVERITY_LOW_COLOR", "#4ECDC4"),
    },
}

# 대시보드 새로고침 설정
REFRESH_CONFIG = {
    "auto_refresh_enabled": os.getenv("DASHBOARD_AUTO_REFRESH", "true").lower()
    == "true",
    "refresh_interval_seconds": int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "30")),
    "chart_update_interval": int(os.getenv("CHART_UPDATE_INTERVAL", "60")),
    "stats_update_interval": int(os.getenv("STATS_UPDATE_INTERVAL", "15")),
}

# 퀵 액션 버튼 설정
QUICK_ACTIONS_CONFIG = {
    "traffic_analysis_enabled": os.getenv(
        "QUICK_ACTION_TRAFFIC_ANALYSIS", "true"
    ).lower()
    == "true",
    "policy_optimization_enabled": os.getenv("QUICK_ACTION_POLICY_OPT", "true").lower()
    == "true",
    "report_generation_enabled": os.getenv("QUICK_ACTION_REPORT_GEN", "true").lower()
    == "true",
    "security_diagnostics_enabled": os.getenv(
        "QUICK_ACTION_SECURITY_DIAG", "true"
    ).lower()
    == "true",
}


def get_dashboard_config() -> Dict[str, Any]:
    """대시보드 전체 설정 반환"""
    return {
        "stats": DEFAULT_STATS,
        "chart": CHART_CONFIG,
        "external_resources": EXTERNAL_RESOURCES,
        "alert_templates": ALERT_TEMPLATES,
        "device_list": DEVICE_LIST_CONFIG,
        "security_events": SECURITY_EVENTS_CONFIG,
        "refresh": REFRESH_CONFIG,
        "quick_actions": QUICK_ACTIONS_CONFIG,
    }


def get_alert_template(alert_type: str) -> Dict[str, Any]:
    """특정 알림 타입의 템플릿 반환"""
    for template in ALERT_TEMPLATES:
        if template["type"] == alert_type:
            return template
    return ALERT_TEMPLATES[0]  # 기본값으로 첫 번째 반환


def generate_mock_alerts(count: int = 3) -> List[Dict[str, Any]]:
    """모의 알림 데이터 생성"""
    import random

    alerts = []
    devices = [
        "FIREWALL-09",
        "SWITCH-11",
        "WORKSTATION-14",
        "SERVER-03",
        "ROUTER-07",
        "AP-22",
    ]

    for i in range(count):
        template = random.choice(ALERT_TEMPLATES)
        device = random.choice(devices)

        # 시간을 무작위로 생성 (최근 2시간 내)
        time_ago = random.randint(5, 120)
        time_str = f"{time_ago}분 전" if time_ago < 60 else f"{time_ago // 60}시간 전"

        alert = {
            "type": template["type"],
            "icon": template["icon"],
            "color": template["color"],
            "title": template["title_template"],
            "description": template["description_template"].format(
                device=device, threshold=template.get("threshold", 75)
            ),
            "time": time_str,
            "device": device,
            "severity": template["type"],
        }
        alerts.append(alert)

    return alerts


def get_chart_data_points(hours: int = 24) -> Dict[str, List]:
    """차트 데이터 포인트 생성"""
    import random

    labels = [f"{i}:00" for i in range(hours)]

    return {
        "labels": labels,
        "inbound_data": [round(random.random() * 3 + 1, 2) for _ in range(hours)],
        "outbound_data": [round(random.random() * 2 + 0.5, 2) for _ in range(hours)],
    }

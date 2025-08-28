#!/usr/bin/env python3
"""
장치 관리 페이지 기본 설정 및 하드코딩 값 관리
"""

import os
from typing import Any, Dict, List

# 장치 타입 아이콘 매핑
DEVICE_TYPE_ICONS = {
    "firewall": {
        "icon": "fas fa-shield-alt",
        "class": "firewall",
        "display_name": os.getenv("DEVICE_TYPE_FIREWALL_NAME", "방화벽"),
    },
    "router": {
        "icon": "fas fa-route",
        "class": "router",
        "display_name": os.getenv("DEVICE_TYPE_ROUTER_NAME", "라우터"),
    },
    "switch": {
        "icon": "fas fa-network-wired",
        "class": "switch",
        "display_name": os.getenv("DEVICE_TYPE_SWITCH_NAME", "스위치"),
    },
    "client": {
        "icon": "fas fa-desktop",
        "class": "client",
        "display_name": os.getenv("DEVICE_TYPE_CLIENT_NAME", "클라이언트"),
    },
    "server": {
        "icon": "fas fa-server",
        "class": "server",
        "display_name": os.getenv("DEVICE_TYPE_SERVER_NAME", "서버"),
    },
    "workstation": {
        "icon": "fas fa-laptop",
        "class": "client",
        "display_name": os.getenv("DEVICE_TYPE_WORKSTATION_NAME", "워크스테이션"),
    },
}

# 상태 배지 설정
STATUS_BADGES = {
    "online": {
        "class": "status-badge-success",
        "display": os.getenv("STATUS_ONLINE_TEXT", "온라인"),
        "color": os.getenv("STATUS_ONLINE_COLOR", "#28a745"),
    },
    "offline": {
        "class": "status-badge-danger",
        "display": os.getenv("STATUS_OFFLINE_TEXT", "오프라인"),
        "color": os.getenv("STATUS_OFFLINE_COLOR", "#dc3545"),
    },
    "unknown": {
        "class": "status-badge-warning",
        "display": os.getenv("STATUS_UNKNOWN_TEXT", "알 수 없음"),
        "color": os.getenv("STATUS_UNKNOWN_COLOR", "#ffc107"),
    },
    "maintenance": {
        "class": "status-badge-info",
        "display": os.getenv("STATUS_MAINTENANCE_TEXT", "점검중"),
        "color": os.getenv("STATUS_MAINTENANCE_COLOR", "#17a2b8"),
    },
}

# DataTables 언어 설정
DATATABLE_LANGUAGE = {
    "search": os.getenv("DATATABLE_SEARCH_TEXT", "검색:"),
    "lengthMenu": os.getenv("DATATABLE_LENGTH_MENU", "_MENU_ 개씩 보기"),
    "info": os.getenv("DATATABLE_INFO_TEXT", "_TOTAL_ 개 중 _START_ - _END_ 표시"),
    "infoEmpty": os.getenv("DATATABLE_INFO_EMPTY", "표시할 데이터가 없습니다"),
    "infoFiltered": os.getenv("DATATABLE_INFO_FILTERED", "(총 _MAX_ 개 중 필터링됨)"),
    "paginate": {
        "first": os.getenv("DATATABLE_FIRST_TEXT", "처음"),
        "last": os.getenv("DATATABLE_LAST_TEXT", "마지막"),
        "next": os.getenv("DATATABLE_NEXT_TEXT", "다음"),
        "previous": os.getenv("DATATABLE_PREVIOUS_TEXT", "이전"),
    },
}

# 장치 필터 설정
DEVICE_FILTERS = [
    {
        "key": "all",
        "label": os.getenv("FILTER_ALL_TEXT", "모든 장치"),
        "active": True,
    },
    {
        "key": "firewall",
        "label": os.getenv("FILTER_FIREWALL_TEXT", "방화벽"),
        "active": False,
    },
    {
        "key": "router",
        "label": os.getenv("FILTER_ROUTER_TEXT", "라우터"),
        "active": False,
    },
    {
        "key": "switch",
        "label": os.getenv("FILTER_SWITCH_TEXT", "스위치"),
        "active": False,
    },
    {
        "key": "client",
        "label": os.getenv("FILTER_CLIENT_TEXT", "클라이언트"),
        "active": False,
    },
    {
        "key": "server",
        "label": os.getenv("FILTER_SERVER_TEXT", "서버"),
        "active": False,
    },
]

# 테이블 컬럼 설정
TABLE_COLUMNS = {
    "type": {
        "header": os.getenv("COLUMN_TYPE_HEADER", "유형"),
        "class": "table-col-xs",
        "sortable": True,
    },
    "name": {
        "header": os.getenv("COLUMN_NAME_HEADER", "장치 이름"),
        "class": "table-col-md",
        "sortable": True,
    },
    "ip": {
        "header": os.getenv("COLUMN_IP_HEADER", "IP 주소"),
        "class": "table-col-sm",
        "sortable": True,
    },
    "mac": {
        "header": os.getenv("COLUMN_MAC_HEADER", "MAC 주소"),
        "class": "table-col-sm",
        "sortable": False,
    },
    "status": {
        "header": os.getenv("COLUMN_STATUS_HEADER", "상태"),
        "class": "table-col-xs",
        "sortable": True,
    },
    "zone": {
        "header": os.getenv("COLUMN_ZONE_HEADER", "Zone"),
        "class": "table-col-xs",
        "sortable": True,
    },
    "last_seen": {
        "header": os.getenv("COLUMN_LAST_SEEN_HEADER", "마지막 활동"),
        "class": "table-col-sm",
        "sortable": True,
    },
    "actions": {
        "header": os.getenv("COLUMN_ACTIONS_HEADER", "액션"),
        "class": "table-col-xs",
        "sortable": False,
    },
}

# 모달 설정
MODAL_CONFIG = {
    "title": os.getenv("MODAL_DEVICE_DETAILS_TITLE", "장치 상세 정보"),
    "loading_message": os.getenv("MODAL_LOADING_MESSAGE", "장치 정보를 불러오는 중입니다..."),
    "error_message": os.getenv("MODAL_ERROR_MESSAGE", "장치 정보를 가져오는데 실패했습니다"),
    "no_interfaces_message": os.getenv("MODAL_NO_INTERFACES", "인터페이스 정보가 없습니다."),
    "no_policies_message": os.getenv("MODAL_NO_POLICIES", "정책 정보가 없습니다."),
    "test_data_suffix": os.getenv("MODAL_TEST_DATA_SUFFIX", " (테스트 데이터)"),
}

# 버튼 텍스트
BUTTON_TEXTS = {
    "refresh": os.getenv("BUTTON_REFRESH_TEXT", "새로고침"),
    "refreshing": os.getenv("BUTTON_REFRESHING_TEXT", "새로고침 중..."),
    "view_details": os.getenv("BUTTON_VIEW_DETAILS_TEXT", "상세"),
    "close": os.getenv("BUTTON_CLOSE_TEXT", "닫기"),
    "analyze_path": os.getenv("BUTTON_ANALYZE_PATH_TEXT", "경로 분석"),
    "packet_sniffer": os.getenv("BUTTON_PACKET_SNIFFER_TEXT", "패킷 스니퍼 실행"),
}

# 검색 및 필터 설정
SEARCH_CONFIG = {
    "placeholder": os.getenv("SEARCH_PLACEHOLDER_TEXT", "장치 검색 (이름, IP, MAC 등)"),
    "debounce_delay": int(os.getenv("SEARCH_DEBOUNCE_DELAY", "300")),  # 밀리초
    "min_search_length": int(os.getenv("SEARCH_MIN_LENGTH", "1")),
}

# 테스트 모드 설정
TEST_MODE_CONFIG = {
    "banner_message": os.getenv(
        "TEST_MODE_BANNER_MESSAGE",
        "현재 테스트 모드로 실행 중입니다. 실제 장비 연결 시 이 메시지가 사라집니다.",
    ),
    "badge_text": os.getenv("TEST_MODE_BADGE_TEXT", "테스트"),
    "device_suffix": os.getenv("TEST_MODE_DEVICE_SUFFIX", " (테스트 데이터)"),
}

# API 엔드포인트 설정
API_ENDPOINTS = {
    "devices_list": os.getenv("API_DEVICES_LIST_ENDPOINT", "/api/devices"),
    "device_detail": os.getenv("API_DEVICE_DETAIL_ENDPOINT", "/api/device/"),
    "refresh_timeout": int(os.getenv("API_REFRESH_TIMEOUT", "10000")),  # 밀리초
}

# 성능 설정
PERFORMANCE_CONFIG = {
    "datatable_page_length": int(os.getenv("DATATABLE_PAGE_LENGTH", "25")),
    "auto_refresh_interval": int(os.getenv("DEVICE_AUTO_REFRESH_INTERVAL", "60000")),  # 밀리초
    "auto_refresh_enabled": os.getenv("DEVICE_AUTO_REFRESH_ENABLED", "false").lower() == "true",
}


def get_device_config() -> Dict[str, Any]:
    """장치 관리 페이지 전체 설정 반환"""
    return {
        "device_types": DEVICE_TYPE_ICONS,
        "status_badges": STATUS_BADGES,
        "datatable_language": DATATABLE_LANGUAGE,
        "device_filters": DEVICE_FILTERS,
        "table_columns": TABLE_COLUMNS,
        "modal": MODAL_CONFIG,
        "buttons": BUTTON_TEXTS,
        "search": SEARCH_CONFIG,
        "test_mode": TEST_MODE_CONFIG,
        "api_endpoints": API_ENDPOINTS,
        "performance": PERFORMANCE_CONFIG,
    }


def get_device_type_icon(device_type: str) -> Dict[str, str]:
    """장치 타입에 따른 아이콘 정보 반환"""
    return DEVICE_TYPE_ICONS.get(
        device_type,
        {
            "icon": "fas fa-question-circle",
            "class": "unknown",
            "display_name": "알 수 없음",
        },
    )


def get_status_badge(status: str) -> Dict[str, str]:
    """상태에 따른 배지 정보 반환"""
    return STATUS_BADGES.get(status, STATUS_BADGES["unknown"])


def generate_device_table_html(devices: List[Dict[str, Any]]) -> str:
    """장치 목록 테이블 HTML 생성"""
    if not devices:
        return '<tr><td colspan="8" style="text-align: center;">장치가 없습니다.</td></tr>'

    html_rows = []
    for device in devices:
        device_type = get_device_type_icon(device.get("type", "unknown"))
        status_badge = get_status_badge(device.get("status", "unknown"))

        html_rows.append(
            f"""
            <tr>
                <td><span class="device-type-badge {device_type['class']}">
                    <i class="{device_type['icon']}"></i></span></td>
                <td class="truncate">{device.get('name', 'Unknown')}</td>
                <td class="device-ip">{device.get('ip', 'N/A')}</td>
                <td class="device-mac">{device.get('mac', 'N/A')}</td>
                <td><span class="status-badge {status_badge['class']}">{status_badge['display']}</span></td>
                <td class="truncate">{device.get('zone', 'N/A')}</td>
                <td>{device.get('last_seen', 'N/A')}</td>
                <td><button class="btn-action btn-view view-device" data-device-id="{device.get('id', '')}">
                    <i class="fas fa-eye"></i> {BUTTON_TEXTS['view_details']}</button></td>
            </tr>
        """
        )

    return "".join(html_rows)

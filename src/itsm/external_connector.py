#!/usr/bin/env python3

"""
외부 ITSM 시스템 연동 모듈
외부 ITSM에서 방화벽 정책 요청을 자동으로 수집하고 처리
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

import requests

# Optional async HTTP library
try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ITSMPlatform(Enum):
    """지원하는 ITSM 플랫폼"""

    SERVICENOW = "servicenow"
    JIRA_SERVICE_MANAGEMENT = "jira"
    NEXTRADE_ITSM = "nextrade"
    REMEDY = "remedy"
    CHERWELL = "cherwell"
    CUSTOM_API = "custom"


@dataclass
class FirewallPolicyRequest:
    """방화벽 정책 요청 데이터 구조"""

    ticket_id: str
    source_ip: str
    destination_ip: str
    port: Union[int, List[int]]
    protocol: str
    action: str = "allow"
    description: str = ""
    business_justification: str = ""
    requester: str = ""
    created_at: datetime = None
    priority: str = "normal"
    category: str = "firewall_access"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ITSMConfig:
    """ITSM 연동 설정"""

    platform: ITSMPlatform
    base_url: str
    username: str
    password: str = None
    api_token: str = None
    client_id: str = None
    client_secret: str = None
    custom_headers: Dict[str, str] = None
    poll_interval: int = 300  # 5분마다 폴링

    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


class ExternalITSMConnector:
    """외부 ITSM 시스템 연동 클래스"""

    def __init__(self, config: ITSMConfig):
        """
        외부 ITSM 연동 초기화

        Args:
            config (ITSMConfig): ITSM 연동 설정
        """
        self.config = config
        self.session = requests.Session()
        self.is_connected = False
        self.last_sync_time = None

        # 플랫폼별 API 엔드포인트 매핑
        self.endpoint_mapping = {
            ITSMPlatform.SERVICENOW: {
                "tickets": "/api/now/table/incident",
                "auth_type": "basic",
            },
            ITSMPlatform.JIRA_SERVICE_MANAGEMENT: {
                "tickets": "/rest/api/2/search",
                "auth_type": "token",
            },
            ITSMPlatform.NEXTRADE_ITSM: {
                "tickets": "/api/tickets",
                "auth_type": "custom",
            },
        }

        # 방화벽 정책 요청 키워드 패턴
        self.firewall_patterns = [
            r"방화벽\s*(정책|오픈|허용|차단)",
            r"firewall\s*(policy|open|allow|block)",
            r"포트\s*(오픈|허용|개방)",
            r"port\s*(open|allow|access)",
            r"접속\s*(허용|요청)",
            r"access\s*(request|allow)",
            r"VPN\s*(접속|연결)",
            r"인바운드|아웃바운드",
            r"inbound|outbound",
        ]

        self._setup_authentication()

    def _setup_authentication(self):
        """인증 설정"""
        platform = self.config.platform

        if platform == ITSMPlatform.SERVICENOW:
            # ServiceNow Basic Auth
            self.session.auth = (self.config.username, self.config.password)

        elif platform == ITSMPlatform.JIRA_SERVICE_MANAGEMENT:
            # Jira API Token
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.config.api_token}",
                    "Content-Type": "application/json",
                }
            )

        elif platform == ITSMPlatform.NEXTRADE_ITSM:
            # Nextrade ITSM Custom Auth
            self.session.headers.update(
                {
                    "X-API-Key": self.config.api_token,
                    "Content-Type": "application/json",
                }
            )

        # 공통 헤더 추가
        self.session.headers.update(self.config.custom_headers)

        logger.info(f"Authentication setup completed for {platform.value}")

    async def connect(self) -> bool:
        """ITSM 시스템 연결 테스트"""
        try:
            test_url = f"{self.config.base_url}/api/health"
            response = self.session.get(test_url, timeout=10)

            if response.status_code == 200:
                self.is_connected = True
                logger.info(f"Successfully connected to {self.config.platform.value}")
                return True
            else:
                logger.error(f"Connection failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def fetch_firewall_requests(self, since: datetime = None) -> List[FirewallPolicyRequest]:
        """
        방화벽 정책 요청 티켓 수집

        Args:
            since (datetime): 이 시간 이후의 티켓만 가져오기

        Returns:
            List[FirewallPolicyRequest]: 방화벽 정책 요청 목록
        """
        if not self.is_connected:
            await self.connect()

        if since is None:
            since = datetime.now() - timedelta(hours=24)

        try:
            platform = self.config.platform
            tickets = await self._fetch_tickets_by_platform(platform, since)
            firewall_requests = []

            for ticket in tickets:
                if self._is_firewall_request(ticket):
                    request = self._parse_firewall_request(ticket)
                    if request:
                        firewall_requests.append(request)

            logger.info(f"Fetched {len(firewall_requests)} firewall policy requests")
            return firewall_requests

        except Exception as e:
            logger.error(f"Error fetching firewall requests: {e}")
            return []

    async def _fetch_tickets_by_platform(self, platform: ITSMPlatform, since: datetime) -> List[Dict]:
        """플랫폼별 티켓 조회"""
        endpoints = self.endpoint_mapping.get(platform, {})
        endpoint = endpoints.get("tickets", "/api/tickets")

        if platform == ITSMPlatform.SERVICENOW:
            return await self._fetch_servicenow_tickets(endpoint, since)
        elif platform == ITSMPlatform.JIRA_SERVICE_MANAGEMENT:
            return await self._fetch_jira_tickets(endpoint, since)
        elif platform == ITSMPlatform.NEXTRADE_ITSM:
            return await self._fetch_nextrade_tickets(endpoint, since)
        else:
            return await self._fetch_custom_tickets(endpoint, since)

    async def _fetch_servicenow_tickets(self, endpoint: str, since: datetime) -> List[Dict]:
        """ServiceNow 티켓 조회"""
        url = f"{self.config.base_url}{endpoint}"

        params = {
            "sysparm_query": f'opened_at>{since.strftime("%Y-%m-%d %H:%M:%S")}',
            "sysparm_fields": "number,short_description,description,state,priority,opened_at,sys_created_on",
            "sysparm_limit": 1000,
        }

        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            logger.error(f"ServiceNow API error: {response.status_code}")
            return []

    async def _fetch_jira_tickets(self, endpoint: str, since: datetime) -> List[Dict]:
        """Jira Service Management 티켓 조회"""
        url = f"{self.config.base_url}{endpoint}"

        jql = (
            f'project = "IT" AND created >= "{since.strftime("%Y-%m-%d")}" AND '
            '(summary ~ "firewall" OR description ~ "firewall" OR '
            'summary ~ "방화벽" OR description ~ "방화벽")'
        )

        params = {
            "jql": jql,
            "fields": "summary,description,status,priority,created,reporter",
            "maxResults": 1000,
        }

        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("issues", [])
        else:
            logger.error(f"Jira API error: {response.status_code}")
            return []

    async def _fetch_nextrade_tickets(self, endpoint: str, since: datetime) -> List[Dict]:
        """Nextrade ITSM 티켓 조회"""
        url = f"{self.config.base_url}{endpoint}"

        params = {
            "since": since.isoformat(),
            "category": "network,security,firewall",
            "status": "new,in_progress,pending",
            "limit": 1000,
        }

        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("tickets", [])
        else:
            logger.error(f"Nextrade ITSM API error: {response.status_code}")
            return []

    async def _fetch_custom_tickets(self, endpoint: str, since: datetime) -> List[Dict]:
        """커스텀 API 티켓 조회"""
        url = f"{self.config.base_url}{endpoint}"

        params = {
            "created_after": since.isoformat(),
            "keywords": "firewall,방화벽,port,포트,access,접속",
        }

        response = self.session.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Custom API error: {response.status_code}")
            return []

    def _is_firewall_request(self, ticket: Dict) -> bool:
        """티켓이 방화벽 정책 요청인지 판단"""
        content = ""

        # 플랫폼별로 내용 추출
        if self.config.platform == ITSMPlatform.SERVICENOW:
            content = f"{ticket.get('short_description', '')} {ticket.get('description', '')}"
        elif self.config.platform == ITSMPlatform.JIRA_SERVICE_MANAGEMENT:
            fields = ticket.get("fields", {})
            content = f"{fields.get('summary', '')} {fields.get('description', '')}"
        elif self.config.platform == ITSMPlatform.NEXTRADE_ITSM:
            content = f"{ticket.get('title', '')} {ticket.get('description', '')}"

        content = content.lower()

        # 방화벽 관련 키워드 매칭
        for pattern in self.firewall_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False

    def _parse_firewall_request(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """티켓에서 방화벽 정책 요청 정보 추출"""
        try:
            # 플랫폼별 데이터 추출
            if self.config.platform == ITSMPlatform.SERVICENOW:
                return self._parse_servicenow_ticket(ticket)
            elif self.config.platform == ITSMPlatform.JIRA_SERVICE_MANAGEMENT:
                return self._parse_jira_ticket(ticket)
            elif self.config.platform == ITSMPlatform.NEXTRADE_ITSM:
                return self._parse_nextrade_ticket(ticket)
            else:
                return self._parse_custom_ticket(ticket)

        except Exception as e:
            logger.error(f"Error parsing ticket: {e}")
            return None

    def _parse_servicenow_ticket(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """ServiceNow 티켓 파싱"""
        description = f"{ticket.get('short_description', '')} {ticket.get('description', '')}"

        # IP 주소 추출
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, description)

        # 포트 추출
        port_pattern = r"(?:port|포트)[\s:]*(\d+)"
        ports = re.findall(port_pattern, description, re.IGNORECASE)

        if len(ips) >= 2 and ports:
            return FirewallPolicyRequest(
                ticket_id=ticket.get("number"),
                source_ip=ips[0],
                destination_ip=ips[1],
                port=int(ports[0]),
                protocol=self._extract_protocol(description),
                description=ticket.get("short_description", ""),
                created_at=datetime.fromisoformat(ticket.get("opened_at", "").replace("Z", "+00:00")),
                priority=ticket.get("priority", "normal"),
            )

        return None

    def _parse_jira_ticket(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """Jira 티켓 파싱"""
        fields = ticket.get("fields", {})
        description = f"{fields.get('summary', '')} {fields.get('description', '')}"

        # IP 주소와 포트 추출 (ServiceNow와 동일 로직)
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, description)

        port_pattern = r"(?:port|포트)[\s:]*(\d+)"
        ports = re.findall(port_pattern, description, re.IGNORECASE)

        if len(ips) >= 2 and ports:
            return FirewallPolicyRequest(
                ticket_id=ticket.get("key"),
                source_ip=ips[0],
                destination_ip=ips[1],
                port=int(ports[0]),
                protocol=self._extract_protocol(description),
                description=fields.get("summary", ""),
                created_at=datetime.fromisoformat(fields.get("created", "").replace("Z", "+00:00")),
                priority=fields.get("priority", {}).get("name", "normal"),
            )

        return None

    def _parse_nextrade_ticket(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """Nextrade ITSM 티켓 파싱"""
        f"{ticket.get('title', '')} {ticket.get('description', '')}"

        # 구조화된 데이터가 있는 경우 직접 사용
        if "firewall_request" in ticket:
            fw_data = ticket["firewall_request"]
            return FirewallPolicyRequest(
                ticket_id=ticket.get("id"),
                source_ip=fw_data.get("source_ip"),
                destination_ip=fw_data.get("destination_ip"),
                port=fw_data.get("port"),
                protocol=fw_data.get("protocol", "TCP"),
                description=ticket.get("title", ""),
                business_justification=fw_data.get("justification", ""),
                requester=ticket.get("requester", ""),
                created_at=datetime.fromisoformat(ticket.get("created_at", "")),
                priority=ticket.get("priority", "normal"),
            )

        # 자연어 처리를 통한 추출
        return self._extract_from_natural_language(ticket)

    def _parse_custom_ticket(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """커스텀 티켓 파싱"""
        # 기본 추출 로직
        return self._extract_from_natural_language(ticket)

    def _extract_from_natural_language(self, ticket: Dict) -> Optional[FirewallPolicyRequest]:
        """자연어 처리를 통한 방화벽 요청 정보 추출"""
        description = ticket.get("description", "") + " " + ticket.get("title", "")

        # IP 주소 추출
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, description)

        # 포트 추출 (다양한 패턴 지원)
        port_patterns = [
            r"(?:port|포트)[\s:]*(\d+)",
            r"(\d+)번?\s*포트",
            r":(\d+)",
            r"포트\s*(\d+)",
        ]

        ports = []
        for pattern in port_patterns:
            ports.extend(re.findall(pattern, description, re.IGNORECASE))

        # 프로토콜 추출
        protocol = self._extract_protocol(description)

        if len(ips) >= 2 and ports:
            return FirewallPolicyRequest(
                ticket_id=str(ticket.get("id", ticket.get("number", "unknown"))),
                source_ip=ips[0],
                destination_ip=ips[1],
                port=int(ports[0]),
                protocol=protocol,
                description=ticket.get("title", ticket.get("short_description", "")),
                business_justification=description,
                requester=ticket.get("requester", ticket.get("reporter", "unknown")),
                created_at=self._parse_datetime(ticket.get("created_at", ticket.get("opened_at", ""))),
                priority=ticket.get("priority", "normal"),
            )

        return None

    def _extract_protocol(self, text: str) -> str:
        """텍스트에서 프로토콜 추출"""
        text_lower = text.lower()

        if any(word in text_lower for word in ["https", "ssl", "tls"]):
            return "HTTPS"
        elif any(word in text_lower for word in ["http", "web"]):
            return "HTTP"
        elif any(word in text_lower for word in ["ssh", "secure shell"]):
            return "SSH"
        elif any(word in text_lower for word in ["ftp", "file transfer"]):
            return "FTP"
        elif any(word in text_lower for word in ["dns", "domain"]):
            return "DNS"
        elif any(word in text_lower for word in ["smtp", "mail", "메일"]):
            return "SMTP"
        elif any(word in text_lower for word in ["tcp"]):
            return "TCP"
        elif any(word in text_lower for word in ["udp"]):
            return "UDP"
        else:
            return "TCP"  # 기본값

    def _parse_datetime(self, date_str: str) -> datetime:
        """다양한 날짜 형식 파싱"""
        if not date_str:
            return datetime.now()

        # ISO 형식
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            pass

        # 다른 형식들 시도
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue

        return datetime.now()

    async def update_ticket_status(self, ticket_id: str, status: str, comment: str = "") -> bool:
        """티켓 상태 업데이트"""
        try:
            if self.config.platform == ITSMPlatform.SERVICENOW:
                return await self._update_servicenow_ticket(ticket_id, status, comment)
            elif self.config.platform == ITSMPlatform.JIRA_SERVICE_MANAGEMENT:
                return await self._update_jira_ticket(ticket_id, status, comment)
            elif self.config.platform == ITSMPlatform.NEXTRADE_ITSM:
                return await self._update_nextrade_ticket(ticket_id, status, comment)
            else:
                return await self._update_custom_ticket(ticket_id, status, comment)

        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            return False

    async def _update_servicenow_ticket(self, ticket_id: str, status: str, comment: str) -> bool:
        """ServiceNow 티켓 상태 업데이트"""
        url = f"{self.config.base_url}/api/now/table/incident/{ticket_id}"

        data = {
            "state": self._map_status_to_servicenow(status),
            "work_notes": f"FortiGate Nextrade: {comment}",
        }

        response = self.session.patch(url, json=data)
        return response.status_code == 200

    async def _update_jira_ticket(self, ticket_id: str, status: str, comment: str) -> bool:
        """Jira 티켓 상태 업데이트"""
        # 코멘트 추가
        comment_url = f"{self.config.base_url}/rest/api/2/issue/{ticket_id}/comment"
        comment_data = {"body": f"FortiGate Nextrade: {comment}"}

        response = self.session.post(comment_url, json=comment_data)
        return response.status_code == 201

    async def _update_nextrade_ticket(self, ticket_id: str, status: str, comment: str) -> bool:
        """Nextrade ITSM 티켓 상태 업데이트"""
        url = f"{self.config.base_url}/api/tickets/{ticket_id}"

        data = {
            "status": status,
            "resolution_notes": comment,
            "resolved_by": "FortiGate Nextrade Auto-Deploy",
        }

        response = self.session.patch(url, json=data)
        return response.status_code == 200

    async def _update_custom_ticket(self, ticket_id: str, status: str, comment: str) -> bool:
        """커스텀 API 티켓 상태 업데이트"""
        url = f"{self.config.base_url}/api/tickets/{ticket_id}/status"

        data = {"status": status, "comment": comment}

        response = self.session.post(url, json=data)
        return response.status_code == 200

    def _map_status_to_servicenow(self, status: str) -> str:
        """상태를 ServiceNow 상태 코드로 매핑"""
        mapping = {
            "new": "1",
            "in_progress": "2",
            "on_hold": "3",
            "resolved": "6",
            "closed": "7",
            "cancelled": "8",
        }
        return mapping.get(status, "2")  # 기본값: In Progress

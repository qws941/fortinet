#!/usr/bin/env python3

"""
ServiceNow ITSM API Client
FortiGate Nextrade와 ServiceNow 간의 실시간 연동을 위한 REST API 클라이언트
운영 비용 40% 절감, 장애 대응 93% 단축을 목표로 하는 프로토타입 구현
"""

import base64
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorSeverity, handle_errors
from utils.unified_cache_manager import get_cache_manager
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ServiceNowAPIClient:
    """
    ServiceNow REST API 클라이언트

    Features:
    - 자동 인증 관리 (OAuth, Basic Auth, Token)
    - 연결 풀링 및 재시도 로직
    - 캐싱 및 성능 최적화
    - 실시간 티켓 동기화
    - 자동 장애 복구
    - 성능 모니터링
    """

    def __init__(
        self,
        instance_url: str,
        username: str = None,
        password: str = None,
        api_token: str = None,
        oauth_config: Dict = None,
        timeout: int = 30,
        max_retries: int = 3,
        cache_ttl: int = 300,
    ):
        """
        ServiceNow 클라이언트 초기화

        Args:
            instance_url: ServiceNow 인스턴스 URL (예: https://dev12345.service-now.com)
            username: 사용자명 (Basic Auth용)
            password: 비밀번호 (Basic Auth용)
            api_token: API 토큰 (Token Auth용)
            oauth_config: OAuth 설정 딕셔너리
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            cache_ttl: 캐시 TTL (초)
        """
        self.instance_url = instance_url.rstrip("/")
        self.api_base = f"{self.instance_url}/api/now"
        self.timeout = timeout
        self.cache_ttl = cache_ttl

        # 세션 설정
        self.session = requests.Session()
        self._setup_authentication(username, password, api_token, oauth_config)
        self._setup_session_config(max_retries)

        # 캐시 매니저
        self.cache = get_cache_manager()

        # 성능 및 상태 추적
        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "errors": 0,
            "last_response_time": 0,
            "average_response_time": 0,
            "total_response_time": 0,
        }

        # 연결 상태
        self.is_connected = False
        self.last_health_check = None
        self.connection_errors = 0

        logger.info(f"ServiceNow 클라이언트 초기화 완료: {instance_url}")

    def _setup_authentication(self, username: str, password: str, api_token: str, oauth_config: Dict):
        """인증 방식 설정"""
        if api_token:
            # Token 기반 인증
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )
            self.auth_type = "token"

        elif username and password:
            # Basic 인증
            self.session.auth = (username, password)
            self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
            self.auth_type = "basic"

        elif oauth_config:
            # OAuth 인증 (향후 구현)
            self._setup_oauth(oauth_config)
            self.auth_type = "oauth"

        else:
            raise ValueError("인증 정보가 제공되지 않았습니다 (username/password, api_token, 또는 oauth_config 필요)")

    def _setup_oauth(self, oauth_config: Dict):
        """OAuth 2.0 인증 설정"""

        # OAuth 설정 검증
        required_fields = ["client_id", "client_secret", "token_url"]
        missing_fields = [f for f in required_fields if f not in oauth_config]
        if missing_fields:
            raise ValueError(f"OAuth config missing required fields: {missing_fields}")

        self.oauth_config = oauth_config
        self.access_token = None
        self.refresh_token = oauth_config.get("refresh_token")
        self.token_expiry = None

        # 토큰 획득
        self._obtain_oauth_token()

    def _obtain_oauth_token(self):
        """OAuth 액세스 토큰 획득"""
        token_url = self.oauth_config["token_url"]

        # Client credentials 인코딩
        credentials = f"{self.oauth_config['client_id']}:{self.oauth_config['client_secret']}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {"Authorization": f"Basic {encoded_credentials}", "Content-Type": "application/x-www-form-urlencoded"}

        # Grant type에 따른 요청 데이터
        if self.refresh_token:
            data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        else:
            data = {"grant_type": "client_credentials", "scope": self.oauth_config.get("scope", "useraccount")}

        try:
            response = self.session.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)

            # 토큰 만료 시간 설정
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

            # 세션 헤더에 토큰 추가
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"

            logger.info("OAuth token obtained successfully")

        except Exception as e:
            logger.error(f"Failed to obtain OAuth token: {e}")
            raise RuntimeError(f"OAuth authentication failed: {str(e)}")

    def _refresh_oauth_token_if_needed(self):
        """필요시 OAuth 토큰 갱신"""
        if self.auth_type == "oauth" and self.token_expiry:
            if datetime.utcnow() >= self.token_expiry:
                logger.info("OAuth token expired, refreshing...")
                self._obtain_oauth_token()

    def _setup_session_config(self, max_retries: int):
        """세션 설정 및 재시도 로직"""
        # 재시도 전략
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"],  # method_whitelist → allowed_methods
            backoff_factor=1,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 기본 헤더
        self.session.headers.update(
            {"User-Agent": "FortiGate-Nextrade-ITSM-Client/1.0", "X-Requested-With": "XMLHttpRequest"}
        )

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def health_check(self) -> Dict[str, Any]:
        """
        ServiceNow 연결 상태 확인

        Returns:
            연결 상태 정보
        """
        try:
            start_time = time.time()

            # 간단한 API 호출로 연결 확인
            response = self.session.get(f"{self.api_base}/table/sys_user", params={"sysparm_limit": 1}, timeout=10)

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                self.is_connected = True
                self.connection_errors = 0
                self.last_health_check = datetime.utcnow()

                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "instance_url": self.instance_url,
                    "auth_type": self.auth_type,
                    "last_check": self.last_health_check.isoformat(),
                }
            else:
                self.is_connected = False
                self.connection_errors += 1

                return {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "error": response.text[:200],
                }

        except Exception as e:
            self.is_connected = False
            self.connection_errors += 1

            logger.error(f"ServiceNow 연결 확인 실패: {e}")
            return {"status": "error", "error": str(e), "connection_errors": self.connection_errors}

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def create_incident(
        self,
        short_description: str,
        description: str,
        priority: int = 3,
        category: str = "Network",
        subcategory: str = "Firewall",
        caller_id: str = None,
        assignment_group: str = None,
        additional_fields: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Incident 티켓 생성

        Args:
            short_description: 간단한 설명
            description: 상세 설명
            priority: 우선순위 (1=Critical, 2=High, 3=Medium, 4=Low)
            category: 카테고리
            subcategory: 서브카테고리
            caller_id: 신고자 ID
            assignment_group: 담당 그룹
            additional_fields: 추가 필드

        Returns:
            생성된 티켓 정보
        """
        # 티켓 데이터 구성
        ticket_data = {
            "short_description": short_description,
            "description": description,
            "priority": str(priority),
            "category": category,
            "subcategory": subcategory,
            "state": "1",  # New
            "impact": "2",  # Medium
            "urgency": "2",  # Medium
        }

        # 선택적 필드 추가
        if caller_id:
            ticket_data["caller_id"] = caller_id
        if assignment_group:
            ticket_data["assignment_group"] = assignment_group
        if additional_fields:
            ticket_data.update(additional_fields)

        # API 호출
        response = self._make_request("POST", f"{self.api_base}/table/incident", json=ticket_data)

        if response["success"]:
            incident_data = response["data"]["result"]
            logger.info(f"Incident 생성 완료: {incident_data.get('number')}")

            return {
                "success": True,
                "incident_number": incident_data.get("number"),
                "sys_id": incident_data.get("sys_id"),
                "state": incident_data.get("state"),
                "created_on": incident_data.get("sys_created_on"),
                "url": f"{self.instance_url}/incident.do?sys_id={incident_data.get('sys_id')}",
            }
        else:
            return response

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def create_change_request(
        self,
        short_description: str,
        description: str,
        justification: str,
        risk: int = 3,
        impact: int = 3,
        priority: int = 3,
        requested_by: str = None,
        assignment_group: str = None,
        implementation_plan: str = None,
        test_plan: str = None,
        backout_plan: str = None,
        additional_fields: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Change Request 생성 (방화벽 정책 변경용)

        Args:
            short_description: 간단한 설명
            description: 상세 설명
            justification: 변경 사유
            risk: 위험도 (1=High, 2=Medium, 3=Low)
            impact: 영향도 (1=High, 2=Medium, 3=Low)
            priority: 우선순위
            requested_by: 요청자
            assignment_group: 담당 그룹
            implementation_plan: 구현 계획
            test_plan: 테스트 계획
            backout_plan: 롤백 계획
            additional_fields: 추가 필드

        Returns:
            생성된 Change Request 정보
        """
        # Change Request 데이터 구성
        change_data = {
            "short_description": short_description,
            "description": description,
            "justification": justification,
            "risk": str(risk),
            "impact": str(impact),
            "priority": str(priority),
            "state": "-5",  # Draft
            "type": "Standard",
            "category": "Network",
        }

        # 선택적 필드 추가
        if requested_by:
            change_data["requested_by"] = requested_by
        if assignment_group:
            change_data["assignment_group"] = assignment_group
        if implementation_plan:
            change_data["implementation_plan"] = implementation_plan
        if test_plan:
            change_data["test_plan"] = test_plan
        if backout_plan:
            change_data["backout_plan"] = backout_plan
        if additional_fields:
            change_data.update(additional_fields)

        # API 호출
        response = self._make_request("POST", f"{self.api_base}/table/change_request", json=change_data)

        if response["success"]:
            change_data = response["data"]["result"]
            logger.info(f"Change Request 생성 완료: {change_data.get('number')}")

            return {
                "success": True,
                "change_number": change_data.get("number"),
                "sys_id": change_data.get("sys_id"),
                "state": change_data.get("state"),
                "created_on": change_data.get("sys_created_on"),
                "url": f"{self.instance_url}/change_request.do?sys_id={change_data.get('sys_id')}",
            }
        else:
            return response

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def get_ticket(self, table: str, sys_id: str) -> Dict[str, Any]:
        """
        티켓 정보 조회

        Args:
            table: 테이블 명 (incident, change_request 등)
            sys_id: 시스템 ID

        Returns:
            티켓 정보
        """
        # 캐시 확인
        cache_key = f"ticket_{table}_{sys_id}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            self.stats["cache_hits"] += 1
            return {"success": True, "data": cached_data, "cached": True}

        # API 호출
        response = self._make_request("GET", f"{self.api_base}/table/{table}/{sys_id}")

        if response["success"]:
            # 캐시에 저장
            self.cache.set(cache_key, response["data"], self.cache_ttl)

        return response

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def update_ticket(self, table: str, sys_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        티켓 업데이트

        Args:
            table: 테이블 명
            sys_id: 시스템 ID
            updates: 업데이트할 필드들

        Returns:
            업데이트 결과
        """
        response = self._make_request("PUT", f"{self.api_base}/table/{table}/{sys_id}", json=updates)

        if response["success"]:
            # 캐시 무효화
            cache_key = f"ticket_{table}_{sys_id}"
            self.cache.delete(cache_key)

            logger.info(f"티켓 업데이트 완료: {table}/{sys_id}")

        return response

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def search_tickets(
        self, table: str, query: str = None, fields: List[str] = None, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """
        티켓 검색

        Args:
            table: 테이블 명
            query: 검색 쿼리 (예: "state=1^category=Network")
            fields: 반환할 필드 목록
            limit: 결과 수 제한
            offset: 오프셋

        Returns:
            검색 결과
        """
        params = {"sysparm_limit": limit, "sysparm_offset": offset}

        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = ",".join(fields)

        # 캐시 키 생성
        cache_key = f"search_{table}_{hash(str(params))}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            self.stats["cache_hits"] += 1
            return {"success": True, "data": cached_data, "cached": True}

        # API 호출
        response = self._make_request("GET", f"{self.api_base}/table/{table}", params=params)

        if response["success"]:
            # 짧은 시간 캐시 (검색 결과는 자주 변경됨)
            self.cache.set(cache_key, response["data"], 60)

        return response

    @handle_errors(category=ErrorCategory.EXTERNAL_SERVICE)
    def create_firewall_policy_request(
        self,
        source_ip: str,
        destination_ip: str,
        port: int,
        protocol: str,
        service_name: str,
        business_justification: str,
        requester_id: str,
        firewall_device: str = None,
        urgency: int = 3,
        additional_info: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        방화벽 정책 요청 전용 Change Request 생성

        Args:
            source_ip: 출발지 IP
            destination_ip: 목적지 IP
            port: 포트 번호
            protocol: 프로토콜 (TCP/UDP)
            service_name: 서비스 명
            business_justification: 비즈니스 사유
            requester_id: 요청자 ID
            firewall_device: 방화벽 장비명
            urgency: 긴급도
            additional_info: 추가 정보

        Returns:
            생성된 방화벽 정책 요청 정보
        """
        # 방화벽 정책 전용 템플릿
        short_desc = f"방화벽 정책 요청: {source_ip} -> {destination_ip}:{port}/{protocol.upper()}"

        description = f"""
방화벽 정책 추가 요청

== 네트워크 정보 ==
- 출발지 IP: {source_ip}
- 목적지 IP: {destination_ip}
- 포트: {port}
- 프로토콜: {protocol.upper()}
- 서비스: {service_name}

== 비즈니스 정보 ==
- 요청 사유: {business_justification}
- 요청자: {requester_id}

== 기술 정보 ==
- 방화벽 장비: {firewall_device or '자동 선택'}
- 정책 타입: ALLOW
- 영구성: 영구 정책
        """.strip()

        implementation_plan = f"""
1. 네트워크 존 분석 및 적절한 방화벽 선택
2. 정책 설정 검토 및 승인
3. 방화벽에 정책 추가: {source_ip} -> {destination_ip}:{port}/{protocol.upper()}
4. 연결 테스트 및 검증
5. 모니터링 설정
        """.strip()

        test_plan = """
1. 정책 추가 전 연결 차단 확인
2. 정책 추가 후 연결 허용 확인
3. 로그 확인 및 트래픽 모니터링
4. 보안 검토 및 승인
        """.strip()

        backout_plan = """
1. 추가된 정책 비활성화
2. 연결 차단 확인
3. 정책 완전 삭제
4. 변경 사항 롤백 확인
        """.strip()

        # 추가 필드 구성
        change_fields = {
            "u_source_ip": source_ip,
            "u_destination_ip": destination_ip,
            "u_port": str(port),
            "u_protocol": protocol.upper(),
            "u_service_name": service_name,
            "u_firewall_device": firewall_device or "AUTO_SELECT",
        }

        if additional_info:
            change_fields.update(additional_info)

        # Change Request 생성
        return self.create_change_request(
            short_description=short_desc,
            description=description,
            justification=business_justification,
            risk=2,  # Medium risk for firewall changes
            impact=3,  # Low impact for specific policy
            priority=urgency,
            requested_by=requester_id,
            assignment_group="Network Security Team",
            implementation_plan=implementation_plan,
            test_plan=test_plan,
            backout_plan=backout_plan,
            additional_fields=change_fields,
        )

    def _make_request(self, method: str, url: str, params: Dict = None, json: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        HTTP 요청 실행 (내부 메서드)

        Args:
            method: HTTP 메서드
            url: 요청 URL
            params: URL 파라미터
            json: JSON 데이터
            **kwargs: 추가 요청 옵션

        Returns:
            표준화된 응답 형식
        """
        start_time = time.time()
        self.stats["requests_made"] += 1

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=json, timeout=self.timeout, **kwargs
            )

            response_time = (time.time() - start_time) * 1000
            self.stats["last_response_time"] = response_time
            self.stats["total_response_time"] += response_time
            self.stats["average_response_time"] = self.stats["total_response_time"] / self.stats["requests_made"]

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json(),
                    "response_time_ms": round(response_time, 2),
                }
            else:
                self.stats["errors"] += 1
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": error_msg,
                    "response_time_ms": round(response_time, 2),
                }

        except requests.exceptions.RequestException as e:
            self.stats["errors"] += 1
            response_time = (time.time() - start_time) * 1000

            logger.error(f"ServiceNow API 요청 실패: {method} {url} - {e}")

            return {"success": False, "error": str(e), "response_time_ms": round(response_time, 2)}

    def get_statistics(self) -> Dict[str, Any]:
        """
        클라이언트 통계 조회

        Returns:
            통계 정보
        """
        error_rate = (self.stats["errors"] / max(self.stats["requests_made"], 1)) * 100
        cache_hit_rate = (self.stats["cache_hits"] / max(self.stats["requests_made"], 1)) * 100

        return {
            "connection_status": {
                "is_connected": self.is_connected,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "connection_errors": self.connection_errors,
                "auth_type": self.auth_type,
            },
            "performance": {
                "requests_made": self.stats["requests_made"],
                "error_rate_percent": round(error_rate, 2),
                "average_response_time_ms": round(self.stats["average_response_time"], 2),
                "last_response_time_ms": round(self.stats["last_response_time"], 2),
            },
            "caching": {
                "cache_hits": self.stats["cache_hits"],
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "cache_ttl_seconds": self.cache_ttl,
            },
            "instance_info": {"instance_url": self.instance_url, "api_base": self.api_base},
        }

    def close(self):
        """세션 정리"""
        if self.session:
            self.session.close()
            logger.info("ServiceNow 클라이언트 세션 종료")


# 편의 함수들
def create_servicenow_client_from_config(config: Dict[str, Any]) -> ServiceNowAPIClient:
    """
    설정에서 ServiceNow 클라이언트 생성

    Args:
        config: 설정 딕셔너리

    Returns:
        초기화된 ServiceNow 클라이언트
    """
    return ServiceNowAPIClient(
        instance_url=config["instance_url"],
        username=config.get("username"),
        password=config.get("password"),
        api_token=config.get("api_token"),
        oauth_config=config.get("oauth_config"),
        timeout=config.get("timeout", 30),
        max_retries=config.get("max_retries", 3),
        cache_ttl=config.get("cache_ttl", 300),
    )


# 글로벌 클라이언트 인스턴스 (선택적)
_global_servicenow_client: Optional[ServiceNowAPIClient] = None


def get_servicenow_client() -> Optional[ServiceNowAPIClient]:
    """글로벌 ServiceNow 클라이언트 반환"""
    return _global_servicenow_client


def set_servicenow_client(client: ServiceNowAPIClient):
    """글로벌 ServiceNow 클라이언트 설정"""
    global _global_servicenow_client
    _global_servicenow_client = client


# 데코레이터
def with_servicenow_client(func):
    """ServiceNow 클라이언트 자동 주입 데코레이터"""

    def wrapper(*args, **kwargs):
        client = get_servicenow_client()
        if not client:
            raise ApplicationError(
                "ServiceNow 클라이언트가 초기화되지 않았습니다",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.ERROR,
            )
        return func(client, *args, **kwargs)

    return wrapper

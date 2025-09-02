#!/usr/bin/env python3

"""
ITSM 스크래핑 모듈
itsm2.nxtd.co.kr에서 실제 방화벽 정책 요청을 스크래핑하고 분석
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ITSMScraper:
    """ITSM 사이트 스크래핑 클래스"""

    def __init__(self, base_url=None, username=None, password=None):
        """
        ITSM 스크래퍼 초기화

        Args:
            base_url (str): ITSM 기본 URL
            username (str): 로그인 사용자명
            password (str): 로그인 패스워드
        """
        from config.services import EXTERNAL_SERVICES

        # Use default URL from config if not provided
        if base_url is None:
            base_url = EXTERNAL_SERVICES["itsm"]

        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

        # 방화벽 정책 요청 관련 매핑
        self.firewall_keywords = [
            "방화벽",
            "firewall",
            "포트",
            "port",
            "허용",
            "allow",
            "차단",
            "block",
            "VPN",
            "vpn",
            "접속",
            "access",
            "오픈",
            "open",
            "보안정책",
        ]

        # 프로세스 매핑
        self.process_mapping = {
            "FRM004812": "방화벽_정책_요청",
            "SRMNXTCAT04050": "방화벽_허용요청",
            "VPN허용요청": "VPN_접속_허용",
            "방화벽오픈허용": "방화벽_포트_오픈",
        }

    def login(self) -> bool:
        """ITSM 사이트 로그인"""
        try:
            # 로그인 페이지 접근
            login_url = f"{self.base_url}/xefc/egene/login.jsp"
            response = self.session.get(login_url)

            if response.status_code != 200:
                logger.error(f"로그인 페이지 접근 실패: {response.status_code}")
                return False

            # 로그인 폼 데이터 준비 (실제 구현 시 사이트 구조에 맞게 수정 필요)
            login_data = {
                "username": self.username,
                "password": self.password,
                "login_type": "normal",
            }

            # 로그인 수행 (더미 - 실제 구현 시 사이트 구조 분석 필요)
            login_response = self.session.post(login_url, data=login_data)

            if "로그아웃" in login_response.text or "logout" in login_response.text:
                logger.info("ITSM 로그인 성공")
                return True
            else:
                logger.warning("ITSM 로그인 실패 또는 더미 모드")
                return False

        except Exception as e:
            logger.error(f"로그인 중 오류 발생: {str(e)}")
            return False

    def get_firewall_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        방화벽 정책 요청 목록 조회

        Args:
            limit (int): 조회할 최대 건수

        Returns:
            List[Dict]: 방화벽 정책 요청 목록
        """
        try:
            # 나의 요청 목록 API 호출
            list_url = f"{self.base_url}/api/egene/list/LSTMYREQ00001.html"

            params = {
                "limit": limit,
                "offset": 0,
                "search_type": "all",
                "search_keyword": "방화벽",
            }

            response = self.session.get(list_url, params=params)

            if response.status_code == 200:
                # 실제 API 응답 파싱
                try:
                    data = response.json()
                    requests_list = self._parse_request_list(data)
                except json.JSONDecodeError:
                    # HTML 응답인 경우 파싱
                    requests_list = self._parse_html_request_list(response.text)
            else:
                logger.warning(f"요청 목록 조회 실패: {response.status_code}")
                requests_list = self._generate_dummy_requests()

            # 방화벽 관련 요청 필터링
            firewall_requests = self._filter_firewall_requests(requests_list)

            logger.info(f"방화벽 정책 요청 {len(firewall_requests)}건 조회 완료")
            return firewall_requests

        except Exception as e:
            logger.error(f"방화벽 요청 목록 조회 중 오류: {str(e)}")
            return self._generate_dummy_requests()

    def get_request_detail(self, request_id: str) -> Dict[str, Any]:
        """
        특정 요청의 상세 정보 조회

        Args:
            request_id (str): 요청 ID

        Returns:
            Dict: 요청 상세 정보
        """
        try:
            # 폼 상세 정보 조회
            detail_url = f"{self.base_url}/api/egene/form.html"

            params = {
                "form_id": "FRM004812",
                "entity_id": "SRM",
                "request_id": request_id,
            }

            response = self.session.get(detail_url, params=params)

            if response.status_code == 200:
                try:
                    detail_data = response.json()
                    return self._parse_request_detail(detail_data)
                except json.JSONDecodeError:
                    # HTML 파싱
                    return self._parse_html_request_detail(response.text, request_id)
            else:
                logger.warning(f"요청 상세 조회 실패: {response.status_code}")
                return self._generate_dummy_detail(request_id)

        except Exception as e:
            logger.error(f"요청 상세 조회 중 오류: {str(e)}")
            return self._generate_dummy_detail(request_id)

    def _parse_request_list(self, data: Dict) -> List[Dict[str, Any]]:
        """JSON 형태의 요청 목록 파싱"""
        requests = []

        if "rows" in data:
            for row in data["rows"]:
                request_info = {
                    "id": row.get("com_id", ""),
                    "title": row.get("req_title", ""),
                    "category": row.get("cat_nm", ""),
                    "status": row.get("tas_name", ""),
                    "requester": row.get("req_emp_name", ""),
                    "request_date": row.get("req_dttm", ""),
                    "assignee": row.get("ass_emp_name", ""),
                    "entity_id": row.get("ent_id", ""),
                    "form_id": row.get("frm_id", ""),
                }
                requests.append(request_info)

        return requests

    def _parse_html_request_list(self, html: str) -> List[Dict[str, Any]]:
        """HTML 형태의 요청 목록 파싱"""
        requests = []
        soup = BeautifulSoup(html, "html.parser")

        # 테이블 데이터 파싱 (실제 구조에 맞게 수정 필요)
        rows = soup.find_all("tr")
        for row in rows[1:]:  # 헤더 제외
            cells = row.find_all("td")
            if len(cells) >= 6:
                request_info = {
                    "id": cells[0].get_text(strip=True),
                    "title": cells[1].get_text(strip=True),
                    "category": cells[2].get_text(strip=True),
                    "status": cells[3].get_text(strip=True),
                    "requester": cells[4].get_text(strip=True),
                    "request_date": cells[5].get_text(strip=True),
                }
                requests.append(request_info)

        return requests

    def _filter_firewall_requests(self, requests: List[Dict]) -> List[Dict]:
        """방화벽 관련 요청 필터링"""
        firewall_requests = []

        for request in requests:
            title = request.get("title", "").lower()
            category = request.get("category", "").lower()

            # 방화벽 관련 키워드 검사
            is_firewall_request = any(
                keyword in title or keyword in category
                for keyword in self.firewall_keywords
            )

            if is_firewall_request:
                request["request_type"] = self._classify_request_type(request)
                firewall_requests.append(request)

        return firewall_requests

    def _classify_request_type(self, request: Dict) -> str:
        """요청 유형 분류"""
        title = request.get("title", "").lower()
        category = request.get("category", "").lower()

        if "vpn" in title or "vpn" in category:
            return "VPN_ACCESS"
        elif "허용" in title or "allow" in title:
            return "FIREWALL_ALLOW"
        elif "차단" in title or "block" in title:
            return "FIREWALL_BLOCK"
        elif "포트" in title or "port" in title:
            return "PORT_OPEN"
        else:
            return "GENERAL_FIREWALL"

    def _parse_request_detail(self, data: Dict) -> Dict[str, Any]:
        """요청 상세 정보 파싱"""
        detail = {
            "request_id": data.get("com_id", ""),
            "title": data.get("req_title", ""),
            "description": data.get("req_desc", ""),
            "requester": data.get("req_emp_name", ""),
            "department": data.get("req_dept_name", ""),
            "request_date": data.get("req_dttm", ""),
            "status": data.get("tas_name", ""),
            "form_data": self._extract_firewall_form_data(data),
        }

        return detail

    def _extract_firewall_form_data(self, data: Dict) -> Dict[str, Any]:
        """방화벽 정책 관련 폼 데이터 추출"""
        form_data = {}

        # 일반적인 방화벽 정책 필드들 매핑
        field_mapping = {
            "source_ip": ["src_ip", "source_ip", "출발지ip", "소스ip"],
            "destination_ip": ["dst_ip", "dest_ip", "destination_ip", "목적지ip"],
            "port": ["port", "port_num", "포트", "포트번호"],
            "protocol": ["protocol", "protocol_type", "프로토콜"],
            "service": ["service", "service_name", "서비스"],
            "action": ["action", "policy_action", "액션", "정책"],
            "justification": ["reason", "justification", "사유", "목적"],
            "duration": ["duration", "period", "기간"],
            "business_owner": ["owner", "business_owner", "업무담당자"],
        }

        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in data:
                    form_data[standard_field] = data[field]
                    break

        return form_data

    def _parse_html_request_detail(self, html: str, request_id: str) -> Dict[str, Any]:
        """HTML 형태의 요청 상세 파싱"""
        soup = BeautifulSoup(html, "html.parser")

        detail = {
            "request_id": request_id,
            "title": "",
            "description": "",
            "form_data": {},
        }

        # 폼 필드 추출 (실제 구조에 맞게 수정 필요)
        input_fields = soup.find_all(["input", "textarea", "select"])
        for field in input_fields:
            name = field.get("name", "")
            value = field.get("value", "") or field.get_text(strip=True)

            if name and value:
                detail["form_data"][name] = value

        return detail

    def _generate_dummy_requests(self) -> List[Dict[str, Any]]:
        """더미 방화벽 요청 데이터 생성"""
        dummy_requests = [
            {
                "id": "SR2025-001",
                "title": "웹 서버 포트 80 허용 요청",
                "category": "방화벽 허용요청",
                "status": "검토중",
                "requester": "김개발",
                "request_date": "2025-06-05 09:30:00",
                "assignee": "이보안",
                "request_type": "FIREWALL_ALLOW",
            },
            {
                "id": "SR2025-002",
                "title": "DB 서버 접속 허용 (포트 3306)",
                "category": "방화벽 허용요청",
                "status": "승인대기",
                "requester": "박데이터",
                "request_date": "2025-06-05 10:15:00",
                "assignee": "최네트워크",
                "request_type": "PORT_OPEN",
            },
            {
                "id": "SR2025-003",
                "title": "VPN 외부 접속 허용",
                "category": "VPN 허용요청",
                "status": "완료",
                "requester": "정재택",
                "request_date": "2025-06-04 16:20:00",
                "assignee": "이보안",
                "request_type": "VPN_ACCESS",
            },
            {
                "id": "SR2025-004",
                "title": "악성 IP 차단 요청",
                "category": "방화벽 차단요청",
                "status": "진행중",
                "requester": "강보안",
                "request_date": "2025-06-05 11:45:00",
                "assignee": "이보안",
                "request_type": "FIREWALL_BLOCK",
            },
        ]

        return dummy_requests

    def _generate_dummy_detail(self, request_id: str) -> Dict[str, Any]:
        """더미 요청 상세 데이터 생성"""
        dummy_details = {
            "SR2025-001": {
                "request_id": "SR2025-001",
                "title": "웹 서버 포트 80 허용 요청",
                "description": "신규 웹 서비스 런칭을 위한 포트 80 허용 요청",
                "requester": "김개발",
                "department": "IT개발팀",
                "request_date": "2025-06-05 09:30:00",
                "status": "검토중",
                "form_data": {
                    "source_ip": "192.168.1.0/24",
                    "destination_ip": "172.16.10.100",
                    "port": "80",
                    "protocol": "TCP",
                    "service": "HTTP",
                    "action": "ALLOW",
                    "justification": "신규 웹 서비스 런칭",
                    "business_owner": "김팀장",
                },
            },
            "SR2025-002": {
                "request_id": "SR2025-002",
                "title": "DB 서버 접속 허용 (포트 3306)",
                "description": "애플리케이션 서버에서 DB 서버 접속 허용",
                "requester": "박데이터",
                "department": "IT개발팀",
                "request_date": "2025-06-05 10:15:00",
                "status": "승인대기",
                "form_data": {
                    "source_ip": "172.16.20.0/24",
                    "destination_ip": "172.16.30.50",
                    "port": "3306",
                    "protocol": "TCP",
                    "service": "MySQL",
                    "action": "ALLOW",
                    "justification": "DB 연동을 위한 접속 허용",
                    "business_owner": "박팀장",
                },
            },
        }

        return dummy_details.get(
            request_id,
            {
                "request_id": request_id,
                "title": f"요청 {request_id}",
                "description": "상세 정보 없음",
                "form_data": {},
            },
        )

    def monitor_new_requests(self, callback_func, interval: int = 300):
        """
        새로운 방화벽 요청 모니터링

        Args:
            callback_func: 새 요청 발견 시 호출할 콜백 함수
            interval (int): 모니터링 간격 (초)
        """
        logger.info(f"방화벽 요청 모니터링 시작 (간격: {interval}초)")

        last_check_time = datetime.now()

        while True:
            try:
                current_requests = self.get_firewall_requests()

                # 마지막 체크 이후 새로운 요청 필터링
                new_requests = [
                    req
                    for req in current_requests
                    if datetime.strptime(
                        req.get("request_date", ""), "%Y-%m-%d %H:%M:%S"
                    )
                    > last_check_time
                ]

                if new_requests:
                    logger.info(f"새로운 방화벽 요청 {len(new_requests)}건 발견")
                    for request in new_requests:
                        try:
                            detail = self.get_request_detail(request["id"])
                            callback_func(request, detail)
                        except Exception as e:
                            logger.error(f"요청 처리 중 오류: {str(e)}")

                last_check_time = datetime.now()
                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("모니터링 중단됨")
                break
            except Exception as e:
                logger.error(f"모니터링 중 오류: {str(e)}")
                time.sleep(interval)

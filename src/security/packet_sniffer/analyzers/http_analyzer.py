#!/usr/bin/env python3
"""
HTTP 분석기 - HTTP/HTTPS 프로토콜 전용 분석
"""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from security.packet_sniffer.base_sniffer import PacketInfo

from .protocol_analyzer import BaseProtocolAnalyzer, ProtocolAnalysisResult


class HttpAnalyzer(BaseProtocolAnalyzer):
    """HTTP/HTTPS 프로토콜 분석기"""

    def __init__(self):
        super().__init__("http")

        # HTTP 메서드
        self.http_methods = [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "HEAD",
            "OPTIONS",
            "PATCH",
            "TRACE",
            "CONNECT",
        ]

        # HTTP 상태 코드 범주
        self.status_categories = {
            "1xx": "Informational",
            "2xx": "Success",
            "3xx": "Redirection",
            "4xx": "Client Error",
            "5xx": "Server Error",
        }

        # 보안 관련 헤더
        self.security_headers = [
            "content-security-policy",
            "strict-transport-security",
            "x-frame-options",
            "x-content-type-options",
            "x-xss-protection",
            "referrer-policy",
        ]

        # 민감한 정보 패턴
        self.sensitive_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
            "api_key": r'(?i)(api[_-]?key|apikey|access[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9]{32,})["\']?',
            "password": r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        }

    def can_analyze(self, packet: PacketInfo) -> bool:
        """HTTP 패킷 분석 가능 여부 확인"""
        # HTTP 기본 포트 확인
        http_ports = [80, 8080, 8000, 8888, 3000, 5000]
        https_ports = [443, 8443, 9443]

        if packet.dst_port in http_ports or packet.src_port in http_ports:
            return True
        if packet.dst_port in https_ports or packet.src_port in https_ports:
            return True

        # 페이로드에서 HTTP 시그니처 확인
        if packet.payload:
            try:
                payload_str = packet.payload.decode("utf-8", errors="ignore")
                return self._has_http_signature(payload_str)
            except Exception:
                return False

        return False

    def analyze(self, packet: PacketInfo) -> Optional[ProtocolAnalysisResult]:
        """HTTP 패킷 분석"""
        if not self.can_analyze(packet):
            return None

        try:
            payload_str = packet.payload.decode("utf-8", errors="ignore")

            # HTTP 요청 분석
            request_result = self._analyze_http_request(payload_str)
            if request_result:
                confidence = self._calculate_http_confidence(packet, payload_str, "request")
                return ProtocolAnalysisResult(
                    protocol="HTTP",
                    confidence=confidence,
                    details=request_result,
                    flags=self._extract_http_flags(request_result),
                    security_flags=self._analyze_security_aspects(request_result, payload_str),
                )

            # HTTP 응답 분석
            response_result = self._analyze_http_response(payload_str)
            if response_result:
                confidence = self._calculate_http_confidence(packet, payload_str, "response")
                return ProtocolAnalysisResult(
                    protocol="HTTP",
                    confidence=confidence,
                    details=response_result,
                    flags=self._extract_http_flags(response_result),
                    security_flags=self._analyze_security_aspects(response_result, payload_str),
                )

        except Exception as e:
            self.logger.error(f"HTTP 분석 실패: {e}")

        return None

    def _has_http_signature(self, payload: str) -> bool:
        """HTTP 시그니처 확인"""
        # HTTP 요청 시그니처
        for method in self.http_methods:
            if payload.startswith(f"{method} "):
                return True

        # HTTP 응답 시그니처
        if payload.startswith("HTTP/"):
            return True

        # HTTP 헤더 패턴
        http_header_pattern = r"^[A-Za-z-]+:\s*.+$"
        lines = payload.split("\n")
        header_count = 0
        for line in lines[:10]:  # 첫 10줄만 확인
            if re.match(http_header_pattern, line.strip()):
                header_count += 1

        return header_count >= 2

    def _analyze_http_request(self, payload: str) -> Optional[Dict[str, Any]]:
        """HTTP 요청 분석"""
        lines = payload.split("\n")
        if not lines:
            return None

        # 요청 라인 파싱
        request_line = lines[0].strip()
        request_parts = request_line.split(" ")

        if len(request_parts) < 3:
            return None

        method = request_parts[0]
        if method not in self.http_methods:
            return None

        uri = request_parts[1]
        version = request_parts[2] if len(request_parts) > 2 else "HTTP/1.1"

        # 헤더 파싱
        headers = self._parse_headers(lines[1:])

        # 바디 파싱 (있는 경우)
        body = self._extract_body(payload)

        result = {
            "type": "request",
            "method": method,
            "uri": uri,
            "version": version,
            "headers": headers,
            "body_length": len(body) if body else 0,
        }

        # URI 상세 분석
        uri_analysis = self._analyze_uri(uri)
        if uri_analysis:
            result["uri_analysis"] = uri_analysis

        # 바디 분석 (POST, PUT 등)
        if body and method in ["POST", "PUT", "PATCH"]:
            body_analysis = self._analyze_request_body(body, headers)
            if body_analysis:
                result["body_analysis"] = body_analysis

        # 사용자 에이전트 분석
        user_agent = headers.get("user-agent")
        if user_agent:
            result["user_agent_analysis"] = self._analyze_user_agent(user_agent)

        return result

    def _analyze_http_response(self, payload: str) -> Optional[Dict[str, Any]]:
        """HTTP 응답 분석"""
        lines = payload.split("\n")
        if not lines:
            return None

        # 상태 라인 파싱
        status_line = lines[0].strip()
        if not status_line.startswith("HTTP/"):
            return None

        status_parts = status_line.split(" ", 2)
        if len(status_parts) < 2:
            return None

        version = status_parts[0]
        status_code = status_parts[1]
        reason_phrase = status_parts[2] if len(status_parts) > 2 else ""

        # 헤더 파싱
        headers = self._parse_headers(lines[1:])

        # 바디 파싱
        body = self._extract_body(payload)

        result = {
            "type": "response",
            "version": version,
            "status_code": int(status_code),
            "reason_phrase": reason_phrase,
            "headers": headers,
            "body_length": len(body) if body else 0,
        }

        # 상태 코드 분석
        result["status_category"] = self._categorize_status_code(status_code)

        # 응답 바디 분석
        if body:
            body_analysis = self._analyze_response_body(body, headers)
            if body_analysis:
                result["body_analysis"] = body_analysis

        # 보안 헤더 분석
        security_headers = self._analyze_security_headers(headers)
        if security_headers:
            result["security_headers"] = security_headers

        return result

    def _parse_headers(self, lines: List[str]) -> Dict[str, str]:
        """HTTP 헤더 파싱"""
        headers = {}

        for line in lines:
            line = line.strip()
            if not line:  # 빈 줄 (헤더 끝)
                break

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        return headers

    def _extract_body(self, payload: str) -> Optional[str]:
        """HTTP 바디 추출"""
        # 헤더와 바디 구분 (빈 줄로 구분)
        parts = payload.split("\r\n\r\n", 1)
        if len(parts) == 2:
            return parts[1]

        parts = payload.split("\n\n", 1)
        if len(parts) == 2:
            return parts[1]

        return None

    def _analyze_uri(self, uri: str) -> Dict[str, Any]:
        """URI 분석"""
        try:
            parsed = urlparse(uri)

            analysis = {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "path": parsed.path,
                "params": parsed.params,
                "fragment": parsed.fragment,
            }

            # 쿼리 파라미터 분석
            if parsed.query:
                query_params = parse_qs(parsed.query)
                analysis["query_params"] = query_params
                analysis["query_param_count"] = len(query_params)

            # 경로 분석
            path_parts = [part for part in parsed.path.split("/") if part]
            analysis["path_segments"] = path_parts
            analysis["path_depth"] = len(path_parts)

            # 파일 확장자 확인
            if "." in parsed.path:
                extension = parsed.path.split(".")[-1].lower()
                analysis["file_extension"] = extension

            return analysis

        except Exception as e:
            self.logger.error(f"URI 분석 실패: {e}")
            return {}

    def _analyze_request_body(self, body: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """요청 바디 분석"""
        analysis = {
            "size": len(body),
            "content_type": headers.get("content-type", "unknown"),
        }

        content_type = headers.get("content-type", "").lower()

        # JSON 바디 분석
        if "application/json" in content_type:
            try:
                json_data = json.loads(body)
                analysis["json_structure"] = self._analyze_json_structure(json_data)
            except json.JSONDecodeError:
                analysis["json_parse_error"] = True

        # Form 데이터 분석
        elif "application/x-www-form-urlencoded" in content_type:
            try:
                form_data = parse_qs(body)
                analysis["form_fields"] = list(form_data.keys())
                analysis["form_field_count"] = len(form_data)
            except Exception:
                analysis["form_parse_error"] = True

        # XML 바디 분석
        elif "application/xml" in content_type or "text/xml" in content_type:
            analysis["xml_detected"] = True
            # 간단한 XML 태그 개수 세기
            xml_tags = re.findall(r"<(\w+)", body)
            analysis["xml_tag_count"] = len(xml_tags)
            analysis["unique_xml_tags"] = len(set(xml_tags))

        # 민감한 정보 탐지
        sensitive_data = self._detect_sensitive_data(body)
        if sensitive_data:
            analysis["sensitive_data_detected"] = sensitive_data

        return analysis

    def _analyze_response_body(self, body: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """응답 바디 분석"""
        analysis = {
            "size": len(body),
            "content_type": headers.get("content-type", "unknown"),
        }

        content_type = headers.get("content-type", "").lower()

        # HTML 분석
        if "text/html" in content_type:
            html_analysis = self._analyze_html_content(body)
            analysis.update(html_analysis)

        # JSON 분석
        elif "application/json" in content_type:
            try:
                json_data = json.loads(body)
                analysis["json_structure"] = self._analyze_json_structure(json_data)
            except json.JSONDecodeError:
                analysis["json_parse_error"] = True

        # 에러 페이지 탐지
        if self._is_error_page(body):
            analysis["error_page_detected"] = True
            analysis["potential_info_disclosure"] = True

        return analysis

    def _analyze_json_structure(self, json_data: Any) -> Dict[str, Any]:
        """JSON 구조 분석"""
        analysis = {"type": type(json_data).__name__}

        if isinstance(json_data, dict):
            analysis["key_count"] = len(json_data)
            analysis["keys"] = list(json_data.keys())[:10]  # 최대 10개 키만
        elif isinstance(json_data, list):
            analysis["array_length"] = len(json_data)
            if json_data and isinstance(json_data[0], dict):
                analysis["array_item_keys"] = list(json_data[0].keys())[:10]

        return analysis

    def _analyze_html_content(self, html: str) -> Dict[str, Any]:
        """HTML 컨텐츠 분석"""
        analysis = {}

        # 폼 탐지
        forms = re.findall(r"<form[^>]*>", html, re.IGNORECASE)
        if forms:
            analysis["form_count"] = len(forms)

        # 스크립트 태그 탐지
        scripts = re.findall(r"<script[^>]*>", html, re.IGNORECASE)
        if scripts:
            analysis["script_count"] = len(scripts)

        # 이미지 탐지
        images = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
        if images:
            analysis["image_count"] = len(images)

        # 링크 탐지
        links = re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
        if links:
            analysis["link_count"] = len(links)
            analysis["external_links"] = [link for link in links if link.startswith("http")]

        return analysis

    def _analyze_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """User-Agent 분석"""
        analysis = {"raw": user_agent, "length": len(user_agent)}

        # 브라우저 탐지
        browsers = {
            "chrome": r"Chrome/([0-9.]+)",
            "firefox": r"Firefox/([0-9.]+)",
            "safari": r"Safari/([0-9.]+)",
            "edge": r"Edg/([0-9.]+)",
            "opera": r"Opera/([0-9.]+)",
        }

        for browser, pattern in browsers.items():
            match = re.search(pattern, user_agent, re.IGNORECASE)
            if match:
                analysis["browser"] = browser
                analysis["browser_version"] = match.group(1)
                break

        # OS 탐지
        if "Windows" in user_agent:
            analysis["os"] = "Windows"
        elif "Macintosh" in user_agent or "Mac OS" in user_agent:
            analysis["os"] = "macOS"
        elif "Linux" in user_agent:
            analysis["os"] = "Linux"
        elif "Android" in user_agent:
            analysis["os"] = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            analysis["os"] = "iOS"

        # 봇 탐지
        bot_patterns = ["bot", "crawler", "spider", "scraper"]
        for pattern in bot_patterns:
            if pattern.lower() in user_agent.lower():
                analysis["is_bot"] = True
                break

        return analysis

    def _analyze_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """보안 헤더 분석"""
        security_analysis = {}

        for header in self.security_headers:
            if header in headers:
                security_analysis[header] = headers[header]

        # HTTPS 관련
        if "strict-transport-security" in headers:
            security_analysis["hsts_enabled"] = True

        # 프레임 보호
        if "x-frame-options" in headers:
            security_analysis["clickjacking_protection"] = True

        # XSS 보호
        if "x-xss-protection" in headers:
            security_analysis["xss_protection"] = True

        return security_analysis

    def _detect_sensitive_data(self, content: str) -> List[str]:
        """민감한 데이터 탐지"""
        detected = []

        for data_type, pattern in self.sensitive_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                detected.append(f"{data_type}: {len(matches)} occurrences")

        return detected

    def _is_error_page(self, content: str) -> bool:
        """에러 페이지 탐지"""
        error_indicators = [
            "stack trace",
            "exception",
            "error 500",
            "internal server error",
            "sql error",
            "database error",
            "php error",
            "python error",
            "java.lang.",
            "system.exception",
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in error_indicators)

    def _categorize_status_code(self, status_code: str) -> str:
        """HTTP 상태 코드 분류"""
        try:
            code = int(status_code)
            category = f"{code // 100}xx"
            return self.status_categories.get(category, "Unknown")
        except Exception:
            return "Invalid"

    def _extract_http_flags(self, analysis: Dict[str, Any]) -> Dict[str, bool]:
        """HTTP 플래그 추출"""
        flags = {}

        # 요청/응답 타입
        flags["is_request"] = analysis.get("type") == "request"
        flags["is_response"] = analysis.get("type") == "response"

        # HTTPS 여부 (헤더 기반 추정)
        headers = analysis.get("headers", {})
        flags["likely_https"] = "strict-transport-security" in headers

        # 에러 여부
        if "status_code" in analysis:
            flags["is_error"] = analysis["status_code"] >= 400

        # 보안 관련
        flags["has_security_headers"] = bool(analysis.get("security_headers"))
        flags["potential_info_disclosure"] = analysis.get("potential_info_disclosure", False)

        return flags

    def _analyze_security_aspects(self, analysis: Dict[str, Any], payload: str) -> Dict[str, Any]:
        """보안 측면 분석"""
        security_flags = {}

        # 민감한 정보 노출
        if "sensitive_data_detected" in analysis.get("body_analysis", {}):
            security_flags["sensitive_data_exposure"] = True

        # 에러 정보 노출
        if analysis.get("potential_info_disclosure"):
            security_flags["information_disclosure"] = True

        # 보안 헤더 누락
        if analysis.get("type") == "response":
            missing_headers = []
            headers = analysis.get("headers", {})
            for security_header in self.security_headers:
                if security_header not in headers:
                    missing_headers.append(security_header)

            if missing_headers:
                security_flags["missing_security_headers"] = missing_headers

        # 잠재적 공격 패턴
        attack_patterns = {
            "sql_injection": [
                r"union\s+select",
                r"drop\s+table",
                r"insert\s+into",
            ],
            "xss": [r"<script>", r"javascript:", r"onerror\s*="],
            "directory_traversal": [r"\.\./", r"\.\.\\"],
            "command_injection": [r";\s*rm\s+", r";\s*cat\s+", r"\|\s*nc\s+"],
        }

        for attack_type, patterns in attack_patterns.items():
            for pattern in patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    security_flags[f"potential_{attack_type}"] = True
                    break

        return security_flags

    def _calculate_http_confidence(self, packet: PacketInfo, payload: str, message_type: str) -> float:
        """HTTP 신뢰도 계산"""
        confidence = 0.0

        # 기본 신뢰도 (시그니처 기반)
        if message_type == "request":
            for method in self.http_methods:
                if payload.startswith(f"{method} "):
                    confidence = 0.9
                    break
        elif message_type == "response":
            if payload.startswith("HTTP/"):
                confidence = 0.9

        # 포트 기반 보정
        http_ports = [80, 8080, 8000, 8888, 3000, 5000]
        https_ports = [443, 8443, 9443]

        if packet.dst_port in http_ports or packet.src_port in http_ports:
            confidence += 0.1
        elif packet.dst_port in https_ports or packet.src_port in https_ports:
            confidence += 0.05

        # 헤더 존재 여부
        header_count = payload.count("\n")
        if header_count >= 3:
            confidence += 0.05

        return min(confidence, 1.0)

    def get_confidence_score(self, packet: PacketInfo) -> float:
        """신뢰도 점수 계산"""
        if not self.can_analyze(packet):
            return 0.0

        try:
            payload_str = packet.payload.decode("utf-8", errors="ignore")

            # HTTP 요청 확인
            for method in self.http_methods:
                if payload_str.startswith(f"{method} "):
                    return self._calculate_http_confidence(packet, payload_str, "request")

            # HTTP 응답 확인
            if payload_str.startswith("HTTP/"):
                return self._calculate_http_confidence(packet, payload_str, "response")

        except Exception:
            pass

        return 0.0

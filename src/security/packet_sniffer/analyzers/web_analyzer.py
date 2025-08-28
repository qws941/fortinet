#!/usr/bin/env python3
"""
웹 프로토콜 분석기 (HTTP/HTTPS)
웹 트래픽 및 보안 분석
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class WebAnalyzer:
    """HTTP/HTTPS 프로토콜 전용 분석기"""

    def __init__(self):
        self.http_methods = []
        self.user_agents = []
        self.domains = []

    def analyze_http(self, payload: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP 패킷 분석"""

        try:
            payload_str = payload.decode("utf-8", errors="ignore")

            analysis = {
                "protocol": "HTTP",
                "port": packet_info.get("dst_port", 80),
                "payload_size": len(payload),
                "timestamp": packet_info.get("timestamp"),
            }

            # HTTP 요청 분석
            if self._is_http_request(payload_str):
                analysis.update(self._parse_http_request(payload_str))

            # HTTP 응답 분석
            elif self._is_http_response(payload_str):
                analysis.update(self._parse_http_response(payload_str))

            # 보안 검사
            security_issues = self._check_web_security(payload_str, analysis)
            if security_issues:
                analysis["security_issues"] = security_issues
                analysis["risk_level"] = self._calculate_risk_level(security_issues)

            # 콘텐츠 타입 분석
            content_analysis = self._analyze_content(payload_str)
            if content_analysis:
                analysis["content_analysis"] = content_analysis

            return analysis

        except Exception as e:
            logger.error(f"HTTP 분석 오류: {e}")
            return {
                "protocol": "HTTP",
                "error": str(e),
                "payload_size": len(payload),
            }

    def _is_http_request(self, payload_str: str) -> bool:
        """HTTP 요청인지 확인"""

        http_methods = [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "HEAD",
            "OPTIONS",
            "PATCH",
            "TRACE",
        ]
        first_line = payload_str.split("\n")[0] if "\n" in payload_str else payload_str

        return any(first_line.startswith(method + " ") for method in http_methods)

    def _is_http_response(self, payload_str: str) -> bool:
        """HTTP 응답인지 확인"""

        return payload_str.startswith("HTTP/")

    def _parse_http_request(self, payload_str: str) -> Dict[str, Any]:
        """HTTP 요청 파싱"""

        lines = payload_str.split("\n")
        if not lines:
            return {}

        # 요청 라인 파싱
        request_line = lines[0].strip()
        parts = request_line.split(" ")

        if len(parts) < 3:
            return {}

        method, uri, version = parts[0], parts[1], parts[2]

        request_info = {
            "type": "request",
            "method": method,
            "uri": uri,
            "version": version,
            "headers": {},
        }

        # 헤더 파싱
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                request_info["headers"][key.strip().lower()] = value.strip()

        # URI 상세 분석
        if uri:
            request_info.update(self._analyze_uri(uri))

        # User-Agent 분석
        user_agent = request_info["headers"].get("user-agent", "")
        if user_agent:
            request_info["user_agent_analysis"] = self._analyze_user_agent(user_agent)

        # 호스트 정보
        host = request_info["headers"].get("host", "")
        if host:
            request_info["host"] = host

        return request_info

    def _parse_http_response(self, payload_str: str) -> Dict[str, Any]:
        """HTTP 응답 파싱"""

        lines = payload_str.split("\n")
        if not lines:
            return {}

        # 상태 라인 파싱
        status_line = lines[0].strip()
        parts = status_line.split(" ", 2)

        if len(parts) < 2:
            return {}

        version, status_code = parts[0], parts[1]
        status_message = parts[2] if len(parts) > 2 else ""

        response_info = {
            "type": "response",
            "version": version,
            "status_code": int(status_code),
            "status_message": status_message,
            "headers": {},
        }

        # 헤더 파싱
        for line in lines[1:]:
            if ":" in line and line.strip():
                key, value = line.split(":", 1)
                response_info["headers"][key.strip().lower()] = value.strip()

        # 보안 헤더 분석
        response_info["security_headers"] = self._analyze_security_headers(response_info["headers"])

        return response_info

    def _analyze_uri(self, uri: str) -> Dict[str, Any]:
        """URI 분석"""

        try:
            parsed = urlparse(uri)

            uri_analysis = {
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
            }

            # 쿼리 파라미터 분석
            if parsed.query:
                uri_analysis["query_params"] = parse_qs(parsed.query)
                uri_analysis["param_count"] = len(parse_qs(parsed.query))

            # 의심스러운 패턴 검사
            suspicious_patterns = self._check_suspicious_uri_patterns(uri)
            if suspicious_patterns:
                uri_analysis["suspicious_patterns"] = suspicious_patterns

            return uri_analysis

        except Exception as e:
            logger.error(f"URI 분석 오류: {e}")
            return {"uri_error": str(e)}

    def _analyze_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """User-Agent 분석"""

        ua_analysis = {
            "original": user_agent,
            "browser": "unknown",
            "os": "unknown",
            "is_bot": False,
            "is_suspicious": False,
        }

        # 브라우저 탐지
        browser_patterns = {
            "Chrome": r"Chrome/([0-9.]+)",
            "Firefox": r"Firefox/([0-9.]+)",
            "Safari": r"Safari/([0-9.]+)",
            "Edge": r"Edge/([0-9.]+)",
            "Internet Explorer": r"MSIE ([0-9.]+)",
        }

        for browser, pattern in browser_patterns.items():
            match = re.search(pattern, user_agent)
            if match:
                ua_analysis["browser"] = browser
                ua_analysis["browser_version"] = match.group(1)
                break

        # 운영체제 탐지
        os_patterns = {
            "Windows": r"Windows NT ([0-9.]+)",
            "macOS": r"Mac OS X ([0-9_.]+)",
            "Linux": r"Linux",
            "Android": r"Android ([0-9.]+)",
            "iOS": r"OS ([0-9_]+)",
        }

        for os_name, pattern in os_patterns.items():
            if re.search(pattern, user_agent):
                ua_analysis["os"] = os_name
                break

        # 봇 탐지
        bot_indicators = [
            "bot",
            "crawler",
            "spider",
            "scraper",
            "curl",
            "wget",
        ]
        ua_analysis["is_bot"] = any(indicator in user_agent.lower() for indicator in bot_indicators)

        # 의심스러운 User-Agent 검사
        ua_analysis["is_suspicious"] = self._is_suspicious_user_agent(user_agent)

        return ua_analysis

    def _analyze_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """보안 헤더 분석"""

        security_headers = {
            "x-frame-options": headers.get("x-frame-options"),
            "x-content-type-options": headers.get("x-content-type-options"),
            "x-xss-protection": headers.get("x-xss-protection"),
            "strict-transport-security": headers.get("strict-transport-security"),
            "content-security-policy": headers.get("content-security-policy"),
            "referrer-policy": headers.get("referrer-policy"),
        }

        # 보안 헤더 점수 계산
        present_headers = [k for k, v in security_headers.items() if v is not None]
        security_score = len(present_headers) / len(security_headers) * 100

        return {
            "headers": security_headers,
            "security_score": round(security_score, 1),
            "missing_headers": [k for k, v in security_headers.items() if v is None],
        }

    def _check_web_security(self, payload_str: str, analysis: Dict[str, Any]) -> List[str]:
        """웹 보안 검사"""

        issues = []

        # SQL 인젝션 패턴 검사
        if self._detect_sql_injection(payload_str):
            issues.append("sql_injection_attempt")

        # XSS 패턴 검사
        if self._detect_xss(payload_str):
            issues.append("xss_attempt")

        # 디렉토리 트래버설 검사
        if self._detect_directory_traversal(payload_str):
            issues.append("directory_traversal")

        # 민감한 파일 접근 시도
        if self._detect_sensitive_file_access(payload_str):
            issues.append("sensitive_file_access")

        # 비정상적인 HTTP 메소드
        method = analysis.get("method", "")
        if method in ["TRACE", "CONNECT", "DEBUG"]:
            issues.append("unusual_http_method")

        return issues

    def _detect_sql_injection(self, payload_str: str) -> bool:
        """SQL 인젝션 탐지"""

        sql_patterns = [
            r"'.*or.*'.*=.*'",
            r"union.*select",
            r"drop.*table",
            r"insert.*into",
            r"delete.*from",
            r"exec.*xp_",
            r"sp_.*password",
        ]

        payload_lower = payload_str.lower()
        return any(re.search(pattern, payload_lower) for pattern in sql_patterns)

    def _detect_xss(self, payload_str: str) -> bool:
        """XSS 탐지"""

        xss_patterns = [
            r"<script.*>",
            r"javascript:",
            r"onerror=",
            r"onload=",
            r"onclick=",
            r"<iframe.*>",
        ]

        payload_lower = payload_str.lower()
        return any(re.search(pattern, payload_lower) for pattern in xss_patterns)

    def _detect_directory_traversal(self, payload_str: str) -> bool:
        """디렉토리 트래버설 탐지"""

        traversal_patterns = [r"\.\./", r"\.\.\\", r"%2e%2e%2f", r"%2e%2e%5c"]

        return any(re.search(pattern, payload_str, re.IGNORECASE) for pattern in traversal_patterns)

    def _detect_sensitive_file_access(self, payload_str: str) -> bool:
        """민감한 파일 접근 탐지"""

        sensitive_files = [
            "passwd",
            "shadow",
            "hosts",
            "web.config",
            ".htaccess",
            ".env",
            "config.php",
            "database.yml",
        ]

        payload_lower = payload_str.lower()
        return any(filename in payload_lower for filename in sensitive_files)

    def _check_suspicious_uri_patterns(self, uri: str) -> List[str]:
        """의심스러운 URI 패턴 검사"""

        patterns = []

        # 긴 쿼리 스트링
        if "?" in uri and len(uri.split("?")[1]) > 1000:
            patterns.append("long_query_string")

        # 과도한 파라미터
        if uri.count("=") > 20:
            patterns.append("excessive_parameters")

        # 인코딩된 공격 패턴
        encoded_patterns = ["%3Cscript%3E", "%27or%27", "%22or%22"]
        if any(pattern in uri.lower() for pattern in encoded_patterns):
            patterns.append("encoded_attack_pattern")

        return patterns

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """의심스러운 User-Agent 검사"""

        suspicious_indicators = [
            len(user_agent) < 10,  # 너무 짧음
            len(user_agent) > 500,  # 너무 김
            user_agent.lower() in ["", "-", "none"],  # 비어있음
            "sql" in user_agent.lower(),
            "hack" in user_agent.lower(),
            "exploit" in user_agent.lower(),
        ]

        return any(suspicious_indicators)

    def _analyze_content(self, payload_str: str) -> Optional[Dict[str, Any]]:
        """콘텐츠 분석"""

        content_analysis = {}

        # HTML 콘텐츠 검사
        if "<html" in payload_str.lower():
            content_analysis["content_type"] = "html"
            content_analysis["title"] = self._extract_html_title(payload_str)

        # JSON 콘텐츠 검사
        elif payload_str.strip().startswith("{") and payload_str.strip().endswith("}"):
            content_analysis["content_type"] = "json"

        # XML 콘텐츠 검사
        elif "<?xml" in payload_str:
            content_analysis["content_type"] = "xml"

        return content_analysis if content_analysis else None

    def _extract_html_title(self, payload_str: str) -> Optional[str]:
        """HTML 제목 추출"""

        title_match = re.search(r"<title>(.*?)</title>", payload_str, re.IGNORECASE | re.DOTALL)
        return title_match.group(1).strip() if title_match else None

    def _calculate_risk_level(self, security_issues: List[str]) -> str:
        """위험 수준 계산"""

        high_risk_issues = [
            "sql_injection_attempt",
            "xss_attempt",
            "directory_traversal",
        ]
        medium_risk_issues = ["sensitive_file_access", "unusual_http_method"]

        if any(issue in high_risk_issues for issue in security_issues):
            return "HIGH"
        elif any(issue in medium_risk_issues for issue in security_issues):
            return "MEDIUM"
        else:
            return "LOW"

    def get_web_statistics(self) -> Dict[str, Any]:
        """웹 트래픽 통계"""

        # HTTP 메소드 통계
        method_counts = {}
        for method in self.http_methods:
            method_counts[method] = method_counts.get(method, 0) + 1

        # 가장 많이 사용된 User-Agent
        ua_counts = {}
        for ua in self.user_agents:
            ua_counts[ua] = ua_counts.get(ua, 0) + 1

        # 가장 많이 접근한 도메인
        domain_counts = {}
        for domain in self.domains:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_requests": len(self.http_methods),
            "method_distribution": method_counts,
            "top_user_agents": sorted(ua_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_domains": sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "unique_user_agents": len(set(self.user_agents)),
            "unique_domains": len(set(self.domains)),
        }

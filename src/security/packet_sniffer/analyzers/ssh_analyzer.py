#!/usr/bin/env python3
"""
SSH 프로토콜 분석기
SSH 연결 및 보안 분석
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SSHAnalyzer:
    """SSH 프로토콜 전용 분석기"""

    def __init__(self):
        self.ssh_versions = []
        self.key_exchanges = []
        self.sessions = {}

    def analyze_ssh(self, payload: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """SSH 패킷 분석"""

        try:
            analysis = {
                "protocol": "SSH",
                "port": packet_info.get("dst_port", 0),
                "payload_size": len(payload),
                "timestamp": packet_info.get("timestamp"),
            }

            payload_str = payload.decode("utf-8", errors="ignore")

            # SSH 버전 식별
            ssh_version_match = re.search(r"SSH-([0-9.]+)-(.+)", payload_str)
            if ssh_version_match:
                analysis["ssh_version"] = ssh_version_match.group(1)
                analysis["ssh_implementation"] = ssh_version_match.group(2)
                analysis["connection_stage"] = "version_exchange"

                # 취약한 SSH 버전 검사
                if ssh_version_match.group(1) in ["1.0", "1.1"]:
                    analysis["security_issues"] = ["outdated_ssh_version"]
                    analysis["risk_level"] = "HIGH"

            # 키 교환 분석
            if b"diffie-hellman" in payload.lower():
                analysis["connection_stage"] = "key_exchange"
                analysis["key_exchange_method"] = "diffie-hellman"

            # 암호화 협상 분석
            if "aes" in payload_str.lower():
                analysis["encryption"] = self._analyze_encryption_methods(payload_str)

            # 인증 시도 탐지
            if any(
                keyword in payload_str.lower()
                for keyword in [
                    "password",
                    "publickey",
                    "keyboard-interactive",
                ]
            ):
                analysis["connection_stage"] = "authentication"
                analysis["auth_method"] = self._detect_auth_method(payload_str)

            # SSH 터널링 탐지
            if self._detect_ssh_tunneling(payload, packet_info):
                analysis["tunneling_detected"] = True
                analysis["risk_level"] = "MEDIUM"

            # 보안 검사
            security_issues = self._check_ssh_security(analysis, payload_str)
            if security_issues:
                analysis["security_issues"] = security_issues

            return analysis

        except Exception as e:
            logger.error(f"SSH 분석 오류: {e}")
            return {
                "protocol": "SSH",
                "error": str(e),
                "payload_size": len(payload),
            }

    def _analyze_encryption_methods(self, payload_str: str) -> Dict[str, Any]:
        """암호화 방법 분석"""

        encryption_info = {"ciphers": [], "strength": "unknown"}

        # 암호화 알고리즘 검출
        cipher_patterns = {
            "aes128-ctr": "AES-128",
            "aes192-ctr": "AES-192",
            "aes256-ctr": "AES-256",
            "aes128-cbc": "AES-128-CBC",
            "aes192-cbc": "AES-192-CBC",
            "aes256-cbc": "AES-256-CBC",
            "3des-cbc": "3DES-CBC",
            "blowfish-cbc": "Blowfish-CBC",
            "cast128-cbc": "CAST-128-CBC",
        }

        for pattern, cipher_name in cipher_patterns.items():
            if pattern in payload_str.lower():
                encryption_info["ciphers"].append(cipher_name)

        # 암호화 강도 평가
        if any("256" in cipher for cipher in encryption_info["ciphers"]):
            encryption_info["strength"] = "strong"
        elif any("128" in cipher for cipher in encryption_info["ciphers"]):
            encryption_info["strength"] = "medium"
        elif any(
            weak in cipher.lower() for cipher in encryption_info["ciphers"] for weak in ["3des", "blowfish", "cast"]
        ):
            encryption_info["strength"] = "weak"

        return encryption_info

    def _detect_auth_method(self, payload_str: str) -> str:
        """인증 방법 탐지"""

        if "password" in payload_str.lower():
            return "password"
        elif "publickey" in payload_str.lower():
            return "public_key"
        elif "keyboard-interactive" in payload_str.lower():
            return "keyboard_interactive"
        elif "gssapi" in payload_str.lower():
            return "gssapi"
        else:
            return "unknown"

    def _detect_ssh_tunneling(self, payload: bytes, packet_info: Dict[str, Any]) -> bool:
        """SSH 터널링 탐지"""

        # 포트 포워딩 패턴 검사
        port_forward_patterns = [
            b"tcpip-forward",
            b"direct-tcpip",
            b"forwarded-tcpip",
        ]

        return any(pattern in payload for pattern in port_forward_patterns)

    def _check_ssh_security(self, analysis: Dict[str, Any], payload_str: str) -> List[str]:
        """SSH 보안 검사"""

        issues = []

        # 취약한 SSH 버전
        ssh_version = analysis.get("ssh_version", "")
        if ssh_version.startswith("1."):
            issues.append("vulnerable_ssh_version")

        # 약한 암호화
        encryption = analysis.get("encryption", {})
        if encryption.get("strength") == "weak":
            issues.append("weak_encryption")

        # 브루트포스 공격 패턴
        if self._detect_brute_force_pattern(payload_str):
            issues.append("potential_brute_force")

        # 비표준 포트 사용
        port = analysis.get("port", 22)
        if port != 22:
            issues.append("non_standard_port")

        return issues

    def _detect_brute_force_pattern(self, payload_str: str) -> bool:
        """브루트포스 공격 패턴 탐지"""

        # 반복적인 실패 패턴 검사
        failure_patterns = [
            "authentication failed",
            "invalid user",
            "permission denied",
        ]

        return any(pattern in payload_str.lower() for pattern in failure_patterns)

    def get_ssh_session_info(self, src_ip: str, dst_ip: str) -> Dict[str, Any]:
        """SSH 세션 정보 조회"""

        session_key = f"{src_ip}:{dst_ip}"
        return self.sessions.get(session_key, {})

    def update_ssh_session(self, src_ip: str, dst_ip: str, analysis: Dict[str, Any]):
        """SSH 세션 정보 업데이트"""

        session_key = f"{src_ip}:{dst_ip}"

        if session_key not in self.sessions:
            self.sessions[session_key] = {
                "start_time": analysis.get("timestamp"),
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "connection_attempts": 0,
                "successful_auth": False,
                "auth_failures": 0,
            }

        session = self.sessions[session_key]
        session["connection_attempts"] += 1
        session["last_activity"] = analysis.get("timestamp")

        # 인증 상태 업데이트
        if analysis.get("connection_stage") == "authentication":
            if "authentication failed" in str(analysis).lower():
                session["auth_failures"] += 1
            elif "authentication successful" in str(analysis).lower():
                session["successful_auth"] = True

    def get_ssh_statistics(self) -> Dict[str, Any]:
        """SSH 분석 통계"""

        total_sessions = len(self.sessions)
        successful_auths = sum(1 for s in self.sessions.values() if s.get("successful_auth"))
        failed_auths = sum(s.get("auth_failures", 0) for s in self.sessions.values())

        # 가장 많이 사용된 SSH 버전
        version_counts = {}
        for version in self.ssh_versions:
            version_counts[version] = version_counts.get(version, 0) + 1

        most_common_version = max(version_counts.items(), key=lambda x: x[1])[0] if version_counts else "unknown"

        return {
            "total_sessions": total_sessions,
            "successful_authentications": successful_auths,
            "failed_authentications": failed_auths,
            "most_common_version": most_common_version,
            "version_distribution": version_counts,
            "active_sessions": len([s for s in self.sessions.values() if s.get("successful_auth")]),
        }

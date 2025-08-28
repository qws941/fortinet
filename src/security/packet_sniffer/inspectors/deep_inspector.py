#!/usr/bin/env python3
"""
딥 패킷 검사 (Deep Packet Inspection)
프로토콜별 심층 분석 및 보안 위협 탐지
"""

import logging
import re
import struct
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeepInspector:
    """딥 패킷 검사 엔진"""

    def __init__(self):
        """딥 패킷 검사 초기화"""
        self.suspicious_patterns = self._load_suspicious_patterns()
        self.protocol_signatures = self._load_protocol_signatures()
        self.statistics = {
            "inspected_packets": 0,
            "threats_detected": 0,
            "last_inspection": None,
        }

    def inspect_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        패킷 딥 검사 수행

        Args:
            packet: 패킷 정보

        Returns:
            dict: 검사 결과
        """
        try:
            self.statistics["inspected_packets"] += 1
            self.statistics["last_inspection"] = datetime.now().isoformat()

            inspection_result = {
                "timestamp": packet.get("timestamp", datetime.now().isoformat()),
                "protocol_analysis": {},
                "security_threats": [],
                "suspicious_patterns": [],
                "payload_analysis": {},
                "malware_indicators": [],
            }

            protocol = packet.get("protocol", "").upper()
            payload = packet.get("payload", b"")

            # 페이로드가 문자열인 경우 바이트로 변환
            if isinstance(payload, str):
                try:
                    payload = payload.encode("utf-8")
                except Exception:
                    payload = b""

            # 프로토콜별 심층 분석
            if protocol == "HTTP":
                inspection_result["protocol_analysis"] = self._analyze_http_packet(packet, payload)
            elif protocol == "TCP" and (packet.get("dst_port") == 443 or packet.get("src_port") == 443):
                inspection_result["protocol_analysis"] = self._analyze_tls_packet(packet, payload)
            elif protocol == "UDP" and (packet.get("dst_port") == 53 or packet.get("src_port") == 53):
                inspection_result["protocol_analysis"] = self._analyze_dns_packet(packet, payload)
            elif protocol == "ICMP":
                inspection_result["protocol_analysis"] = self._analyze_icmp_packet(packet, payload)
            elif protocol == "TCP" and (packet.get("dst_port") == 22 or packet.get("src_port") == 22):
                inspection_result["protocol_analysis"] = self._analyze_ssh_packet(packet, payload)

            # 보안 위협 탐지
            threats = self._detect_security_threats(packet, payload)
            inspection_result["security_threats"] = threats

            # 의심스러운 패턴 탐지
            suspicious = self._detect_suspicious_patterns(packet, payload)
            inspection_result["suspicious_patterns"] = suspicious

            # 페이로드 분석
            payload_analysis = self._analyze_payload(payload)
            inspection_result["payload_analysis"] = payload_analysis

            # 멀웨어 지표 탐지
            malware_indicators = self._detect_malware_indicators(packet, payload)
            inspection_result["malware_indicators"] = malware_indicators

            # 위협 수준 계산
            threat_level = self._calculate_threat_level(inspection_result)
            inspection_result["threat_level"] = threat_level

            if threats or suspicious or malware_indicators:
                self.statistics["threats_detected"] += 1

            return inspection_result

        except Exception as e:
            logger.error(f"딥 패킷 검사 오류: {e}")
            return {
                "error": str(e),
                "timestamp": packet.get("timestamp", datetime.now().isoformat()),
            }

    def _analyze_http_packet(self, packet: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
        """HTTP 패킷 심층 분석"""
        try:
            payload_str = payload.decode("utf-8", errors="ignore")

            analysis = {
                "method": None,
                "url": None,
                "user_agent": None,
                "host": None,
                "status_code": None,
                "content_type": None,
                "suspicious_headers": [],
                "sql_injection_attempt": False,
                "xss_attempt": False,
                "directory_traversal_attempt": False,
            }

            # HTTP 요청 분석
            if payload_str.startswith(("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS")):
                lines = payload_str.split("\r\n")
                if lines:
                    # 첫 번째 줄에서 메서드와 URL 추출
                    request_line = lines[0].split(" ")
                    if len(request_line) >= 2:
                        analysis["method"] = request_line[0]
                        analysis["url"] = request_line[1]

                    # 헤더 분석
                    for line in lines[1:]:
                        if ":" in line:
                            header, value = line.split(":", 1)
                            header = header.strip().lower()
                            value = value.strip()

                            if header == "user-agent":
                                analysis["user_agent"] = value
                            elif header == "host":
                                analysis["host"] = value

                            # 의심스러운 헤더 탐지
                            if self._is_suspicious_header(header, value):
                                analysis["suspicious_headers"].append({"header": header, "value": value})

            # HTTP 응답 분석
            elif payload_str.startswith("HTTP/"):
                lines = payload_str.split("\r\n")
                if lines:
                    # 상태 코드 추출
                    status_line = lines[0].split(" ")
                    if len(status_line) >= 2:
                        try:
                            analysis["status_code"] = int(status_line[1])
                        except ValueError:
                            pass

                    # 헤더 분석
                    for line in lines[1:]:
                        if ":" in line:
                            header, value = line.split(":", 1)
                            header = header.strip().lower()
                            value = value.strip()

                            if header == "content-type":
                                analysis["content_type"] = value

            # 공격 패턴 탐지
            url = analysis.get("url", "")
            if url:
                # SQL 인젝션 탐지
                sql_patterns = [
                    r"('|(\\')|(;)|(--)|(\s+(or|and)\s+))",
                    r"(union\s+select)|(select\s+.*\s+from)",
                    r"(drop\s+table)|(delete\s+from)|(insert\s+into)",
                ]
                for pattern in sql_patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        analysis["sql_injection_attempt"] = True
                        break

                # XSS 탐지
                xss_patterns = [
                    r"<script.*?>.*?</script>",
                    r"javascript:",
                    r"on(load|error|click|mouseover)\s*=",
                ]
                for pattern in xss_patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        analysis["xss_attempt"] = True
                        break

                # 디렉토리 트래버설 탐지
                import os

                normalized_url = os.path.normpath(url)
                if ".." in normalized_url or normalized_url.startswith("/etc/") or "\\" in url:
                    analysis["directory_traversal_attempt"] = True

            return analysis

        except Exception as e:
            logger.error(f"HTTP 패킷 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_tls_packet(self, packet: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
        """TLS/SSL 패킷 심층 분석"""
        try:
            analysis = {
                "tls_version": None,
                "handshake_type": None,
                "cipher_suite": None,
                "sni": None,
                "certificate_info": {},
                "security_level": "unknown",
                "weak_cipher": False,
                "self_signed_cert": False,
            }

            if len(payload) < 5:
                return analysis

            # TLS 레코드 헤더 분석
            record_type = payload[0]
            version_bytes = payload[1:3]

            if len(version_bytes) >= 2:
                version = struct.unpack(">H", version_bytes)[0]

                # TLS 버전 매핑
                version_map = {
                    0x0301: "TLS 1.0",
                    0x0302: "TLS 1.1",
                    0x0303: "TLS 1.2",
                    0x0304: "TLS 1.3",
                    0x0300: "SSL 3.0",
                }
                analysis["tls_version"] = version_map.get(version, f"Unknown (0x{version:04x})")

                # 구버전 SSL/TLS는 취약함
                if version <= 0x0301:
                    analysis["security_level"] = "low"
                elif version == 0x0302:
                    analysis["security_level"] = "medium"
                else:
                    analysis["security_level"] = "high"

            # 핸드셰이크 메시지 분석
            if record_type == 22:  # Handshake
                if len(payload) > 5:
                    handshake_type = payload[5]
                    handshake_types = {
                        1: "Client Hello",
                        2: "Server Hello",
                        11: "Certificate",
                        12: "Server Key Exchange",
                        13: "Certificate Request",
                        14: "Server Hello Done",
                        15: "Certificate Verify",
                        16: "Client Key Exchange",
                        20: "Finished",
                    }
                    analysis["handshake_type"] = handshake_types.get(handshake_type, f"Unknown ({handshake_type})")

                    # Client Hello에서 SNI 추출
                    if handshake_type == 1:
                        sni = self._extract_sni_from_client_hello(payload[5:])
                        if sni:
                            analysis["sni"] = sni

                    # Server Hello에서 암호화 스위트 추출
                    elif handshake_type == 2:
                        cipher_suite = self._extract_cipher_suite(payload[5:])
                        if cipher_suite:
                            analysis["cipher_suite"] = cipher_suite
                            # 약한 암호화 스위트 검사
                            if self._is_weak_cipher(cipher_suite):
                                analysis["weak_cipher"] = True
                                analysis["security_level"] = "low"

            return analysis

        except Exception as e:
            logger.error(f"TLS 패킷 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_dns_packet(self, packet: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
        """DNS 패킷 심층 분석"""
        try:
            analysis = {
                "query_type": None,
                "domain": None,
                "response_code": None,
                "answer_count": 0,
                "dga_suspected": False,
                "entropy_score": 0,
                "suspicious_domain": False,
                "malware_domain": False,
            }

            if len(payload) < 12:
                return analysis

            # DNS 헤더 분석
            header = struct.unpack(">HHHHHH", payload[:12])
            (
                transaction_id,
                flags,
                questions,
                answers,
                authority,
                additional,
            ) = header

            analysis["answer_count"] = answers

            # 응답 코드 추출
            rcode = flags & 0xF
            rcodes = {
                0: "NOERROR",
                1: "FORMERR",
                2: "SERVFAIL",
                3: "NXDOMAIN",
                4: "NOTIMP",
                5: "REFUSED",
            }
            analysis["response_code"] = rcodes.get(rcode, f"Unknown ({rcode})")

            # 질의 섹션 분석
            if questions > 0 and len(payload) > 12:
                domain, query_type = self._parse_dns_question(payload[12:])
                if domain:
                    analysis["domain"] = domain
                    analysis["query_type"] = query_type

                    # 도메인 분석
                    entropy = self._calculate_entropy(domain)
                    analysis["entropy_score"] = entropy

                    # DGA 의심 (높은 엔트로피)
                    if entropy > 4.5:
                        analysis["dga_suspected"] = True

                    # 의심스러운 도메인 패턴
                    if self._is_suspicious_domain(domain):
                        analysis["suspicious_domain"] = True

                    # 알려진 멀웨어 도메인 확인
                    if self._is_malware_domain(domain):
                        analysis["malware_domain"] = True

            return analysis

        except Exception as e:
            logger.error(f"DNS 패킷 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_icmp_packet(self, packet: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
        """ICMP 패킷 심층 분석"""
        try:
            analysis = {
                "icmp_type": None,
                "icmp_code": None,
                "payload_size": len(payload),
                "tunnel_suspected": False,
                "dos_pattern": False,
                "covert_channel": False,
            }

            if len(payload) < 8:
                return analysis

            icmp_type = payload[0]
            icmp_code = payload[1]

            analysis["icmp_type"] = icmp_type
            analysis["icmp_code"] = icmp_code

            # ICMP 터널링 의심 (큰 페이로드)
            if len(payload) > 100:
                analysis["tunnel_suspected"] = True

            # Ping flood 패턴 (Echo Request with large payload)
            if icmp_type == 8 and len(payload) > 1000:
                analysis["dos_pattern"] = True

            # 은밀한 채널 탐지 (비정상적인 ICMP 코드)
            if icmp_type in [8, 0] and icmp_code != 0:
                analysis["covert_channel"] = True

            return analysis

        except Exception as e:
            logger.error(f"ICMP 패킷 분석 오류: {e}")
            return {"error": str(e)}

    def _analyze_ssh_packet(self, packet: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
        """SSH 패킷 심층 분석"""
        try:
            analysis = {
                "ssh_version": None,
                "key_exchange": False,
                "authentication_attempt": False,
                "weak_algorithms": [],
                "brute_force_pattern": False,
            }

            payload_str = payload.decode("utf-8", errors="ignore")

            # SSH 버전 식별
            if payload_str.startswith("SSH-"):
                version_line = payload_str.split("\r\n")[0]
                analysis["ssh_version"] = version_line

                # SSH-1.x는 취약함
                if "SSH-1." in version_line:
                    analysis["weak_algorithms"].append("SSH Protocol 1.x")

            # 키 교환 감지
            if b"\x00\x00\x00" in payload[:4]:  # SSH 패킷 길이 필드
                analysis["key_exchange"] = True

            # 인증 시도 감지 (단순 휴리스틱)
            if "password" in payload_str.lower() or "auth" in payload_str.lower():
                analysis["authentication_attempt"] = True

            return analysis

        except Exception as e:
            logger.error(f"SSH 패킷 분석 오류: {e}")
            return {"error": str(e)}

    def _detect_security_threats(self, packet: Dict[str, Any], payload: bytes) -> List[Dict[str, Any]]:
        """보안 위협 탐지"""
        threats = []

        try:
            payload_str = payload.decode("utf-8", errors="ignore").lower()

            # 버퍼 오버플로 시도
            if len(payload) > 10000:
                threats.append(
                    {
                        "type": "buffer_overflow",
                        "severity": "high",
                        "description": f"비정상적으로 큰 패킷 크기: {len(payload)} bytes",
                    }
                )

            # 쉘코드 패턴
            shellcode_patterns = [
                b"\x90" * 10,  # NOP sled
                b"\xcc",  # INT3
                b"\x31\xc0",  # XOR EAX, EAX
            ]

            for pattern in shellcode_patterns:
                if pattern in payload:
                    threats.append(
                        {
                            "type": "shellcode",
                            "severity": "critical",
                            "description": "쉘코드 패턴 감지",
                        }
                    )
                    break

            # 백도어 시그니처
            backdoor_strings = [
                "metasploit",
                "meterpreter",
                "backdoor",
                "rootkit",
                "keylogger",
                "trojan",
                "netcat",
            ]

            for backdoor in backdoor_strings:
                if backdoor in payload_str:
                    threats.append(
                        {
                            "type": "backdoor",
                            "severity": "critical",
                            "description": f"백도어 시그니처 감지: {backdoor}",
                        }
                    )

            # 익스플로잇 킷
            exploit_patterns = [
                "exploit",
                "payload",
                "rop",
                "heap spray",
                "use after free",
                "format string",
            ]

            for exploit in exploit_patterns:
                if exploit in payload_str:
                    threats.append(
                        {
                            "type": "exploit",
                            "severity": "high",
                            "description": f"익스플로잇 패턴 감지: {exploit}",
                        }
                    )

        except Exception as e:
            logger.error(f"보안 위협 탐지 오류: {e}")

        return threats

    def _detect_suspicious_patterns(self, packet: Dict[str, Any], payload: bytes) -> List[Dict[str, Any]]:
        """의심스러운 패턴 탐지"""
        patterns = []

        try:
            # Base64 인코딩된 데이터 (대량)
            payload_str = payload.decode("utf-8", errors="ignore")
            base64_matches = re.findall(r"[A-Za-z0-9+/]{50,}={0,2}", payload_str)

            if base64_matches:
                patterns.append(
                    {
                        "type": "base64_data",
                        "severity": "medium",
                        "description": f"{len(base64_matches)}개의 Base64 인코딩된 데이터 블록 발견",
                    }
                )

            # 16진수 데이터
            hex_matches = re.findall(r"[0-9a-fA-F]{100,}", payload_str)
            if hex_matches:
                patterns.append(
                    {
                        "type": "hex_data",
                        "severity": "low",
                        "description": f"{len(hex_matches)}개의 긴 16진수 문자열 발견",
                    }
                )

            # 의심스러운 URL 패턴
            suspicious_urls = re.findall(r"https?://[^\s]+", payload_str)
            for url in suspicious_urls:
                if any(domain in url.lower() for domain in ["bit.ly", "tinyurl", "short.link"]):
                    patterns.append(
                        {
                            "type": "suspicious_url",
                            "severity": "medium",
                            "description": f"의심스러운 단축 URL: {url}",
                        }
                    )

        except Exception as e:
            logger.error(f"의심스러운 패턴 탐지 오류: {e}")

        return patterns

    def _analyze_payload(self, payload: bytes) -> Dict[str, Any]:
        """페이로드 분석"""
        try:
            analysis = {
                "size": len(payload),
                "entropy": self._calculate_entropy(payload),
                "printable_ratio": 0,
                "null_bytes": payload.count(b"\x00"),
                "file_signatures": [],
            }

            if payload:
                # 출력 가능한 문자 비율
                try:
                    text = payload.decode("utf-8", errors="ignore")
                    printable_chars = sum(1 for c in text if c.isprintable())
                    analysis["printable_ratio"] = printable_chars / len(text) if text else 0
                except Exception:
                    analysis["printable_ratio"] = 0

                # 파일 시그니처 확인
                file_sigs = self._detect_file_signatures(payload)
                analysis["file_signatures"] = file_sigs

            return analysis

        except Exception as e:
            logger.error(f"페이로드 분석 오류: {e}")
            return {"error": str(e)}

    def _detect_malware_indicators(self, packet: Dict[str, Any], payload: bytes) -> List[Dict[str, Any]]:
        """멀웨어 지표 탐지"""
        indicators = []

        try:
            payload_str = payload.decode("utf-8", errors="ignore").lower()

            # 알려진 멀웨어 시그니처
            malware_signatures = [
                "wannacry",
                "petya",
                "conficker",
                "stuxnet",
                "emotet",
                "trickbot",
                "ransomware",
            ]

            for signature in malware_signatures:
                if signature in payload_str:
                    indicators.append(
                        {
                            "type": "malware_signature",
                            "name": signature,
                            "severity": "critical",
                        }
                    )

            # C&C 통신 패턴
            if packet.get("dst_port") in [8080, 8443, 9999] and len(payload) > 100:
                indicators.append(
                    {
                        "type": "cnc_communication",
                        "severity": "high",
                        "description": "의심스러운 C&C 통신 패턴",
                    }
                )

        except Exception as e:
            logger.error(f"멀웨어 지표 탐지 오류: {e}")

        return indicators

    def _calculate_threat_level(self, inspection_result: Dict[str, Any]) -> str:
        """위협 수준 계산"""
        score = 0

        # 보안 위협
        for threat in inspection_result.get("security_threats", []):
            if threat.get("severity") == "critical":
                score += 10
            elif threat.get("severity") == "high":
                score += 5
            elif threat.get("severity") == "medium":
                score += 2

        # 멀웨어 지표
        for indicator in inspection_result.get("malware_indicators", []):
            if indicator.get("severity") == "critical":
                score += 10
            elif indicator.get("severity") == "high":
                score += 5

        # 의심스러운 패턴
        score += len(inspection_result.get("suspicious_patterns", []))

        # 위협 수준 결정
        if score >= 10:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 2:
            return "medium"
        elif score >= 1:
            return "low"
        else:
            return "none"

    def _load_suspicious_patterns(self) -> List[str]:
        """의심스러운 패턴 로드"""
        return [
            r"eval\s*\(",
            r"exec\s*\(",
            r"system\s*\(",
            r"cmd\s*\.",
            r"powershell",
            r"\\x[0-9a-fA-F]{2}",
            r"%[0-9a-fA-F]{2}",
        ]

    def _load_protocol_signatures(self) -> Dict[str, List[bytes]]:
        """프로토콜 시그니처 로드"""
        return {
            "http": [b"GET ", b"POST ", b"HTTP/"],
            "ftp": [b"USER ", b"PASS ", b"RETR "],
            "smtp": [b"HELO ", b"MAIL FROM:", b"RCPT TO:"],
            "pop3": [b"USER ", b"PASS ", b"+OK "],
            "ssh": [b"SSH-"],
            "tls": [b"\x16\x03"],
        }

    def _extract_sni_from_client_hello(self, handshake_data: bytes) -> Optional[str]:
        """Client Hello에서 SNI 추출"""
        try:
            # 간단한 SNI 추출 로직 (실제로는 더 복잡함)
            if len(handshake_data) > 40:
                # SNI 확장 찾기
                if b"\x00\x00" in handshake_data:  # server_name extension
                    # 실제 구현에서는 TLS 구조를 정확히 파싱해야 함
                    pass
            return None
        except Exception:
            return None

    def _extract_cipher_suite(self, handshake_data: bytes) -> Optional[str]:
        """Server Hello에서 암호화 스위트 추출"""
        try:
            if len(handshake_data) > 6:
                # 간단한 암호화 스위트 추출
                cipher_suite_bytes = handshake_data[6:8]
                if len(cipher_suite_bytes) == 2:
                    cipher_id = struct.unpack(">H", cipher_suite_bytes)[0]
                    return f"0x{cipher_id:04x}"
            return None
        except Exception:
            return None

    def _is_weak_cipher(self, cipher_suite: str) -> bool:
        """약한 암호화 스위트 확인"""
        weak_ciphers = [
            "0x0004",  # TLS_RSA_WITH_RC4_128_MD5
            "0x0005",  # TLS_RSA_WITH_RC4_128_SHA
            "0x000a",  # TLS_RSA_WITH_3DES_EDE_CBC_SHA
        ]
        return cipher_suite in weak_ciphers

    def _parse_dns_question(self, question_data: bytes) -> tuple:
        """DNS 질의 섹션 파싱"""
        try:
            domain_parts = []
            offset = 0

            while offset < len(question_data):
                length = question_data[offset]
                if length == 0:
                    offset += 1
                    break
                if offset + length + 1 > len(question_data):
                    break

                part = question_data[offset + 1 : offset + 1 + length].decode("utf-8", errors="ignore")
                domain_parts.append(part)
                offset += length + 1

            domain = ".".join(domain_parts)

            # 질의 타입과 클래스
            if offset + 4 <= len(question_data):
                qtype, qclass = struct.unpack(">HH", question_data[offset : offset + 4])
                query_types = {
                    1: "A",
                    2: "NS",
                    5: "CNAME",
                    15: "MX",
                    16: "TXT",
                    28: "AAAA",
                }
                return domain, query_types.get(qtype, f"TYPE{qtype}")

            return domain, "UNKNOWN"

        except Exception as e:
            logger.error(f"DNS 질의 파싱 오류: {e}")
            return None, None

    def _calculate_entropy(self, data: bytes) -> float:
        """데이터 엔트로피 계산"""
        try:
            if not data:
                return 0

            # 바이트 빈도 계산
            byte_counts = defaultdict(int)
            for byte in data:
                byte_counts[byte] += 1

            # 엔트로피 계산
            entropy = 0
            length = len(data)

            for count in byte_counts.values():
                probability = count / length
                entropy -= probability * (probability.bit_length() - 1)

            return entropy

        except Exception:
            return 0

    def _is_suspicious_domain(self, domain: str) -> bool:
        """의심스러운 도메인 패턴 확인"""
        suspicious_patterns = [
            r"[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}",  # IP 형태 도메인
            r"[a-z]{20,}",  # 매우 긴 랜덤 문자열
            r"[0-9]{5,}",  # 숫자만으로 된 긴 문자열
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return True

        return False

    def _is_malware_domain(self, domain: str) -> bool:
        """알려진 멀웨어 도메인 확인"""
        # 실제 구현에서는 위협 인텔리전스 피드 사용
        malware_domains = ["malware.com", "botnet.net", "trojan.org"]

        return any(malware in domain.lower() for malware in malware_domains)

    def _detect_file_signatures(self, payload: bytes) -> List[str]:
        """파일 시그니처 탐지"""
        signatures = []

        if len(payload) < 4:
            return signatures

        # 파일 매직 바이트
        file_signatures = {
            b"\x89PNG": "PNG Image",
            b"\xff\xd8\xff": "JPEG Image",
            b"GIF8": "GIF Image",
            b"PK\x03\x04": "ZIP Archive",
            b"%PDF": "PDF Document",
            b"MZ": "Executable",
            b"\x7fELF": "ELF Executable",
        }

        for signature, file_type in file_signatures.items():
            if payload.startswith(signature):
                signatures.append(file_type)

        return signatures

    def _is_suspicious_header(self, header: str, value: str) -> bool:
        """의심스러운 HTTP 헤더 확인"""
        suspicious_headers = {
            "x-forwarded-for": lambda v: len(v.split(",")) > 10,  # 과도한 프록시 체인
            "user-agent": lambda v: len(v) > 500 or "bot" in v.lower(),  # 비정상적인 UA
            "referer": lambda v: "javascript:" in v.lower(),  # XSS 시도
        }

        if header in suspicious_headers:
            return suspicious_headers[header](value)

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """검사 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "inspected_packets": 0,
            "threats_detected": 0,
            "last_inspection": None,
        }
        logger.info("딥 패킷 검사 통계 초기화됨")


# 팩토리 함수
def create_deep_inspector() -> DeepInspector:
    """딥 패킷 검사 인스턴스 생성"""
    return DeepInspector()

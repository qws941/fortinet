#!/usr/bin/env python3
"""
DNS 분석기 - DNS 프로토콜 전용 분석
"""

import struct
from typing import Any, Dict, List, Optional, Tuple

from security.packet_sniffer.base_sniffer import PacketInfo

from .protocol_analyzer import BaseProtocolAnalyzer, ProtocolAnalysisResult


class DnsAnalyzer(BaseProtocolAnalyzer):
    """DNS 프로토콜 분석기"""

    def __init__(self):
        super().__init__("dns")

        # DNS 레코드 타입
        self.record_types = {
            1: "A",
            2: "NS",
            5: "CNAME",
            6: "SOA",
            12: "PTR",
            15: "MX",
            16: "TXT",
            28: "AAAA",
            33: "SRV",
            35: "NAPTR",
            39: "DNAME",
            41: "OPT",
            43: "DS",
            46: "RRSIG",
            47: "NSEC",
            48: "DNSKEY",
            50: "NSEC3",
            51: "NSEC3PARAM",
            52: "TLSA",
            257: "CAA",
        }

        # DNS 응답 코드
        self.response_codes = {
            0: "NOERROR",
            1: "FORMERR",
            2: "SERVFAIL",
            3: "NXDOMAIN",
            4: "NOTIMP",
            5: "REFUSED",
            6: "YXDOMAIN",
            7: "YXRRSET",
            8: "NXRRSET",
            9: "NOTAUTH",
            10: "NOTZONE",
        }

        # DNS 클래스
        self.dns_classes = {
            1: "IN",
            2: "CS",
            3: "CH",
            4: "HS",
            254: "NONE",
            255: "ANY",
        }

        # 의심스러운 도메인 패턴
        self.suspicious_patterns = [
            r"[a-f0-9]{8,}\.",  # 긴 헥스 문자열
            r"[0-9]{8,}\.",  # 긴 숫자 문자열
            r".*\.tk$",
            r".*\.ml$",
            r".*\.ga$",  # 무료 도메인
            r".*\.onion$",  # Tor 도메인
        ]

    def can_analyze(self, packet: PacketInfo) -> bool:
        """DNS 패킷 분석 가능 여부 확인"""
        # DNS 포트 확인
        if packet.dst_port == 53 or packet.src_port == 53:
            return True

        # DNS over HTTPS (DoH) 포트
        if (
            packet.dst_port == 443 or packet.src_port == 443
        ) and packet.protocol == "TCP":
            return True

        # 페이로드 시그니처 확인
        if packet.payload and len(packet.payload) >= 12:
            return self._has_dns_signature(packet.payload)

        return False

    def analyze(self, packet: PacketInfo) -> Optional[ProtocolAnalysisResult]:
        """DNS 패킷 분석"""
        if not self.can_analyze(packet):
            return None

        try:
            # DNS 패킷 파싱
            dns_data = self._parse_dns_packet(packet.payload)
            if not dns_data:
                return None

            # 보안 분석
            security_flags = self._analyze_dns_security(dns_data)

            # 이상 탐지
            anomalies = self._detect_dns_anomalies(dns_data)

            confidence = self._calculate_dns_confidence(packet, dns_data)

            return ProtocolAnalysisResult(
                protocol="DNS",
                confidence=confidence,
                details=dns_data,
                flags=self._extract_dns_flags(dns_data),
                security_flags=security_flags,
                anomalies=anomalies,
            )

        except Exception as e:
            self.logger.error(f"DNS 분석 실패: {e}")
            return None

    def _has_dns_signature(self, payload: bytes) -> bool:
        """DNS 시그니처 확인"""
        if len(payload) < 12:
            return False

        try:
            # DNS 헤더 파싱
            header = struct.unpack("!HHHHHH", payload[:12])
            transaction_id, flags, qdcount, ancount, nscount, arcount = header

            # 기본 검증
            if qdcount > 100 or ancount > 100 or nscount > 100 or arcount > 100:
                return False

            # QR 비트와 opcode 확인
            (flags >> 15) & 1
            opcode = (flags >> 11) & 15

            # 유효한 opcode 범위
            if opcode > 2:
                return False

            return True

        except Exception:
            return False

    def _parse_dns_packet(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """DNS 패킷 파싱"""
        if len(payload) < 12:
            return None

        try:
            # DNS 헤더 파싱
            header = struct.unpack("!HHHHHH", payload[:12])
            transaction_id, flags, qdcount, ancount, nscount, arcount = header

            # 플래그 분해
            qr = (flags >> 15) & 1
            opcode = (flags >> 11) & 15
            aa = (flags >> 10) & 1
            tc = (flags >> 9) & 1
            rd = (flags >> 8) & 1
            ra = (flags >> 7) & 1
            z = (flags >> 4) & 7
            rcode = flags & 15

            dns_data = {
                "transaction_id": transaction_id,
                "flags": {
                    "qr": bool(qr),
                    "opcode": opcode,
                    "aa": bool(aa),
                    "tc": bool(tc),
                    "rd": bool(rd),
                    "ra": bool(ra),
                    "z": z,
                    "rcode": rcode,
                },
                "questions": qdcount,
                "answers": ancount,
                "authority": nscount,
                "additional": arcount,
                "type": "response" if qr else "query",
                "opcode_name": self._get_opcode_name(opcode),
                "rcode_name": self.response_codes.get(rcode, f"Unknown({rcode})"),
            }

            # 질문 섹션 파싱
            offset = 12
            if qdcount > 0 and qdcount <= 10:  # 합리적인 수의 질문만 파싱
                questions, offset = self._parse_questions(payload, offset, qdcount)
                dns_data["question_details"] = questions

            # 응답 섹션 파싱 (간단히)
            if qr and ancount > 0 and ancount <= 10:
                answers = self._parse_answers(payload, offset, ancount)
                if answers:
                    dns_data["answer_details"] = answers

            return dns_data

        except Exception as e:
            self.logger.debug(f"DNS 파싱 실패: {e}")
            return None

    def _get_opcode_name(self, opcode: int) -> str:
        """Opcode 이름 반환"""
        opcodes = {0: "QUERY", 1: "IQUERY", 2: "STATUS"}
        return opcodes.get(opcode, f"Unknown({opcode})")

    def _parse_questions(
        self, payload: bytes, offset: int, count: int
    ) -> Tuple[List[Dict], int]:
        """DNS 질문 섹션 파싱"""
        questions = []

        for _ in range(count):
            try:
                # 도메인 이름 파싱
                domain, new_offset = self._parse_domain_name(payload, offset)

                if new_offset + 4 > len(payload):
                    break

                # 쿼리 타입과 클래스
                qtype, qclass = struct.unpack(
                    "!HH", payload[new_offset : new_offset + 4]
                )

                questions.append(
                    {
                        "domain": domain,
                        "type": self.record_types.get(qtype, f"Unknown({qtype})"),
                        "class": self.dns_classes.get(qclass, f"Unknown({qclass})"),
                        "type_code": qtype,
                        "class_code": qclass,
                    }
                )

                offset = new_offset + 4

            except Exception as e:
                self.logger.debug(f"질문 파싱 실패: {e}")
                break

        return questions, offset

    def _parse_answers(self, payload: bytes, offset: int, count: int) -> List[Dict]:
        """DNS 응답 섹션 파싱 (간단히)"""
        answers = []

        for _ in range(min(count, 5)):  # 최대 5개만 파싱
            try:
                # 이름 파싱
                name, new_offset = self._parse_domain_name(payload, offset)

                if new_offset + 10 > len(payload):
                    break

                # 리소스 레코드 헤더
                rr_type, rr_class, ttl, rdlength = struct.unpack(
                    "!HHIH", payload[new_offset : new_offset + 10]
                )

                answer = {
                    "name": name,
                    "type": self.record_types.get(rr_type, f"Unknown({rr_type})"),
                    "class": self.dns_classes.get(rr_class, f"Unknown({rr_class})"),
                    "ttl": ttl,
                    "rdlength": rdlength,
                }

                # 데이터 파싱 (타입별로 간단히)
                data_offset = new_offset + 10
                if data_offset + rdlength <= len(payload):
                    rdata = payload[data_offset : data_offset + rdlength]
                    answer["rdata"] = self._parse_rdata(rr_type, rdata, payload)

                answers.append(answer)
                offset = data_offset + rdlength

            except Exception as e:
                self.logger.debug(f"응답 파싱 실패: {e}")
                break

        return answers

    def _parse_domain_name(self, payload: bytes, offset: int) -> Tuple[str, int]:
        """도메인 이름 파싱"""
        labels = []
        original_offset = offset
        jumped = False

        while offset < len(payload):
            length = payload[offset]

            if length == 0:
                offset += 1
                break
            elif (length & 0xC0) == 0xC0:  # 압축 포인터
                if not jumped:
                    original_offset = offset + 2
                    jumped = True
                pointer = ((length & 0x3F) << 8) | payload[offset + 1]
                offset = pointer
            else:
                offset += 1
                if offset + length > len(payload):
                    break
                label = payload[offset : offset + length].decode(
                    "utf-8", errors="ignore"
                )
                labels.append(label)
                offset += length

        domain = ".".join(labels) if labels else ""
        return domain, original_offset if jumped else offset

    def _parse_rdata(self, rr_type: int, rdata: bytes, full_payload: bytes) -> str:
        """리소스 데이터 파싱"""
        try:
            if rr_type == 1:  # A 레코드
                if len(rdata) == 4:
                    return ".".join(str(b) for b in rdata)
            elif rr_type == 28:  # AAAA 레코드
                if len(rdata) == 16:
                    return ":".join(
                        f"{rdata[i]:02x}{rdata[i + 1]:02x}" for i in range(0, 16, 2)
                    )
            elif rr_type in [2, 5, 12]:  # NS, CNAME, PTR
                domain, _ = self._parse_domain_name(full_payload, 0)  # 간소화
                return domain
            elif rr_type == 15:  # MX 레코드
                if len(rdata) >= 2:
                    priority = struct.unpack("!H", rdata[:2])[0]
                    return f"Priority: {priority}"

            # 기본적으로 헥스 덤프
            return rdata.hex() if len(rdata) <= 32 else f"{rdata[:32].hex()}..."

        except Exception:
            return "Parse Error"

    def _analyze_dns_security(self, dns_data: Dict[str, Any]) -> Dict[str, Any]:
        """DNS 보안 분석"""
        security_flags = {}

        # DNS over TLS/HTTPS 탐지
        if dns_data.get("flags", {}).get("encrypted"):
            security_flags["encrypted_dns"] = True

        # DNSSEC 관련 플래그
        flags = dns_data.get("flags", {})
        if flags.get("cd") or flags.get("ad"):
            security_flags["dnssec_related"] = True

        # 응답 코드 분석
        rcode = flags.get("rcode", 0)
        if rcode != 0:
            security_flags["error_response"] = True
            security_flags["error_type"] = self.response_codes.get(rcode, "Unknown")

        # 질문 분석
        questions = dns_data.get("question_details", [])
        for question in questions:
            domain = question.get("domain", "")

            # 의심스러운 도메인 패턴
            import re

            for pattern in self.suspicious_patterns:
                if re.search(pattern, domain, re.IGNORECASE):
                    security_flags["suspicious_domain"] = True
                    security_flags["suspicious_pattern"] = pattern
                    break

            # DGA (Domain Generation Algorithm) 탐지
            if self._is_potential_dga(domain):
                security_flags["potential_dga"] = True

            # 터널링 탐지
            if self._is_potential_tunneling(domain):
                security_flags["potential_tunneling"] = True

        return security_flags

    def _detect_dns_anomalies(self, dns_data: Dict[str, Any]) -> List[str]:
        """DNS 이상 탐지"""
        anomalies = []

        # 비정상적인 레코드 수
        if dns_data.get("questions", 0) > 10:
            anomalies.append(f"Too many questions: {dns_data['questions']}")

        if dns_data.get("answers", 0) > 50:
            anomalies.append(f"Too many answers: {dns_data['answers']}")

        # 비정상적인 트랜잭션 ID 패턴
        tid = dns_data.get("transaction_id", 0)
        if tid == 0 or tid == 0xFFFF:
            anomalies.append("Unusual transaction ID")

        # 재귀 요청이지만 재귀 불가능
        flags = dns_data.get("flags", {})
        if flags.get("rd") and not flags.get("ra") and flags.get("qr"):
            anomalies.append("Recursion desired but not available")

        # 권위 응답이지만 권위 서버가 아님
        if flags.get("aa") and flags.get("qr") and flags.get("rcode") == 3:
            anomalies.append("Authoritative answer for NXDOMAIN")

        # 질문 도메인 분석
        questions = dns_data.get("question_details", [])
        for question in questions:
            domain = question.get("domain", "")

            # 매우 긴 도메인
            if len(domain) > 253:
                anomalies.append(f"Extremely long domain: {len(domain)} chars")

            # 매우 깊은 서브도메인
            if domain.count(".") > 10:
                anomalies.append(f"Deep subdomain: {domain.count('.')} levels")

            # 숫자만으로 이루어진 라벨
            labels = domain.split(".")
            numeric_labels = [label for label in labels if label.isdigit()]
            if len(numeric_labels) > len(labels) / 2:
                anomalies.append("Many numeric labels in domain")

        return anomalies

    def _is_potential_dga(self, domain: str) -> bool:
        """DGA 도메인 탐지"""
        if not domain or "." not in domain:
            return False

        # 기본 검사
        labels = domain.split(".")
        if len(labels) < 2:
            return False

        # 두 번째 레벨 도메인 분석
        sld = labels[-2]

        # 길이 검사
        if len(sld) < 6 or len(sld) > 20:
            return False

        # 문자 패턴 분석
        vowels = "aeiou"
        consonants = "bcdfghjklmnpqrstvwxyz"

        vowel_count = sum(1 for c in sld.lower() if c in vowels)
        consonant_count = sum(1 for c in sld.lower() if c in consonants)

        # 자음/모음 비율 이상
        if vowel_count == 0 or consonant_count / vowel_count > 4:
            return True

        # 연속된 자음 검사
        consecutive_consonants = 0
        max_consecutive = 0
        for c in sld.lower():
            if c in consonants:
                consecutive_consonants += 1
                max_consecutive = max(max_consecutive, consecutive_consonants)
            else:
                consecutive_consonants = 0

        if max_consecutive > 4:
            return True

        return False

    def _is_potential_tunneling(self, domain: str) -> bool:
        """DNS 터널링 탐지"""
        if not domain:
            return False

        # 매우 긴 서브도메인 라벨
        labels = domain.split(".")
        for label in labels:
            if len(label) > 63:  # DNS 라벨 최대 길이
                return True

            # Base64 패턴 (터널링에서 흔히 사용)
            if len(label) > 20 and label.replace("-", "").replace("_", "").isalnum():
                # Base64 문자 비율 확인
                b64_chars = (
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
                )
                b64_ratio = sum(1 for c in label if c in b64_chars) / len(label)
                if b64_ratio > 0.8:
                    return True

        # 너무 깊은 서브도메인
        if len(labels) > 8:
            return True

        return False

    def _extract_dns_flags(self, dns_data: Dict[str, Any]) -> Dict[str, bool]:
        """DNS 플래그 추출"""
        flags = dns_data.get("flags", {})

        return {
            "is_query": not flags.get("qr", False),
            "is_response": flags.get("qr", False),
            "is_authoritative": flags.get("aa", False),
            "is_truncated": flags.get("tc", False),
            "recursion_desired": flags.get("rd", False),
            "recursion_available": flags.get("ra", False),
            "has_error": flags.get("rcode", 0) != 0,
        }

    def _calculate_dns_confidence(
        self, packet: PacketInfo, dns_data: Dict[str, Any]
    ) -> float:
        """DNS 신뢰도 계산"""
        confidence = 0.0

        # 포트 기반 신뢰도
        if packet.dst_port == 53 or packet.src_port == 53:
            confidence = 0.9
        else:
            confidence = 0.5

        # 구조적 유효성
        if dns_data.get("questions", 0) > 0 and dns_data.get("questions", 0) <= 10:
            confidence += 0.1

        # 유효한 도메인 존재
        questions = dns_data.get("question_details", [])
        if questions and any(q.get("domain") for q in questions):
            confidence += 0.1

        # 유효한 opcode와 rcode
        flags = dns_data.get("flags", {})
        if flags.get("opcode", 99) <= 2 and flags.get("rcode", 99) <= 10:
            confidence += 0.05

        return min(confidence, 1.0)

    def get_confidence_score(self, packet: PacketInfo) -> float:
        """신뢰도 점수 계산"""
        if not self.can_analyze(packet):
            return 0.0

        try:
            dns_data = self._parse_dns_packet(packet.payload)
            if dns_data:
                return self._calculate_dns_confidence(packet, dns_data)
        except Exception:
            pass

        return 0.0

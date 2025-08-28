#!/usr/bin/env python3
"""
BPF (Berkeley Packet Filter) 필터
표준 BPF 문법을 사용한 패킷 필터링
"""

import logging
import re
from ipaddress import ip_address, ip_network
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BPFFilter:
    """BPF 형식 패킷 필터"""

    def __init__(self):
        """BPF 필터 초기화"""
        self.filter_string = ""
        self.compiled_filter = None
        self.statistics = {
            "total_packets": 0,
            "matched_packets": 0,
            "compilation_errors": 0,
        }

    def set_filter(self, filter_string: str) -> bool:
        """
        BPF 필터 문자열 설정 및 컴파일

        Args:
            filter_string: BPF 필터 문자열

        Returns:
            bool: 컴파일 성공 여부
        """
        try:
            self.filter_string = filter_string.strip()

            if not self.filter_string:
                self.compiled_filter = None
                return True

            # BPF 문법 검증 및 파싱
            self.compiled_filter = self._compile_bpf(self.filter_string)

            if self.compiled_filter is None:
                self.statistics["compilation_errors"] += 1
                return False

            logger.info(f"BPF 필터 컴파일 성공: {filter_string}")
            return True

        except Exception as e:
            logger.error(f"BPF 필터 컴파일 오류: {e}")
            self.statistics["compilation_errors"] += 1
            return False

    def matches(self, packet_info: Dict[str, Any]) -> bool:
        """
        패킷이 BPF 필터와 매치되는지 확인

        Args:
            packet_info: 패킷 정보

        Returns:
            bool: 매치 여부
        """
        try:
            self.statistics["total_packets"] += 1

            if self.compiled_filter is None:
                return True  # 필터가 없으면 모든 패킷 통과

            result = self._evaluate_filter(self.compiled_filter, packet_info)

            if result:
                self.statistics["matched_packets"] += 1

            return result

        except Exception as e:
            logger.error(f"BPF 필터 매칭 오류: {e}")
            return False

    def _compile_bpf(self, filter_string: str) -> Optional[Dict[str, Any]]:
        """
        BPF 필터 문자열을 파싱하여 내부 표현으로 컴파일

        Args:
            filter_string: BPF 필터 문자열

        Returns:
            dict: 컴파일된 필터 또는 None
        """
        try:
            # 공백 정규화
            filter_string = " ".join(filter_string.split())

            # 논리 연산자로 분할
            tokens = self._tokenize(filter_string)

            # 파싱 트리 생성
            parsed = self._parse_tokens(tokens)

            return parsed

        except Exception as e:
            logger.error(f"BPF 컴파일 오류: {e}")
            return None

    def _tokenize(self, filter_string: str) -> List[str]:
        """필터 문자열을 토큰으로 분할"""
        # 논리 연산자와 괄호를 기준으로 토큰화
        pattern = r"(\s+and\s+|\s+or\s+|\s+not\s+|[()])"

        tokens = []
        parts = re.split(pattern, filter_string, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()
            if part and part.lower() not in ["and", "or", "not", "(", ")"]:
                tokens.append(part)
            elif part.lower() in ["and", "or", "not", "(", ")"]:
                tokens.append(part.lower())

        return [t for t in tokens if t]

    def _parse_tokens(self, tokens: List[str]) -> Dict[str, Any]:
        """토큰 리스트를 파싱하여 필터 트리 생성"""
        if not tokens:
            return {"type": "always_true"}

        # 단일 조건인 경우
        if len(tokens) == 1:
            return self._parse_condition(tokens[0])

        # 복합 조건 파싱
        return self._parse_expression(tokens)

    def _parse_expression(self, tokens: List[str]) -> Dict[str, Any]:
        """복합 표현식 파싱"""
        # 간단한 좌에서 우로 파싱 (실제 BPF는 더 복잡한 우선순위 적용)
        if len(tokens) == 3 and tokens[1].lower() in ["and", "or"]:
            return {
                "type": "binary_op",
                "operator": tokens[1].lower(),
                "left": self._parse_condition(tokens[0]),
                "right": self._parse_condition(tokens[2]),
            }

        # NOT 연산자 처리
        if len(tokens) >= 2 and tokens[0].lower() == "not":
            return {
                "type": "unary_op",
                "operator": "not",
                "operand": self._parse_tokens(tokens[1:]),
            }

        # 기본적으로 첫 번째 조건만 사용
        return self._parse_condition(tokens[0])

    def _parse_condition(self, condition: str) -> Dict[str, Any]:
        """단일 조건 파싱"""
        try:
            condition = condition.strip()

            # IP 주소 조건 (host, src, dst)
            if condition.startswith("host "):
                ip = condition[5:].strip()
                return {"type": "host", "ip": ip}

            if condition.startswith("src ") or condition.startswith("src host "):
                ip = condition.replace("src host ", "").replace("src ", "").strip()
                return {"type": "src_host", "ip": ip}

            if condition.startswith("dst ") or condition.startswith("dst host "):
                ip = condition.replace("dst host ", "").replace("dst ", "").strip()
                return {"type": "dst_host", "ip": ip}

            # 네트워크 조건
            if condition.startswith("net "):
                network = condition[4:].strip()
                return {"type": "net", "network": network}

            if condition.startswith("src net "):
                network = condition[8:].strip()
                return {"type": "src_net", "network": network}

            if condition.startswith("dst net "):
                network = condition[8:].strip()
                return {"type": "dst_net", "network": network}

            # 포트 조건
            if condition.startswith("port "):
                port = int(condition[5:].strip())
                return {"type": "port", "port": port}

            if condition.startswith("src port "):
                port = int(condition[9:].strip())
                return {"type": "src_port", "port": port}

            if condition.startswith("dst port "):
                port = int(condition[9:].strip())
                return {"type": "dst_port", "port": port}

            # 포트 범위
            port_range_match = re.match(r"port\s+(\d+)-(\d+)", condition)
            if port_range_match:
                start_port = int(port_range_match.group(1))
                end_port = int(port_range_match.group(2))
                return {
                    "type": "port_range",
                    "start": start_port,
                    "end": end_port,
                }

            # 프로토콜 조건
            protocols = ["tcp", "udp", "icmp", "ip", "ip6", "arp", "rarp"]
            if condition.lower() in protocols:
                return {"type": "protocol", "protocol": condition.lower()}

            # 기본적으로 프로토콜로 처리
            return {"type": "protocol", "protocol": condition.lower()}

        except Exception as e:
            logger.error(f"조건 파싱 오류 ({condition}): {e}")
            return {"type": "always_false"}

    def _evaluate_filter(self, filter_expr: Dict[str, Any], packet_info: Dict[str, Any]) -> bool:
        """컴파일된 필터를 패킷 정보에 대해 평가"""
        try:
            expr_type = filter_expr.get("type")

            if expr_type == "always_true":
                return True
            elif expr_type == "always_false":
                return False

            elif expr_type == "binary_op":
                operator = filter_expr["operator"]
                left_result = self._evaluate_filter(filter_expr["left"], packet_info)
                right_result = self._evaluate_filter(filter_expr["right"], packet_info)

                if operator == "and":
                    return left_result and right_result
                elif operator == "or":
                    return left_result or right_result

            elif expr_type == "unary_op":
                operator = filter_expr["operator"]
                operand_result = self._evaluate_filter(filter_expr["operand"], packet_info)

                if operator == "not":
                    return not operand_result

            elif expr_type == "host":
                ip = filter_expr["ip"]
                src_ip = packet_info.get("src_ip", "")
                dst_ip = packet_info.get("dst_ip", "")
                return src_ip == ip or dst_ip == ip

            elif expr_type == "src_host":
                ip = filter_expr["ip"]
                src_ip = packet_info.get("src_ip", "")
                return src_ip == ip

            elif expr_type == "dst_host":
                ip = filter_expr["ip"]
                dst_ip = packet_info.get("dst_ip", "")
                return dst_ip == ip

            elif expr_type == "net":
                network = filter_expr["network"]
                return self._ip_in_network(packet_info.get("src_ip"), network) or self._ip_in_network(
                    packet_info.get("dst_ip"), network
                )

            elif expr_type == "src_net":
                network = filter_expr["network"]
                return self._ip_in_network(packet_info.get("src_ip"), network)

            elif expr_type == "dst_net":
                network = filter_expr["network"]
                return self._ip_in_network(packet_info.get("dst_ip"), network)

            elif expr_type == "port":
                port = filter_expr["port"]
                src_port = packet_info.get("src_port", 0)
                dst_port = packet_info.get("dst_port", 0)
                return src_port == port or dst_port == port

            elif expr_type == "src_port":
                port = filter_expr["port"]
                src_port = packet_info.get("src_port", 0)
                return src_port == port

            elif expr_type == "dst_port":
                port = filter_expr["port"]
                dst_port = packet_info.get("dst_port", 0)
                return dst_port == port

            elif expr_type == "port_range":
                start_port = filter_expr["start"]
                end_port = filter_expr["end"]
                src_port = packet_info.get("src_port", 0)
                dst_port = packet_info.get("dst_port", 0)
                return (start_port <= src_port <= end_port) or (start_port <= dst_port <= end_port)

            elif expr_type == "protocol":
                protocol = filter_expr["protocol"]
                packet_protocol = packet_info.get("protocol", "").lower()
                return packet_protocol == protocol

            return False

        except Exception as e:
            logger.error(f"필터 평가 오류: {e}")
            return False

    def _ip_in_network(self, ip_str: str, network_str: str) -> bool:
        """IP가 네트워크에 속하는지 확인"""
        try:
            if not ip_str or not network_str:
                return False

            ip = ip_address(ip_str)

            # CIDR 표기법 확인
            if "/" in network_str:
                network = ip_network(network_str, strict=False)
                return ip in network
            else:
                # 단일 IP 주소
                return str(ip) == network_str

        except Exception as e:
            logger.error(f"IP 네트워크 검사 오류: {e}")
            return False

    def get_predefined_filters(self) -> Dict[str, str]:
        """미리 정의된 BPF 필터 반환"""
        return {
            "http_traffic": "port 80 or port 443",
            "ssh_traffic": "port 22",
            "dns_traffic": "port 53",
            "ftp_traffic": "port 21 or port 20",
            "smtp_traffic": "port 25 or port 587",
            "pop3_traffic": "port 110 or port 995",
            "imap_traffic": "port 143 or port 993",
            "telnet_traffic": "port 23",
            "snmp_traffic": "port 161 or port 162",
            "ldap_traffic": "port 389 or port 636",
            "mysql_traffic": "port 3306",
            "postgresql_traffic": "port 5432",
            "mssql_traffic": "port 1433",
            "oracle_traffic": "port 1521",
            "mongodb_traffic": "port 27017",
            "redis_traffic": "port 6379",
            "rdp_traffic": "port 3389",
            "vnc_traffic": "port 5900",
            "private_networks": "net 192.168.0.0/16 or net 10.0.0.0/8 or net 172.16.0.0/12",
            "local_traffic": "host 127.0.0.1",
            "tcp_traffic": "tcp",
            "udp_traffic": "udp",
            "icmp_traffic": "icmp",
            "large_packets": "greater 1000",  # 1000바이트 이상
            "small_packets": "less 100",  # 100바이트 이하
            "syn_packets": "tcp[tcpflags] & tcp-syn != 0",
            "rst_packets": "tcp[tcpflags] & tcp-rst != 0",
            "broadcast": "dst host 255.255.255.255",
            "multicast": "multicast",
        }

    def apply_predefined_filter(self, filter_name: str) -> bool:
        """미리 정의된 필터 적용"""
        predefined = self.get_predefined_filters()

        if filter_name in predefined:
            return self.set_filter(predefined[filter_name])
        else:
            logger.warning(f"알 수 없는 미리 정의된 필터: {filter_name}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """필터링 통계 반환"""
        stats = self.statistics.copy()

        if stats["total_packets"] > 0:
            stats["match_rate"] = stats["matched_packets"] / stats["total_packets"]
        else:
            stats["match_rate"] = 0.0

        stats.update(
            {
                "filter_string": self.filter_string,
                "is_compiled": self.compiled_filter is not None,
            }
        )

        return stats

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "total_packets": 0,
            "matched_packets": 0,
            "compilation_errors": 0,
        }

        logger.info("BPF 필터 통계 초기화됨")

    def validate_syntax(self, filter_string: str) -> Tuple[bool, str]:
        """
        BPF 필터 문법 검증

        Args:
            filter_string: 검증할 BPF 필터 문자열

        Returns:
            tuple: (유효성, 오류 메시지)
        """
        try:
            old_filter = self.filter_string
            old_compiled = self.compiled_filter

            # 임시로 필터 설정해보기
            success = self.set_filter(filter_string)

            # 원래 필터로 복원
            self.filter_string = old_filter
            self.compiled_filter = old_compiled

            if success:
                return True, "문법이 올바릅니다"
            else:
                return False, "문법 오류가 있습니다"

        except Exception as e:
            return False, f"문법 검증 오류: {str(e)}"

    def get_filter_examples(self) -> List[Dict[str, str]]:
        """BPF 필터 예제 반환"""
        return [
            {
                "name": "특정 호스트와의 통신",
                "filter": "host 192.168.1.100",
                "description": "192.168.1.100과 주고받는 모든 패킷",
            },
            {
                "name": "HTTP 트래픽",
                "filter": "port 80 or port 443",
                "description": "웹 트래픽 (HTTP/HTTPS)",
            },
            {
                "name": "TCP 트래픽만",
                "filter": "tcp",
                "description": "TCP 프로토콜 패킷만",
            },
            {
                "name": "특정 서브넷에서 오는 트래픽",
                "filter": "src net 192.168.0.0/24",
                "description": "192.168.0.x 네트워크에서 오는 패킷",
            },
            {
                "name": "SSH 접속",
                "filter": "dst port 22 and tcp",
                "description": "SSH 서버로의 연결",
            },
            {
                "name": "DNS 쿼리",
                "filter": "port 53 and udp",
                "description": "DNS 조회 패킷",
            },
            {
                "name": "사설 네트워크 제외",
                "filter": "not (net 192.168.0.0/16 or net 10.0.0.0/8)",
                "description": "사설 IP 대역을 제외한 트래픽",
            },
            {
                "name": "이메일 트래픽",
                "filter": "port 25 or port 587 or port 143 or port 993",
                "description": "SMTP/IMAP 이메일 트래픽",
            },
        ]


# 팩토리 함수
def create_bpf_filter() -> BPFFilter:
    """BPF 필터 인스턴스 생성"""
    return BPFFilter()

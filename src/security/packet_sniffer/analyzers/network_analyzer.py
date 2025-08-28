#!/usr/bin/env python3
"""
네트워크 프로토콜 분석기 (TCP/UDP/ICMP)
기본 네트워크 프로토콜 분석 및 네트워크 상태 감지
"""

import logging
import socket
import struct
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """네트워크 프로토콜 분석기"""

    # IP 프로토콜 번호
    IP_PROTOCOLS = {
        1: "ICMP",
        6: "TCP",
        17: "UDP",
        41: "IPv6",
        47: "GRE",
        50: "ESP",
        51: "AH",
        89: "OSPF",
        132: "SCTP",
    }

    # TCP 플래그
    TCP_FLAGS = {
        0x01: "FIN",
        0x02: "SYN",
        0x04: "RST",
        0x08: "PSH",
        0x10: "ACK",
        0x20: "URG",
        0x40: "ECE",
        0x80: "CWR",
    }

    # ICMP 타입
    ICMP_TYPES = {
        0: "Echo Reply",
        3: "Destination Unreachable",
        4: "Source Quench",
        5: "Redirect",
        8: "Echo Request",
        9: "Router Advertisement",
        10: "Router Solicitation",
        11: "Time Exceeded",
        12: "Parameter Problem",
        13: "Timestamp Request",
        14: "Timestamp Reply",
        15: "Information Request",
        16: "Information Reply",
    }

    # 잘 알려진 포트
    WELL_KNOWN_PORTS = {
        20: "FTP-DATA",
        21: "FTP",
        22: "SSH",
        23: "TELNET",
        25: "SMTP",
        53: "DNS",
        67: "DHCP-SERVER",
        68: "DHCP-CLIENT",
        69: "TFTP",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        161: "SNMP",
        162: "SNMP-TRAP",
        389: "LDAP",
        443: "HTTPS",
        445: "SMB",
        993: "IMAPS",
        995: "POP3S",
        1433: "MSSQL",
        1521: "ORACLE",
        3306: "MYSQL",
        3389: "RDP",
        5432: "POSTGRESQL",
        6379: "REDIS",
        27017: "MONGODB",
    }

    def __init__(self):
        self.connections = defaultdict(dict)  # TCP 연결 추적
        self.flow_stats = defaultdict(lambda: {"packets": 0, "bytes": 0})  # 플로우 통계
        self.port_stats = defaultdict(int)  # 포트 사용 통계

    def analyze(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        네트워크 패킷 분석

        Args:
            packet_data: 패킷 데이터
            packet_info: 패킷 기본 정보

        Returns:
            dict: 네트워크 분석 결과
        """
        try:
            analysis = {
                "protocol_stack": [],
                "flow_info": {},
                "connection_state": {},
                "anomalies": [],
                "statistics": {},
                "timestamp": packet_info.get("timestamp", datetime.now().isoformat()),
            }

            # IP 계층 분석
            ip_info = self._analyze_ip_layer(packet_data, packet_info)
            if ip_info:
                analysis["ip_layer"] = ip_info
                analysis["protocol_stack"].append(f"IP/{ip_info.get('version', 'unknown')}")

            # 전송 계층 분석
            protocol = packet_info.get("protocol")
            if protocol == "TCP":
                tcp_analysis = self._analyze_tcp(packet_data, packet_info)
                if tcp_analysis:
                    analysis["tcp_layer"] = tcp_analysis
                    analysis["protocol_stack"].append("TCP")
                    analysis["connection_state"] = tcp_analysis.get("connection_state", {})

            elif protocol == "UDP":
                udp_analysis = self._analyze_udp(packet_data, packet_info)
                if udp_analysis:
                    analysis["udp_layer"] = udp_analysis
                    analysis["protocol_stack"].append("UDP")

            elif protocol == "ICMP":
                icmp_analysis = self._analyze_icmp(packet_data, packet_info)
                if icmp_analysis:
                    analysis["icmp_layer"] = icmp_analysis
                    analysis["protocol_stack"].append("ICMP")

            # 플로우 정보 생성
            flow_info = self._generate_flow_info(packet_info)
            analysis["flow_info"] = flow_info

            # 통계 업데이트
            self._update_statistics(packet_info, len(packet_data))
            analysis["statistics"] = self._get_current_statistics()

            # 이상 징후 검사
            anomalies = self._detect_anomalies(analysis, packet_info)
            analysis["anomalies"] = anomalies

            return analysis

        except Exception as e:
            logger.error(f"네트워크 분석 오류: {e}")
            return {
                "error": str(e),
                "timestamp": packet_info.get("timestamp", datetime.now().isoformat()),
            }

    def _analyze_ip_layer(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """IP 계층 분석"""
        try:
            if len(packet_data) < 20:
                return None

            # IP 헤더 파싱
            version_ihl = packet_data[0]
            version = (version_ihl >> 4) & 0xF
            ihl = version_ihl & 0xF
            ihl * 4

            if version == 4:
                return self._analyze_ipv4(packet_data, packet_info)
            elif version == 6:
                return self._analyze_ipv6(packet_data, packet_info)
            else:
                return {
                    "version": version,
                    "error": f"Unknown IP version: {version}",
                }

        except Exception as e:
            logger.error(f"IP 계층 분석 오류: {e}")
            return None

    def _analyze_ipv4(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """IPv4 헤더 분석"""
        try:
            if len(packet_data) < 20:
                return {}

            # IPv4 헤더 파싱
            version_ihl = packet_data[0]
            ihl = version_ihl & 0xF
            header_length = ihl * 4

            tos = packet_data[1]
            total_length = struct.unpack(">H", packet_data[2:4])[0]
            identification = struct.unpack(">H", packet_data[4:6])[0]
            flags_frag = struct.unpack(">H", packet_data[6:8])[0]
            ttl = packet_data[8]
            protocol = packet_data[9]
            checksum = struct.unpack(">H", packet_data[10:12])[0]
            src_ip = socket.inet_ntoa(packet_data[12:16])
            dst_ip = socket.inet_ntoa(packet_data[16:20])

            # 플래그 및 프래그먼트 오프셋
            flags = (flags_frag >> 13) & 0x7
            fragment_offset = flags_frag & 0x1FFF

            ipv4_info = {
                "version": 4,
                "header_length": header_length,
                "type_of_service": tos,
                "dscp": (tos >> 2) & 0x3F,
                "ecn": tos & 0x3,
                "total_length": total_length,
                "identification": identification,
                "flags": {
                    "reserved": bool(flags & 0x4),
                    "dont_fragment": bool(flags & 0x2),
                    "more_fragments": bool(flags & 0x1),
                },
                "fragment_offset": fragment_offset,
                "ttl": ttl,
                "protocol": protocol,
                "protocol_name": self.IP_PROTOCOLS.get(protocol, f"unknown_{protocol}"),
                "header_checksum": checksum,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
            }

            # IPv4 옵션 파싱 (있는 경우)
            if header_length > 20:
                options = packet_data[20:header_length]
                ipv4_info["options"] = self._parse_ipv4_options(options)

            # 보안 검사
            security_issues = self._check_ipv4_security(ipv4_info)
            if security_issues:
                ipv4_info["security_issues"] = security_issues

            return ipv4_info

        except Exception as e:
            logger.error(f"IPv4 분석 오류: {e}")
            return {"version": 4, "error": str(e)}

    def _analyze_ipv6(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """IPv6 헤더 분석"""
        try:
            if len(packet_data) < 40:
                return {}

            # IPv6 헤더 파싱
            version_class_label = struct.unpack(">I", packet_data[0:4])[0]
            (version_class_label >> 28) & 0xF
            traffic_class = (version_class_label >> 20) & 0xFF
            flow_label = version_class_label & 0xFFFFF

            payload_length = struct.unpack(">H", packet_data[4:6])[0]
            next_header = packet_data[6]
            hop_limit = packet_data[7]

            src_ip = socket.inet_ntop(socket.AF_INET6, packet_data[8:24])
            dst_ip = socket.inet_ntop(socket.AF_INET6, packet_data[24:40])

            return {
                "version": 6,
                "traffic_class": traffic_class,
                "dscp": (traffic_class >> 2) & 0x3F,
                "ecn": traffic_class & 0x3,
                "flow_label": flow_label,
                "payload_length": payload_length,
                "next_header": next_header,
                "next_header_name": self.IP_PROTOCOLS.get(next_header, f"unknown_{next_header}"),
                "hop_limit": hop_limit,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
            }

        except Exception as e:
            logger.error(f"IPv6 분석 오류: {e}")
            return {"version": 6, "error": str(e)}

    def _parse_ipv4_options(self, options_data: bytes) -> List[Dict[str, Any]]:
        """IPv4 옵션 파싱"""
        options = []
        offset = 0

        while offset < len(options_data):
            if options_data[offset] == 0:  # End of Option List
                break
            elif options_data[offset] == 1:  # No Operation
                options.append({"type": "NOP"})
                offset += 1
            else:
                if offset + 1 >= len(options_data):
                    break

                opt_type = options_data[offset]
                opt_length = options_data[offset + 1] if offset + 1 < len(options_data) else 0

                if opt_length < 2 or offset + opt_length > len(options_data):
                    break

                opt_data = options_data[offset + 2 : offset + opt_length]

                option = {
                    "type": opt_type,
                    "length": opt_length,
                    "data": opt_data.hex() if opt_data else "",
                }

                # 알려진 옵션 타입 해석
                if opt_type == 7:  # Record Route
                    option["name"] = "Record Route"
                elif opt_type == 9:  # Strict Source Route
                    option["name"] = "Strict Source Route"
                elif opt_type == 131:  # Loose Source Route
                    option["name"] = "Loose Source Route"
                elif opt_type == 68:  # Timestamp
                    option["name"] = "Timestamp"

                options.append(option)
                offset += opt_length

        return options

    def _analyze_tcp(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """TCP 세그먼트 분석"""
        try:
            # IP 헤더 길이 계산
            ip_header_length = (packet_data[0] & 0xF) * 4 if len(packet_data) > 0 else 20
            tcp_start = ip_header_length

            if len(packet_data) < tcp_start + 20:
                return None

            tcp_data = packet_data[tcp_start:]

            # TCP 헤더 파싱
            src_port = struct.unpack(">H", tcp_data[0:2])[0]
            dst_port = struct.unpack(">H", tcp_data[2:4])[0]
            seq_num = struct.unpack(">I", tcp_data[4:8])[0]
            ack_num = struct.unpack(">I", tcp_data[8:12])[0]

            data_offset_flags = struct.unpack(">H", tcp_data[12:14])[0]
            data_offset = (data_offset_flags >> 12) & 0xF
            tcp_header_length = data_offset * 4
            flags = data_offset_flags & 0x1FF

            window_size = struct.unpack(">H", tcp_data[14:16])[0]
            checksum = struct.unpack(">H", tcp_data[16:18])[0]
            urgent_pointer = struct.unpack(">H", tcp_data[18:20])[0]

            # TCP 플래그 분석
            flag_list = []
            for flag_bit, flag_name in self.TCP_FLAGS.items():
                if flags & flag_bit:
                    flag_list.append(flag_name)

            tcp_info = {
                "src_port": src_port,
                "dst_port": dst_port,
                "src_service": self.WELL_KNOWN_PORTS.get(src_port, f"port_{src_port}"),
                "dst_service": self.WELL_KNOWN_PORTS.get(dst_port, f"port_{dst_port}"),
                "sequence_number": seq_num,
                "acknowledgment_number": ack_num,
                "header_length": tcp_header_length,
                "flags": flag_list,
                "flags_raw": flags,
                "window_size": window_size,
                "checksum": checksum,
                "urgent_pointer": urgent_pointer,
            }

            # TCP 옵션 파싱
            if tcp_header_length > 20:
                options = tcp_data[20:tcp_header_length]
                tcp_info["options"] = self._parse_tcp_options(options)

            # 페이로드 크기
            payload_size = len(tcp_data) - tcp_header_length
            tcp_info["payload_size"] = payload_size

            # TCP 연결 상태 추적
            connection_state = self._track_tcp_connection(tcp_info, packet_info)
            tcp_info["connection_state"] = connection_state

            # TCP 이상 징후 검사
            tcp_anomalies = self._check_tcp_anomalies(tcp_info)
            if tcp_anomalies:
                tcp_info["anomalies"] = tcp_anomalies

            return tcp_info

        except Exception as e:
            logger.error(f"TCP 분석 오류: {e}")
            return None

    def _parse_tcp_options(self, options_data: bytes) -> List[Dict[str, Any]]:
        """TCP 옵션 파싱"""
        options = []
        offset = 0

        while offset < len(options_data):
            if options_data[offset] == 0:  # End of Option List
                break
            elif options_data[offset] == 1:  # No Operation
                options.append({"type": 1, "name": "NOP"})
                offset += 1
            else:
                if offset + 1 >= len(options_data):
                    break

                opt_type = options_data[offset]
                opt_length = options_data[offset + 1]

                if opt_length < 2 or offset + opt_length > len(options_data):
                    break

                opt_data = options_data[offset + 2 : offset + opt_length]

                option = {
                    "type": opt_type,
                    "length": opt_length,
                    "data": opt_data.hex() if opt_data else "",
                }

                # 알려진 TCP 옵션 해석
                if opt_type == 2:  # Maximum Segment Size
                    option["name"] = "MSS"
                    if len(opt_data) >= 2:
                        option["mss"] = struct.unpack(">H", opt_data[:2])[0]
                elif opt_type == 3:  # Window Scale
                    option["name"] = "Window Scale"
                    if len(opt_data) >= 1:
                        option["scale"] = opt_data[0]
                elif opt_type == 4:  # SACK Permitted
                    option["name"] = "SACK Permitted"
                elif opt_type == 5:  # SACK
                    option["name"] = "SACK"
                elif opt_type == 8:  # Timestamp
                    option["name"] = "Timestamp"
                    if len(opt_data) >= 8:
                        option["ts_val"] = struct.unpack(">I", opt_data[:4])[0]
                        option["ts_ecr"] = struct.unpack(">I", opt_data[4:8])[0]

                options.append(option)
                offset += opt_length

        return options

    def _track_tcp_connection(self, tcp_info: Dict[str, Any], packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """TCP 연결 상태 추적"""
        try:
            src_ip = packet_info.get("src_ip")
            dst_ip = packet_info.get("dst_ip")
            src_port = tcp_info["src_port"]
            dst_port = tcp_info["dst_port"]

            # 연결 키 생성 (양방향)
            conn_key1 = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}"
            conn_key2 = f"{dst_ip}:{dst_port}-{src_ip}:{src_port}"

            connection = None
            if conn_key1 in self.connections:
                connection = self.connections[conn_key1]
                direction = "forward"
            elif conn_key2 in self.connections:
                connection = self.connections[conn_key2]
                direction = "reverse"
            else:
                connection = {
                    "state": "UNKNOWN",
                    "seq_next": {},
                    "packets": 0,
                    "bytes": 0,
                    "start_time": packet_info.get("timestamp"),
                }
                self.connections[conn_key1] = connection
                direction = "forward"

            # 패킷 수 및 바이트 수 업데이트
            connection["packets"] += 1
            connection["bytes"] += tcp_info.get("payload_size", 0)

            # TCP 상태 머신 업데이트
            flags = tcp_info["flags"]

            if "SYN" in flags and "ACK" not in flags:
                connection["state"] = "SYN_SENT"
            elif "SYN" in flags and "ACK" in flags:
                connection["state"] = "SYN_RECEIVED"
            elif "ACK" in flags and connection["state"] in [
                "SYN_SENT",
                "SYN_RECEIVED",
            ]:
                connection["state"] = "ESTABLISHED"
            elif "FIN" in flags:
                if connection["state"] == "ESTABLISHED":
                    connection["state"] = "FIN_WAIT"
                elif connection["state"] == "FIN_WAIT":
                    connection["state"] = "CLOSE_WAIT"
            elif "RST" in flags:
                connection["state"] = "RESET"

            return {
                "state": connection["state"],
                "direction": direction,
                "packets": connection["packets"],
                "bytes": connection["bytes"],
                "duration": self._calculate_duration(connection["start_time"], packet_info.get("timestamp")),
            }

        except Exception as e:
            logger.error(f"TCP 연결 추적 오류: {e}")
            return {"state": "ERROR", "error": str(e)}

    def _analyze_udp(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """UDP 데이터그램 분석"""
        try:
            # IP 헤더 길이 계산
            ip_header_length = (packet_data[0] & 0xF) * 4 if len(packet_data) > 0 else 20
            udp_start = ip_header_length

            if len(packet_data) < udp_start + 8:
                return None

            udp_data = packet_data[udp_start:]

            # UDP 헤더 파싱
            src_port = struct.unpack(">H", udp_data[0:2])[0]
            dst_port = struct.unpack(">H", udp_data[2:4])[0]
            length = struct.unpack(">H", udp_data[4:6])[0]
            checksum = struct.unpack(">H", udp_data[6:8])[0]

            udp_info = {
                "src_port": src_port,
                "dst_port": dst_port,
                "src_service": self.WELL_KNOWN_PORTS.get(src_port, f"port_{src_port}"),
                "dst_service": self.WELL_KNOWN_PORTS.get(dst_port, f"port_{dst_port}"),
                "length": length,
                "checksum": checksum,
                "payload_size": length - 8 if length >= 8 else 0,
            }

            # UDP 이상 징후 검사
            udp_anomalies = self._check_udp_anomalies(udp_info)
            if udp_anomalies:
                udp_info["anomalies"] = udp_anomalies

            return udp_info

        except Exception as e:
            logger.error(f"UDP 분석 오류: {e}")
            return None

    def _analyze_icmp(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ICMP 메시지 분석"""
        try:
            # IP 헤더 길이 계산
            ip_header_length = (packet_data[0] & 0xF) * 4 if len(packet_data) > 0 else 20
            icmp_start = ip_header_length

            if len(packet_data) < icmp_start + 8:
                return None

            icmp_data = packet_data[icmp_start:]

            # ICMP 헤더 파싱
            icmp_type = icmp_data[0]
            icmp_code = icmp_data[1]
            checksum = struct.unpack(">H", icmp_data[2:4])[0]

            icmp_info = {
                "type": icmp_type,
                "type_name": self.ICMP_TYPES.get(icmp_type, f"unknown_{icmp_type}"),
                "code": icmp_code,
                "checksum": checksum,
                "payload_size": len(icmp_data) - 8,
            }

            # ICMP 타입별 상세 분석
            if icmp_type in [8, 0]:  # Echo Request/Reply
                if len(icmp_data) >= 8:
                    identifier = struct.unpack(">H", icmp_data[4:6])[0]
                    sequence = struct.unpack(">H", icmp_data[6:8])[0]
                    icmp_info.update({"identifier": identifier, "sequence": sequence})

            elif icmp_type == 3:  # Destination Unreachable
                icmp_info["unreachable_code"] = {
                    0: "Network Unreachable",
                    1: "Host Unreachable",
                    2: "Protocol Unreachable",
                    3: "Port Unreachable",
                    4: "Fragmentation Needed",
                    5: "Source Route Failed",
                }.get(icmp_code, f"Code {icmp_code}")

            elif icmp_type == 11:  # Time Exceeded
                icmp_info["time_exceeded_code"] = {
                    0: "TTL Exceeded in Transit",
                    1: "Fragment Reassembly Time Exceeded",
                }.get(icmp_code, f"Code {icmp_code}")

            # ICMP 이상 징후 검사
            icmp_anomalies = self._check_icmp_anomalies(icmp_info, packet_info)
            if icmp_anomalies:
                icmp_info["anomalies"] = icmp_anomalies

            return icmp_info

        except Exception as e:
            logger.error(f"ICMP 분석 오류: {e}")
            return None

    def _generate_flow_info(self, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """플로우 정보 생성"""
        try:
            src_ip = packet_info.get("src_ip")
            dst_ip = packet_info.get("dst_ip")
            src_port = packet_info.get("src_port", 0)
            dst_port = packet_info.get("dst_port", 0)
            protocol = packet_info.get("protocol", "unknown")

            # 5-tuple 플로우 키
            flow_key = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}/{protocol}"
            reverse_key = f"{dst_ip}:{dst_port}-{src_ip}:{src_port}/{protocol}"

            return {
                "flow_key": flow_key,
                "reverse_key": reverse_key,
                "src_endpoint": f"{src_ip}:{src_port}",
                "dst_endpoint": f"{dst_ip}:{dst_port}",
                "protocol": protocol,
                "direction": "outbound" if src_port > dst_port else "inbound",
            }

        except Exception as e:
            logger.error(f"플로우 정보 생성 오류: {e}")
            return {}

    def _update_statistics(self, packet_info: Dict[str, Any], packet_size: int):
        """통계 업데이트"""
        try:
            protocol = packet_info.get("protocol", "unknown")
            src_port = packet_info.get("src_port")
            dst_port = packet_info.get("dst_port")

            # 프로토콜별 통계
            flow_key = f"{packet_info.get('src_ip')}:{src_port}-{packet_info.get('dst_ip')}:{dst_port}/{protocol}"
            self.flow_stats[flow_key]["packets"] += 1
            self.flow_stats[flow_key]["bytes"] += packet_size

            # 포트별 통계
            if src_port:
                self.port_stats[src_port] += 1
            if dst_port:
                self.port_stats[dst_port] += 1

        except Exception as e:
            logger.error(f"통계 업데이트 오류: {e}")

    def _get_current_statistics(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        try:
            # 상위 플로우
            top_flows = sorted(
                [(k, v) for k, v in self.flow_stats.items()],
                key=lambda x: x[1]["bytes"],
                reverse=True,
            )[:10]

            # 상위 포트
            top_ports = sorted(
                [(k, v) for k, v in self.port_stats.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10]

            return {
                "total_flows": len(self.flow_stats),
                "total_connections": len(self.connections),
                "top_flows": [
                    {
                        "flow": f[0],
                        "packets": f[1]["packets"],
                        "bytes": f[1]["bytes"],
                    }
                    for f in top_flows
                ],
                "top_ports": [
                    {
                        "port": p[0],
                        "service": self.WELL_KNOWN_PORTS.get(p[0], "unknown"),
                        "count": p[1],
                    }
                    for p in top_ports
                ],
            }

        except Exception as e:
            logger.error(f"통계 생성 오류: {e}")
            return {}

    def _detect_anomalies(self, analysis: Dict[str, Any], packet_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """네트워크 이상 징후 검사"""
        anomalies = []

        try:
            # 각 계층의 이상 징후 수집
            for layer in ["tcp_layer", "udp_layer", "icmp_layer"]:
                if layer in analysis and "anomalies" in analysis[layer]:
                    anomalies.extend(analysis[layer]["anomalies"])

            # 추가 네트워크 레벨 이상 징후 검사
            ip_layer = analysis.get("ip_layer", {})

            # TTL 이상
            ttl = ip_layer.get("ttl", 64)
            if ttl < 5:
                anomalies.append(
                    {
                        "type": "low_ttl",
                        "description": f"비정상적으로 낮은 TTL 값: {ttl}",
                        "severity": "medium",
                    }
                )
            elif ttl > 200:
                anomalies.append(
                    {
                        "type": "high_ttl",
                        "description": f"비정상적으로 높은 TTL 값: {ttl}",
                        "severity": "low",
                    }
                )

            # 프래그먼트 이상
            if ip_layer.get("flags", {}).get("more_fragments") and ip_layer.get("fragment_offset", 0) == 0:
                anomalies.append(
                    {
                        "type": "fragment_anomaly",
                        "description": "의심스러운 IP 프래그먼트 패턴",
                        "severity": "medium",
                    }
                )

        except Exception as e:
            logger.error(f"이상 징후 검사 오류: {e}")

        return anomalies

    def _check_ipv4_security(self, ipv4_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """IPv4 보안 검사"""
        issues = []

        try:
            # Source routing 검사
            options = ipv4_info.get("options", [])
            for option in options:
                if option.get("name") in [
                    "Strict Source Route",
                    "Loose Source Route",
                ]:
                    issues.append(
                        {
                            "type": "source_routing",
                            "description": "Source routing 옵션 감지",
                            "severity": "medium",
                        }
                    )

            # 의심스러운 TOS 값
            tos = ipv4_info.get("type_of_service", 0)
            if tos > 0:
                issues.append(
                    {
                        "type": "tos_manipulation",
                        "description": f"비표준 TOS 값: {tos}",
                        "severity": "low",
                    }
                )

        except Exception as e:
            logger.error(f"IPv4 보안 검사 오류: {e}")

        return issues

    def _check_tcp_anomalies(self, tcp_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """TCP 이상 징후 검사"""
        anomalies = []

        try:
            flags = tcp_info.get("flags", [])

            # 비정상적인 플래그 조합
            if "SYN" in flags and "FIN" in flags:
                anomalies.append(
                    {
                        "type": "tcp_flag_anomaly",
                        "description": "SYN과 FIN 플래그가 동시에 설정됨",
                        "severity": "high",
                    }
                )

            if "RST" in flags and ("SYN" in flags or "FIN" in flags):
                anomalies.append(
                    {
                        "type": "tcp_flag_anomaly",
                        "description": "RST와 다른 플래그가 동시에 설정됨",
                        "severity": "medium",
                    }
                )

            # 윈도우 크기 이상
            window_size = tcp_info.get("window_size", 0)
            if window_size == 0 and "RST" not in flags:
                anomalies.append(
                    {
                        "type": "zero_window",
                        "description": "윈도우 크기가 0",
                        "severity": "medium",
                    }
                )
            elif window_size > 65535:
                anomalies.append(
                    {
                        "type": "large_window",
                        "description": f"비정상적으로 큰 윈도우 크기: {window_size}",
                        "severity": "low",
                    }
                )

            # 포트 스캔 탐지
            src_port = tcp_info.get("src_port")
            dst_port = tcp_info.get("dst_port")

            if src_port and dst_port:
                if src_port == dst_port:
                    anomalies.append(
                        {
                            "type": "same_port",
                            "description": f"송신 포트와 수신 포트가 동일: {src_port}",
                            "severity": "medium",
                        }
                    )

        except Exception as e:
            logger.error(f"TCP 이상 징후 검사 오류: {e}")

        return anomalies

    def _check_udp_anomalies(self, udp_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """UDP 이상 징후 검사"""
        anomalies = []

        try:
            # 길이 검증
            length = udp_info.get("length", 0)
            udp_info.get("payload_size", 0)

            if length < 8:
                anomalies.append(
                    {
                        "type": "invalid_udp_length",
                        "description": f"잘못된 UDP 길이: {length}",
                        "severity": "high",
                    }
                )

            # 포트 0 사용
            src_port = udp_info.get("src_port")
            dst_port = udp_info.get("dst_port")

            if src_port == 0 or dst_port == 0:
                anomalies.append(
                    {
                        "type": "port_zero",
                        "description": "포트 0 사용",
                        "severity": "medium",
                    }
                )

        except Exception as e:
            logger.error(f"UDP 이상 징후 검사 오류: {e}")

        return anomalies

    def _check_icmp_anomalies(self, icmp_info: Dict[str, Any], packet_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ICMP 이상 징후 검사"""
        anomalies = []

        try:
            icmp_type = icmp_info.get("type")
            payload_size = icmp_info.get("payload_size", 0)

            # 큰 ICMP 페이로드 (DDoS 가능성)
            if payload_size > 1000:
                anomalies.append(
                    {
                        "type": "large_icmp_payload",
                        "description": f"큰 ICMP 페이로드: {payload_size} bytes",
                        "severity": "medium",
                    }
                )

            # ICMP 터널링 의심
            if icmp_type in [8, 0] and payload_size > 100:
                anomalies.append(
                    {
                        "type": "possible_icmp_tunnel",
                        "description": "ICMP 터널링 의심",
                        "severity": "medium",
                    }
                )

        except Exception as e:
            logger.error(f"ICMP 이상 징후 검사 오류: {e}")

        return anomalies

    def _calculate_duration(self, start_time: str, current_time: str) -> float:
        """연결 지속 시간 계산"""
        try:
            if not start_time or not current_time:
                return 0.0

            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_time.replace("Z", "+00:00"))

            return (current - start).total_seconds()

        except Exception:
            return 0.0


# 팩토리 함수
def create_network_analyzer() -> NetworkAnalyzer:
    """네트워크 분석기 인스턴스 생성"""
    return NetworkAnalyzer()

#!/usr/bin/env python3
"""
PCAP 내보내기
패킷 캡처 데이터를 PCAP 형식으로 저장
"""

import logging
import socket
import struct
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

logger = logging.getLogger(__name__)


class PCAPExporter:
    """PCAP 형식 데이터 내보내기"""

    # PCAP 파일 헤더
    PCAP_GLOBAL_HEADER = struct.pack(
        "<IHHIIII",
        0xA1B2C3D4,  # magic number
        2,  # version major
        4,  # version minor
        0,  # thiszone
        0,  # sigfigs
        65535,  # snaplen
        1,  # network (Ethernet)
    )

    # DLT (Data Link Type) 값들
    DLT_NULL = 0
    DLT_EN10MB = 1  # Ethernet
    DLT_RAW = 12  # Raw IP
    DLT_LINUX_SLL = 113  # Linux cooked

    def __init__(self, snaplen: int = 65535, network: int = DLT_EN10MB):
        """
        PCAP 내보내기 초기화

        Args:
            snaplen: 최대 패킷 크기
            network: 네트워크 타입 (DLT 값)
        """
        self.snaplen = snaplen
        self.network = network
        self.statistics = {
            "exported_files": 0,
            "exported_packets": 0,
            "total_bytes": 0,
            "last_export": None,
        }

    def export_packets(
        self,
        packets: List[Dict[str, Any]],
        output_path: str,
        include_metadata: bool = False,
    ) -> Dict[str, Any]:
        """
        패킷 목록을 PCAP 파일로 내보내기

        Args:
            packets: 패킷 데이터 목록
            output_path: 출력 파일 경로
            include_metadata: 메타데이터 포함 여부

        Returns:
            dict: 내보내기 결과
        """
        try:
            if not packets:
                return {
                    "success": False,
                    "error": "내보낼 패킷 데이터가 없습니다",
                    "exported_count": 0,
                }

            # 출력 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            exported_count = 0
            total_bytes = 0

            with open(output_path, "wb") as pcap_file:
                # PCAP 글로벌 헤더 작성
                self._write_global_header(pcap_file)

                for packet in packets:
                    packet_data = self._extract_packet_data(packet)
                    if packet_data:
                        timestamp = self._extract_timestamp(packet)
                        self._write_packet_record(pcap_file, packet_data, timestamp)
                        exported_count += 1
                        total_bytes += len(packet_data)

            # 메타데이터 파일 생성 (선택사항)
            if include_metadata:
                metadata_path = output_path + ".meta"
                self._write_metadata_file(metadata_path, packets, exported_count)

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["exported_packets"] += exported_count
            self.statistics["total_bytes"] += total_bytes
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"PCAP 내보내기 완료: {output_path} ({exported_count}개 패킷)")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": exported_count,
                "file_size": file_size,
                "total_packet_bytes": total_bytes,
                "metadata_file": metadata_path if include_metadata else None,
            }

        except Exception as e:
            logger.error(f"PCAP 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_filtered_packets(
        self,
        packets: List[Dict[str, Any]],
        filter_expression: str,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        필터링된 패킷을 PCAP으로 내보내기

        Args:
            packets: 전체 패킷 목록
            filter_expression: BPF 필터 표현식
            output_path: 출력 파일 경로

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 필터 적용
            filtered_packets = self._apply_bpf_filter(packets, filter_expression)

            if not filtered_packets:
                return {
                    "success": False,
                    "error": "필터 조건에 맞는 패킷이 없습니다",
                    "exported_count": 0,
                    "total_packets": len(packets),
                    "filter_expression": filter_expression,
                }

            # 필터링된 패킷 내보내기
            result = self.export_packets(filtered_packets, output_path, include_metadata=True)

            if result["success"]:
                result.update(
                    {
                        "filter_expression": filter_expression,
                        "total_packets": len(packets),
                        "filtered_packets": len(filtered_packets),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"필터링된 PCAP 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_by_protocol(self, packets: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """
        프로토콜별로 패킷을 분리하여 PCAP 파일 생성

        Args:
            packets: 패킷 데이터 목록
            output_dir: 출력 디렉토리

        Returns:
            dict: 프로토콜별 내보내기 결과
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 프로토콜별 패킷 분류
            protocols = {}
            for packet in packets:
                protocol = packet.get("protocol", "unknown").upper()
                if protocol not in protocols:
                    protocols[protocol] = []
                protocols[protocol].append(packet)

            results = {}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for protocol, protocol_packets in protocols.items():
                filename = f"{protocol.lower()}_{timestamp}.pcap"
                file_path = output_path / filename

                result = self.export_packets(protocol_packets, str(file_path))
                result["protocol"] = protocol
                result["packet_count"] = len(protocol_packets)
                results[protocol] = result

            logger.info(f"프로토콜별 PCAP 내보내기 완료: {len(protocols)}개 프로토콜")

            return {
                "success": True,
                "output_directory": str(output_path),
                "protocols": list(protocols.keys()),
                "protocol_counts": {p: len(pkts) for p, pkts in protocols.items()},
                "results": results,
            }

        except Exception as e:
            logger.error(f"프로토콜별 PCAP 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_files": 0}

    def export_time_sliced(
        self,
        packets: List[Dict[str, Any]],
        output_dir: str,
        slice_duration: int = 3600,
    ) -> Dict[str, Any]:
        """
        시간 단위로 패킷을 분할하여 PCAP 파일 생성

        Args:
            packets: 패킷 데이터 목록
            output_dir: 출력 디렉토리
            slice_duration: 분할 간격 (초)

        Returns:
            dict: 시간별 내보내기 결과
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 시간별 패킷 분류
            time_slices = {}

            for packet in packets:
                timestamp_str = packet.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        # 시간 슬라이스 계산
                        slice_start = timestamp.replace(minute=0, second=0, microsecond=0)

                        if slice_duration < 3600:  # 1시간 미만이면 분 단위로
                            slice_minutes = (timestamp.minute // (slice_duration // 60)) * (slice_duration // 60)
                            slice_start = slice_start.replace(minute=slice_minutes)

                        slice_key = slice_start.strftime("%Y%m%d_%H%M%S")

                        if slice_key not in time_slices:
                            time_slices[slice_key] = []
                        time_slices[slice_key].append(packet)

                    except Exception:
                        # 타임스탬프 파싱 실패 시 기본 슬라이스에 추가
                        if "unknown" not in time_slices:
                            time_slices["unknown"] = []
                        time_slices["unknown"].append(packet)

            results = {}

            for slice_key, slice_packets in time_slices.items():
                filename = f"capture_{slice_key}.pcap"
                file_path = output_path / filename

                result = self.export_packets(slice_packets, str(file_path))
                result["time_slice"] = slice_key
                result["packet_count"] = len(slice_packets)
                results[slice_key] = result

            logger.info(f"시간별 PCAP 내보내기 완료: {len(time_slices)}개 파일")

            return {
                "success": True,
                "output_directory": str(output_path),
                "time_slices": list(time_slices.keys()),
                "slice_duration": slice_duration,
                "slice_counts": {s: len(pkts) for s, pkts in time_slices.items()},
                "results": results,
            }

        except Exception as e:
            logger.error(f"시간별 PCAP 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_files": 0}

    def _write_global_header(self, pcap_file: BinaryIO):
        """PCAP 글로벌 헤더 작성"""
        header = struct.pack(
            "<IHHIIII",
            0xA1B2C3D4,  # magic number
            2,  # version major
            4,  # version minor
            0,  # thiszone
            0,  # sigfigs
            self.snaplen,  # snaplen
            self.network,  # network
        )
        pcap_file.write(header)

    def _write_packet_record(self, pcap_file: BinaryIO, packet_data: bytes, timestamp: float):
        """패킷 레코드 작성"""
        # 타임스탬프를 초와 마이크로초로 분리
        ts_sec = int(timestamp)
        ts_usec = int((timestamp - ts_sec) * 1000000)

        # 패킷 길이 제한
        caplen = min(len(packet_data), self.snaplen)

        # 패킷 헤더 작성
        packet_header = struct.pack(
            "<IIII",
            ts_sec,  # timestamp seconds
            ts_usec,  # timestamp microseconds
            caplen,  # captured length
            len(packet_data),  # original length
        )

        pcap_file.write(packet_header)
        pcap_file.write(packet_data[:caplen])

    def _extract_packet_data(self, packet: Dict[str, Any]) -> Optional[bytes]:
        """패킷에서 바이너리 데이터 추출"""
        try:
            # 원본 패킷 데이터가 있는 경우
            if "raw_data" in packet:
                raw_data = packet["raw_data"]
                if isinstance(raw_data, bytes):
                    return raw_data
                elif isinstance(raw_data, str):
                    return bytes.fromhex(raw_data)

            # 패킷 정보에서 재구성
            return self._reconstruct_packet(packet)

        except Exception as e:
            logger.error(f"패킷 데이터 추출 오류: {e}")
            return None

    def _reconstruct_packet(self, packet: Dict[str, Any]) -> Optional[bytes]:
        """패킷 정보에서 패킷 재구성"""
        try:
            # 간단한 패킷 재구성 (실제로는 더 복잡한 로직 필요)
            protocol = packet.get("protocol", "").upper()
            src_ip = packet.get("src_ip", "127.0.0.1")
            dst_ip = packet.get("dst_ip", "127.0.0.1")

            # IP 헤더 생성 (20바이트)
            ip_header = self._create_ip_header(src_ip, dst_ip, protocol)

            # 프로토콜별 헤더 추가
            if protocol == "TCP":
                transport_header = self._create_tcp_header(packet)
            elif protocol == "UDP":
                transport_header = self._create_udp_header(packet)
            elif protocol == "ICMP":
                transport_header = self._create_icmp_header(packet)
            else:
                transport_header = b""

            # 페이로드 (있는 경우)
            payload = packet.get("payload", b"")
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            elif not isinstance(payload, bytes):
                payload = b""

            # 이더넷 헤더 추가 (14바이트)
            eth_header = self._create_ethernet_header()

            return eth_header + ip_header + transport_header + payload

        except Exception as e:
            logger.error(f"패킷 재구성 오류: {e}")
            return None

    def _create_ethernet_header(self) -> bytes:
        """간단한 이더넷 헤더 생성"""
        # 목적지 MAC (6바이트) + 송신지 MAC (6바이트) + 타입 (2바이트)
        dst_mac = b"\x00\x00\x00\x00\x00\x00"
        src_mac = b"\x00\x00\x00\x00\x00\x00"
        eth_type = struct.pack(">H", 0x0800)  # IPv4
        return dst_mac + src_mac + eth_type

    def _create_ip_header(self, src_ip: str, dst_ip: str, protocol: str) -> bytes:
        """간단한 IP 헤더 생성"""
        protocol_map = {"TCP": 6, "UDP": 17, "ICMP": 1}
        proto_num = protocol_map.get(protocol, 0)

        # 간단한 IPv4 헤더 (20바이트)
        version_ihl = 0x45  # IPv4, 20바이트 헤더
        tos = 0
        total_length = 20  # 최소 IP 헤더 길이
        identification = 0
        flags_fragment = 0
        ttl = 64
        checksum = 0  # 계산하지 않음

        try:
            src_addr = socket.inet_aton(src_ip)
            dst_addr = socket.inet_aton(dst_ip)
        except socket.error:
            src_addr = socket.inet_aton("127.0.0.1")
            dst_addr = socket.inet_aton("127.0.0.1")

        return struct.pack(
            ">BBHHHBBH4s4s",
            version_ihl,
            tos,
            total_length,
            identification,
            flags_fragment,
            ttl,
            proto_num,
            checksum,
            src_addr,
            dst_addr,
        )

    def _create_tcp_header(self, packet: Dict[str, Any]) -> bytes:
        """간단한 TCP 헤더 생성"""
        src_port = packet.get("src_port", 0)
        dst_port = packet.get("dst_port", 0)
        seq_num = packet.get("sequence_number", 0)
        ack_num = packet.get("acknowledgment_number", 0)
        data_offset = 5 << 4  # 20바이트 헤더
        flags = 0x18  # PSH + ACK
        window = packet.get("window_size", 8192)
        checksum = 0
        urgent = 0

        return struct.pack(
            ">HHIIBBHHH",
            src_port,
            dst_port,
            seq_num,
            ack_num,
            data_offset,
            flags,
            window,
            checksum,
            urgent,
        )

    def _create_udp_header(self, packet: Dict[str, Any]) -> bytes:
        """간단한 UDP 헤더 생성"""
        src_port = packet.get("src_port", 0)
        dst_port = packet.get("dst_port", 0)
        length = 8  # UDP 헤더 길이
        checksum = 0

        return struct.pack(">HHHH", src_port, dst_port, length, checksum)

    def _create_icmp_header(self, packet: Dict[str, Any]) -> bytes:
        """간단한 ICMP 헤더 생성"""
        icmp_type = packet.get("icmp_type", 8)  # Echo Request
        icmp_code = packet.get("icmp_code", 0)
        checksum = 0
        identifier = packet.get("identifier", 0)
        sequence = packet.get("sequence", 0)

        return struct.pack(">BBHHH", icmp_type, icmp_code, checksum, identifier, sequence)

    def _extract_timestamp(self, packet: Dict[str, Any]) -> float:
        """패킷에서 타임스탬프 추출"""
        try:
            timestamp_str = packet.get("timestamp")
            if timestamp_str:
                # ISO 형식 타임스탬프 파싱
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                return dt.timestamp()
            else:
                return datetime.now().timestamp()
        except Exception:
            return datetime.now().timestamp()

    def _apply_bpf_filter(self, packets: List[Dict[str, Any]], filter_expression: str) -> List[Dict[str, Any]]:
        """BPF 필터 적용 (간단한 구현)"""
        try:
            # 간단한 필터 파싱 및 적용
            filtered = []

            for packet in packets:
                if self._matches_filter(packet, filter_expression):
                    filtered.append(packet)

            return filtered

        except Exception as e:
            logger.error(f"BPF 필터 적용 오류: {e}")
            return packets

    def _matches_filter(self, packet: Dict[str, Any], filter_expression: str) -> bool:
        """패킷이 필터 조건에 맞는지 확인 (간단한 구현)"""
        try:
            # 기본적인 필터 표현식 처리
            filter_lower = filter_expression.lower()

            # 프로토콜 필터
            if filter_lower in ["tcp", "udp", "icmp"]:
                return packet.get("protocol", "").lower() == filter_lower

            # 포트 필터
            if "port" in filter_lower:
                port_match = filter_lower.replace("port", "").strip()
                try:
                    port_num = int(port_match)
                    return packet.get("src_port") == port_num or packet.get("dst_port") == port_num
                except ValueError:
                    pass

            # IP 주소 필터
            if "host" in filter_lower:
                ip_match = filter_lower.replace("host", "").strip()
                return packet.get("src_ip") == ip_match or packet.get("dst_ip") == ip_match

            # 기본적으로 모든 패킷 포함
            return True

        except Exception as e:
            logger.error(f"필터 매칭 오류: {e}")
            return True

    def _write_metadata_file(
        self,
        metadata_path: str,
        packets: List[Dict[str, Any]],
        exported_count: int,
    ):
        """메타데이터 파일 작성"""
        try:
            metadata = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "total_packets": len(packets),
                    "exported_packets": exported_count,
                    "exporter": "FortiGate Nextrade PCAP Exporter",
                },
                "capture_info": {
                    "snaplen": self.snaplen,
                    "network_type": self.network,
                    "protocols": list(set(p.get("protocol", "unknown") for p in packets)),
                },
                "statistics": self._generate_packet_statistics(packets),
            }

            import json

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"메타데이터 파일 작성 오류: {e}")

    def _generate_packet_statistics(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """패킷 통계 생성"""
        from collections import Counter

        protocols = Counter(p.get("protocol", "unknown") for p in packets)
        src_ips = Counter(p.get("src_ip") for p in packets if p.get("src_ip"))
        dst_ips = Counter(p.get("dst_ip") for p in packets if p.get("dst_ip"))

        return {
            "protocol_distribution": dict(protocols),
            "top_src_ips": dict(src_ips.most_common(10)),
            "top_dst_ips": dict(dst_ips.most_common(10)),
            "total_packets": len(packets),
        }

    def merge_pcap_files(self, input_files: List[str], output_path: str) -> Dict[str, Any]:
        """여러 PCAP 파일을 하나로 병합"""
        try:
            total_packets = 0

            with open(output_path, "wb") as output_file:
                # 글로벌 헤더 작성
                self._write_global_header(output_file)

                for input_file in input_files:
                    if not Path(input_file).exists():
                        logger.warning(f"파일이 존재하지 않음: {input_file}")
                        continue

                    with open(input_file, "rb") as input_f:
                        # 글로벌 헤더 건너뛰기
                        input_f.seek(24)

                        # 패킷 레코드 복사
                        while True:
                            packet_header = input_f.read(16)
                            if not packet_header or len(packet_header) < 16:
                                break

                            caplen = struct.unpack("<I", packet_header[8:12])[0]
                            packet_data = input_f.read(caplen)

                            if len(packet_data) < caplen:
                                break

                            output_file.write(packet_header)
                            output_file.write(packet_data)
                            total_packets += 1

            file_size = Path(output_path).stat().st_size

            logger.info(f"PCAP 파일 병합 완료: {output_path} ({total_packets}개 패킷)")

            return {
                "success": True,
                "output_path": output_path,
                "merged_files": len(input_files),
                "total_packets": total_packets,
                "file_size": file_size,
            }

        except Exception as e:
            logger.error(f"PCAP 파일 병합 오류: {e}")
            return {"success": False, "error": str(e), "merged_files": 0}

    def get_statistics(self) -> Dict[str, Any]:
        """내보내기 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "exported_files": 0,
            "exported_packets": 0,
            "total_bytes": 0,
            "last_export": None,
        }
        logger.info("PCAP 내보내기 통계 초기화됨")


# 팩토리 함수
def create_pcap_exporter(snaplen: int = 65535, network: int = PCAPExporter.DLT_EN10MB) -> PCAPExporter:
    """PCAP 내보내기 인스턴스 생성"""
    return PCAPExporter(snaplen, network)

#!/usr/bin/env python3
"""
패킷 패턴 탐지기
주기적, 버스트, 스캔, 표적화, 비정상 패턴 등 다양한 네트워크 패턴 식별
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PatternDetector:
    """패킷 패턴 탐지 엔진"""

    def __init__(self):
        """
        패턴 탐지기 초기화
        """
        self.statistics = {
            "patterns_detected": 0,
            "periodic_patterns": 0,
            "burst_patterns": 0,
            "scan_patterns": 0,
            "targeted_patterns": 0,
            "unusual_patterns": 0,
            "last_analysis": None,
        }

        # 패턴 탐지 임계값 설정
        self.thresholds = {
            "periodic_min_packets": 3,  # 주기성 판단 최소 패킷 수
            "periodic_variance_ratio": 0.5,  # 주기성 편차 비율
            "burst_window_seconds": 1.0,  # 버스트 탐지 시간 윈도우
            "burst_min_packets": 5,  # 버스트 최소 패킷 수
            "scan_min_ports": 5,  # 포트 스캔 최소 포트 수
            "scan_max_duration": 10.0,  # 포트 스캔 최대 지속 시간
            "targeted_packet_ratio": 0.3,  # 표적화 통신 패킷 비율
            "targeted_min_sources": 2,  # 표적화 통신 최소 발신지 수
            "targeted_min_protocols": 2,  # 표적화 통신 최소 프로토콜 수
            "large_packet_threshold": 1500,  # 큰 패킷 임계값
        }

    def detect_patterns(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        패킷에서 다양한 패턴 탐지

        Args:
            packets: 패킷 목록

        Returns:
            dict: 탐지된 패턴 결과
        """
        try:
            if not packets:
                return {"patterns": {}, "statistics": self.statistics}

            # 패턴 분석 결과 초기화
            patterns = {
                "periodic": [],  # 주기적 패턴
                "burst": [],  # 버스트 패턴
                "scan": [],  # 스캔 패턴
                "unusual": [],  # 비정상 패턴
                "targeted": [],  # 표적화된 통신 패턴
            }

            # 시간순 정렬
            sorted_packets = sorted(packets, key=lambda x: x.get("timestamp", 0))

            # 각종 패턴 탐지 수행
            patterns["periodic"] = self._detect_periodic_patterns(sorted_packets)
            patterns["burst"] = self._detect_burst_patterns(sorted_packets)
            patterns["scan"] = self._detect_scan_patterns(sorted_packets)
            patterns["targeted"] = self._detect_targeted_patterns(sorted_packets)
            patterns["unusual"] = self._detect_unusual_patterns(sorted_packets)

            # 통계 업데이트
            self._update_statistics(patterns)

            logger.info(
                f"패턴 탐지 완료: 총 {len(packets)}개 패킷에서 " f"{sum(len(p) for p in patterns.values())}개 패턴 탐지"
            )

            return {
                "patterns": patterns,
                "statistics": self.statistics,
                "analysis_summary": self._generate_summary(patterns),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"패턴 탐지 오류: {e}")
            return {
                "patterns": {},
                "statistics": self.statistics,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _detect_periodic_patterns(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """주기적 패턴 탐지"""
        try:
            if len(sorted_packets) < self.thresholds["periodic_min_packets"]:
                return []

            # 시간 간격 계산
            time_series = []
            for i in range(1, len(sorted_packets)):
                current = sorted_packets[i]
                prev = sorted_packets[i - 1]
                interval = current.get("timestamp", 0) - prev.get("timestamp", 0)
                time_series.append(interval)

            if not time_series:
                return []

            # 시간 간격 통계
            avg_interval = sum(time_series) / len(time_series)
            max_interval = max(time_series)
            min_interval = min(time_series)

            # 주기성 판단 (편차가 작은 경우)
            if (
                max_interval > 0
                and (max_interval - min_interval) / avg_interval < self.thresholds["periodic_variance_ratio"]
            ):
                # 주기적 패킷 그룹 식별
                periodic_groups = defaultdict(
                    lambda: {
                        "count": 0,
                        "protocol": "",
                        "src_ip": "",
                        "dst_ip": "",
                        "interval": avg_interval,
                        "first_seen": float("inf"),
                        "last_seen": 0,
                    }
                )

                for packet in sorted_packets:
                    proto = packet.get("protocol", "Unknown")
                    src_ip = packet.get("src_ip", "")
                    dst_ip = packet.get("dst_ip", "")
                    timestamp = packet.get("timestamp", 0)

                    # 그룹화 키 생성
                    group_key = f"{proto}_{src_ip}_{dst_ip}"

                    group = periodic_groups[group_key]
                    group["count"] += 1
                    group["protocol"] = proto
                    group["src_ip"] = src_ip
                    group["dst_ip"] = dst_ip
                    group["first_seen"] = min(group["first_seen"], timestamp)
                    group["last_seen"] = max(group["last_seen"], timestamp)

                # 일정 개수 이상의 패킷이 있는 주기적 그룹 선택
                periodic_patterns = []
                for group_key, group in periodic_groups.items():
                    if group["count"] >= self.thresholds["periodic_min_packets"]:
                        # 주기성 점수 계산
                        duration = group["last_seen"] - group["first_seen"]
                        expected_intervals = duration / avg_interval if avg_interval > 0 else 0
                        periodicity_score = group["count"] / expected_intervals if expected_intervals > 0 else 0

                        periodic_patterns.append(
                            {
                                "group_key": group_key,
                                "protocol": group["protocol"],
                                "src_ip": group["src_ip"],
                                "dst_ip": group["dst_ip"],
                                "packet_count": group["count"],
                                "avg_interval": avg_interval,
                                "duration": duration,
                                "periodicity_score": min(periodicity_score, 1.0),
                                "first_seen": group["first_seen"],
                                "last_seen": group["last_seen"],
                            }
                        )

                return periodic_patterns

            return []

        except Exception as e:
            logger.error(f"주기적 패턴 탐지 오류: {e}")
            return []

    def _detect_burst_patterns(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """버스트 패턴 탐지 (짧은 시간 내 다수의 유사 패킷)"""
        try:
            if len(sorted_packets) < self.thresholds["burst_min_packets"]:
                return []

            burst_patterns = []
            burst_window = self.thresholds["burst_window_seconds"]
            min_packets = self.thresholds["burst_min_packets"]

            for i in range(len(sorted_packets) - min_packets + 1):
                start_packet = sorted_packets[i]
                end_packet = sorted_packets[i + min_packets - 1]

                # 시간 윈도우 확인
                time_diff = end_packet.get("timestamp", 0) - start_packet.get("timestamp", 0)

                if time_diff <= burst_window:
                    # 같은 출발지/목적지 확인
                    window_packets = sorted_packets[i : i + min_packets]
                    src_ips = set(p.get("src_ip", "") for p in window_packets)
                    dst_ips = set(p.get("dst_ip", "") for p in window_packets)
                    protocols = set(p.get("protocol", "") for p in window_packets)

                    # 동일한 엔드포인트 간의 버스트인지 확인
                    if len(src_ips) == 1 and len(dst_ips) == 1:
                        burst = {
                            "start_time": start_packet.get("timestamp", 0),
                            "end_time": end_packet.get("timestamp", 0),
                            "src_ip": list(src_ips)[0],
                            "dst_ip": list(dst_ips)[0],
                            "protocols": list(protocols),
                            "packet_count": min_packets,
                            "duration": time_diff,
                            "intensity": (min_packets / time_diff if time_diff > 0 else float("inf")),
                        }

                        # 확장된 버스트 확인 (더 많은 패킷이 같은 패턴인지)
                        extended_count = min_packets
                        for j in range(i + min_packets, len(sorted_packets)):
                            next_packet = sorted_packets[j]
                            next_time = next_packet.get("timestamp", 0)

                            if (
                                next_time - start_packet.get("timestamp", 0) <= burst_window
                                and next_packet.get("src_ip") == burst["src_ip"]
                                and next_packet.get("dst_ip") == burst["dst_ip"]
                            ):
                                extended_count += 1
                                burst["end_time"] = next_time
                                burst["duration"] = next_time - burst["start_time"]
                            else:
                                break

                        burst["packet_count"] = extended_count
                        burst["intensity"] = (
                            extended_count / burst["duration"] if burst["duration"] > 0 else float("inf")
                        )

                        # 중복 제거 (유사한 시간대의 버스트)
                        is_duplicate = False
                        for existing_burst in burst_patterns:
                            if (
                                abs(existing_burst["start_time"] - burst["start_time"]) < 1.0
                                and existing_burst["src_ip"] == burst["src_ip"]
                                and existing_burst["dst_ip"] == burst["dst_ip"]
                            ):
                                is_duplicate = True
                                break

                        if not is_duplicate:
                            burst_patterns.append(burst)

            return burst_patterns

        except Exception as e:
            logger.error(f"버스트 패턴 탐지 오류: {e}")
            return []

    def _detect_scan_patterns(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """스캔 패턴 탐지 (포트 스캔, 호스트 스캔 등)"""
        try:
            scan_patterns = []

            # 포트 스캔 탐지
            port_scans = self._detect_port_scans(sorted_packets)
            scan_patterns.extend(port_scans)

            # 호스트 스캔 탐지
            host_scans = self._detect_host_scans(sorted_packets)
            scan_patterns.extend(host_scans)

            return scan_patterns

        except Exception as e:
            logger.error(f"스캔 패턴 탐지 오류: {e}")
            return []

    def _detect_port_scans(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """포트 스캔 탐지"""
        try:
            port_scans = defaultdict(
                lambda: {
                    "src_ip": "",
                    "dst_ip": "",
                    "ports": set(),
                    "start_time": float("inf"),
                    "end_time": 0,
                    "tcp_flags": set(),
                    "packet_count": 0,
                }
            )

            for packet in sorted_packets:
                src_ip = packet.get("src_ip", "")
                dst_ip = packet.get("dst_ip", "")
                dst_port = packet.get("dst_port")
                timestamp = packet.get("timestamp", 0)
                tcp_flags = packet.get("flags", [])

                if not (src_ip and dst_ip and dst_port is not None):
                    continue

                # 스캔 키 생성
                scan_key = f"{src_ip}_{dst_ip}"
                scan = port_scans[scan_key]

                scan["src_ip"] = src_ip
                scan["dst_ip"] = dst_ip
                scan["ports"].add(dst_port)
                scan["start_time"] = min(scan["start_time"], timestamp)
                scan["end_time"] = max(scan["end_time"], timestamp)
                scan["packet_count"] += 1

                if isinstance(tcp_flags, list):
                    scan["tcp_flags"].update(tcp_flags)

            # 포트 스캔 조건 확인
            detected_scans = []
            for scan_key, scan in port_scans.items():
                port_count = len(scan["ports"])
                duration = scan["end_time"] - scan["start_time"]

                if port_count >= self.thresholds["scan_min_ports"] and duration <= self.thresholds["scan_max_duration"]:
                    # 스캔 유형 분류
                    scan_type = "unknown"
                    if "SYN" in scan["tcp_flags"] and "ACK" not in scan["tcp_flags"]:
                        scan_type = "syn_scan"
                    elif "FIN" in scan["tcp_flags"]:
                        scan_type = "fin_scan"
                    elif not scan["tcp_flags"]:
                        scan_type = "udp_scan"

                    detected_scans.append(
                        {
                            "type": "port_scan",
                            "scan_type": scan_type,
                            "src_ip": scan["src_ip"],
                            "dst_ip": scan["dst_ip"],
                            "port_count": port_count,
                            "ports": sorted(list(scan["ports"]))[:20],  # 최대 20개 포트만 표시
                            "packet_count": scan["packet_count"],
                            "duration": duration,
                            "start_time": scan["start_time"],
                            "end_time": scan["end_time"],
                            "scan_rate": (port_count / duration if duration > 0 else float("inf")),
                        }
                    )

            return detected_scans

        except Exception as e:
            logger.error(f"포트 스캔 탐지 오류: {e}")
            return []

    def _detect_host_scans(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """호스트 스캔 탐지"""
        try:
            host_scans = defaultdict(
                lambda: {
                    "src_ip": "",
                    "dst_ips": set(),
                    "start_time": float("inf"),
                    "end_time": 0,
                    "packet_count": 0,
                    "protocols": set(),
                }
            )

            for packet in sorted_packets:
                src_ip = packet.get("src_ip", "")
                dst_ip = packet.get("dst_ip", "")
                protocol = packet.get("protocol", "")
                timestamp = packet.get("timestamp", 0)

                if not (src_ip and dst_ip):
                    continue

                scan = host_scans[src_ip]
                scan["src_ip"] = src_ip
                scan["dst_ips"].add(dst_ip)
                scan["protocols"].add(protocol)
                scan["start_time"] = min(scan["start_time"], timestamp)
                scan["end_time"] = max(scan["end_time"], timestamp)
                scan["packet_count"] += 1

            # 호스트 스캔 조건 확인
            detected_scans = []
            for src_ip, scan in host_scans.items():
                host_count = len(scan["dst_ips"])
                duration = scan["end_time"] - scan["start_time"]

                # 다수의 목적지 호스트를 짧은 시간에 스캔하는 경우
                if host_count >= 5 and duration <= 30.0:  # 30초 내 5개 이상 호스트
                    detected_scans.append(
                        {
                            "type": "host_scan",
                            "src_ip": scan["src_ip"],
                            "host_count": host_count,
                            "dst_ips": sorted(list(scan["dst_ips"]))[:10],  # 최대 10개 호스트만 표시
                            "protocols": list(scan["protocols"]),
                            "packet_count": scan["packet_count"],
                            "duration": duration,
                            "start_time": scan["start_time"],
                            "end_time": scan["end_time"],
                            "scan_rate": (host_count / duration if duration > 0 else float("inf")),
                        }
                    )

            return detected_scans

        except Exception as e:
            logger.error(f"호스트 스캔 탐지 오류: {e}")
            return []

    def _detect_targeted_patterns(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """표적화된 통신 패턴 탐지"""
        try:
            # 특정 목적지로의 집중적인 통신 분석
            target_analysis = defaultdict(
                lambda: {
                    "count": 0,
                    "sources": set(),
                    "protocols": set(),
                    "start_time": float("inf"),
                    "end_time": 0,
                    "total_bytes": 0,
                }
            )

            for packet in sorted_packets:
                dst_ip = packet.get("dst_ip", "")
                src_ip = packet.get("src_ip", "")
                protocol = packet.get("protocol", "")
                timestamp = packet.get("timestamp", 0)
                packet_size = packet.get("size", 0)

                if not dst_ip:
                    continue

                target = target_analysis[dst_ip]
                target["count"] += 1
                target["sources"].add(src_ip)
                target["protocols"].add(protocol)
                target["start_time"] = min(target["start_time"], timestamp)
                target["end_time"] = max(target["end_time"], timestamp)
                target["total_bytes"] += packet_size

            # 표적화 패턴 조건 확인
            targeted_patterns = []
            total_packets = len(sorted_packets)

            for dst_ip, target in target_analysis.items():
                packet_ratio = target["count"] / total_packets if total_packets > 0 else 0
                source_count = len(target["sources"])
                protocol_count = len(target["protocols"])

                # 조건: 전체 패킷의 일정 비율 이상 + 다수 발신지 + 다양한 프로토콜
                if (
                    packet_ratio > self.thresholds["targeted_packet_ratio"]
                    and source_count >= self.thresholds["targeted_min_sources"]
                    and protocol_count >= self.thresholds["targeted_min_protocols"]
                ):
                    duration = target["end_time"] - target["start_time"]

                    targeted_patterns.append(
                        {
                            "type": "targeted_communication",
                            "dst_ip": dst_ip,
                            "packet_count": target["count"],
                            "packet_ratio": packet_ratio,
                            "source_count": source_count,
                            "sources": sorted(list(target["sources"]))[:5],  # 최대 5개 발신지
                            "protocols": list(target["protocols"]),
                            "total_bytes": target["total_bytes"],
                            "duration": duration,
                            "start_time": target["start_time"],
                            "end_time": target["end_time"],
                            "traffic_intensity": (target["count"] / duration if duration > 0 else float("inf")),
                        }
                    )

            return targeted_patterns

        except Exception as e:
            logger.error(f"표적화 패턴 탐지 오류: {e}")
            return []

    def _detect_unusual_patterns(self, sorted_packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """비정상 패턴 탐지"""
        try:
            unusual_patterns = []

            # 프로토콜 분석
            unusual_protocols = self._detect_unusual_protocols(sorted_packets)
            if unusual_protocols:
                unusual_patterns.append(unusual_protocols)

            # 큰 패킷 분석
            large_packets = self._detect_large_packets(sorted_packets)
            if large_packets:
                unusual_patterns.append(large_packets)

            # TCP 플래그 이상 분석
            flag_anomalies = self._detect_flag_anomalies(sorted_packets)
            if flag_anomalies:
                unusual_patterns.append(flag_anomalies)

            # 시간 이상 분석
            time_anomalies = self._detect_time_anomalies(sorted_packets)
            if time_anomalies:
                unusual_patterns.append(time_anomalies)

            return unusual_patterns

        except Exception as e:
            logger.error(f"비정상 패턴 탐지 오류: {e}")
            return []

    def _detect_unusual_protocols(self, sorted_packets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """비정상 프로토콜 탐지"""
        common_protocols = {
            "TCP",
            "UDP",
            "ICMP",
            "DNS",
            "HTTP",
            "HTTPS",
            "ARP",
        }
        unusual_protocols = set()

        for packet in sorted_packets:
            protocol = packet.get("protocol", "Unknown")
            if protocol not in common_protocols:
                unusual_protocols.add(protocol)

        if unusual_protocols:
            return {
                "type": "unusual_protocols",
                "description": "일반적이지 않은 프로토콜 사용",
                "protocols": list(unusual_protocols),
                "protocol_count": len(unusual_protocols),
            }

        return None

    def _detect_large_packets(self, sorted_packets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """큰 패킷 탐지"""
        large_packets = []
        threshold = self.thresholds["large_packet_threshold"]

        for packet in sorted_packets:
            length = packet.get("length", 0) or packet.get("size", 0)
            if length > threshold:
                large_packets.append(
                    {
                        "timestamp": packet.get("timestamp", 0),
                        "length": length,
                        "protocol": packet.get("protocol", "Unknown"),
                        "src_ip": packet.get("src_ip", ""),
                        "dst_ip": packet.get("dst_ip", ""),
                    }
                )

        if large_packets:
            return {
                "type": "large_packets",
                "description": f"{threshold}바이트 이상의 큰 패킷",
                "packet_count": len(large_packets),
                "packets": large_packets[:5],  # 최대 5개만 표시
                "max_size": max(p["length"] for p in large_packets),
                "avg_size": sum(p["length"] for p in large_packets) / len(large_packets),
            }

        return None

    def _detect_flag_anomalies(self, sorted_packets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """TCP 플래그 이상 탐지"""
        flag_anomalies = []

        for packet in sorted_packets:
            protocol = packet.get("protocol", "")
            flags = packet.get("flags", [])

            if protocol == "TCP" and isinstance(flags, list):
                # 비정상적인 플래그 조합 확인
                anomaly_type = None
                if "SYN" in flags and "FIN" in flags:
                    anomaly_type = "SYN+FIN"
                elif "RST" in flags and "FIN" in flags:
                    anomaly_type = "RST+FIN"
                elif "URG" in flags and "PSH" in flags and "FIN" in flags:
                    anomaly_type = "URG+PSH+FIN"

                if anomaly_type:
                    flag_anomalies.append(
                        {
                            "timestamp": packet.get("timestamp", 0),
                            "src_ip": packet.get("src_ip", ""),
                            "dst_ip": packet.get("dst_ip", ""),
                            "flags": flags,
                            "anomaly": anomaly_type,
                        }
                    )

        if flag_anomalies:
            return {
                "type": "flag_anomalies",
                "description": "TCP 플래그 조합 이상",
                "anomaly_count": len(flag_anomalies),
                "anomalies": flag_anomalies[:5],  # 최대 5개만 표시
            }

        return None

    def _detect_time_anomalies(self, sorted_packets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """시간 이상 탐지"""
        if len(sorted_packets) < 2:
            return None

        # 시간 간격 분석
        time_gaps = []
        for i in range(1, len(sorted_packets)):
            gap = sorted_packets[i].get("timestamp", 0) - sorted_packets[i - 1].get("timestamp", 0)
            time_gaps.append(gap)

        if not time_gaps:
            return None

        # 비정상적으로 긴 시간 간격 탐지
        avg_gap = sum(time_gaps) / len(time_gaps)
        max_gap = max(time_gaps)

        # 평균의 10배 이상인 시간 간격이 있는 경우
        if max_gap > avg_gap * 10:
            return {
                "type": "time_anomalies",
                "description": "비정상적인 시간 간격",
                "avg_gap": avg_gap,
                "max_gap": max_gap,
                "gap_ratio": max_gap / avg_gap if avg_gap > 0 else float("inf"),
            }

        return None

    def _update_statistics(self, patterns: Dict[str, List]):
        """통계 정보 업데이트"""
        try:
            self.statistics["patterns_detected"] = sum(len(p) for p in patterns.values())
            self.statistics["periodic_patterns"] = len(patterns.get("periodic", []))
            self.statistics["burst_patterns"] = len(patterns.get("burst", []))
            self.statistics["scan_patterns"] = len(patterns.get("scan", []))
            self.statistics["targeted_patterns"] = len(patterns.get("targeted", []))
            self.statistics["unusual_patterns"] = len(patterns.get("unusual", []))
            self.statistics["last_analysis"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"통계 업데이트 오류: {e}")

    def _generate_summary(self, patterns: Dict[str, List]) -> Dict[str, Any]:
        """패턴 분석 요약 생성"""
        try:
            total_patterns = sum(len(p) for p in patterns.values())

            summary = {
                "total_patterns": total_patterns,
                "pattern_types": {
                    "periodic": len(patterns.get("periodic", [])),
                    "burst": len(patterns.get("burst", [])),
                    "scan": len(patterns.get("scan", [])),
                    "targeted": len(patterns.get("targeted", [])),
                    "unusual": len(patterns.get("unusual", [])),
                },
                "security_concerns": [],
                "recommendations": [],
            }

            # 보안 우려사항 식별
            if patterns.get("scan"):
                summary["security_concerns"].append("포트/호스트 스캔 활동 탐지")
                summary["recommendations"].append("방화벽 정책 검토 및 침입 탐지 시스템 강화")

            if patterns.get("unusual"):
                summary["security_concerns"].append("비정상적인 네트워크 활동 탐지")
                summary["recommendations"].append("네트워크 모니터링 강화 및 로그 분석")

            if patterns.get("targeted"):
                summary["security_concerns"].append("표적화된 공격 패턴 의심")
                summary["recommendations"].append("해당 대상의 보안 상태 점검 및 접근 제어 강화")

            if patterns.get("burst"):
                summary["security_concerns"].append("버스트 트래픽으로 인한 DDoS 공격 가능성")
                summary["recommendations"].append("트래픽 제한 및 부하 분산 검토")

            return summary

        except Exception as e:
            logger.error(f"요약 생성 오류: {e}")
            return {"total_patterns": 0, "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """패턴 탐지 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "patterns_detected": 0,
            "periodic_patterns": 0,
            "burst_patterns": 0,
            "scan_patterns": 0,
            "targeted_patterns": 0,
            "unusual_patterns": 0,
            "last_analysis": None,
        }
        logger.info("패턴 탐지 통계 초기화됨")

    def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """탐지 임계값 업데이트"""
        try:
            for key, value in new_thresholds.items():
                if key in self.thresholds:
                    self.thresholds[key] = value
                    logger.info(f"임계값 업데이트: {key} = {value}")
                else:
                    logger.warning(f"알 수 없는 임계값 키: {key}")
        except Exception as e:
            logger.error(f"임계값 업데이트 오류: {e}")

    def get_thresholds(self) -> Dict[str, Any]:
        """현재 임계값 설정 반환"""
        return self.thresholds.copy()


# 팩토리 함수
def create_pattern_detector() -> PatternDetector:
    """패턴 탐지기 인스턴스 생성"""
    return PatternDetector()

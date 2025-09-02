#!/usr/bin/env python3
"""
CSV 내보내기
패킷 분석 결과를 CSV 형식으로 내보내기
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CSVExporter:
    """CSV 형식 데이터 내보내기"""

    def __init__(self, delimiter: str = ",", quoting: int = csv.QUOTE_MINIMAL):
        """
        CSV 내보내기 초기화

        Args:
            delimiter: CSV 구분자
            quoting: 인용 방식
        """
        self.delimiter = delimiter
        self.quoting = quoting
        self.statistics = {
            "exported_files": 0,
            "exported_records": 0,
            "last_export": None,
        }

    def export_packets(
        self,
        packets: List[Dict[str, Any]],
        output_path: str,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        패킷 목록을 CSV로 내보내기

        Args:
            packets: 패킷 데이터 목록
            output_path: 출력 파일 경로
            columns: 내보낼 컬럼 목록 (None이면 모든 컬럼)

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

            # 컬럼 결정
            if columns is None:
                columns = self._get_all_columns(packets)

            exported_count = 0

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=columns,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                    extrasaction="ignore",
                )

                # 헤더 작성
                writer.writeheader()

                # 데이터 작성
                for packet in packets:
                    flattened_packet = self._flatten_packet_data(packet)
                    writer.writerow(flattened_packet)
                    exported_count += 1

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += exported_count
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"CSV 내보내기 완료: {output_path} ({exported_count}개 레코드)")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": exported_count,
                "columns": columns,
                "file_size": Path(output_path).stat().st_size,
            }

        except Exception as e:
            logger.error(f"CSV 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_analysis_results(
        self, analysis_results: List[Dict[str, Any]], output_path: str
    ) -> Dict[str, Any]:
        """
        분석 결과를 CSV로 내보내기

        Args:
            analysis_results: 분석 결과 목록
            output_path: 출력 파일 경로

        Returns:
            dict: 내보내기 결과
        """
        try:
            if not analysis_results:
                return {
                    "success": False,
                    "error": "내보낼 분석 결과가 없습니다",
                    "exported_count": 0,
                }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 분석 결과 구조에 맞는 컬럼 정의
            columns = [
                "timestamp",
                "src_ip",
                "dst_ip",
                "src_port",
                "dst_port",
                "protocol",
                "packet_size",
                "analysis_type",
                "result_summary",
                "security_issues",
                "anomalies",
                "confidence_score",
            ]

            exported_count = 0

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=columns,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                    extrasaction="ignore",
                )

                writer.writeheader()

                for result in analysis_results:
                    csv_row = self._convert_analysis_to_csv_row(result)
                    writer.writerow(csv_row)
                    exported_count += 1

            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += exported_count
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"분석 결과 CSV 내보내기 완료: {output_path} ({exported_count}개 레코드)")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": exported_count,
                "columns": columns,
                "file_size": Path(output_path).stat().st_size,
            }

        except Exception as e:
            logger.error(f"분석 결과 CSV 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_statistics(
        self, statistics: Dict[str, Any], output_path: str
    ) -> Dict[str, Any]:
        """
        통계 데이터를 CSV로 내보내기

        Args:
            statistics: 통계 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 내보내기 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 통계 데이터를 행으로 변환
            rows = []

            def flatten_stats(data: Dict[str, Any], prefix: str = ""):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key

                    if isinstance(value, dict):
                        flatten_stats(value, full_key)
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                flatten_stats(item, f"{full_key}[{i}]")
                            else:
                                rows.append(
                                    {
                                        "category": full_key,
                                        "index": i,
                                        "value": str(item),
                                        "type": type(item).__name__,
                                    }
                                )
                    else:
                        rows.append(
                            {
                                "category": full_key,
                                "index": "",
                                "value": str(value),
                                "type": type(value).__name__,
                            }
                        )

            flatten_stats(statistics)

            if not rows:
                return {
                    "success": False,
                    "error": "내보낼 통계 데이터가 없습니다",
                    "exported_count": 0,
                }

            columns = ["category", "index", "value", "type"]

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=columns,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                )

                writer.writeheader()
                writer.writerows(rows)

            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += len(rows)
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"통계 CSV 내보내기 완료: {output_path} ({len(rows)}개 레코드)")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": len(rows),
                "columns": columns,
                "file_size": Path(output_path).stat().st_size,
            }

        except Exception as e:
            logger.error(f"통계 CSV 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_filtered_packets(
        self,
        packets: List[Dict[str, Any]],
        filter_criteria: Dict[str, Any],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        필터링된 패킷을 CSV로 내보내기

        Args:
            packets: 전체 패킷 목록
            filter_criteria: 필터 조건
            output_path: 출력 파일 경로

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 필터 적용
            filtered_packets = self._apply_filter(packets, filter_criteria)

            if not filtered_packets:
                return {
                    "success": False,
                    "error": "필터 조건에 맞는 패킷이 없습니다",
                    "exported_count": 0,
                    "total_packets": len(packets),
                }

            # 필터 정보를 메타데이터로 추가
            result = self.export_packets(filtered_packets, output_path)

            if result["success"]:
                result.update(
                    {
                        "filter_criteria": filter_criteria,
                        "total_packets": len(packets),
                        "filtered_packets": len(filtered_packets),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"필터링된 패킷 CSV 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def _get_all_columns(self, packets: List[Dict[str, Any]]) -> List[str]:
        """모든 패킷에서 사용되는 컬럼 추출"""
        columns = set()

        for packet in packets:
            flattened = self._flatten_packet_data(packet)
            columns.update(flattened.keys())

        # 일반적인 순서로 정렬
        priority_columns = [
            "timestamp",
            "src_ip",
            "dst_ip",
            "src_port",
            "dst_port",
            "protocol",
            "size",
            "packet_size",
        ]

        ordered_columns = []
        for col in priority_columns:
            if col in columns:
                ordered_columns.append(col)
                columns.remove(col)

        # 나머지 컬럼 추가 (알파벳 순)
        ordered_columns.extend(sorted(columns))

        return ordered_columns

    def _flatten_packet_data(
        self, packet: Dict[str, Any], prefix: str = ""
    ) -> Dict[str, Any]:
        """패킷 데이터를 플랫 구조로 변환"""
        flattened = {}

        for key, value in packet.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # 중첩된 딕셔너리 평면화
                nested_flattened = self._flatten_packet_data(value, full_key)
                flattened.update(nested_flattened)
            elif isinstance(value, list):
                # 리스트를 문자열로 변환
                if value and isinstance(value[0], dict):
                    # 딕셔너리 리스트인 경우 첫 번째 요소만 사용
                    nested_flattened = self._flatten_packet_data(value[0], full_key)
                    flattened.update(nested_flattened)
                else:
                    # 단순 리스트인 경우 문자열로 결합
                    flattened[full_key] = ", ".join(str(item) for item in value)
            else:
                # 단순 값
                flattened[full_key] = value

        return flattened

    def _convert_analysis_to_csv_row(
        self, analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """분석 결과를 CSV 행으로 변환"""
        packet_info = analysis_result.get("packet_info", {})

        # 보안 이슈를 문자열로 변환
        security_issues = analysis_result.get("security_issues", [])
        security_summary = (
            "; ".join(
                [
                    f"{issue.get('type', 'unknown')}: {issue.get('description', '')}"
                    for issue in security_issues
                ]
            )
            if security_issues
            else ""
        )

        # 이상 징후를 문자열로 변환
        anomalies = analysis_result.get("anomalies", [])
        anomaly_summary = (
            "; ".join(
                [
                    f"{anomaly.get('type', 'unknown')}: {anomaly.get('description', '')}"
                    for anomaly in anomalies
                ]
            )
            if anomalies
            else ""
        )

        return {
            "timestamp": analysis_result.get("timestamp", ""),
            "src_ip": packet_info.get("src_ip", ""),
            "dst_ip": packet_info.get("dst_ip", ""),
            "src_port": packet_info.get("src_port", ""),
            "dst_port": packet_info.get("dst_port", ""),
            "protocol": packet_info.get("protocol", ""),
            "packet_size": packet_info.get("size", ""),
            "analysis_type": analysis_result.get("analysis_type", ""),
            "result_summary": analysis_result.get("summary", ""),
            "security_issues": security_summary,
            "anomalies": anomaly_summary,
            "confidence_score": analysis_result.get("confidence", ""),
        }

    def _apply_filter(
        self, packets: List[Dict[str, Any]], filter_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """패킷에 필터 조건 적용"""
        filtered = []

        for packet in packets:
            if self._packet_matches_filter(packet, filter_criteria):
                filtered.append(packet)

        return filtered

    def _packet_matches_filter(
        self, packet: Dict[str, Any], filter_criteria: Dict[str, Any]
    ) -> bool:
        """패킷이 필터 조건에 맞는지 확인"""
        try:
            for field, condition in filter_criteria.items():
                packet_value = packet.get(field)

                if packet_value is None:
                    return False

                if isinstance(condition, dict):
                    operator = condition.get("operator", "eq")
                    value = condition.get("value")

                    if operator == "eq" and packet_value != value:
                        return False
                    elif operator == "ne" and packet_value == value:
                        return False
                    elif operator == "gt" and packet_value <= value:
                        return False
                    elif operator == "lt" and packet_value >= value:
                        return False
                    elif operator == "contains" and value not in str(packet_value):
                        return False
                    elif operator == "in" and packet_value not in value:
                        return False
                else:
                    # 단순 값 비교
                    if packet_value != condition:
                        return False

            return True

        except Exception as e:
            logger.error(f"필터 매칭 오류: {e}")
            return False

    def create_summary_report(
        self, packets: List[Dict[str, Any]], output_path: str
    ) -> Dict[str, Any]:
        """패킷 데이터의 요약 보고서를 CSV로 생성"""
        try:
            if not packets:
                return {
                    "success": False,
                    "error": "요약할 패킷 데이터가 없습니다",
                    "exported_count": 0,
                }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 요약 통계 계산
            summary_data = self._calculate_summary_statistics(packets)

            # 요약 데이터를 CSV 형태로 변환
            rows = []

            # 기본 통계
            rows.append(
                {
                    "metric": "Total Packets",
                    "value": summary_data["total_packets"],
                    "description": "전체 패킷 수",
                }
            )

            # 프로토콜별 통계
            for protocol, count in summary_data["protocols"].items():
                rows.append(
                    {
                        "metric": f"Protocol: {protocol}",
                        "value": count,
                        "description": f"{protocol} 프로토콜 패킷 수",
                    }
                )

            # 상위 IP 주소
            for i, (ip, count) in enumerate(summary_data["top_src_ips"][:10]):
                rows.append(
                    {
                        "metric": f"Top Source IP #{i + 1}",
                        "value": f"{ip} ({count})",
                        "description": "상위 송신 IP 주소",
                    }
                )

            # 상위 포트
            for i, (port, count) in enumerate(summary_data["top_dst_ports"][:10]):
                rows.append(
                    {
                        "metric": f"Top Destination Port #{i + 1}",
                        "value": f"{port} ({count})",
                        "description": "상위 수신 포트",
                    }
                )

            columns = ["metric", "value", "description"]

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=columns,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                )

                writer.writeheader()
                writer.writerows(rows)

            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += len(rows)
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"요약 보고서 CSV 생성 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": len(rows),
                "columns": columns,
                "file_size": Path(output_path).stat().st_size,
                "summary_data": summary_data,
            }

        except Exception as e:
            logger.error(f"요약 보고서 CSV 생성 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def _calculate_summary_statistics(
        self, packets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """패킷 데이터의 요약 통계 계산"""
        from collections import Counter

        protocols = Counter()
        src_ips = Counter()
        dst_ips = Counter()
        src_ports = Counter()
        dst_ports = Counter()
        packet_sizes = []

        for packet in packets:
            protocol = packet.get("protocol", "unknown")
            protocols[protocol] += 1

            src_ip = packet.get("src_ip")
            if src_ip:
                src_ips[src_ip] += 1

            dst_ip = packet.get("dst_ip")
            if dst_ip:
                dst_ips[dst_ip] += 1

            src_port = packet.get("src_port")
            if src_port:
                src_ports[src_port] += 1

            dst_port = packet.get("dst_port")
            if dst_port:
                dst_ports[dst_port] += 1

            size = packet.get("size") or packet.get("packet_size")
            if size:
                packet_sizes.append(size)

        # 통계 계산
        avg_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0

        return {
            "total_packets": len(packets),
            "protocols": dict(protocols),
            "top_src_ips": src_ips.most_common(10),
            "top_dst_ips": dst_ips.most_common(10),
            "top_src_ports": src_ports.most_common(10),
            "top_dst_ports": dst_ports.most_common(10),
            "average_packet_size": avg_size,
            "min_packet_size": min(packet_sizes) if packet_sizes else 0,
            "max_packet_size": max(packet_sizes) if packet_sizes else 0,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """내보내기 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "exported_files": 0,
            "exported_records": 0,
            "last_export": None,
        }
        logger.info("CSV 내보내기 통계 초기화됨")


# 팩토리 함수
def create_csv_exporter(
    delimiter: str = ",", quoting: int = csv.QUOTE_MINIMAL
) -> CSVExporter:
    """CSV 내보내기 인스턴스 생성"""
    return CSVExporter(delimiter, quoting)

#!/usr/bin/env python3
"""
데이터 내보내기 (JSON/CSV)
패킷 데이터를 JSON 및 CSV 형식으로 내보내기
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataExporter:
    """패킷 데이터 내보내기"""

    def __init__(self, output_base_dir: str = "data/output/download"):
        """
        데이터 내보내기 초기화

        Args:
            output_base_dir: 출력 파일 기본 디렉토리
        """
        self.output_base_dir = output_base_dir
        self.statistics = {
            "exported_files": 0,
            "total_packets_exported": 0,
            "last_export": None,
        }

        # 출력 디렉토리 생성
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)

    def export_to_json(
        self,
        packets: List[Dict[str, Any]],
        session_id: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        패킷 데이터를 JSON 형식으로 내보내기

        Args:
            packets: 패킷 목록
            session_id: 세션 ID
            filename: 사용자 지정 파일명 (선택)

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 파일 경로 설정
            if filename:
                file_path = os.path.join(self.output_base_dir, filename)
                if not file_path.endswith(".json"):
                    file_path += ".json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(
                    self.output_base_dir,
                    f"packets_{session_id}_{timestamp}.json",
                )

            # 패킷 데이터 단순화
            simplified_packets = self._simplify_packets(packets)

            # JSON 파일로 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(simplified_packets, f, indent=2, ensure_ascii=False)

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["total_packets_exported"] += len(simplified_packets)
            self.statistics["last_export"] = datetime.now().isoformat()

            file_size = Path(file_path).stat().st_size

            logger.info(f"JSON 내보내기 완료: {file_path} ({len(simplified_packets)}개 패킷)")

            return {
                "success": True,
                "format": "json",
                "file_path": file_path,
                "packet_count": len(simplified_packets),
                "file_size": file_size,
                "message": f"{len(simplified_packets)}개 패킷이 JSON 형식으로 저장됨",
            }

        except Exception as e:
            logger.error(f"JSON 내보내기 오류: {e}")
            return {
                "success": False,
                "format": "json",
                "error": str(e),
                "message": f"JSON 파일 저장 중 오류: {str(e)}",
            }

    def export_to_csv(
        self,
        packets: List[Dict[str, Any]],
        session_id: str,
        filename: Optional[str] = None,
        custom_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        패킷 데이터를 CSV 형식으로 내보내기

        Args:
            packets: 패킷 목록
            session_id: 세션 ID
            filename: 사용자 지정 파일명 (선택)
            custom_fields: 사용자 지정 필드 목록 (선택)

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 파일 경로 설정
            if filename:
                file_path = os.path.join(self.output_base_dir, filename)
                if not file_path.endswith(".csv"):
                    file_path += ".csv"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(
                    self.output_base_dir,
                    f"packets_{session_id}_{timestamp}.csv",
                )

            # CSV 필드명 설정
            if custom_fields:
                fieldnames = custom_fields
            else:
                fieldnames = [
                    "id",
                    "timestamp",
                    "time",
                    "src_ip",
                    "dst_ip",
                    "protocol",
                    "src_port",
                    "dst_port",
                    "length",
                    "info",
                    "flags",
                    "payload_preview",
                ]

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                # 패킷 데이터 작성
                for packet in packets:
                    row = self._prepare_csv_row(packet, fieldnames)
                    writer.writerow(row)

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["total_packets_exported"] += len(packets)
            self.statistics["last_export"] = datetime.now().isoformat()

            file_size = Path(file_path).stat().st_size

            logger.info(f"CSV 내보내기 완료: {file_path} ({len(packets)}개 패킷)")

            return {
                "success": True,
                "format": "csv",
                "file_path": file_path,
                "packet_count": len(packets),
                "file_size": file_size,
                "message": f"{len(packets)}개 패킷이 CSV 형식으로 저장됨",
            }

        except Exception as e:
            logger.error(f"CSV 내보내기 오류: {e}")
            return {
                "success": False,
                "format": "csv",
                "error": str(e),
                "message": f"CSV 파일 저장 중 오류: {str(e)}",
            }

    def export_summary_json(
        self,
        summary_data: Dict[str, Any],
        session_id: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        요약 데이터를 JSON 형식으로 내보내기

        Args:
            summary_data: 요약 데이터
            session_id: 세션 ID
            filename: 사용자 지정 파일명 (선택)

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 파일 경로 설정
            if filename:
                file_path = os.path.join(self.output_base_dir, filename)
                if not file_path.endswith(".json"):
                    file_path += ".json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(
                    self.output_base_dir,
                    f"summary_{session_id}_{timestamp}.json",
                )

            # 요약 데이터에 메타정보 추가
            export_data = {
                "export_info": {
                    "session_id": session_id,
                    "export_time": datetime.now().isoformat(),
                    "export_type": "summary",
                },
                "summary": summary_data,
            }

            # JSON 파일로 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["last_export"] = datetime.now().isoformat()

            file_size = Path(file_path).stat().st_size

            logger.info(f"요약 JSON 내보내기 완료: {file_path}")

            return {
                "success": True,
                "format": "summary_json",
                "file_path": file_path,
                "file_size": file_size,
                "message": "요약 데이터가 JSON 형식으로 저장됨",
            }

        except Exception as e:
            logger.error(f"요약 JSON 내보내기 오류: {e}")
            return {
                "success": False,
                "format": "summary_json",
                "error": str(e),
                "message": f"요약 JSON 파일 저장 중 오류: {str(e)}",
            }

    def export_filtered_data(
        self,
        packets: List[Dict[str, Any]],
        filter_criteria: Dict[str, Any],
        export_format: str,
        session_id: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        필터링된 데이터 내보내기

        Args:
            packets: 패킷 목록
            filter_criteria: 필터 조건
            export_format: 내보내기 형식 ('json' 또는 'csv')
            session_id: 세션 ID
            filename: 사용자 지정 파일명 (선택)

        Returns:
            dict: 내보내기 결과
        """
        try:
            # 패킷 필터링
            filtered_packets = self._apply_filters(packets, filter_criteria)

            # 필터 정보 추가
            filter_info = {
                "original_count": len(packets),
                "filtered_count": len(filtered_packets),
                "filter_criteria": filter_criteria,
                "filter_time": datetime.now().isoformat(),
            }

            # 형식에 따른 내보내기
            if export_format.lower() == "json":
                result = self.export_to_json(filtered_packets, session_id, filename)
                if result["success"]:
                    result["filter_info"] = filter_info
            elif export_format.lower() == "csv":
                result = self.export_to_csv(filtered_packets, session_id, filename)
                if result["success"]:
                    result["filter_info"] = filter_info
            else:
                return {
                    "success": False,
                    "error": f"지원되지 않는 형식: {export_format}",
                    "message": f"지원되지 않는 형식: {export_format}",
                }

            return result

        except Exception as e:
            logger.error(f"필터링된 데이터 내보내기 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"필터링된 데이터 내보내기 중 오류: {str(e)}",
            }

    def _simplify_packets(self, packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """패킷 데이터 단순화"""
        simplified = []

        for packet in packets:
            # 기본 필드만 포함하여 파일 크기 최적화
            simple_packet = {
                "id": packet.get("id", ""),
                "timestamp": packet.get("timestamp", ""),
                "time": packet.get("time", ""),
                "src_ip": packet.get("src_ip", ""),
                "dst_ip": packet.get("dst_ip", ""),
                "protocol": packet.get("protocol", ""),
                "src_port": packet.get("src_port", ""),
                "dst_port": packet.get("dst_port", ""),
                "length": packet.get("length", 0),
                "info": packet.get("info", ""),
                "flags": packet.get("flags", []),
            }

            # 딥 검사 결과가 있으면 요약 정보만 포함
            if "deep_inspection" in packet:
                deep_inspection = packet["deep_inspection"]
                simple_packet["security_summary"] = {
                    "threat_level": deep_inspection.get("threat_level", "none"),
                    "suspicious_patterns": len(deep_inspection.get("suspicious_patterns", [])),
                    "malware_indicators": len(deep_inspection.get("malware_indicators", [])),
                }

            # 페이로드 미리보기 (처음 100자만)
            payload = packet.get("payload", "")
            if payload:
                if isinstance(payload, bytes):
                    try:
                        payload_str = payload.decode("utf-8", errors="ignore")
                    except Exception:
                        payload_str = str(payload)
                else:
                    payload_str = str(payload)

                simple_packet["payload_preview"] = payload_str[:100] + ("..." if len(payload_str) > 100 else "")

            simplified.append(simple_packet)

        return simplified

    def _prepare_csv_row(self, packet: Dict[str, Any], fieldnames: List[str]) -> Dict[str, str]:
        """CSV 행 데이터 준비"""
        row = {}

        for field in fieldnames:
            value = packet.get(field, "")

            # 특수 필드 처리
            if field == "flags" and isinstance(value, list):
                row[field] = ",".join(str(flag) for flag in value)
            elif field == "payload_preview":
                payload = packet.get("payload", "")
                if payload:
                    if isinstance(payload, bytes):
                        try:
                            payload_str = payload.decode("utf-8", errors="ignore")
                        except Exception:
                            payload_str = str(payload)
                    else:
                        payload_str = str(payload)
                    row[field] = payload_str[:50] + ("..." if len(payload_str) > 50 else "")
                else:
                    row[field] = ""
            else:
                # 일반 필드는 문자열로 변환
                row[field] = str(value) if value is not None else ""

        return row

    def _apply_filters(self, packets: List[Dict[str, Any]], filter_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """필터 조건 적용"""
        filtered = []

        for packet in packets:
            include_packet = True

            # 프로토콜 필터
            if "protocol" in filter_criteria:
                required_protocol = filter_criteria["protocol"]
                if packet.get("protocol") != required_protocol:
                    include_packet = False
                    continue

            # IP 필터
            if "src_ip" in filter_criteria:
                required_src = filter_criteria["src_ip"]
                if packet.get("src_ip") != required_src:
                    include_packet = False
                    continue

            if "dst_ip" in filter_criteria:
                required_dst = filter_criteria["dst_ip"]
                if packet.get("dst_ip") != required_dst:
                    include_packet = False
                    continue

            # 포트 필터
            if "port" in filter_criteria:
                required_port = filter_criteria["port"]
                src_port = packet.get("src_port")
                dst_port = packet.get("dst_port")
                if src_port != required_port and dst_port != required_port:
                    include_packet = False
                    continue

            # 시간 범위 필터
            if "time_range" in filter_criteria:
                time_range = filter_criteria["time_range"]
                packet_time = packet.get("timestamp", 0)
                if not (time_range.get("start", 0) <= packet_time <= time_range.get("end", float("inf"))):
                    include_packet = False
                    continue

            # 패킷 크기 필터
            if "min_length" in filter_criteria:
                min_length = filter_criteria["min_length"]
                if packet.get("length", 0) < min_length:
                    include_packet = False
                    continue

            if "max_length" in filter_criteria:
                max_length = filter_criteria["max_length"]
                if packet.get("length", 0) > max_length:
                    include_packet = False
                    continue

            if include_packet:
                filtered.append(packet)

        return filtered

    def get_supported_formats(self) -> List[str]:
        """지원되는 내보내기 형식 반환"""
        return ["json", "csv", "summary_json"]

    def get_statistics(self) -> Dict[str, Any]:
        """내보내기 통계 반환"""
        return self.statistics.copy()

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "exported_files": 0,
            "total_packets_exported": 0,
            "last_export": None,
        }
        logger.info("데이터 내보내기 통계 초기화됨")

    def cleanup_old_files(self, max_age_days: int = 7) -> Dict[str, Any]:
        """오래된 내보내기 파일 정리"""
        try:
            from datetime import timedelta

            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            deleted_files = []
            total_size_freed = 0

            for file_path in Path(self.output_base_dir).glob("*"):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        total_size_freed += file_size

            logger.info(f"오래된 파일 정리 완료: {len(deleted_files)}개 파일, {total_size_freed} bytes")

            return {
                "success": True,
                "deleted_count": len(deleted_files),
                "size_freed": total_size_freed,
                "deleted_files": deleted_files,
            }

        except Exception as e:
            logger.error(f"파일 정리 오류: {e}")
            return {"success": False, "error": str(e)}


# 팩토리 함수
def create_data_exporter(
    output_base_dir: str = "data/output/download",
) -> DataExporter:
    """데이터 내보내기 인스턴스 생성"""
    return DataExporter(output_base_dir)

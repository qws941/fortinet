#!/usr/bin/env python3
"""
JSON 내보내기
패킷 분석 결과를 JSON 형식으로 내보내기
"""

import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JSONExporter:
    """JSON 형식 데이터 내보내기"""

    def __init__(
        self,
        indent: Optional[int] = 2,
        ensure_ascii: bool = False,
        compress: bool = False,
    ):
        """
        JSON 내보내기 초기화

        Args:
            indent: JSON 들여쓰기 (None이면 한 줄로)
            ensure_ascii: ASCII 문자만 사용 여부
            compress: gzip 압축 여부
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.compress = compress
        self.statistics = {
            "exported_files": 0,
            "exported_records": 0,
            "compressed_files": 0,
            "total_size": 0,
            "last_export": None,
        }

    def export_packets(
        self,
        packets: List[Dict[str, Any]],
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        패킷 목록을 JSON으로 내보내기

        Args:
            packets: 패킷 데이터 목록
            output_path: 출력 파일 경로
            metadata: 추가 메타데이터

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

            # JSON 구조 생성
            json_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "packet_count": len(packets),
                    "exporter": "FortiGate Nextrade Packet Sniffer",
                },
                "packets": packets,
            }

            # 사용자 정의 메타데이터 추가
            if metadata:
                json_data["metadata"].update(metadata)

            # 압축 여부에 따라 다른 방식으로 저장
            if self.compress:
                output_path = self._ensure_gz_extension(output_path)
                with gzip.open(output_path, "wt", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )
                self.statistics["compressed_files"] += 1
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += len(packets)
            self.statistics["total_size"] += file_size
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"JSON 내보내기 완료: {output_path} ({len(packets)}개 패킷)")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": len(packets),
                "file_size": file_size,
                "compressed": self.compress,
                "metadata": json_data["metadata"],
            }

        except Exception as e:
            logger.error(f"JSON 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_analysis_results(
        self,
        analysis_results: List[Dict[str, Any]],
        output_path: str,
        include_raw_packets: bool = False,
    ) -> Dict[str, Any]:
        """
        분석 결과를 JSON으로 내보내기

        Args:
            analysis_results: 분석 결과 목록
            output_path: 출력 파일 경로
            include_raw_packets: 원본 패킷 데이터 포함 여부

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

            # 분석 결과 처리
            processed_results = []
            for result in analysis_results:
                processed_result = self._process_analysis_result(result, include_raw_packets)
                processed_results.append(processed_result)

            # 요약 통계 생성
            summary = self._generate_analysis_summary(processed_results)

            # JSON 구조 생성
            json_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "analysis_count": len(processed_results),
                    "include_raw_packets": include_raw_packets,
                    "exporter": "FortiGate Nextrade Packet Analyzer",
                },
                "summary": summary,
                "analysis_results": processed_results,
            }

            # 파일 저장
            if self.compress:
                output_path = self._ensure_gz_extension(output_path)
                with gzip.open(output_path, "wt", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )
                self.statistics["compressed_files"] += 1
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += len(processed_results)
            self.statistics["total_size"] += file_size
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"분석 결과 JSON 내보내기 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "exported_count": len(processed_results),
                "file_size": file_size,
                "compressed": self.compress,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"분석 결과 JSON 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_statistics(
        self,
        statistics: Dict[str, Any],
        output_path: str,
        include_charts_data: bool = True,
    ) -> Dict[str, Any]:
        """
        통계 데이터를 JSON으로 내보내기

        Args:
            statistics: 통계 데이터
            output_path: 출력 파일 경로
            include_charts_data: 차트 데이터 포함 여부

        Returns:
            dict: 내보내기 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 차트 데이터 생성
            charts_data = {}
            if include_charts_data:
                charts_data = self._generate_charts_data(statistics)

            # JSON 구조 생성
            json_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "include_charts_data": include_charts_data,
                    "exporter": "FortiGate Nextrade Statistics",
                },
                "statistics": statistics,
                "charts_data": charts_data,
            }

            # 파일 저장
            if self.compress:
                output_path = self._ensure_gz_extension(output_path)
                with gzip.open(output_path, "wt", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )
                self.statistics["compressed_files"] += 1
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["exported_records"] += self._count_statistics_records(statistics)
            self.statistics["total_size"] += file_size
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"통계 JSON 내보내기 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "compressed": self.compress,
                "include_charts_data": include_charts_data,
            }

        except Exception as e:
            logger.error(f"통계 JSON 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_configuration(self, config: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        설정 데이터를 JSON으로 내보내기

        Args:
            config: 설정 데이터
            output_path: 출력 파일 경로

        Returns:
            dict: 내보내기 결과
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # JSON 구조 생성
            json_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "config_type": "packet_sniffer_configuration",
                    "exporter": "FortiGate Nextrade Configuration",
                },
                "configuration": config,
            }

            # 파일 저장 (설정은 일반적으로 압축하지 않음)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    json_data,
                    f,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    default=self._json_serializer,
                )

            file_size = Path(output_path).stat().st_size

            # 통계 업데이트
            self.statistics["exported_files"] += 1
            self.statistics["total_size"] += file_size
            self.statistics["last_export"] = datetime.now().isoformat()

            logger.info(f"설정 JSON 내보내기 완료: {output_path}")

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "configuration_keys": list(config.keys()),
            }

        except Exception as e:
            logger.error(f"설정 JSON 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def export_batch(self, data_sets: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """
        여러 데이터셋을 일괄 JSON으로 내보내기

        Args:
            data_sets: 데이터셋 목록 [{'name': str, 'data': Any, 'type': str}]
            output_dir: 출력 디렉토리

        Returns:
            dict: 일괄 내보내기 결과
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            results = []
            total_exported = 0

            for dataset in data_sets:
                name = dataset["name"]
                data = dataset["data"]
                data_type = dataset.get("type", "general")

                # 파일명 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}.json"
                if self.compress:
                    filename += ".gz"

                file_path = output_path / filename

                # 데이터 타입에 따른 내보내기
                if data_type == "packets":
                    result = self.export_packets(data, str(file_path))
                elif data_type == "analysis":
                    result = self.export_analysis_results(data, str(file_path))
                elif data_type == "statistics":
                    result = self.export_statistics(data, str(file_path))
                elif data_type == "configuration":
                    result = self.export_configuration(data, str(file_path))
                else:
                    # 일반 데이터
                    result = self._export_general_data(data, str(file_path), name)

                result["dataset_name"] = name
                result["data_type"] = data_type
                results.append(result)

                if result["success"]:
                    total_exported += result.get("exported_count", 1)

            logger.info(f"일괄 JSON 내보내기 완료: {len(results)}개 파일")

            return {
                "success": True,
                "output_directory": str(output_path),
                "exported_files": len([r for r in results if r["success"]]),
                "failed_files": len([r for r in results if not r["success"]]),
                "total_exported_records": total_exported,
                "results": results,
            }

        except Exception as e:
            logger.error(f"일괄 JSON 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_files": 0}

    def _process_analysis_result(self, result: Dict[str, Any], include_raw_packets: bool) -> Dict[str, Any]:
        """분석 결과 처리"""
        processed = result.copy()

        # 원본 패킷 데이터 제거 옵션
        if not include_raw_packets and "packet_info" in processed:
            # 기본 정보만 유지
            packet_info = processed["packet_info"]
            processed["packet_info"] = {
                "src_ip": packet_info.get("src_ip"),
                "dst_ip": packet_info.get("dst_ip"),
                "src_port": packet_info.get("src_port"),
                "dst_port": packet_info.get("dst_port"),
                "protocol": packet_info.get("protocol"),
                "size": packet_info.get("size"),
                "timestamp": packet_info.get("timestamp"),
            }

        return processed

    def _generate_analysis_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """분석 결과 요약 생성"""
        from collections import Counter

        protocols = Counter()
        analysis_types = Counter()
        security_issues = Counter()
        anomalies = Counter()

        for result in analysis_results:
            # 프로토콜 통계
            packet_info = result.get("packet_info", {})
            protocol = packet_info.get("protocol")
            if protocol:
                protocols[protocol] += 1

            # 분석 타입 통계
            analysis_type = result.get("analysis_type")
            if analysis_type:
                analysis_types[analysis_type] += 1

            # 보안 이슈 통계
            for issue in result.get("security_issues", []):
                issue_type = issue.get("type", "unknown")
                security_issues[issue_type] += 1

            # 이상 징후 통계
            for anomaly in result.get("anomalies", []):
                anomaly_type = anomaly.get("type", "unknown")
                anomalies[anomaly_type] += 1

        return {
            "total_analyses": len(analysis_results),
            "protocol_distribution": dict(protocols),
            "analysis_type_distribution": dict(analysis_types),
            "security_issues_summary": dict(security_issues),
            "anomalies_summary": dict(anomalies),
            "summary_timestamp": datetime.now().isoformat(),
        }

    def _generate_charts_data(self, statistics: Dict[str, Any]) -> Dict[str, Any]:
        """차트 데이터 생성"""
        charts = {}

        try:
            # 프로토콜 분포 파이 차트 데이터
            if "protocol_distribution" in statistics:
                protocol_data = statistics["protocol_distribution"]
                charts["protocol_pie_chart"] = {
                    "type": "pie",
                    "title": "Protocol Distribution",
                    "data": [{"name": protocol, "value": count} for protocol, count in protocol_data.items()],
                }

            # 시간별 트래픽 라인 차트 데이터
            if "hourly_traffic" in statistics:
                hourly_data = statistics["hourly_traffic"]
                charts["hourly_traffic_line_chart"] = {
                    "type": "line",
                    "title": "Hourly Traffic",
                    "data": [{"time": hour, "packets": count} for hour, count in hourly_data.items()],
                }

            # 상위 IP 주소 바 차트 데이터
            if "top_src_ips" in statistics:
                top_ips = statistics["top_src_ips"][:10]
                charts["top_src_ips_bar_chart"] = {
                    "type": "bar",
                    "title": "Top Source IP Addresses",
                    "data": [{"ip": ip, "count": count} for ip, count in top_ips],
                }

        except Exception as e:
            logger.error(f"차트 데이터 생성 오류: {e}")

        return charts

    def _export_general_data(self, data: Any, output_path: str, name: str) -> Dict[str, Any]:
        """일반 데이터 내보내기"""
        try:
            json_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "dataset_name": name,
                    "exporter": "FortiGate Nextrade General Exporter",
                },
                "data": data,
            }

            if self.compress:
                output_path = self._ensure_gz_extension(output_path)
                with gzip.open(output_path, "wt", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )
                self.statistics["compressed_files"] += 1
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(
                        json_data,
                        f,
                        indent=self.indent,
                        ensure_ascii=self.ensure_ascii,
                        default=self._json_serializer,
                    )

            file_size = Path(output_path).stat().st_size

            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "exported_count": 1,
            }

        except Exception as e:
            logger.error(f"일반 데이터 내보내기 오류: {e}")
            return {"success": False, "error": str(e), "exported_count": 0}

    def _count_statistics_records(self, statistics: Dict[str, Any]) -> int:
        """통계 레코드 수 계산"""
        count = 0

        def count_items(obj):
            nonlocal count
            if isinstance(obj, dict):
                count += len(obj)
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        count_items(value)
            elif isinstance(obj, list):
                count += len(obj)
                for item in obj:
                    if isinstance(item, (dict, list)):
                        count_items(item)

        count_items(statistics)
        return count

    def _ensure_gz_extension(self, file_path: str) -> str:
        """gzip 확장자 보장"""
        if not file_path.endswith(".gz"):
            return f"{file_path}.gz"
        return file_path

    def _json_serializer(self, obj):
        """JSON 직렬화를 위한 커스텀 시리얼라이저"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            return obj.hex()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)

    def load_json_data(self, file_path: str) -> Dict[str, Any]:
        """JSON 파일에서 데이터 로드"""
        try:
            path = Path(file_path)

            if not path.exists():
                return {"success": False, "error": f"파일이 존재하지 않음: {file_path}"}

            # 압축 파일 여부 확인
            if file_path.endswith(".gz"):
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            return {
                "success": True,
                "data": data,
                "file_size": path.stat().st_size,
            }

        except Exception as e:
            logger.error(f"JSON 파일 로드 오류: {e}")
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """내보내기 통계 반환"""
        stats = self.statistics.copy()

        # 압축률 계산
        if stats["compressed_files"] > 0:
            stats["compression_ratio"] = stats["compressed_files"] / stats["exported_files"]
        else:
            stats["compression_ratio"] = 0.0

        return stats

    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            "exported_files": 0,
            "exported_records": 0,
            "compressed_files": 0,
            "total_size": 0,
            "last_export": None,
        }
        logger.info("JSON 내보내기 통계 초기화됨")


# 팩토리 함수
def create_json_exporter(
    indent: Optional[int] = 2,
    ensure_ascii: bool = False,
    compress: bool = False,
) -> JSONExporter:
    """JSON 내보내기 인스턴스 생성"""
    return JSONExporter(indent, ensure_ascii, compress)

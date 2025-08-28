#!/usr/bin/env python3

"""
데이터 변환 유틸리티
다양한 형식의 데이터를 정규화된 형식으로 변환합니다.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict


class DataTransformer:
    """데이터 변환 및 정규화 클래스"""

    def __init__(self):
        self.format_handlers = {
            "json": self._transform_json,
            "csv": self._transform_csv,
            "syslog": self._transform_syslog,
            "xml": self._transform_xml,
        }

    def transform(self, data: Any, input_format: str = "json") -> Dict[str, Any]:
        """
        데이터를 정규화된 형식으로 변환

        Args:
            data: 입력 데이터
            input_format: 입력 형식 (json, csv, syslog 등)

        Returns:
            정규화된 데이터 딕셔너리
        """
        handler = self.format_handlers.get(input_format, self._transform_json)
        return handler(data)

    def _transform_json(self, data: Any) -> Dict[str, Any]:
        """JSON 데이터 변환"""
        if isinstance(data, str):
            data = json.loads(data)

        # 필드 매핑
        normalized = {
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "src_ip": data.get("src", data.get("src_ip", "")),
            "dst_ip": data.get("dst", data.get("dst_ip", "")),
            "src_port": data.get("src_port", 0),
            "dst_port": data.get("dst_port", 0),
            "protocol": data.get("protocol", "unknown"),
            "action": data.get("action", ""),
            "length": data.get("length", 0),
        }

        return normalized

    def _transform_csv(self, data: str) -> Dict[str, Any]:
        """CSV 데이터 변환"""
        # 간단한 CSV 파싱 (실제로는 csv 모듈 사용)
        parts = data.strip().split(",")

        if len(parts) >= 6:
            return {
                "timestamp": parts[0],
                "src_ip": parts[1],
                "dst_ip": parts[2],
                "dst_port": int(parts[3]) if parts[3].isdigit() else 0,
                "protocol": parts[4],
                "action": parts[5],
            }

        return {}

    def _transform_syslog(self, data: str) -> Dict[str, Any]:
        """Syslog 형식 데이터 변환"""
        # Syslog 파싱 정규식
        pattern = r"SRC=(\d+\.\d+\.\d+\.\d+)\s+DST=(\d+\.\d+\.\d+\.\d+)"
        match = re.search(pattern, data)

        normalized = {
            "timestamp": datetime.now().isoformat(),
            "action": "accept" if "ACCEPT" in data else "drop",
        }

        if match:
            normalized["src_ip"] = match.group(1)
            normalized["dst_ip"] = match.group(2)

        return normalized

    def _transform_xml(self, data: str) -> Dict[str, Any]:
        """XML 데이터 변환 (간단한 구현)"""
        # 실제로는 xml.etree.ElementTree 사용
        return {
            "timestamp": datetime.now().isoformat(),
            "format": "xml",
            "data": str(data),
        }

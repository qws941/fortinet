#!/usr/bin/env python3
"""
Port Scanner Module
Handles port scanning functionality for security assessment
"""

import logging
import socket
from datetime import datetime
from typing import Dict, List

import psutil

logger = logging.getLogger(__name__)


class PortScannerMixin:
    """Mixin for port scanning functionality"""

    def scan_open_ports(self) -> Dict:
        """스캔 열린 포트"""
        try:
            logger.info("포트 스캔 시작")

            open_ports = []
            suspicious_ports = []

            # 네트워크 연결 확인
            connections = psutil.net_connections()

            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    port_info = {
                        "port": conn.laddr.port,
                        "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                        "process": self._get_process_name(conn.pid),
                    }

                    open_ports.append(port_info)

                    # 허용된 포트 목록과 비교
                    if hasattr(self, "security_baselines") and conn.laddr.port not in self.security_baselines.get(
                        "open_ports", []
                    ):
                        suspicious_ports.append(port_info)

            result = {
                "scan_type": "port_scan",
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "open_ports": open_ports,
                "total_open_ports": len(open_ports),
                "suspicious_ports": suspicious_ports,
                "risk_level": self._assess_port_risk(open_ports, suspicious_ports),
            }

            logger.info(f"포트 스캔 완료: {len(open_ports)}개 포트 발견")
            return result

        except Exception as e:
            logger.error(f"포트 스캔 오류: {e}")
            return {
                "scan_type": "port_scan",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "risk_level": "unknown",
            }

    def _get_process_name(self, pid) -> str:
        """PID로 프로세스 이름 가져오기"""
        try:
            if pid:
                process = psutil.Process(pid)
                return process.name()
            return "unknown"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "unknown"

    def _assess_port_risk(self, open_ports: List, suspicious_ports: List) -> str:
        """포트 위험도 평가"""
        if not open_ports:
            return "low"

        if len(suspicious_ports) > 5:
            return "critical"
        elif len(suspicious_ports) > 2:
            return "high"
        elif len(suspicious_ports) > 0:
            return "medium"
        else:
            return "low"

    def check_specific_port(self, port: int, host: str = "localhost") -> Dict:
        """특정 포트 연결 확인"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()

            is_open = result == 0

            return {
                "port": port,
                "host": host,
                "open": is_open,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "port": port,
                "host": host,
                "open": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def scan_port_range(self, start_port: int, end_port: int, host: str = "localhost") -> Dict:
        """포트 범위 스캔"""
        logger.info(f"포트 범위 스캔 시작: {start_port}-{end_port} @ {host}")

        open_ports = []
        closed_ports = []

        for port in range(start_port, end_port + 1):
            result = self.check_specific_port(port, host)
            if result["open"]:
                open_ports.append(port)
            else:
                closed_ports.append(port)

        return {
            "scan_type": "port_range_scan",
            "host": host,
            "port_range": f"{start_port}-{end_port}",
            "open_ports": open_ports,
            "closed_ports": closed_ports,
            "total_scanned": len(range(start_port, end_port + 1)),
            "total_open": len(open_ports),
            "timestamp": datetime.now().isoformat(),
        }

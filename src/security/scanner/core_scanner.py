#!/usr/bin/env python3
"""
Core Security Scanner Module
Main scanner orchestration and management
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

from .auto_fix import AutoFixMixin
from .file_integrity import FileIntegrityMixin
from .log_analyzer import LogAnalyzerMixin
from .network_scanner import NetworkScannerMixin
from .port_scanner import PortScannerMixin
from .vulnerability_detector import VulnerabilityDetectorMixin

logger = logging.getLogger(__name__)


class CoreSecurityScanner(
    PortScannerMixin,
    VulnerabilityDetectorMixin,
    FileIntegrityMixin,
    NetworkScannerMixin,
    LogAnalyzerMixin,
    AutoFixMixin,
):
    """보안 스캐너 및 취약점 관리 - 모듈러 아키텍처"""

    def __init__(self):
        self.is_scanning = False
        self.scan_thread = None
        self.scan_results = []
        self.vulnerability_database = {}
        self.security_policies = {}
        self.listeners = []

        # 스캔 설정
        self.scan_config = {
            "port_scan": True,
            "vulnerability_scan": True,
            "file_integrity_check": True,
            "network_scan": True,
            "docker_security_scan": True,
            "log_analysis": True,
        }

        # 보안 기준점
        self.security_baselines = {
            "open_ports": [22, 80, 443, 7777],  # 허용된 포트
            "critical_files": [
                "/etc/passwd",
                "/etc/shadow",
                "/etc/hosts",
                "/home/jclee/dev/fortinet/.env",
            ],
            "max_cpu_usage": 90.0,
            "max_memory_usage": 85.0,
            "min_disk_space_gb": 5.0,
        }

    def start_continuous_scan(self, interval_hours: int = 6):
        """지속적인 보안 스캔 시작"""
        if self.is_scanning:
            logger.warning("이미 스캔이 실행 중입니다")
            return

        self.is_scanning = True
        self.scan_thread = threading.Thread(
            target=self._continuous_scan_loop, args=(interval_hours,)
        )
        self.scan_thread.daemon = True
        self.scan_thread.start()
        logger.info(f"지속적인 보안 스캔 시작 ({interval_hours}시간 간격)")

    def stop_scanning(self):
        """스캔 중지"""
        self.is_scanning = False
        if self.scan_thread and self.scan_thread.is_alive():
            logger.info("스캔 중지 중...")
            # 스레드가 자연스럽게 종료될 때까지 대기

    def run_full_security_scan(self) -> Dict[str, Any]:
        """전체 보안 스캔 실행"""
        logger.info("전체 보안 스캔 시작")
        scan_start_time = datetime.now()

        scan_results = {
            "scan_id": f"scan_{int(scan_start_time.timestamp())}",
            "start_time": scan_start_time.isoformat(),
            "scan_config": self.scan_config.copy(),
            "results": {},
            "summary": {},
        }

        # 각 스캔 모듈 실행
        if self.scan_config.get("port_scan"):
            scan_results["results"]["port_scan"] = self.scan_open_ports()

        if self.scan_config.get("vulnerability_scan"):
            scan_results["results"]["vulnerability_scan"] = self.scan_vulnerabilities()

        if self.scan_config.get("file_integrity_check"):
            scan_results["results"]["file_integrity"] = self.check_file_integrity()

        if self.scan_config.get("network_scan"):
            scan_results["results"]["network_scan"] = self.scan_network_security()

        if self.scan_config.get("log_analysis"):
            scan_results["results"]["log_analysis"] = self.analyze_security_logs()

        # 스캔 완료 시간 기록
        scan_end_time = datetime.now()
        scan_results["end_time"] = scan_end_time.isoformat()
        scan_results["duration_seconds"] = (
            scan_end_time - scan_start_time
        ).total_seconds()

        # 요약 정보 생성
        scan_results["summary"] = self._generate_scan_summary(scan_results["results"])

        # 결과 저장
        self.scan_results.append(scan_results)

        # 리스너들에게 알림
        self._notify_listeners(scan_results)

        logger.info(f"전체 보안 스캔 완료 (\uc18c요시간: {scan_results['duration_seconds']:.2f}초)")
        return scan_results

    def get_security_dashboard(self) -> Dict:
        """보안 대시보드 데이터 반환"""
        latest_scan = self.scan_results[-1] if self.scan_results else None

        dashboard = {
            "status": "scanning" if self.is_scanning else "idle",
            "total_scans": len(self.scan_results),
            "latest_scan": latest_scan,
            "security_metrics": self._calculate_security_metrics(),
            "recommendations": self._get_security_recommendations(),
        }

        return dashboard

    def _continuous_scan_loop(self, interval_hours: int):
        """지속적인 스캔 루프"""
        while self.is_scanning:
            try:
                # 전체 스캔 실행
                scan_result = self.run_full_security_scan()

                # 자동 수정 실행 (옵션)
                if hasattr(self, "auto_fix_enabled") and self.auto_fix_enabled:
                    self.auto_fix_vulnerabilities(scan_result)

                # 지정된 시간만큼 대기
                for _ in range(interval_hours * 3600):  # 초 단위로 반복
                    if not self.is_scanning:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"지속적인 스캔 오류: {e}")
                time.sleep(300)  # 5분 대기 후 재시도

    def _generate_scan_summary(self, results: Dict) -> Dict:
        """스캔 결과 요약 생성"""
        summary = {
            "total_issues": 0,
            "risk_levels": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "categories": {},
            "recommendations": [],
        }

        # 각 스캔 결과에서 정보 추출
        for scan_type, result in results.items():
            if isinstance(result, dict):
                # 위험도 집계
                risk_level = result.get("risk_level", "unknown")
                if risk_level in summary["risk_levels"]:
                    summary["risk_levels"][risk_level] += 1

                # 이슈 개수 집계
                if "vulnerabilities" in result:
                    summary["total_issues"] += len(result["vulnerabilities"])
                elif "total_open_ports" in result:
                    summary["total_issues"] += result.get("suspicious_ports", 0)

        return summary

    def _calculate_security_metrics(self) -> Dict:
        """보안 메트릭 계산"""
        if not self.scan_results:
            return {"score": 0, "trend": "unknown"}

        latest_scan = self.scan_results[-1]
        total_issues = latest_scan.get("summary", {}).get("total_issues", 0)

        # 간단한 보안 점수 계산
        base_score = 100
        penalty = min(total_issues * 5, 90)  # 최대 90점 감점
        score = max(base_score - penalty, 10)  # 최소 10점

        # 트렌드 계산
        trend = "stable"
        if len(self.scan_results) >= 2:
            prev_issues = (
                self.scan_results[-2].get("summary", {}).get("total_issues", 0)
            )
            if total_issues > prev_issues:
                trend = "worsening"
            elif total_issues < prev_issues:
                trend = "improving"

        return {
            "score": score,
            "total_issues": total_issues,
            "trend": trend,
        }

    def _get_security_recommendations(self) -> List[str]:
        """보안 권장사항 생성"""
        recommendations = []

        if not self.scan_results:
            recommendations.append("첫 보안 스캔을 실행하세요")
            return recommendations

        latest_scan = self.scan_results[-1]
        results = latest_scan.get("results", {})

        # 포트 스캔 추천사항
        port_scan = results.get("port_scan", {})
        if port_scan.get("suspicious_ports"):
            recommendations.append("비인가된 열린 포트를 확인하고 필요없는 서비스를 중지하세요")

        # 취약점 추천사항
        vuln_scan = results.get("vulnerability_scan", {})
        if vuln_scan.get("total_vulnerabilities", 0) > 0:
            recommendations.append("발견된 취약점을 수정하세요")

        # 파일 무결성 추천사항
        file_integrity = results.get("file_integrity", {})
        if file_integrity.get("changed_files"):
            recommendations.append("중요 파일의 변경사항을 확인하세요")

        if not recommendations:
            recommendations.append("현재 보안 상태가 양호합니다")

        return recommendations

    def _notify_listeners(self, scan_results: Dict):
        """리스너들에게 스캔 결과 알림"""
        for listener in self.listeners:
            try:
                listener(scan_results)
            except Exception as e:
                logger.error(f"리스너 알림 오류: {e}")

    def add_listener(self, listener_func):
        """스캔 결과 리스너 추가"""
        self.listeners.append(listener_func)

    def remove_listener(self, listener_func):
        """리스너 제거"""
        if listener_func in self.listeners:
            self.listeners.remove(listener_func)

#!/usr/bin/env python3
"""
시스템 메트릭 수집기 - 실시간 시스템 리소스 모니터링
CLAUDE.md 지시사항에 따른 완전 자율적 시스템 모니터링
"""
import json
import logging
import os
import subprocess
import time
from collections import deque
from datetime import datetime
from typing import Dict, Optional

import psutil

from monitoring.base import HealthCheckMixin, MonitoringBase, ThresholdMixin
from monitoring.config import get_config

logger = logging.getLogger(__name__)


class SystemMetricsCollector(MonitoringBase, ThresholdMixin, HealthCheckMixin):
    """시스템 메트릭 실시간 수집기"""

    def __init__(self, collection_interval=None):
        """
        Args:
            collection_interval: 수집 간격 (초)
        """
        # 설정에서 기본값 가져오기
        config = get_config()
        if collection_interval is None:
            collection_interval = config.system_metrics.collection_interval

        super().__init__(
            name="system_metrics",
            collection_interval=collection_interval,
            max_history=config.system_metrics.max_history,
        )

        # 믹스인 초기화
        self.thresholds = {}
        self.threshold_violations = deque(maxlen=100)
        self.health_status = "unknown"
        self.health_details = {}

        # 임계값 설정
        for name, threshold_config in config.system_metrics.thresholds.items():
            self.set_threshold(name, threshold_config.warning, threshold_config.critical)

    def _collect_data(self) -> Optional[Dict]:
        """시스템 메트릭 데이터 수집"""
        try:
            metrics = {
                "system": self._get_system_info(),
                "cpu": self._get_cpu_metrics(),
                "memory": self._get_memory_metrics(),
                "disk": self._get_disk_metrics(),
                "network": self._get_network_metrics(),
                "processes": self._get_process_metrics(),
                "docker": self._get_docker_metrics(),
                "services": self._get_service_metrics(),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"메트릭 수집 실패: {e}")
            return None

    def _process_data(self, data: Dict) -> Optional[Dict]:
        """데이터 처리 및 임계값 체크"""
        try:
            processed = data.copy()

            # 임계값 체크
            cpu_usage = data.get("cpu", {}).get("usage_percent", 0)
            memory_usage = data.get("memory", {}).get("usage_percent", 0)
            disk_usage = data.get("disk", {}).get("usage_percent", 0)
            network_error_rate = data.get("network", {}).get("error_rate", 0)

            # 임계값 위반 체크 및 기록
            violations = []

            if self.check_threshold("cpu_usage", cpu_usage):
                violations.append(
                    {
                        "type": "cpu_usage",
                        "value": cpu_usage,
                        "severity": self.check_threshold("cpu_usage", cpu_usage),
                    }
                )

            if self.check_threshold("memory_usage", memory_usage):
                violations.append(
                    {
                        "type": "memory_usage",
                        "value": memory_usage,
                        "severity": self.check_threshold("memory_usage", memory_usage),
                    }
                )

            if self.check_threshold("disk_usage", disk_usage):
                violations.append(
                    {
                        "type": "disk_usage",
                        "value": disk_usage,
                        "severity": self.check_threshold("disk_usage", disk_usage),
                    }
                )

            if self.check_threshold("network_error_rate", network_error_rate):
                violations.append(
                    {
                        "type": "network_error_rate",
                        "value": network_error_rate,
                        "severity": self.check_threshold("network_error_rate", network_error_rate),
                    }
                )

            processed["threshold_violations"] = violations

            # 헬스 상태 업데이트
            if violations:
                critical_violations = [v for v in violations if v["severity"] == "critical"]
                if critical_violations:
                    self._update_health(
                        "critical",
                        {"critical_violations": critical_violations},
                    )
                else:
                    self._update_health("warning", {"violations": violations})
            else:
                self._update_health("healthy", {})

            return processed

        except Exception as e:
            self.logger.error(f"데이터 처리 실패: {e}")
            return data

    def _get_system_info(self) -> Dict:
        """시스템 정보"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            return {
                "hostname": os.uname().nodename,
                "platform": os.uname().sysname,
                "release": os.uname().release,
                "architecture": os.uname().machine,
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": int(uptime.total_seconds()),
                "load_average": (os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0]),
            }
        except Exception as e:
            logger.error(f"시스템 정보 수집 실패: {e}")
            return {}

    def _get_cpu_metrics(self) -> Dict:
        """CPU 메트릭 (성능 최적화: interval=None으로 빠른 측정)"""
        try:
            # 성능 최적화: interval=1 제거로 3초 단축
            cpu_percent = psutil.cpu_percent(interval=None)  # 빠른 측정
            cpu_times = psutil.cpu_times()
            psutil.cpu_count()

            return {
                "usage_percent": cpu_percent,
                "count_logical": psutil.cpu_count(logical=True),
                "count_physical": psutil.cpu_count(logical=False),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle,
                    "iowait": getattr(cpu_times, "iowait", 0),
                },
                "per_cpu": psutil.cpu_percent(percpu=True, interval=None),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            }
        except Exception as e:
            logger.error(f"CPU 메트릭 수집 실패: {e}")
            return {}

    def _get_memory_metrics(self) -> Dict:
        """메모리 메트릭"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            return {
                "usage_percent": memory.percent,
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "cached": getattr(memory, "cached", 0),
                "buffers": getattr(memory, "buffers", 0),
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
            }
        except Exception as e:
            logger.error(f"메모리 메트릭 수집 실패: {e}")
            return {}

    def _get_disk_metrics(self) -> Dict:
        """디스크 메트릭"""
        try:
            partitions = psutil.disk_partitions()
            disk_data = {}
            total_usage = 0
            partition_count = 0

            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_data[partition.device] = {
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    }

                    if usage.total > 0:  # 유효한 파티션만 포함
                        total_usage += usage.percent
                        partition_count += 1

                except (PermissionError, OSError):
                    continue

            # 디스크 I/O 통계
            disk_io = psutil.disk_io_counters()

            result = {
                "partitions": disk_data,
                "usage_percent": (total_usage / partition_count if partition_count > 0 else 0),
            }

            if disk_io:
                result["io"] = {
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time,
                }

            return result

        except Exception as e:
            logger.error(f"디스크 메트릭 수집 실패: {e}")
            return {}

    def _get_network_metrics(self) -> Dict:
        """네트워크 메트릭"""
        try:
            net_io = psutil.net_io_counters()
            net_connections = len(psutil.net_connections())

            # 인터페이스별 통계
            interfaces = {}
            for interface, stats in psutil.net_io_counters(pernic=True).items():
                interfaces[interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout,
                }

            result = {
                "total": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout,
                },
                "interfaces": interfaces,
                "connections_count": net_connections,
            }

            # 네트워크 오류율 계산
            total_packets = net_io.packets_sent + net_io.packets_recv
            total_errors = net_io.errin + net_io.errout
            result["error_rate"] = (total_errors / total_packets * 100) if total_packets > 0 else 0

            return result

        except Exception as e:
            logger.error(f"네트워크 메트릭 수집 실패: {e}")
            return {}

    def _get_process_metrics(self) -> Dict:
        """프로세스 메트릭"""
        try:
            processes = []
            total_processes = 0
            running_processes = 0

            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                try:
                    pinfo = proc.info
                    total_processes += 1

                    if pinfo["status"] == psutil.STATUS_RUNNING:
                        running_processes += 1

                    # 리소스 사용량이 높은 상위 프로세스만 저장
                    if pinfo["cpu_percent"] > 5 or pinfo["memory_percent"] > 5:
                        processes.append(pinfo)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # CPU와 메모리 사용량으로 정렬
            processes.sort(
                key=lambda x: x["cpu_percent"] + x["memory_percent"],
                reverse=True,
            )

            return {
                "total_count": total_processes,
                "running_count": running_processes,
                "high_usage_processes": processes[:10],  # 상위 10개만
            }

        except Exception as e:
            logger.error(f"프로세스 메트릭 수집 실패: {e}")
            return {}

    def _get_docker_metrics(self) -> Dict:
        """Docker 메트릭 (성능 최적화: timeout 단축)"""
        try:
            # 성능 최적화: timeout 10초 → 3초
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            container_stats = json.loads(line)
                            containers.append(
                                {
                                    "name": container_stats.get("Name", ""),
                                    "cpu_percent": container_stats.get("CPUPerc", "0%").rstrip("%"),
                                    "memory_usage": container_stats.get("MemUsage", ""),
                                    "memory_percent": container_stats.get("MemPerc", "0%").rstrip("%"),
                                    "network_io": container_stats.get("NetIO", ""),
                                    "block_io": container_stats.get("BlockIO", ""),
                                }
                            )
                        except json.JSONDecodeError:
                            continue

                return {
                    "containers": containers,
                    "total_containers": len(containers),
                }
            else:
                return {"error": "Docker not available or not running"}

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"error": "Docker command not found or timeout"}
        except Exception as e:
            logger.error(f"Docker 메트릭 수집 실패: {e}")
            return {}

    def _get_service_metrics(self) -> Dict:
        """시스템 서비스 메트릭"""
        try:
            # FortiGate Nextrade 서비스 상태 확인
            services = {
                "fortigate-nextrade": self._check_service_status("fortigate-nextrade"),
                "nginx": self._check_service_status("nginx"),
                "redis": self._check_service_status("redis"),
                "postgresql": self._check_service_status("postgresql"),
            }

            return services

        except Exception as e:
            logger.error(f"서비스 메트릭 수집 실패: {e}")
            return {}

    def _check_service_status(self, service_name: str) -> Dict:
        """개별 서비스 상태 확인 (성능 최적화: timeout 단축)"""
        try:
            # 성능 최적화: timeout 5초 → 2초
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=2,
            )

            status = result.stdout.strip()

            # 성능 최적화: systemctl show 생략 (느림)
            # 기본 정보만 제공
            return {
                "status": status,
                "active": status == "active",
                "main_pid": "0",
                "memory": "0",
                "restart_count": "0",
            }

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {
                "status": "unknown",
                "active": False,
                "main_pid": "0",
                "memory": "0",
                "restart_count": "0",
            }


# 전역 인스턴스 생성 함수 (통합 관리자와 연동)
def get_system_metrics_collector() -> SystemMetricsCollector:
    """시스템 메트릭 수집기 반환"""
    return SystemMetricsCollector()


if __name__ == "__main__":
    # 테스트 코드
    collector = SystemMetricsCollector()

    def test_listener(event_type, data):
        if event_type == "data_collected":
            metrics = data["data"]
            print(
                f"메트릭 수신: CPU {metrics.get('cpu', {}).get('usage_percent', 0)}%, "
                f"메모리 {metrics.get('memory', {}).get('usage_percent', 0)}%"
            )
            if metrics.get("threshold_violations"):
                print(f"임계값 위반: {len(metrics['threshold_violations'])}개")

    collector.add_listener(test_listener)
    collector.start()

    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("중단됨")

    collector.stop()
    print("테스트 완료")

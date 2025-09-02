#!/usr/bin/env python3
"""
통합 모니터링 설정 관리자
CLAUDE.md 지시사항에 따른 중앙화된 설정 관리 시스템
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThresholdConfig:
    """임계값 설정"""

    warning: float
    critical: float
    unit: str = ""
    description: str = ""


@dataclass
class SystemMetricsConfig:
    """시스템 메트릭 설정"""

    collection_interval: float = 5.0
    max_history: int = 1000
    thresholds: Dict[str, ThresholdConfig] = None

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = {
                "cpu_usage": ThresholdConfig(80.0, 95.0, "%", "CPU 사용률"),
                "memory_usage": ThresholdConfig(85.0, 95.0, "%", "메모리 사용률"),
                "disk_usage": ThresholdConfig(85.0, 95.0, "%", "디스크 사용률"),
                "network_error_rate": ThresholdConfig(1.0, 5.0, "%", "네트워크 오류율"),
                "load_average": ThresholdConfig(2.0, 4.0, "", "시스템 로드"),
            }


@dataclass
class APIPerformanceConfig:
    """API 성능 모니터링 설정"""

    collection_interval: float = 5.0
    max_history: int = 1000
    auto_optimization: bool = True
    thresholds: Dict[str, ThresholdConfig] = None

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = {
                "response_time_warning": ThresholdConfig(1000.0, 3000.0, "ms", "응답 시간"),
                "error_rate": ThresholdConfig(5.0, 10.0, "%", "오류율"),
                "throughput_min": ThresholdConfig(10.0, 5.0, "req/min", "최소 처리량"),
            }


@dataclass
class SecurityScanConfig:
    """보안 스캔 설정"""

    scan_interval: float = 3600.0  # 1시간
    max_history: int = 500
    auto_fix: bool = True
    scan_types: Dict[str, bool] = None

    def __post_init__(self):
        if self.scan_types is None:
            self.scan_types = {
                "port_scan": True,
                "vulnerability_scan": True,
                "file_integrity_check": True,
                "network_scan": True,
                "docker_security_scan": True,
                "log_analysis": True,
            }


@dataclass
class AutoRecoveryConfig:
    """자동 복구 설정"""

    check_interval: float = 30.0
    max_history: int = 1000
    enabled: bool = True
    recovery_rules: List[Dict] = None

    def __post_init__(self):
        if self.recovery_rules is None:
            self.recovery_rules = [
                {
                    "name": "high_cpu_usage",
                    "condition": {
                        "type": "threshold",
                        "metric": "cpu_usage",
                        "operator": ">",
                        "value": 90,
                    },
                    "action": {"type": "free_memory", "params": {}},
                    "cooldown": 300,
                },
                {
                    "name": "high_memory_usage",
                    "condition": {
                        "type": "threshold",
                        "metric": "memory_usage",
                        "operator": ">",
                        "value": 95,
                    },
                    "action": {"type": "free_memory", "params": {}},
                    "cooldown": 300,
                },
                {
                    "name": "application_unresponsive",
                    "condition": {
                        "type": "boolean",
                        "metric": "application.responsive",
                        "value": False,
                    },
                    "action": {
                        "type": "restart_container",
                        "params": {"container_name": "fortigate-nextrade"},
                    },
                    "cooldown": 600,
                },
            ]


@dataclass
class MonitoringConfig:
    """통합 모니터링 설정"""

    system_metrics: SystemMetricsConfig = None
    api_performance: APIPerformanceConfig = None
    security_scan: SecurityScanConfig = None
    auto_recovery: AutoRecoveryConfig = None

    # 글로벌 설정
    global_log_level: str = "INFO"
    data_retention_hours: int = 24
    export_enabled: bool = True
    export_interval: int = 3600  # 1시간
    websocket_enabled: bool = True

    def __post_init__(self):
        if self.system_metrics is None:
            self.system_metrics = SystemMetricsConfig()
        if self.api_performance is None:
            self.api_performance = APIPerformanceConfig()
        if self.security_scan is None:
            self.security_scan = SecurityScanConfig()
        if self.auto_recovery is None:
            self.auto_recovery = AutoRecoveryConfig()


class MonitoringConfigManager:
    """모니터링 설정 관리자"""

    def __init__(self, config_file: str = None):
        """
        Args:
            config_file: 설정 파일 경로 (기본값: data/monitoring_config.json)
        """
        if config_file is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            config_file = os.path.join(base_dir, "data", "monitoring_config.json")

        self.config_file = config_file
        self.config = MonitoringConfig()
        self._lock = RLock()
        self._watchers = []

        # 설정 로드
        self.load_config()

    def load_config(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                # JSON에서 설정 객체로 변환
                self.config = self._dict_to_config(config_data)
                logger.info(f"모니터링 설정 로드 완료: {self.config_file}")
                return True
            else:
                # 기본 설정으로 파일 생성
                self.save_config()
                logger.info(f"기본 모니터링 설정 파일 생성: {self.config_file}")
                return True

        except Exception as e:
            logger.error(f"모니터링 설정 로드 실패: {e}")
            # 기본 설정 사용
            self.config = MonitoringConfig()
            return False

    def save_config(self) -> bool:
        """설정을 파일에 저장"""
        try:
            with self._lock:
                # 디렉토리 생성
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

                # 설정을 딕셔너리로 변환
                config_dict = self._config_to_dict(self.config)

                # 메타데이터 추가
                config_dict["_metadata"] = {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "description": "FortiGate Nextrade 통합 모니터링 설정",
                }

                # 파일에 저장
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)

                logger.info(f"모니터링 설정 저장 완료: {self.config_file}")

                # 변경 알림
                self._notify_watchers("config_saved")
                return True

        except Exception as e:
            logger.error(f"모니터링 설정 저장 실패: {e}")
            return False

    def get_config(self) -> MonitoringConfig:
        """현재 설정 반환"""
        with self._lock:
            return self.config

    def update_config(self, new_config: MonitoringConfig) -> bool:
        """설정 업데이트"""
        try:
            with self._lock:
                old_config = self.config
                self.config = new_config

                # 파일에 저장
                if self.save_config():
                    # 변경 알림
                    self._notify_watchers(
                        "config_updated",
                        {"old_config": old_config, "new_config": new_config},
                    )
                    return True
                else:
                    # 저장 실패 시 롤백
                    self.config = old_config
                    return False

        except Exception as e:
            logger.error(f"모니터링 설정 업데이트 실패: {e}")
            return False

    def get_system_config(self) -> SystemMetricsConfig:
        """시스템 메트릭 설정 조회"""
        return self.config.system_metrics

    def get_api_config(self) -> APIPerformanceConfig:
        """API 성능 설정 조회"""
        return self.config.api_performance

    def get_security_config(self) -> SecurityScanConfig:
        """보안 스캔 설정 조회"""
        return self.config.security_scan

    def get_recovery_config(self) -> AutoRecoveryConfig:
        """자동 복구 설정 조회"""
        return self.config.auto_recovery

    def update_threshold(
        self, module: str, name: str, warning: float, critical: float
    ) -> bool:
        """임계값 업데이트"""
        try:
            with self._lock:
                if module == "system":
                    self.config.system_metrics.thresholds[name] = ThresholdConfig(
                        warning,
                        critical,
                        self.config.system_metrics.thresholds.get(
                            name, ThresholdConfig(0, 0)
                        ).unit,
                        self.config.system_metrics.thresholds.get(
                            name, ThresholdConfig(0, 0)
                        ).description,
                    )
                elif module == "api":
                    self.config.api_performance.thresholds[name] = ThresholdConfig(
                        warning,
                        critical,
                        self.config.api_performance.thresholds.get(
                            name, ThresholdConfig(0, 0)
                        ).unit,
                        self.config.api_performance.thresholds.get(
                            name, ThresholdConfig(0, 0)
                        ).description,
                    )
                else:
                    return False

                # 저장 및 알림
                success = self.save_config()
                if success:
                    self._notify_watchers(
                        "threshold_updated",
                        {
                            "module": module,
                            "name": name,
                            "warning": warning,
                            "critical": critical,
                        },
                    )
                return success

        except Exception as e:
            logger.error(f"임계값 업데이트 실패: {e}")
            return False

    def get_threshold(self, module: str, name: str) -> Optional[ThresholdConfig]:
        """임계값 조회"""
        try:
            if module == "system":
                return self.config.system_metrics.thresholds.get(name)
            elif module == "api":
                return self.config.api_performance.thresholds.get(name)
            return None
        except Exception:
            return None

    def add_config_watcher(self, callback):
        """설정 변경 감시자 추가"""
        if callback not in self._watchers:
            self._watchers.append(callback)

    def remove_config_watcher(self, callback):
        """설정 변경 감시자 제거"""
        if callback in self._watchers:
            self._watchers.remove(callback)

    def _notify_watchers(self, event_type: str, data: Dict = None):
        """설정 변경 감시자들에게 알림"""
        for watcher in self._watchers[:]:
            try:
                watcher(event_type, data or {})
            except Exception as e:
                logger.error(f"설정 감시자 호출 실패: {e}")
                self._watchers.remove(watcher)

    def _dict_to_config(self, data: Dict) -> MonitoringConfig:
        """딕셔너리를 설정 객체로 변환"""
        try:
            # 시스템 메트릭 설정
            system_data = data.get("system_metrics", {})
            system_thresholds = {}
            for name, thresh_data in system_data.get("thresholds", {}).items():
                system_thresholds[name] = ThresholdConfig(
                    thresh_data.get("warning", 0),
                    thresh_data.get("critical", 0),
                    thresh_data.get("unit", ""),
                    thresh_data.get("description", ""),
                )

            system_config = SystemMetricsConfig(
                collection_interval=system_data.get("collection_interval", 5.0),
                max_history=system_data.get("max_history", 1000),
                thresholds=system_thresholds if system_thresholds else None,
            )

            # API 성능 설정
            api_data = data.get("api_performance", {})
            api_thresholds = {}
            for name, thresh_data in api_data.get("thresholds", {}).items():
                api_thresholds[name] = ThresholdConfig(
                    thresh_data.get("warning", 0),
                    thresh_data.get("critical", 0),
                    thresh_data.get("unit", ""),
                    thresh_data.get("description", ""),
                )

            api_config = APIPerformanceConfig(
                collection_interval=api_data.get("collection_interval", 5.0),
                max_history=api_data.get("max_history", 1000),
                auto_optimization=api_data.get("auto_optimization", True),
                thresholds=api_thresholds if api_thresholds else None,
            )

            # 보안 스캔 설정
            security_data = data.get("security_scan", {})
            security_config = SecurityScanConfig(
                scan_interval=security_data.get("scan_interval", 3600.0),
                max_history=security_data.get("max_history", 500),
                auto_fix=security_data.get("auto_fix", True),
                scan_types=security_data.get("scan_types"),
            )

            # 자동 복구 설정
            recovery_data = data.get("auto_recovery", {})
            recovery_config = AutoRecoveryConfig(
                check_interval=recovery_data.get("check_interval", 30.0),
                max_history=recovery_data.get("max_history", 1000),
                enabled=recovery_data.get("enabled", True),
                recovery_rules=recovery_data.get("recovery_rules"),
            )

            # 통합 설정
            return MonitoringConfig(
                system_metrics=system_config,
                api_performance=api_config,
                security_scan=security_config,
                auto_recovery=recovery_config,
                global_log_level=data.get("global_log_level", "INFO"),
                data_retention_hours=data.get("data_retention_hours", 24),
                export_enabled=data.get("export_enabled", True),
                export_interval=data.get("export_interval", 3600),
                websocket_enabled=data.get("websocket_enabled", True),
            )

        except Exception as e:
            logger.error(f"설정 변환 실패: {e}")
            return MonitoringConfig()

    def _config_to_dict(self, config: MonitoringConfig) -> Dict:
        """설정 객체를 딕셔너리로 변환"""
        try:

            def threshold_to_dict(threshold: ThresholdConfig) -> Dict:
                return {
                    "warning": threshold.warning,
                    "critical": threshold.critical,
                    "unit": threshold.unit,
                    "description": threshold.description,
                }

            return {
                "system_metrics": {
                    "collection_interval": config.system_metrics.collection_interval,
                    "max_history": config.system_metrics.max_history,
                    "thresholds": {
                        name: threshold_to_dict(threshold)
                        for name, threshold in config.system_metrics.thresholds.items()
                    },
                },
                "api_performance": {
                    "collection_interval": config.api_performance.collection_interval,
                    "max_history": config.api_performance.max_history,
                    "auto_optimization": config.api_performance.auto_optimization,
                    "thresholds": {
                        name: threshold_to_dict(threshold)
                        for name, threshold in config.api_performance.thresholds.items()
                    },
                },
                "security_scan": {
                    "scan_interval": config.security_scan.scan_interval,
                    "max_history": config.security_scan.max_history,
                    "auto_fix": config.security_scan.auto_fix,
                    "scan_types": config.security_scan.scan_types,
                },
                "auto_recovery": {
                    "check_interval": config.auto_recovery.check_interval,
                    "max_history": config.auto_recovery.max_history,
                    "enabled": config.auto_recovery.enabled,
                    "recovery_rules": config.auto_recovery.recovery_rules,
                },
                "global_log_level": config.global_log_level,
                "data_retention_hours": config.data_retention_hours,
                "export_enabled": config.export_enabled,
                "export_interval": config.export_interval,
                "websocket_enabled": config.websocket_enabled,
            }

        except Exception as e:
            logger.error(f"설정 딕셔너리 변환 실패: {e}")
            return {}

    def reset_to_defaults(self) -> bool:
        """기본 설정으로 재설정"""
        try:
            with self._lock:
                self.config = MonitoringConfig()
                success = self.save_config()

                if success:
                    self._notify_watchers("config_reset")
                    logger.info("모니터링 설정이 기본값으로 재설정됨")

                return success

        except Exception as e:
            logger.error(f"설정 재설정 실패: {e}")
            return False

    def validate_config(self) -> List[str]:
        """설정 유효성 검사"""
        errors = []

        try:
            # 간격 검사
            if self.config.system_metrics.collection_interval <= 0:
                errors.append("시스템 메트릭 수집 간격은 0보다 커야 합니다")

            if self.config.api_performance.collection_interval <= 0:
                errors.append("API 성능 수집 간격은 0보다 커야 합니다")

            if self.config.security_scan.scan_interval <= 0:
                errors.append("보안 스캔 간격은 0보다 커야 합니다")

            if self.config.auto_recovery.check_interval <= 0:
                errors.append("자동 복구 체크 간격은 0보다 커야 합니다")

            # 히스토리 크기 검사
            for config_name, config_obj in [
                ("system_metrics", self.config.system_metrics),
                ("api_performance", self.config.api_performance),
                ("security_scan", self.config.security_scan),
                ("auto_recovery", self.config.auto_recovery),
            ]:
                if hasattr(config_obj, "max_history") and config_obj.max_history <= 0:
                    errors.append(f"{config_name} 최대 히스토리는 0보다 커야 합니다")

            # 임계값 검사
            for module_name, thresholds in [
                ("system_metrics", self.config.system_metrics.thresholds),
                ("api_performance", self.config.api_performance.thresholds),
            ]:
                for name, threshold in thresholds.items():
                    if threshold.warning >= threshold.critical:
                        errors.append(
                            f"{module_name}.{name}: 경고 임계값이 위험 임계값보다 크거나 같습니다"
                        )

        except Exception as e:
            errors.append(f"설정 검사 중 오류: {e}")

        return errors


# 전역 설정 관리자 인스턴스
_global_config_manager = None
_config_manager_lock = RLock()


def get_config_manager() -> MonitoringConfigManager:
    """전역 설정 관리자 반환"""
    global _global_config_manager
    with _config_manager_lock:
        if _global_config_manager is None:
            _global_config_manager = MonitoringConfigManager()
        return _global_config_manager


def get_config() -> MonitoringConfig:
    """현재 모니터링 설정 반환"""
    return get_config_manager().get_config()


def update_config(config: MonitoringConfig) -> bool:
    """모니터링 설정 업데이트"""
    return get_config_manager().update_config(config)


def get_threshold(module: str, name: str) -> Optional[ThresholdConfig]:
    """임계값 조회"""
    return get_config_manager().get_threshold(module, name)


def update_threshold(module: str, name: str, warning: float, critical: float) -> bool:
    """임계값 업데이트"""
    return get_config_manager().update_threshold(module, name, warning, critical)


if __name__ == "__main__":
    # 테스트 코드
    config_manager = MonitoringConfigManager()

    print("현재 설정:")
    config = config_manager.get_config()
    print(f"시스템 메트릭 간격: {config.system_metrics.collection_interval}")
    print(f"CPU 경고 임계값: {config.system_metrics.thresholds['cpu_usage'].warning}")

    # 임계값 업데이트 테스트
    print("\n임계값 업데이트 테스트...")
    success = config_manager.update_threshold("system", "cpu_usage", 75.0, 90.0)
    print(f"업데이트 성공: {success}")

    # 설정 검증 테스트
    print("\n설정 검증 테스트...")
    errors = config_manager.validate_config()
    if errors:
        print("설정 오류:")
        for error in errors:
            print(f"- {error}")
    else:
        print("설정이 유효합니다")
